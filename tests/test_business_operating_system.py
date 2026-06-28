import pytest
import pytest_asyncio
import json
from datetime import datetime, timedelta
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from src.main import app
from src.database import get_db, Base
from src.models import Business, Session as SessionModel, Worker, Task, Approval, EventStoreRecord
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

import os

# Isolated file-based test database URL to allow multi-connection concurrency in tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_bos.db"
test_engine = create_async_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

# Override AsyncSessionLocal inside src.database so that module executors connect to the test db
import src.database
src.database.AsyncSessionLocal = TestSessionLocal

async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

@pytest_asyncio.fixture(autouse=True)
async def setup_test_db():
    app.dependency_overrides[get_db] = override_get_db
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    app.dependency_overrides.pop(get_db, None)
    
    # Clean up test database file
    await test_engine.dispose()
    if os.path.exists("./test_bos.db"):
        try:
            os.remove("./test_bos.db")
        except Exception:
            pass

@pytest.mark.asyncio
async def test_worker_scheduling_and_auto_assignment():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Create Business
        biz_res = await ac.post("/api/v1/businesses", json={
            "name": "BOS Staffing Biz",
            "whatsapp_number": "+15551110000"
        })
        assert biz_res.status_code == 201
        biz_id = biz_res.json()["data"]["id"]

        # 2. Register Workers
        worker_a = await ac.post("/api/v1/workers", json={
            "business_id": biz_id,
            "name": "Stylist A",
            "role": "stylist",
            "specialization": "Haircut",
            "capacity": 15
        })
        assert worker_a.status_code == 201
        worker_a_id = worker_a.json()["data"]["id"]

        worker_b = await ac.post("/api/v1/workers", json={
            "business_id": biz_id,
            "name": "Stylist B",
            "role": "stylist",
            "specialization": "Coloring",
            "capacity": 10
        })
        assert worker_b.status_code == 201
        worker_b_id = worker_b.json()["data"]["id"]

        # Verify workers are listed
        list_workers = await ac.get(f"/api/v1/workers?business_id={biz_id}")
        assert len(list_workers.json()["data"]) == 2

        # 3. Register and active a workflow containing task assignment
        graph = {
            "business_id": biz_id,
            "version_number": 1,
            "entry_node_id": "node_greet",
            "nodes": {
                "node_greet": {
                    "id": "node_greet",
                    "module_name": "send_message",
                    "config": {
                        "text": "Welcome to our Salon!",
                        "next_node_id": "node_assign"
                    }
                },
                "node_assign": {
                    "id": "node_assign",
                    "module_name": "assign_task",
                    "config": {
                        "task_title": "Hair wash task for stylist",
                        "task_description": "Prepare customer wash station",
                        "priority": "HIGH"
                    },
                    "fsm_transition_to": "CONFIRMED"
                }
            },
            "edges": [
                {
                    "from_node": "node_greet",
                    "to_node": "node_assign",
                    "condition": {"type": "always"}
                }
            ],
            "fsm_transition_table": {
                "START": {
                    "CONFIRMED": "assign_task"
                }
            },
            "trigger_event": "/start",
            "trigger_events": ["/start"]
        }

        reg_res = await ac.post("/api/v1/workflows/register", json={
            "business_id": biz_id,
            "workflow_type": "static",
            "graph": graph
        })
        assert reg_res.status_code == 201, f"Registration failed: {reg_res.json()}"
        version_id = reg_res.json()["data"]["workflow_version_id"]

        # Compile and activate
        comp_res = await ac.post(f"/api/v1/workflows/compile/{version_id}")
        assert comp_res.status_code == 200, f"Compilation failed: {comp_res.json()}"
        
        act_res = await ac.post(f"/api/v1/workflows/activate/{version_id}")
        assert act_res.status_code == 200, f"Activation failed: {act_res.json()}"

        # Start Session
        sess_res = await ac.post("/api/v1/sessions", json={
            "business_id": biz_id,
            "customer_phone": "+15551110000"
        })
        assert sess_res.status_code == 201, f"Session start failed: {sess_res.json()}"
        session_id = sess_res.json()["data"]["id"]

        # Traversal - triggers greeting and auto task assignment
        dispatch_res = await ac.post(f"/api/v1/sessions/dispatch/{session_id}", json={
            "user_input": "/start"
        })
        assert dispatch_res.status_code == 200, f"Dispatch failed: {dispatch_res.json()}"
        
        # Verify a task was created in database
        tasks_res = await ac.get(f"/api/v1/tasks?business_id={biz_id}")
        assert tasks_res.status_code == 200
        tasks = tasks_res.json()["data"]
        assert len(tasks) == 1
        task = tasks[0]
        assert task["title"] == "Hair wash task for stylist"
        assert task["priority"] == "HIGH"
        assert task["status"] == "PENDING"
        # Auto-assignment selects the worker with lowest load (both were 0, so one is assigned)
        assert task["assigned_worker_id"] in {worker_a_id, worker_b_id}

        # Update task status manually
        update_res = await ac.put(f"/api/v1/tasks/{task['id']}", json={
            "status": "COMPLETED"
        })
        assert update_res.status_code == 200
        assert update_res.json()["data"]["status"] == "COMPLETED"
        assert update_res.json()["data"]["completed_at"] is not None

@pytest.mark.asyncio
async def test_human_approval_traversal_pausing_and_resuming():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create Business
        biz_res = await ac.post("/api/v1/businesses", json={
            "name": "BOS Approvals Biz",
            "whatsapp_number": "+15552220000"
        })
        biz_id = biz_res.json()["data"]["id"]

        # Register workflow with manager approval node
        graph = {
            "business_id": biz_id,
            "version_number": 1,
            "entry_node_id": "node_approval",
            "nodes": {
                "node_approval": {
                    "id": "node_approval",
                    "module_name": "request_approval",
                    "config": {
                        "request_type": "high_value_order",
                        "next_node_id": "node_confirm"
                    }
                },
                "node_confirm": {
                    "id": "node_confirm",
                    "module_name": "send_message",
                    "config": {
                        "text": "Manager approved! Thank you."
                    },
                    "fsm_transition_to": "CONFIRMED"
                }
            },
            "edges": [
                {
                    "from_node": "node_approval",
                    "to_node": "node_confirm",
                    "condition": {
                        "type": "input_equals",
                        "value": "APPROVE"
                    }
                }
            ],
            "fsm_transition_table": {
                "START": {
                    "CONFIRMED": "send_message"
                }
            },
            "trigger_event": "/start",
            "trigger_events": ["/start"]
        }

        reg_res = await ac.post("/api/v1/workflows/register", json={
            "business_id": biz_id,
            "workflow_type": "static",
            "graph": graph
        })
        assert reg_res.status_code == 201, f"Registration failed: {reg_res.json()}"
        version_id = reg_res.json()["data"]["workflow_version_id"]

        # Activate
        comp_res = await ac.post(f"/api/v1/workflows/compile/{version_id}")
        assert comp_res.status_code == 200, f"Compile failed: {comp_res.json()}"
        act_res = await ac.post(f"/api/v1/workflows/activate/{version_id}")
        assert act_res.status_code == 200, f"Activate failed: {act_res.json()}"

        # Start Session
        sess_res = await ac.post("/api/v1/sessions", json={
            "business_id": biz_id,
            "customer_phone": "+15552220000"
        })
        assert sess_res.status_code == 201, f"Session start failed: {sess_res.json()}"
        session_id = sess_res.json()["data"]["id"]

        # Traverse - triggers request_approval
        dispatch_res = await ac.post(f"/api/v1/sessions/dispatch/{session_id}", json={
            "user_input": "/start"
        })
        assert dispatch_res.status_code == 200, f"Dispatch failed: {dispatch_res.json()}"
        assert "manager approval" in dispatch_res.json()["data"]["messages_sent"][0]

        # Verify Approval record is in database
        app_res = await ac.get(f"/api/v1/approvals?business_id={biz_id}")
        assert app_res.status_code == 200
        approvals = app_res.json()["data"]
        assert len(approvals) == 1
        approval = approvals[0]
        assert approval["status"] == "PENDING"
        assert approval["request_type"] == "high_value_order"

        # Subsequent dispatch should be locked/intercepted and return pending warning
        blocked_res = await ac.post(f"/api/v1/sessions/dispatch/{session_id}", json={
            "user_input": "hello"
        })
        assert blocked_res.status_code == 200
        assert "pending approval" in blocked_res.json()["data"]["messages_sent"][0]

        # Approve the request manually via action route
        action_res = await ac.post(f"/api/v1/approvals/{approval['id']}/action", json={
            "action": "APPROVE",
            "resolved_by": "Manager Bob",
            "notes": "Looks good, proceed."
        })
        assert action_res.status_code == 200, f"Approval action failed: {action_res.json()}"
        action_data = action_res.json()["data"]
        assert action_data["status"] == "APPROVED"
        assert action_data["action_taken"] == "APPROVE"
        
        # Verify the traversal has successfully resumed and transitioned FSM state
        assert action_data["dispatch_response"]["fsm_state_after"] == "CONFIRMED"
        assert "Manager approved" in action_data["dispatch_response"]["messages_sent"][0]

@pytest.mark.asyncio
async def test_report_compilation_and_whatsapp_delivery():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create Business
        biz_res = await ac.post("/api/v1/businesses", json={
            "name": "BOS Reporting Biz",
            "whatsapp_number": "+15553330000"
        })
        biz_id = biz_res.json()["data"]["id"]

        # 1. Test manual generate report endpoint
        gen_res = await ac.post("/api/v1/reports/generate", json={
            "business_id": biz_id,
            "report_type": "Daily Orders Report"
        })
        assert gen_res.status_code == 200, f"Generate report failed: {gen_res.json()}"
        report = gen_res.json()["data"]
        assert "Daily Orders Report Summary" in report["content"]
        assert report["report_type"] == "Daily Orders Report"

        # 2. Verify report generated event was persisted in EventStore
        hist_res = await ac.get(f"/api/v1/reports/history?business_id={biz_id}")
        assert hist_res.status_code == 200
        history = hist_res.json()["data"]
        # History filter returns the generated report
        assert len(history) >= 1
        assert history[0]["report_type"] == "Daily Orders Report"

        # 3. Send report via WhatsApp simulator
        send_res = await ac.post("/api/v1/reports/send-whatsapp", json={
            "recipient_phone": "+15553334444",
            "report_content": report["content"]
        })
        assert send_res.status_code == 200, f"Send whatsapp failed: {send_res.json()}"
        assert send_res.json()["data"]["delivered"] is True

@pytest.mark.asyncio
async def test_report_filtering_by_business_type():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Create Business
        biz_res = await ac.post("/api/v1/businesses", json={
            "name": "BOS Hospital Biz",
            "whatsapp_number": "+15554440000"
        })
        assert biz_res.status_code == 201
        biz_id = biz_res.json()["data"]["id"]

        # 2. Update business type to 'hospital'
        up_res = await ac.put("/api/v1/business/config", json={
            "business_id": biz_id,
            "business_type": "hospital"
        })
        assert up_res.status_code == 200
        assert up_res.json()["data"]["business_type"] == "hospital"

        # 3. Attempt to generate an invalid report type for 'hospital' (e.g. 'Daily Orders Report')
        gen_fail = await ac.post("/api/v1/reports/generate", json={
            "business_id": biz_id,
            "report_type": "Daily Orders Report"
        })
        assert gen_fail.status_code == 400
        assert "not allowed for business type" in gen_fail.json()["error"]["message"]

        # 4. Generate a valid report type for 'hospital' ('Doctor Appointment Schedule')
        gen_pass = await ac.post("/api/v1/reports/generate", json={
            "business_id": biz_id,
            "report_type": "Doctor Appointment Schedule"
        })
        assert gen_pass.status_code == 200
        report = gen_pass.json()["data"]
        assert "Doctor" in report["content"]

        # 5. Verify history only contains the valid report type for 'hospital'
        hist_res = await ac.get(f"/api/v1/reports/history?business_id={biz_id}")
        assert hist_res.status_code == 200
        history = hist_res.json()["data"]
        assert len(history) == 1
        assert history[0]["report_type"] == "Doctor Appointment Schedule"

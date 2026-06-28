import pytest
import pytest_asyncio
import json
import datetime
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from src.main import app
from src.database import get_db, Base
from src.models import (
    Business, Employee, EmployeeAvailability, EmployeeCalendarAvailability,
    Task, Approval, CustomerOwnership, SLAConfig, SLATracking, AuditEvent,
    ReportSchedule
)
from src.services.auth import encode_jwt, hash_password
from src.services.assignment_engine import AssignmentEngine
from src.services.whatsapp_commands import WhatsAppCommandRouter
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import event
import os

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_bos.db"
test_engine = create_async_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})

@event.listens_for(test_engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()

TestSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

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
    await test_engine.dispose()
    if os.path.exists("./test_bos.db"):
        try:
            os.remove("./test_bos.db")
        except Exception:
            pass

@pytest.mark.asyncio
async def test_employee_lifecycle_and_rbac():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Create Business
        biz_res = await ac.post("/api/v1/businesses", json={
            "name": "Acme Med Spa",
            "whatsapp_number": "+12223334444"
        })
        assert biz_res.status_code == 201
        biz_id = biz_res.json()["data"]["id"]

        # 2. Register Employee as Owner (uses X-FlowCore-Role fallback header)
        headers_owner = {
            "X-FlowCore-Role": "owner",
            "X-FlowCore-Business-Id": biz_id,
            "X-FlowCore-Phone": "+919652778472",
            "X-FlowCore-Employee-Id": "owner_emp_id"
        }
        emp_res = await ac.post("/api/v1/employees", json={
            "name": "Dr. Alice Smith",
            "phone": "+15559090001",
            "role": "worker",
            "specialization": "Cardiology",
            "capacity": 8
        }, headers=headers_owner)
        assert emp_res.status_code == 201
        emp_data = emp_res.json()["data"]["employee"]
        temp_pass = emp_res.json()["data"]["temporary_password"]
        assert emp_data["name"] == "Dr. Alice Smith"
        assert emp_data["role"] == "worker"
        assert temp_pass is not None

        # Verify audit event is written
        async with TestSessionLocal() as session:
            aud_query = select(AuditEvent).where(AuditEvent.business_id == biz_id, AuditEvent.action == "EMPLOYEE_CREATED")
            aud_res = await session.execute(aud_query)
            audit = aud_res.scalar_one_or_none()
            assert audit is not None
            assert audit.entity_id == emp_data["id"]

        # 3. Log in as the new worker
        login_res = await ac.post("/api/v1/auth/login", json={
            "phone": "+15559090001",
            "password": temp_pass
        })
        assert login_res.status_code == 200
        tokens = login_res.json()["data"]["tokens"]
        access_token = tokens["access_token"]
        assert access_token is not None

        # 4. Enforce RBAC rules (Worker cannot create other employees)
        headers_worker = {
            "Authorization": f"Bearer {access_token}"
        }
        fail_res = await ac.post("/api/v1/employees", json={
            "name": "Dr. Bob",
            "phone": "+15559090002",
            "role": "worker"
        }, headers=headers_worker)
        # Forbidden since Dr. Alice is a worker
        assert fail_res.status_code == 403

        # 5. Owner resets password, suspends employee
        cred_res = await ac.post(f"/api/v1/employees/{emp_data['id']}/credentials/suspend", json={}, headers=headers_owner)
        assert cred_res.status_code == 200
        assert cred_res.json()["data"]["status"] == "SUSPENDED"

        # Log in should fail now
        login_fail = await ac.post("/api/v1/auth/login", json={
            "phone": "+15559090001",
            "password": temp_pass
        })
        assert login_fail.status_code == 401

@pytest.mark.asyncio
async def test_calendar_availability_and_assignment():
    async with TestSessionLocal() as session:
        # Create Business
        biz = Business(name="Staffing Biz", whatsapp_number="+15550001111")
        session.add(biz)
        await session.flush()

        # Create Employee
        emp = Employee(
            business_id=biz.id,
            name="Alice Barber",
            phone="+15559990001",
            role="worker",
            specialization="Haircut",
            capacity=10,
            status="ACTIVE",
            login_enabled=True
        )
        session.add(emp)
        await session.flush()

        # Define Standard Monday Availability (09:00 - 17:00)
        avail = EmployeeAvailability(
            employee_id=emp.id,
            day_of_week="Monday",
            start_time="09:00",
            end_time="17:00"
        )
        session.add(avail)
        await session.commit()

        # Test Case 1: Monday at 10:00 (within standard availability)
        due_monday_10 = datetime.datetime(2026, 6, 1, 10, 0, 0) # June 1, 2026 is Monday
        assigned = await AssignmentEngine.assign_task_to_employee(
            db=session,
            business_id=biz.id,
            due_time=due_monday_10
        )
        assert assigned is not None
        assert assigned.id == emp.id

        # Test Case 2: Monday at 18:00 (outside standard availability)
        due_monday_18 = datetime.datetime(2026, 6, 1, 18, 0, 0)
        assigned_outside = await AssignmentEngine.assign_task_to_employee(
            db=session,
            business_id=biz.id,
            due_time=due_monday_18
        )
        assert assigned_outside is None

        # Test Case 3: Monday at 10:00, but calendar override shows Sick Leave
        override = EmployeeCalendarAvailability(
            employee_id=emp.id,
            date=datetime.datetime(2026, 6, 1, 0, 0, 0),
            is_available=False,
            reason="Sick Leave"
        )
        session.add(override)
        await session.commit()

        assigned_sick = await AssignmentEngine.assign_task_to_employee(
            db=session,
            business_id=biz.id,
            due_time=due_monday_10
        )
        assert assigned_sick is None

@pytest.mark.asyncio
async def test_customer_ownership_and_sla_tracking():
    async with TestSessionLocal() as session:
        # Create Business & Workers
        biz = Business(name="Client Care Biz", whatsapp_number="+15559998888")
        session.add(biz)
        await session.flush()

        emp_primary = Employee(
            business_id=biz.id,
            name="Primary Coach",
            phone="+15551230001",
            role="worker",
            status="ACTIVE",
            login_enabled=True,
            capacity=10
        )
        emp_other = Employee(
            business_id=biz.id,
            name="Other Coach",
            phone="+15551230002",
            role="worker",
            status="ACTIVE",
            login_enabled=True,
            capacity=10
        )
        session.add_all([emp_primary, emp_other])
        await session.flush()

        # Customer Ownership mapping: customer +1234567890 owned by emp_primary
        ownership = CustomerOwnership(
            business_id=biz.id,
            customer_phone="+1234567890",
            assigned_employee_id=emp_primary.id
        )
        session.add(ownership)
        
        # Add SLA Config
        sla_cfg = SLAConfig(
            business_id=biz.id,
            trigger_event="CUSTOMER_BOOKING",
            warning_threshold_minutes=5,
            breach_threshold_minutes=15
        )
        session.add(sla_cfg)
        await session.commit()

        # Run Assignment Engine matching customer phone -> should prioritize owned employee
        assigned = await AssignmentEngine.assign_task_to_employee(
            db=session,
            business_id=biz.id,
            customer_phone="+1234567890"
        )
        assert assigned is not None
        assert assigned.id == emp_primary.id

        # PublishCUSTOMER_BOOKING event and test handlers
        from src.engine.events.event_bus import event_bus
        from src.engine.events.event_models import WorkflowEvent
        
        event = WorkflowEvent(
            session_id="sess_client_care_001",
            event_type="CUSTOMER_BOOKING",
            payload={
                "business_id": biz.id,
                "customer_phone": "+1234567890",
                "message_text": "Need to book coaching session"
            }
        )
        # Publish event
        await event_bus.publish(session, event)
        await session.commit()

        # Verify SLA Tracking record was created
        sla_query = select(SLATracking).where(SLATracking.business_id == biz.id)
        sla_res = await session.execute(sla_query)
        sla_rec = sla_res.scalar_one_or_none()
        assert sla_rec is not None
        assert sla_rec.sla_status == "SLA_MET"
        assert sla_rec.entity_type == "task"

@pytest.mark.asyncio
async def test_whatsapp_command_governance():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Initialize business and employee in DB
        async with TestSessionLocal() as session:
            biz = Business(name="Secure Command Biz", whatsapp_number="+15559876543")
            session.add(biz)
            await session.flush()

            emp = Employee(
                business_id=biz.id,
                name="Security Guard",
                phone="+15550007777",
                role="worker",
                status="ACTIVE",
                login_enabled=True,
                capacity=10
            )
            session.add(emp)
            await session.flush()

            # Create a critical task (High risk keyword: payment)
            task_critical = Task(
                business_id=biz.id,
                title="Approve critical payment refund",
                description="Needs review",
                priority="HIGH",
                assigned_employee_id=emp.id,
                status="PENDING"
            )
            # Create a regular task
            task_low = Task(
                business_id=biz.id,
                title="Clean up station",
                description="Routine chore",
                priority="LOW",
                assigned_employee_id=emp.id,
                status="PENDING"
            )
            session.add_all([task_critical, task_low])
            await session.commit()
            task_critical_id = task_critical.id
            task_low_id = task_low.id

        # 1. Execute regular task COMPLETE -> should complete immediately
        resp_low = await WhatsAppCommandRouter.handle_incoming_text(
            db=session,
            from_phone="+15550007777",
            text_message=f"COMPLETE {task_low_id}"
        )
        assert "completed successfully" in resp_low

        async with TestSessionLocal() as session:
            task_check = await session.get(Task, task_low_id)
            assert task_check.status == "COMPLETED"

        # 2. Execute critical task COMPLETE -> should create an approval record
        resp_high = await WhatsAppCommandRouter.handle_incoming_text(
            db=session,
            from_phone="+15550007777",
            text_message=f"COMPLETE {task_critical_id}"
        )
        assert "requires manager approval" in resp_high

        async with TestSessionLocal() as session:
            # Task status should still be PENDING
            task_check_crit = await session.get(Task, task_critical_id)
            assert task_check_crit.status == "PENDING"

            # Approval record should be created
            app_query = select(Approval).where(Approval.business_id == biz.id, Approval.status == "PENDING")
            app_res = await session.execute(app_query)
            approval = app_res.scalar_one_or_none()
            assert approval is not None
            approval_id = approval.id

        # 3. Manager approves it via route
        headers_owner = {
            "X-FlowCore-Role": "owner",
            "X-FlowCore-Business-Id": biz.id,
            "X-FlowCore-Phone": "+919652778472"
        }
        act_res = await ac.post(f"/api/v1/approvals/{approval_id}/action", json={
            "action": "APPROVE",
            "notes": "Looks safe to execute",
            "resolved_by": "Manager Mode"
        }, headers=headers_owner)
        assert act_res.status_code == 200

        # Verify task is now completed
        async with TestSessionLocal() as session:
            task_check_crit_2 = await session.get(Task, task_critical_id)
            assert task_check_crit_2.status == "COMPLETED"

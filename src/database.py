import contextvars
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, sessionmaker

db_session_context: contextvars.ContextVar[Optional[AsyncSession]] = contextvars.ContextVar("db_session_context", default=None)


from src.config import settings

# Enforce check_same_thread=False for SQLite
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_async_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db() -> None:
    async with engine.begin() as conn:
        # Import models inside to ensure they are registered with Base
        from src.models import (
            Business, WorkflowVersion, Session, ExecutionLog, CompiledGraph, 
            ModuleRegistryModel, ExecutionSnapshot, ExecutionJournal, 
            ExternalOperation, EventStoreRecord, ExecutionMetric, SharedCustomerContext,
            Department, Employee, EmployeeAvailability, EmployeeCalendarAvailability,
            EmployeePerformance, EmployeeShift, EmployeeNotification, CustomerOwnership,
            SLAConfig, SLATracking, AutomationRule, ConversationLog, NotificationPreference,
            UserBusinessAccess, BusinessEvent, AuditEvent, Notification, ReportSchedule,
            AggregatedMetrics, Task, Approval, GenerationBenchmark
        )
        await conn.run_sync(Base.metadata.create_all)

        # SQLite self-healing dynamic schema migrations
        def upgrade_schema(connection):
            # 1. Upgrade businesses table columns
            dbapi_conn = connection.connection
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA table_info(businesses)")
            cols = [row[1] for row in cursor.fetchall()]
            if "business_type" not in cols:
                cursor.execute("ALTER TABLE businesses ADD COLUMN business_type VARCHAR(50) DEFAULT 'restaurant' NOT NULL")
            if "branding_json" not in cols:
                cursor.execute("ALTER TABLE businesses ADD COLUMN branding_json TEXT DEFAULT '{}' NOT NULL")
            if "providers_json" not in cols:
                cursor.execute("ALTER TABLE businesses ADD COLUMN providers_json TEXT DEFAULT '{}' NOT NULL")

            # 2. Upgrade event_store table columns
            cursor.execute("PRAGMA table_info(event_store)")
            cols = [row[1] for row in cursor.fetchall()]
            if "business_id" not in cols:
                cursor.execute("ALTER TABLE event_store ADD COLUMN business_id VARCHAR(36)")
            if "workflow_version_id" not in cols:
                cursor.execute("ALTER TABLE event_store ADD COLUMN workflow_version_id VARCHAR(36)")
            if "customer_id" not in cols:
                cursor.execute("ALTER TABLE event_store ADD COLUMN customer_id VARCHAR(50)")

            # 3. Upgrade tasks table columns
            cursor.execute("PRAGMA table_info(tasks)")
            cols = [row[1] for row in cursor.fetchall()]
            if cols and "assigned_employee_id" not in cols:
                if "assigned_worker_id" in cols:
                    cursor.execute("ALTER TABLE tasks RENAME COLUMN assigned_worker_id TO assigned_employee_id")
                else:
                    cursor.execute("ALTER TABLE tasks ADD COLUMN assigned_employee_id VARCHAR(36)")

            # 4. Upgrade workflow_versions table columns
            cursor.execute("PRAGMA table_info(workflow_versions)")
            cols = [row[1] for row in cursor.fetchall()]
            if "prompt_version" not in cols:
                cursor.execute("ALTER TABLE workflow_versions ADD COLUMN prompt_version VARCHAR(50)")
            if "model_name" not in cols:
                cursor.execute("ALTER TABLE workflow_versions ADD COLUMN model_name VARCHAR(100)")
            if "generation_time" not in cols:
                cursor.execute("ALTER TABLE workflow_versions ADD COLUMN generation_time FLOAT")
            if "validation_result" not in cols:
                cursor.execute("ALTER TABLE workflow_versions ADD COLUMN validation_result TEXT")

            # 5. Create generation_benchmarks table if not exists (SQLite statement)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS generation_benchmarks (
                    id VARCHAR(36) PRIMARY KEY,
                    business_type VARCHAR(50) NOT NULL,
                    input_description TEXT NOT NULL,
                    raw_output TEXT,
                    parsed_draft_json TEXT,
                    is_valid BOOLEAN NOT NULL DEFAULT 0,
                    validation_errors TEXT,
                    created_at DATETIME NOT NULL
                )
                """
            )

        await conn.run_sync(upgrade_schema)

    # Seed the 5 slug-based dev workspaces (idempotent)
    if ":memory:" not in settings.DATABASE_URL:
        from src.models import (
            Business, Employee, Task, Approval, SharedCustomerContext,
            WorkflowVersion, CompiledGraph
        )
        from src.services.ai_generator import AIGenerator
        from src.schemas.graph import WorkflowGraph
        from src.engine.compiler import WorkflowCompiler
        import json
        from sqlalchemy import select

        # ── 1. Business definitions ───────────────────────────────────────────
        DEV_WORKSPACES = [
            # Keep legacy Pizza Planet UUID for backward compat
            {
                "id": "e216b183-8c91-4a56-b819-50ebfb3f8a45",
                "name": "Pizza Planet (Legacy)",
                "whatsapp_number": "+919652778472",
                "business_type": "restaurant",
                "meta_phone_number_id": "10928374928",
            },
            {
                "id": "restaurant_test",
                "name": "Pizza Planet",
                "whatsapp_number": "+10000000001",
                "business_type": "restaurant",
                "meta_phone_number_id": "10928374901",
            },
            {
                "id": "hospital_test",
                "name": "City Hospital",
                "whatsapp_number": "+10000000002",
                "business_type": "hospital",
                "meta_phone_number_id": "10928374902",
            },
            {
                "id": "salon_test",
                "name": "Elite Salon",
                "whatsapp_number": "+10000000003",
                "business_type": "salon",
                "meta_phone_number_id": "10928374903",
            },
            {
                "id": "supermarket_test",
                "name": "SuperMart",
                "whatsapp_number": "+10000000004",
                "business_type": "supermarket",
                "meta_phone_number_id": "10928374904",
            },
            {
                "id": "education_test",
                "name": "Education Academy",
                "whatsapp_number": "+10000000005",
                "business_type": "education",
                "meta_phone_number_id": "10928374905",
            },
        ]

        async with AsyncSessionLocal() as session:
            for biz_data in DEV_WORKSPACES:
                res = await session.execute(select(Business).where(Business.id == biz_data["id"]))
                if not res.scalar_one_or_none():
                    session.add(Business(**biz_data))
            await session.commit()

        # ── 2. Per-business demo data ─────────────────────────────────────────
        DEMO_DATA = {
            "restaurant_test": {
                "employees": [
                    {"id": "rst-emp-001", "name": "Marco Rossi", "phone": "+10000100001", "role": "manager", "specialization": "Kitchen Operations"},
                    {"id": "rst-emp-002", "name": "Lena Kim", "phone": "+10000100002", "role": "worker", "specialization": "Front of House"},
                    {"id": "rst-emp-003", "name": "James Cook", "phone": "+10000100003", "role": "worker", "specialization": "Delivery"},
                ],
                "tasks": [
                    {"id": "rst-task-001", "title": "Prepare Table 4 for party of 8", "priority": "HIGH", "status": "PENDING", "emp": "rst-emp-002"},
                    {"id": "rst-task-002", "title": "Process Order #1021 — Margherita x2", "priority": "CRITICAL", "status": "IN_PROGRESS", "emp": "rst-emp-003"},
                    {"id": "rst-task-003", "title": "End-of-day stock count", "priority": "MEDIUM", "status": "PENDING", "emp": "rst-emp-001"},
                    {"id": "rst-task-004", "title": "Update weekly menu specials", "priority": "LOW", "status": "COMPLETED", "emp": "rst-emp-001"},
                ],
                "approvals": [
                    {"id": "rst-appr-001", "request_type": "large_order", "status": "PENDING", "details": {"order_value": 250, "items": 12, "note": "Corporate lunch order"}},
                    {"id": "rst-appr-002", "request_type": "general", "status": "APPROVED", "details": {"note": "Staff overtime approval for weekend shift"}},
                ],
                "customers": ["+10000900001", "+10000900002", "+10000900003"],
                "category": "restaurant",
                "description": "A pizza restaurant that takes orders and manages deliveries via WhatsApp",
            },
            "hospital_test": {
                "employees": [
                    {"id": "hsp-emp-001", "name": "Dr. Priya Patel", "phone": "+10000200001", "role": "manager", "specialization": "Internal Medicine"},
                    {"id": "hsp-emp-002", "name": "Nurse Anna Melo", "phone": "+10000200002", "role": "worker", "specialization": "Ward Care"},
                    {"id": "hsp-emp-003", "name": "Sam Nair", "phone": "+10000200003", "role": "worker", "specialization": "Reception"},
                ],
                "tasks": [
                    {"id": "hsp-task-001", "title": "Schedule Dr. Patel's OPD appointments", "priority": "HIGH", "status": "PENDING", "emp": "hsp-emp-003"},
                    {"id": "hsp-task-002", "title": "Process lab report — Patient #H0042", "priority": "CRITICAL", "status": "IN_PROGRESS", "emp": "hsp-emp-002"},
                    {"id": "hsp-task-003", "title": "Patient discharge clearance — Room 304", "priority": "HIGH", "status": "PENDING", "emp": "hsp-emp-001"},
                    {"id": "hsp-task-004", "title": "Update pharmacy stock levels", "priority": "MEDIUM", "status": "COMPLETED", "emp": "hsp-emp-002"},
                ],
                "approvals": [
                    {"id": "hsp-appr-001", "request_type": "appointment_request", "status": "PENDING", "details": {"patient": "Ravi Kumar", "type": "Specialist Visit", "urgency": "High"}},
                    {"id": "hsp-appr-002", "request_type": "general", "status": "APPROVED", "details": {"note": "Emergency surgery approval — Room 201"}},
                ],
                "customers": ["+10000901001", "+10000901002", "+10000901003"],
                "category": "hospital",
                "description": "A hospital that manages patient appointments, consultations, and admissions via WhatsApp",
            },
            "salon_test": {
                "employees": [
                    {"id": "sln-emp-001", "name": "Aria Styles", "phone": "+10000300001", "role": "manager", "specialization": "Color Specialist"},
                    {"id": "sln-emp-002", "name": "Tom Barber", "phone": "+10000300002", "role": "worker", "specialization": "Haircut & Styling"},
                    {"id": "sln-emp-003", "name": "Mia Spa", "phone": "+10000300003", "role": "worker", "specialization": "Massage & Spa"},
                ],
                "tasks": [
                    {"id": "sln-task-001", "title": "Set up styling station for morning appointments", "priority": "MEDIUM", "status": "PENDING", "emp": "sln-emp-002"},
                    {"id": "sln-task-002", "title": "Process client refund — Booking #SL-204", "priority": "HIGH", "status": "IN_PROGRESS", "emp": "sln-emp-001"},
                    {"id": "sln-task-003", "title": "Restock product shelf — Shampoo & Conditioners", "priority": "LOW", "status": "PENDING", "emp": "sln-emp-003"},
                    {"id": "sln-task-004", "title": "Confirm tomorrow's appointment slots", "priority": "MEDIUM", "status": "COMPLETED", "emp": "sln-emp-001"},
                ],
                "approvals": [
                    {"id": "sln-appr-001", "request_type": "appointment_request", "status": "PENDING", "details": {"client": "Sarah M.", "service": "Bridal Package", "duration_hrs": 3}},
                    {"id": "sln-appr-002", "request_type": "general", "status": "APPROVED", "details": {"note": "Staff leave approval — Aria Styles, June 10"}},
                ],
                "customers": ["+10000902001", "+10000902002", "+10000902003"],
                "category": "salon",
                "description": "A beauty salon and spa that manages bookings and client services via WhatsApp",
            },
            "supermarket_test": {
                "employees": [
                    {"id": "mkt-emp-001", "name": "Raj Sharma", "phone": "+10000400001", "role": "manager", "specialization": "Store Operations"},
                    {"id": "mkt-emp-002", "name": "Lisa Chen", "phone": "+10000400002", "role": "worker", "specialization": "Inventory"},
                    {"id": "mkt-emp-003", "name": "Carlos M.", "phone": "+10000400003", "role": "worker", "specialization": "Delivery"},
                ],
                "tasks": [
                    {"id": "mkt-task-001", "title": "Restock aisle 3 — Dairy & Eggs", "priority": "HIGH", "status": "PENDING", "emp": "mkt-emp-002"},
                    {"id": "mkt-task-002", "title": "Process supplier invoice — Fresh Farms Ltd", "priority": "MEDIUM", "status": "IN_PROGRESS", "emp": "mkt-emp-001"},
                    {"id": "mkt-task-003", "title": "Weekly inventory audit — Produce section", "priority": "HIGH", "status": "PENDING", "emp": "mkt-emp-002"},
                    {"id": "mkt-task-004", "title": "Arrange home delivery — Order #SM-5510", "priority": "CRITICAL", "status": "IN_PROGRESS", "emp": "mkt-emp-003"},
                ],
                "approvals": [
                    {"id": "mkt-appr-001", "request_type": "large_order", "status": "PENDING", "details": {"order_value": 1800, "items": 65, "note": "Bulk institutional order"}},
                    {"id": "mkt-appr-002", "request_type": "general", "status": "APPROVED", "details": {"note": "Supplier credit limit increase — Fresh Farms"}},
                ],
                "customers": ["+10000903001", "+10000903002", "+10000903003"],
                "category": "supermarket",
                "description": "A supermarket handling orders, home delivery, and inventory management via WhatsApp",
            },
            "education_test": {
                "employees": [
                    {"id": "edu-emp-001", "name": "Prof. Alan Grant", "phone": "+10000500001", "role": "manager", "specialization": "Curriculum"},
                    {"id": "edu-emp-002", "name": "Ms. Tara Singh", "phone": "+10000500002", "role": "worker", "specialization": "Admissions"},
                    {"id": "edu-emp-003", "name": "Mr. Ben Foster", "phone": "+10000500003", "role": "worker", "specialization": "Student Support"},
                ],
                "tasks": [
                    {"id": "edu-task-001", "title": "Grade final assignments — Batch 2026-A", "priority": "HIGH", "status": "IN_PROGRESS", "emp": "edu-emp-001"},
                    {"id": "edu-task-002", "title": "Send enrollment confirmation to 12 students", "priority": "MEDIUM", "status": "PENDING", "emp": "edu-emp-002"},
                    {"id": "edu-task-003", "title": "Schedule parent-teacher meeting — June 12", "priority": "HIGH", "status": "PENDING", "emp": "edu-emp-003"},
                    {"id": "edu-task-004", "title": "Update course material — Module 4", "priority": "LOW", "status": "COMPLETED", "emp": "edu-emp-001"},
                ],
                "approvals": [
                    {"id": "edu-appr-001", "request_type": "general", "status": "PENDING", "details": {"student": "Arjun Nair", "request": "Fee Waiver — Financial Hardship"}},
                    {"id": "edu-appr-002", "request_type": "general", "status": "APPROVED", "details": {"note": "Course schedule change approved — Module 3 to July"}},
                ],
                "customers": ["+10000904001", "+10000904002", "+10000904003"],
                "category": "education",
                "description": "An education academy managing enrollments, course bookings, and student support via WhatsApp",
            },
        }

        async with AsyncSessionLocal() as session:
            for biz_id, data in DEMO_DATA.items():
                # ── Employees ────────────────────────────────────────────────
                for emp_data in data["employees"]:
                    emp_res = await session.execute(select(Employee).where(Employee.id == emp_data["id"]))
                    if not emp_res.scalar_one_or_none():
                        session.add(Employee(
                            id=emp_data["id"],
                            business_id=biz_id,
                            name=emp_data["name"],
                            phone=emp_data["phone"],
                            role=emp_data["role"],
                            specialization=emp_data["specialization"],
                            status="ACTIVE",
                        ))

                # ── Tasks ────────────────────────────────────────────────────
                for t in data["tasks"]:
                    t_res = await session.execute(select(Task).where(Task.id == t["id"]))
                    if not t_res.scalar_one_or_none():
                        session.add(Task(
                            id=t["id"],
                            business_id=biz_id,
                            title=t["title"],
                            priority=t["priority"],
                            status=t["status"],
                            assigned_employee_id=t["emp"],
                        ))

                # ── Approvals ────────────────────────────────────────────────
                for a in data["approvals"]:
                    a_res = await session.execute(select(Approval).where(Approval.id == a["id"]))
                    if not a_res.scalar_one_or_none():
                        # Approvals require a session_id (FK). Use a placeholder sentinel session.
                        # We skip creating full sessions; set session_id to the approval id itself
                        # and rely on SET NULL / no cascade here.
                        # Actually Approval.session_id is FK with CASCADE — use None-safe workaround:
                        # Store a fake session-like id as a string but skip FK enforcement in SQLite
                        # by just using a raw insert via text if needed. Simpler: create a dummy session.
                        # For seed data cleanliness, we mark session_id as the approval id string itself
                        # but we need a valid sessions.id. Skip and store session_id = None won't work
                        # because it's NOT NULL. We'll use a well-known sentinel:
                        pass  # handled below via raw approach

                # ── Customers ────────────────────────────────────────────────
                for phone in data["customers"]:
                    c_res = await session.execute(
                        select(SharedCustomerContext).where(
                            SharedCustomerContext.customer_id == phone,
                            SharedCustomerContext.business_id == biz_id,
                        )
                    )
                    if not c_res.scalar_one_or_none():
                        session.add(SharedCustomerContext(
                            customer_id=phone,
                            business_id=biz_id,
                            loyalty_points=10,
                        ))

            await session.commit()

        # ── Approvals (raw approach to avoid session FK) ─────────────────────
        # Create a sentinel WorkflowVersion + Session per business, then seed approvals
        from src.models import Session as SessionModel
        async with AsyncSessionLocal() as session:
            for biz_id, data in DEMO_DATA.items():
                # Ensure a sentinel workflow version exists
                wv_id = f"{biz_id}-seed-wv"
                wv_res = await session.execute(select(WorkflowVersion).where(WorkflowVersion.id == wv_id))
                if not wv_res.scalar_one_or_none():
                    session.add(WorkflowVersion(
                        id=wv_id,
                        business_id=biz_id,
                        version_number=1,
                        status="APPROVED",
                        workflow_type="dynamic",
                        graph_json=json.dumps({"entry_node_id": "node_menu", "nodes": {}, "edges": [], "fsm_transition_table": {}}),
                        is_current=True,
                    ))
                    await session.flush()

                # Ensure a sentinel session exists
                sess_id = f"{biz_id}-seed-sess"
                s_res = await session.execute(select(SessionModel).where(SessionModel.id == sess_id))
                if not s_res.scalar_one_or_none():
                    session.add(SessionModel(
                        id=sess_id,
                        business_id=biz_id,
                        customer_phone="+10000000099",
                        fsm_state="CONFIRMED",
                        carry_unit_json=json.dumps({}),
                        workflow_version_id=wv_id,
                    ))
                    await session.flush()

                # Now seed approvals using the sentinel session
                for a in data["approvals"]:
                    a_res = await session.execute(select(Approval).where(Approval.id == a["id"]))
                    if not a_res.scalar_one_or_none():
                        session.add(Approval(
                            id=a["id"],
                            business_id=biz_id,
                            session_id=sess_id,
                            node_id="seed_node",
                            request_type=a["request_type"],
                            status=a["status"],
                            details_json=json.dumps(a["details"]),
                        ))

            await session.commit()

        # ── Workflows: generate + register one active workflow per business ──
        async with AsyncSessionLocal() as session:
            for biz_id, data in DEMO_DATA.items():
                # Check if an active workflow already exists
                wv_res = await session.execute(
                    select(WorkflowVersion).where(
                        WorkflowVersion.business_id == biz_id,
                        WorkflowVersion.is_current == True,
                        WorkflowVersion.status == "ACTIVE",
                    )
                )
                existing_active = wv_res.scalars().first()
                if existing_active:
                    continue  # already has an active workflow

                try:
                    result = await AIGenerator.generate_portfolio(
                        db_session=session,
                        business_id=biz_id,
                        description=data["description"],
                        capability_packs=[data["category"]],
                        use_mock_ai=True,
                    )
                    if result.get("success"):
                        workflows = result.get("workflows") or {}
                        first = True
                        for name, graph_dict in workflows.items():
                            try:
                                graph_dict["business_id"] = biz_id
                                graph_obj = WorkflowGraph.model_validate(graph_dict)
                                compiled, report = WorkflowCompiler.validate_and_compile(graph_obj)

                                ver_q = select(WorkflowVersion).where(
                                    WorkflowVersion.business_id == biz_id
                                ).order_by(WorkflowVersion.version_number.desc())
                                ver_r = await session.execute(ver_q)
                                last = ver_r.scalars().first()
                                new_ver = (last.version_number + 1) if last else 1

                                wv = WorkflowVersion(
                                    business_id=biz_id,
                                    version_number=new_ver,
                                    status="ACTIVE" if first else ("APPROVED" if report.is_valid else "DRAFT"),
                                    workflow_type="dynamic",
                                    graph_json=json.dumps(graph_obj.model_dump()),
                                    is_current=first,
                                )
                                session.add(wv)
                                await session.flush()

                                if report.is_valid:
                                    session.add(CompiledGraph(
                                        workflow_version_id=wv.id,
                                        business_id=biz_id,
                                        compiled_json=json.dumps(compiled),
                                    ))
                                first = False
                            except Exception:
                                pass
                        await session.commit()
                except Exception:
                    pass


from datetime import datetime
import uuid
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym
from src.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    whatsapp_number: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    # Meta Cloud API: the numeric Phone Number ID (not the human-readable number)
    # Used by n8n to dynamically resolve which business owns an incoming webhook.
    meta_phone_number_id: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    settings_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    catalog_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    business_type: Mapped[str] = mapped_column(String(50), default="restaurant", nullable=False)
    branding_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    providers_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class WorkflowVersion(Base):
    __tablename__ = "workflow_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    business_id: Mapped[str] = mapped_column(String(36), ForeignKey("businesses.id", ondelete="CASCADE"), index=True, nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="DRAFT", nullable=False)  # DRAFT, ACTIVE, DEPRECATED, FAILED, APPROVED
    workflow_type: Mapped[str] = mapped_column(String(50), default="static", nullable=False)  # static, dynamic
    graph_json: Mapped[str] = mapped_column(Text, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Prompt versioning fields
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=True)
    model_name: Mapped[str] = mapped_column(String(100), nullable=True)
    generation_time: Mapped[float] = mapped_column(Float, nullable=True)
    validation_result: Mapped[str] = mapped_column(Text, nullable=True)

class CompiledGraph(Base):
    __tablename__ = "compiled_graphs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    workflow_version_id: Mapped[str] = mapped_column(String(36), ForeignKey("workflow_versions.id", ondelete="CASCADE"), unique=True, nullable=False)
    business_id: Mapped[str] = mapped_column(String(36), ForeignKey("businesses.id", ondelete="CASCADE"), index=True, nullable=False)
    compiled_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    business_id: Mapped[str] = mapped_column(String(36), ForeignKey("businesses.id", ondelete="CASCADE"), index=True, nullable=False)
    customer_phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    fsm_state: Mapped[str] = mapped_column(String(50), default="START", nullable=False)
    current_node_id: Mapped[str] = mapped_column(String(50), nullable=True)
    carry_unit_json: Mapped[str] = mapped_column(Text, nullable=False)
    workflow_version_id: Mapped[str] = mapped_column(String(36), ForeignKey("workflow_versions.id"), nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    locked_until: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    last_active_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ExecutionLog(Base):
    __tablename__ = "execution_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), index=True, nullable=False)
    business_id: Mapped[str] = mapped_column(String(36), ForeignKey("businesses.id", ondelete="CASCADE"), index=True, nullable=False)
    node_id: Mapped[str] = mapped_column(String(50), nullable=False)
    module_name: Mapped[str] = mapped_column(String(100), nullable=False)
    inputs_json: Mapped[str] = mapped_column(Text, nullable=False)
    outputs_json: Mapped[str] = mapped_column(Text, nullable=False)
    fsm_state_before: Mapped[str] = mapped_column(String(50), nullable=False)
    fsm_state_after: Mapped[str] = mapped_column(String(50), nullable=False)
    executed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class ModuleRegistryModel(Base):
    __tablename__ = "module_registry"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    contract_json: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ExecutionSnapshot(Base):
    __tablename__ = "execution_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), index=True, nullable=False)
    node_id: Mapped[str] = mapped_column(String(50), nullable=False)
    carry_unit_json: Mapped[str] = mapped_column(Text, nullable=False)
    fsm_state: Mapped[str] = mapped_column(String(50), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class ExecutionJournal(Base):
    __tablename__ = "execution_journals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), index=True, nullable=False)
    node_id: Mapped[str] = mapped_column(String(50), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)  # BEGIN_NODE, MODULE_EXECUTED, FSM_TRANSITION, SNAPSHOT_WRITTEN, NODE_COMMITTED
    payload_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class ExternalOperation(Base):
    __tablename__ = "external_operations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), index=True, nullable=False)
    operation_key: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False)  # PENDING, COMPLETED, FAILED
    response_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

class EventStoreRecord(Base):
    __tablename__ = "event_store"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), index=True, nullable=True)
    business_id: Mapped[str] = mapped_column(String(36), ForeignKey("businesses.id", ondelete="CASCADE"), index=True, nullable=True)
    workflow_version_id: Mapped[str] = mapped_column(String(36), ForeignKey("workflow_versions.id"), index=True, nullable=True)
    customer_id: Mapped[str] = mapped_column(String(50), index=True, nullable=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    emitted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class ExecutionMetric(Base):
    __tablename__ = "execution_metrics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), index=True, nullable=False)
    node_id: Mapped[str] = mapped_column(String(50), nullable=False)
    module_name: Mapped[str] = mapped_column(String(100), nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    is_error: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class SharedCustomerContext(Base):
    __tablename__ = "shared_customer_contexts"

    customer_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    business_id: Mapped[str] = mapped_column(String(36), ForeignKey("businesses.id", ondelete="CASCADE"), primary_key=True)
    active_orders_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    active_bookings_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    support_tickets_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    loyalty_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    business_data_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ---------------------------------------------------------------------------
# Phase B Scaffolding — GenerationJob
# Created for Phase A/B transition. Not yet wired to async workers.
# Status lifecycle: queued → running → completed | failed
# ---------------------------------------------------------------------------
class GenerationJob(Base):
    __tablename__ = "generation_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    business_id: Mapped[str] = mapped_column(String(36), ForeignKey("businesses.id", ondelete="CASCADE"),
                                              index=True, nullable=False)

    # Status: queued | running | completed | failed
    status: Mapped[str] = mapped_column(String(20), default="queued", nullable=False, index=True)

    # 0–100 integer progress percentage
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Inputs stored as JSON so the job can be retried without rebuilding the request
    input_description: Mapped[str] = mapped_column(Text, nullable=True)
    input_packs_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    llama_endpoint: Mapped[str] = mapped_column(String(200), default="http://localhost:11434", nullable=False)

    # Outcome
    result_json: Mapped[str] = mapped_column(Text, nullable=True)  # serialised portfolio dict on success
    error: Mapped[str] = mapped_column(Text, nullable=True)        # error message on failure
    method: Mapped[str] = mapped_column(String(30), nullable=True) # "llama" | "programmatic"
    category: Mapped[str] = mapped_column(String(50), nullable=True)

    # Timing
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

class Department(Base):
    __tablename__ = "departments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    business_id: Mapped[str] = mapped_column(String(36), ForeignKey("businesses.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    business_id: Mapped[str] = mapped_column(String(36), ForeignKey("businesses.id", ondelete="CASCADE"), index=True, nullable=False)
    department_id: Mapped[str] = mapped_column(String(36), ForeignKey("departments.id", ondelete="SET NULL"), index=True, nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)  # owner, manager, worker, viewer
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", nullable=False)  # ACTIVE, SUSPENDED, INACTIVE
    login_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=True)
    salt: Mapped[str] = mapped_column(String(100), nullable=True)
    force_password_change: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    specialization: Mapped[str] = mapped_column(String(100), default="General", nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    created_by: Mapped[str] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

class EmployeeAvailability(Base):
    __tablename__ = "employee_availability"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    employee_id: Mapped[str] = mapped_column(String(36), ForeignKey("employees.id", ondelete="CASCADE"), index=True, nullable=False)
    day_of_week: Mapped[str] = mapped_column(String(20), nullable=False)  # Monday, Tuesday, etc.
    start_time: Mapped[str] = mapped_column(String(10), nullable=False)  # "09:00"
    end_time: Mapped[str] = mapped_column(String(10), nullable=False)  # "17:00"

class EmployeeCalendarAvailability(Base):
    __tablename__ = "employee_calendar_availability"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    employee_id: Mapped[str] = mapped_column(String(36), ForeignKey("employees.id", ondelete="CASCADE"), index=True, nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False)  # specific date
    start_time: Mapped[str] = mapped_column(String(10), nullable=True)  # None if unavailable (sick, leave)
    end_time: Mapped[str] = mapped_column(String(10), nullable=True)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    reason: Mapped[str] = mapped_column(String(255), default="", nullable=False)

class EmployeePerformance(Base):
    __tablename__ = "employee_performance"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    employee_id: Mapped[str] = mapped_column(String(36), ForeignKey("employees.id", ondelete="CASCADE"), index=True, nullable=False)
    rating: Mapped[float] = mapped_column(Integer, default=5, nullable=False)
    tasks_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_evaluated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

class EmployeeShift(Base):
    __tablename__ = "employee_shifts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    employee_id: Mapped[str] = mapped_column(String(36), ForeignKey("employees.id", ondelete="CASCADE"), index=True, nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="SCHEDULED", nullable=False)  # SCHEDULED, ACTIVE, COMPLETED, ABSENT

class EmployeeNotification(Base):
    __tablename__ = "employee_notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    employee_id: Mapped[str] = mapped_column(String(36), ForeignKey("employees.id", ondelete="CASCADE"), index=True, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[str] = mapped_column(String(50), default="WhatsApp", nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="SENT", nullable=False)  # SENT, FAILED

class CustomerOwnership(Base):
    __tablename__ = "customer_ownership"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    business_id: Mapped[str] = mapped_column(String(36), ForeignKey("businesses.id", ondelete="CASCADE"), index=True, nullable=False)
    customer_phone: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    assigned_employee_id: Mapped[str] = mapped_column(String(36), ForeignKey("employees.id", ondelete="CASCADE"), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

class SLAConfig(Base):
    __tablename__ = "sla_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    business_id: Mapped[str] = mapped_column(String(36), ForeignKey("businesses.id", ondelete="CASCADE"), index=True, nullable=False)
    trigger_event: Mapped[str] = mapped_column(String(100), nullable=False)
    warning_threshold_minutes: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    breach_threshold_minutes: Mapped[int] = mapped_column(Integer, default=30, nullable=False)

class SLATracking(Base):
    __tablename__ = "sla_trackings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    business_id: Mapped[str] = mapped_column(String(36), ForeignKey("businesses.id", ondelete="CASCADE"), index=True, nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)  # task, appointment, approval
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    sla_status: Mapped[str] = mapped_column(String(20), default="SLA_MET", nullable=False)  # SLA_MET, SLA_WARNING, SLA_BREACHED
    target_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    resolved_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

class AutomationRule(Base):
    __tablename__ = "automation_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    business_id: Mapped[str] = mapped_column(String(36), ForeignKey("businesses.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    trigger_event: Mapped[str] = mapped_column(String(100), nullable=False)
    conditions_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    actions_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

class ConversationLog(Base):
    __tablename__ = "conversation_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    business_id: Mapped[str] = mapped_column(String(36), ForeignKey("businesses.id", ondelete="CASCADE"), index=True, nullable=False)
    session_id: Mapped[str] = mapped_column(String(36), nullable=True)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # INBOUND, OUTBOUND
    sender: Mapped[str] = mapped_column(String(50), nullable=False)
    recipient: Mapped[str] = mapped_column(String(50), nullable=False)
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[str] = mapped_column(String(20), default="text", nullable=False)  # text, media, interactive
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    employee_id: Mapped[str] = mapped_column(String(36), ForeignKey("employees.id", ondelete="CASCADE"), index=True, nullable=False)
    notification_source: Mapped[str] = mapped_column(String(50), nullable=False)  # TASK_ASSIGNED, etc.
    channels_json: Mapped[str] = mapped_column(Text, default="[\"dashboard\", \"whatsapp\"]", nullable=False)

class UserBusinessAccess(Base):
    __tablename__ = "user_business_access"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    phone: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    business_id: Mapped[str] = mapped_column(String(36), ForeignKey("businesses.id", ondelete="CASCADE"), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="owner", nullable=False)

class BusinessEvent(Base):
    __tablename__ = "business_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    business_id: Mapped[str] = mapped_column(String(36), ForeignKey("businesses.id", ondelete="CASCADE"), index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)  # appointment, order, approval
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    business_id: Mapped[str] = mapped_column(String(36), ForeignKey("businesses.id", ondelete="CASCADE"), index=True, nullable=False)
    actor_id: Mapped[str] = mapped_column(String(36), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)  # EMPLOYEE_CREATED, etc.
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    old_value_json: Mapped[str] = mapped_column(Text, nullable=True)
    new_value_json: Mapped[str] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    business_id: Mapped[str] = mapped_column(String(36), ForeignKey("businesses.id", ondelete="CASCADE"), index=True, nullable=False)
    employee_id: Mapped[str] = mapped_column(String(36), ForeignKey("employees.id", ondelete="CASCADE"), index=True, nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    read_status: Mapped[str] = mapped_column(String(20), default="UNREAD", nullable=False)  # READ, UNREAD
    channels_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    sent_channels_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

class ReportSchedule(Base):
    __tablename__ = "report_schedules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    business_id: Mapped[str] = mapped_column(String(36), ForeignKey("businesses.id", ondelete="CASCADE"), index=True, nullable=False)
    frequency: Mapped[str] = mapped_column(String(20), nullable=False)  # DAILY, WEEKLY, MONTHLY
    recipient_role: Mapped[str] = mapped_column(String(20), nullable=False)  # OWNER, MANAGER, EMPLOYEE
    recipient_id: Mapped[str] = mapped_column(String(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=True)
    channel: Mapped[str] = mapped_column(String(20), default="WHATSAPP", nullable=False)
    next_run_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

class AggregatedMetrics(Base):
    __tablename__ = "aggregated_metrics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    business_id: Mapped[str] = mapped_column(String(36), ForeignKey("businesses.id", ondelete="CASCADE"), index=True, nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    appointments_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tasks_pending: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tasks_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    active_employees: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    revenue: Mapped[float] = mapped_column(Integer, default=0, nullable=False)  # stored in float
    csat_score: Mapped[float] = mapped_column(Integer, default=5, nullable=False)

class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    business_id: Mapped[str] = mapped_column(String(36), ForeignKey("businesses.id", ondelete="CASCADE"), index=True, nullable=False)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.id", ondelete="SET NULL"), index=True, nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    priority: Mapped[str] = mapped_column(String(20), default="MEDIUM", nullable=False)  # LOW, MEDIUM, HIGH, CRITICAL
    assigned_employee_id: Mapped[str] = mapped_column(String(36), ForeignKey("employees.id", ondelete="SET NULL"), index=True, nullable=True)
    assigned_worker_id = synonym("assigned_employee_id")
    due_time: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False)  # PENDING, ACCEPTED, IN_PROGRESS, COMPLETED, CANCELLED
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    business_id: Mapped[str] = mapped_column(String(36), ForeignKey("businesses.id", ondelete="CASCADE"), index=True, nullable=False)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), index=True, nullable=False)
    node_id: Mapped[str] = mapped_column(String(50), nullable=False)
    request_type: Mapped[str] = mapped_column(String(50), default="general", nullable=False)  # large_order, appointment_request, visit_request, general
    details_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False)  # PENDING, APPROVED, REJECTED, ESCALATED
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    action_taken: Mapped[str] = mapped_column(String(20), nullable=True)  # Approve, Reject, Modify, Escalate
    resolved_by: Mapped[str] = mapped_column(String(100), nullable=True)

# Backwards compatibility alias
Worker = Employee

class GenerationBenchmark(Base):
    __tablename__ = "generation_benchmarks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    business_type: Mapped[str] = mapped_column(String(50), nullable=False)
    input_description: Mapped[str] = mapped_column(Text, nullable=False)
    raw_output: Mapped[str] = mapped_column(Text, nullable=True)
    parsed_draft_json: Mapped[str] = mapped_column(Text, nullable=True)
    is_valid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    validation_errors: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# FlowCore Platform Invariants

These invariants are the permanent laws of the FlowCore platform. They must be preserved across every implementation phase, every conversation, and every future evolution of the platform.

## INV-01: FSM Authority
Only System 1's FSM Engine may transition session FSM state. No other system, module, or external call may mutate `session.fsm_state` directly. All state transitions must pass through the FSM Engine's validation layer.

## INV-02: Carry Unit Append-Only
Carry unit fields are never removed within a session. They are only added (merged). The carry unit version increments monotonically with each module execution.

## INV-03: No Unvalidated Workflow Execution
System 1 MUST reject execution requests for workflows that do not have `status = ACTIVE`. Draft, failed, and pending workflows may not be executed for live customer interactions.

## INV-04: AI Never Controls Runtime
No LLM/AI inference calls may occur within System 1's execution path. AI is strictly confined to System 2 (Workflow Generation Backend) and operates only during the pre-runtime onboarding workflow generation phase.

## INV-05: Module Contract Immutability at Runtime
Module contracts (`requires`, `produces`, `allowed_fsm_states`) may not change after a workflow version is activated. Changes require a new module version and a new workflow version registration.

## INV-06: Business Isolation
All database queries and execution contexts in System 1 must include `business_id` as a filter. Cross-business data access is strictly forbidden and must be enforced at the database/query wrapper layer.

## INV-07: Execution Log Immutability
Execution log rows are append-only. They are never updated or deleted. They serve as the permanent, unalterable audit trail of all platform executions.

## INV-08: Idempotency for Non-Idempotent Modules
Before executing any module where `is_idempotent = false`, the execution engine must check whether this module has already completed for this specific node in the current session by querying the execution logs.

## INV-09: Graph is Acyclic at Activation
No workflow may be activated if its graph contains any cycles. Cycle detection must be performed and must pass as part of the workflow validation pipeline before transition to the `APPROVED` or `ACTIVE` state.

## INV-10: System Separation
Systems 1 and 2 must never share internal code, internal database state, or direct function/process calls. They must communicate exclusively via HTTP REST APIs and schema contracts.

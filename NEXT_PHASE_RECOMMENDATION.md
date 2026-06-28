# FlowCore Next Phase Recommendation
**System 2: Workflow Generation Backend & System 3/4 Integration Roadmap**

With the completion of the Main Execution Backend (System 1), the platform is fully deterministic, tested, and contract-validated. We recommend the following steps for the next implementation phases:

---

## 1. Phase 3: Workflow Generation Backend (System 2)

### 1.1 Local Llama Integration
* Connect System 2 to the local Llama HTTP server on `localhost:11434`.
* Implement a prompt builder that pulls the active `ModuleRegistry` and FSM states from System 1.
* Construct structured prompt constraints instructing Llama to output *only* valid JSON conforming to the `WorkflowGraph` Pydantic schema, utilizing *only* registered module names and FSM transitions.

### 1.2 Onboarding Chat API
* Design a conversational onboarding state machine in System 2. Instead of generating a workflow immediately, have System 2 ask the owner sequential questions to compile business parameters (e.g., business name, domain, catalog menu, delivery range).
* Use Llama to structure these answers and automatically generate the nodes, config parameters, and edge links.

---

## 2. Phase 4: N8N Orchestration Workflows (System 3 & 4)

### 2.1 Runtime N8N (System 3)
* Build a thin N8N webhook receiver that hooks to the Meta WhatsApp Business API.
* Responsibilities of this N8N flow:
  1. Catch incoming message events.
  2. Extract `customer_phone` and the metadata parameters.
  3. Query System 1 to retrieve `session_id`. If none exists, request session initialization `/api/v1/sessions`.
  4. Dispatch the user's incoming message text to `/api/v1/sessions/dispatch/{session_id}`.
  5. Read the `messages_sent` list in the response and send them back to the customer via the WhatsApp Business API.
* **Invariant Guard**: Enforce that N8N must *never* perform state checks, FSM mutations, or evaluations of business logic. It remains a transport-only webhook router.

### 2.2 Onboarding Generation N8N (System 4)
* Build N8N pipelines to guide the business owner through the onboarding workflow generation, validation, simulation, and manual approval lifecycle.

---

## 3. Production Deployment & Database Transition
* Migrate from SQLite to PostgreSQL. The SQLAlchemy models have been designed utilizing portable data types, so this migration requires only updating the `DATABASE_URL` environment variable.
* Configure alembic migrations (`alembic.ini`) to track and manage changes.

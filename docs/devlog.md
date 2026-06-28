# FlowCore Engineering Devlog & System Architecture Memory

This document acts as the definitive history, architectural memory, and development log for FlowCore: an AI-Powered WhatsApp Business Automation Platform.

---

## 1. Backend Traversal & Runtime Core (System 1)

### 1.1 Architecture & Design Decisions
- **Deterministic Traversal**: Separates natural language AI generations from execution safety. The traverser evaluates input events, resolves conditional edges, validates FSM state constraints, and writes transaction checkpoints atomically.
- **FSM State Immutability**: States `CONFIRMED` and `CANCELLED` represent terminal phases. Traversal steps targeting a locked session throw a strict `TERMINAL_STATE_LOCKED` exception.
- **Monotonic Carry Unit**: Context payloads are merged incrementally via JSON merge patches ($C_{new} = C \cup O$), ensuring carry values are append-only.

### 1.2 Hardening Phase Completes (Phase 1)
- **FSM State Check**: Introduced `IllegalTransitionError` raised inside the `FSMEngine` transition mapping to prevent status hops.
- **Traversal Limits**: Added `STALLED_EXECUTION` check triggered when execution depth reaches `max_depth` (default `10`).
- **Dead-End Detection**: Upgraded both compile-time and static validation to identify non-terminal leaf nodes with no expectations of user input and flag them as `DEAD_END_NODE`.
- **Chronological Replay Verification**: Created a `ReplayVerifier` that reads historical journals and replays them step-by-step to test path identity.

---

## 2. Frontend Platform & Onboarding UX (System 2)

### 2.1 Core UX Decisions
- **AI-First Generation Platform**: Shifted from manual template setup to a conversational onboarding prompt. The system uses local Llama models to dynamically write workflow graphs.
- **Technical Abstraction**: Technical names (FSM tables, carry logs, compilation telemetry) are hidden. Nodes are rendered with friendly names (e.g. `collect_cart` → `Collect Customer Order`) and status checks are simplified (e.g. `✓ Payment Safe`, `✓ Ready To Deploy`).
- **Templates Roadmap**: Template grids for Restaurant, Salon, and Clinic are mapped as "Coming Soon" placeholders. Development prioritizes active AI compiler testing.

### 2.2 Orchestration & Integration Visualization
- **React Flow Layouts**: Renders nodes dynamically in a sequential grid.
- **Docker n8n Connection**: Monitors local docker endpoints, showing integrations (WhatsApp, Stripe API, Express Delivery) as active blocks in the dashboard workspace.
- **AI Refinement Loop**: Interactive prompt panel lets users request modifications (e.g., "Add COD options") to update the layout and re-run compilation checks dynamically.

### 2.3 Directory Layout
All frontend files are isolated under `/frontend`:
- `/frontend/app`: Pages for landing, onboarding, and workspace dashboards.
- `/frontend/services`: API client mapping endpoints to the FastAPI backend.
- `/frontend/features/ai-builder`: Llama inference client and prompt generation.
- `/frontend/stores`: Zustand global store for state and session management.

---

## 3. Bugs & Fixes Log

### 3.1 Draft Activation Rejection
- **Problem**: In test suites, registering a valid workflow set the status to `APPROVED` automatically, bypassing the validation check that draft workflows must not activate directly.
- **Fix**: Updated `test_dynamic_workflow_activation_certification` to manually adjust the db status of the version record to `"DRAFT"` before attempting activation, confirming a 400 error response.

### 3.2 NPM peer conflicts
- **Problem**: Next.js 16/react 19 peer conflict during bootstrap caused npm install errors.
- **Fix**: Boostrapped Next.js using `--skip-install` and then ran a clean `npm install --legacy-peer-deps` with absolute Node.js path overlays.

### 3.3 SQLite Database Schema Mismatch
- **Problem**: Querying `GET /api/v1/businesses/{business_id}` threw a `no such column: businesses.settings_json` 500 Internal Server Error because the existing SQLite database tables had not been updated with the newer columns.
- **Fix**: Executed `ALTER TABLE` migrations on the SQLite database file to dynamically add `settings_json` and `catalog_json` to the `businesses` table, and `workflow_type` to the `workflow_versions` table. This restored the API compatibility and enabled successful workspace loading.

---

## 4. End-to-End Orchestration & Llama Integration (Phase 3)

### 4.1 AI Context & Intent Isolation
- **Versioned AI Context (`flowcore_runtime_context_v1.md`)**: A markdown context file containing state schemas, system module constraints, and condition rules. Rather than sending the entire dynamic codebase, the LLM prompt is primed with this modular versioned context.
- **Negative & Positive Reinforcement**: The context includes explicit `INVALID WORKFLOW EXAMPLES` (negatives like cycles, loose ends, bad state hops) and `GOOD WORKFLOW PATTERNS` (positives like salon scheduling or restaurant checkout) which drastically reduce LLM prompt drift.
- **Workflow Intent Extraction**: The `AIService` first runs a lightweight intent extraction prompt to classify key traits (business type, payments, deliveries) before executing the final graph synthesis.
- **Dynamic Context Serving**: Added the `/api/v1/workflows/ai-context` endpoint to dynamically read and serve the current versioned markdown context to the frontend.

### 4.2 n8n Orchestration Layer
- **Unified Schema Routing**: Designed the main n8n workflow (`flowcore_n8n_workflow.json`) to ingest WhatsApp messages, inspect the session from the backend (`GET /sessions/inspect/{session_id}`), create a new session if needed, and dispatch input to the traverser.
- **Central Event Router**: Evaluates side-effects. Routes `dispatch_delivery_courier` to mock shipping providers and `external_gateway_handshake` to mock payment gateways.
- **Mock Providers**: Added `/orchestration/providers/stripe.json` and `/orchestration/providers/delivery.json` segments to mock external systems synchronously for local validation.

---

## 5. Future Roadmap & TODOs
- [ ] Connect real WhatsApp Business API Cloud credentials in n8n nodes.
- [ ] Connect live Stripe Sandbox API keys in Stripe HttpRequest node templates.
- [ ] Add support for custom CSS themes inside settings catalog.
- [ ] Implement team collaboration metrics dashboards.

---

## 6. Phase 4 — Final Simplified Orchestration Architecture

### 6.1 Architectural Decisions

**Decision: Consolidate to TWO n8n workflow files only.**
All previous fragmented segment files (`whatsapp_webhook.json`, `event_router.json`, `stripe.json`, `delivery.json`) are superseded.
The final architecture uses exactly:
- `orchestration/n8n/main_orchestration.json` — complete operational pipeline
- `orchestration/n8n/dynamic_workflow_generator.json` — complete AI generation pipeline

**Rationale**: Fewer files = simpler debugging, easier import, less context fragmentation in production.

### 6.2 Separation of Concerns (Runtime Boundary Rules)

FlowCore runtime ALWAYS remains authoritative:
- FSM transition decisions stay in FlowCore traversal engine
- Carry unit mutations happen ONLY inside FlowCore
- Workflow legality checked ONLY by FlowCore validation pipeline
- Replay semantics governed ONLY by FlowCore replay engine
- n8n NEVER reads or writes carry state directly

n8n operates as transport + integration layer ONLY:
- Receives Meta webhooks, ACKs immediately (within 20 seconds)
- Calls FlowCore APIs to resolve sessions and dispatch inputs
- Reads FlowCore's side_effects to trigger external integrations
- Sends WhatsApp replies derived from FlowCore's messages_sent

### 6.3 New Backend Endpoints Added (For Dynamic Orchestration)

| Endpoint | Purpose |
|---|---|
| `GET /api/v1/businesses/by-phone-id/{meta_phone_number_id}` | Dynamic business resolver for n8n — no hardcoded IDs |
| `PUT /api/v1/businesses/{id}/meta-phone-id` | Register Meta Phone Number ID for a business |
| `GET /api/v1/sessions/active?business_id=&customer_phone=` | Resolve active session without reconstructing time-based session_id |

### 6.4 Dynamic Business Resolution Architecture

**Problem**: n8n cannot hardcode business IDs — the platform must serve ANY business.
**Solution**: Businesses register their `meta_phone_number_id` once via the API.
  When Meta sends a webhook with `metadata.phone_number_id`, n8n calls `GET /businesses/by-phone-id/{id}` to resolve the FlowCore business_id dynamically.

### 6.5 FSM-Aware Operational Actions

Operational action buttons displayed to customers are derived from the `fsm_state` returned by FlowCore dispatch:
- `PAYMENT` state → Retry Payment, Cancel Order
- `CONFIRMED` state → Track Delivery, Reorder, Contact Support
- etc.

FlowCore is the source of truth. n8n only reads the fsm_state to determine which buttons to show.
No action button logic lives inside n8n independently.

### 6.6 AI Generation Pipeline (2-Pass Architecture)

**Pass 1 — Intent Extraction (lightweight)**: 8 second Llama call extracts business_type, needs_payment, needs_delivery, terminology.
**Pass 2 — Full Generation (comprehensive)**: 60 second Llama call generates complete workflow JSON using FlowCore runtime context + intent.
**Fallback**: Intent-aware mock synthesis generates a valid FlowCore graph without Llama if it's offline.
**Validation Gate**: ALL generated workflows must pass FlowCore validation before storage.

### 6.7 AI Context Versioning

Context file updated to v1 with complete sections:
- System architecture (4-layer diagram)
- All 9 modules with carry outputs, side effects, allowed FSM states
- Condition engine with all 6 condition types
- FSM state space (9 states with terminal markers)
- Graph schema with full JSON structure
- 8 invalid workflow examples (negative reinforcement)
- 5 good workflow patterns (positive reinforcement)
- Business context adaptation per business type (restaurant/salon/clinic/gym/ecommerce)
- Dynamic operational actions with FSM legality table
- Workflow validation checklist (10 pre-submit checks)

### 6.8 Config Changes

Updated `src/config.py` to:
- Use Pydantic v2 `ConfigDict` instead of deprecated `class Config`
- Add `extra="ignore"` to allow `.env` files with n8n/Meta credentials
- Add `META_PHONE_NUMBER_ID`, `META_ACCESS_TOKEN`, `META_WEBHOOK_VERIFY_TOKEN` as typed optional fields

### 6.9 Bugs Fixed

- **Pydantic Settings Rejection**: `.env` file with Meta/n8n vars caused `extra_forbidden` validation errors in pytest. Fixed by switching to `extra="ignore"` in Settings ConfigDict.
- **Session ID Reconstruction**: n8n could not reconstruct time-based session IDs. Fixed by adding `GET /sessions/active` endpoint that resolves by `(business_id, customer_phone)`.

---

## 7. Phase 5 — Generic Side-Effect Execution & Standard UI Contract

### 7.1 Separation of Concerns & FlowCore Authority
- **Route-Based Branching Deprecated**: Deprecated feature-specific orchestration branches (e.g. payment/delivery routers) in n8n. The flow is now entirely linear, keeping n8n as a generic execution and transport layer.
- **Decision Engine Consolidation**: FlowCore now decides all side-effects and interface structures, while n8n merely loops over the received array of side-effects and triggers standard integration adapters.
- **Standardized UI Contract**: Introduced the `ui` response block (`text`, `actions`, `metadata`) inside the dispatch response contract. This allows frontends and message brokers to render buttons, carts, and order summaries dynamically without hardcoding button behaviors.

### 7.2 Scalability & Future-Proofing Benefits
- **Zero Orchestration Re-work**: Adding future business sectors (e.g., clinics, salons, gyms, or finance) requires zero edits to the n8n main pipeline. n8n executes whatever side-effects the FlowCore state machine modules output.
- **Backward Compatibility**: Maintained fallbacks for `messages_sent` and `allowed_actions` on both the backend and frontend store layers, enabling a smooth, gradual transition to the standardized UI contract.

---

## 8. Phase 6 — WhatsApp Configuration Management

### 8.1 Architectural Decisions & Ownership
- **Credential Ownership Consolidated**: Moved WhatsApp API configurations (Phone Number ID and Access Token) out of n8n and Docker environment variables and into FlowCore database storage. This ensures FlowCore is the authoritative source for business configurations.
- **Dynamic Retrieval Endpoint**: Added the `GET /api/v1/businesses/{business_id}/whatsapp-config` API route. This endpoint allows n8n to dynamically fetch credentials for any business at runtime.
- **Service Layer Abstraction**: Created `WhatsAppConfigService` which resolves credentials by inspecting:
  1. The business's settings JSON (`settings_json["whatsapp"]`).
  2. The business's direct `meta_phone_number_id` column as a fallback.
  3. Environment variables as a fallback for the MVP business (`e216b183-8c91-4a56-b819-50ebfb3f8a45`).

### 8.2 Security & Multi-Tenant Support Strategy
- **No Token Leaks**: Configured loggers and debug paths to never print or expose authorization tokens.
- **Static Workflows Untouched**: n8n workflows no longer contain hardcoded tokens. The main orchestration pipeline dynamically retrieves credentials at runtime, enabling:
  - Restaurant A -> WhatsApp Number A
  - Salon B -> WhatsApp Number B
  without modifying any orchestration logic or restarting Docker containers.

---

## 9. Phase 7 — Business-Ready WhatsApp Experience & Customer Experience Transformation

### 9.1 Architectural Decisions & Core Transformation
- **Transition to Business-Ready UI Contract**: Transformed customer-facing messages from raw developer logs/JSON representations to formatted, emoji-rich, structured layouts (e.g. customized catalogs, structured carts, address confirmations, and clear payment calls).
- **Universal Input Error Retry Policy**: Implemented a state-specific 3-retry warning policy. When input routing or module processing fails:
  - First strike: Warns the user (❌) and lists available options/guidance.
  - Second strike: Warns the user (⚠️) that we are still unable to parse.
  - Third strike: Informs the user (🚫) of failure, cancels the session, sets the FSM state to `CANCELLED`, archives the session, and clears the active session mapping.
- **FSM-Aware Operational Actions & Guidance**: Refactored the traversal engine to inject context-aware actions based on FSM states (e.g., payment links for `PAYMENT_PENDING`, delivery trackers/support for `DELIVERY_ACTIVE` / `ORDER_CONFIRMED`) and return state-specific guidance instructions dynamically to frontend adapters.
- **Support Intercept Routing**: Intercepts "Contact Support" input from any state. Keeps the session active in the same state, returning a support routing message without triggering a FSM state change or validation error.
- **Form Abstraction Layer**: Standardized dynamic interactive forms by introducing `FormField` and `FormDefinition` Pydantic models. Applied these schemas directly in modules like `CollectAddressModule` to support custom forms on frontends and n8n webhook handlers.

### 9.2 Transaction Commit/Flush Correction
- **Problem**: Calling `db_session.commit()` inside traversal error handlers caused database sessions to close prematurely, which broke nested transactions created by integration tests and simulation setups, resulting in a `ResourceClosedError: This transaction is closed` on rollback.
- **Fix**: Substituted `commit()` calls with `flush()` inside session traversal exception handlers. This pushes state updates to the database transaction logs while keeping the main transaction boundary open for the orchestrator (or testing harness) to commit or roll back.


# FlowCore Runtime and Validation Specification Context (v2)

**Version**: 2.0 | **Applies To**: All AI workflow generation engines (Llama, GPT-compatible) | **Governed By**: FlowCore Runtime Team
**Supersedes**: flowcore_runtime_context_v1.md (v1 sections A–J are fully preserved and still authoritative)

This document is the authoritative AI training context for the FlowCore Conversational Workflow Platform.
It defines every schema, constraint, module contract, FSM rule, workflow pattern, registry contract, and
generation pipeline that AI generators must respect.

DO NOT generate workflows that violate rules in this document.
FlowCore's validation pipeline will REJECT invalid graphs at compile time.

---

## A. FLOWCORE ARCHITECTURE

### A.1 System Architecture Overview

FlowCore separates concerns into four distinct layers:

```
┌─────────────────────────────────────────────────────────┐
│  LAYER 1 — FlowCore Runtime (Authoritative)             │
│  - Deterministic graph traversal engine                 │
│  - FSM state governance                                 │
│  - Carry unit authority                                 │
│  - Workflow validation & compilation                    │
│  - Replay & snapshot guarantees                         │
│  - Idempotency enforcement                              │
└─────────────────────────────────────────────────────────┘
         ↑ All runtime decisions stay here
┌─────────────────────────────────────────────────────────┐
│  LAYER 2 — n8n Orchestration (Transport Only)           │
│  - WhatsApp webhook ingestion                           │
│  - Session resolution (calls FlowCore API)              │
│  - External integrations (Stripe, logistics)            │
│  - Message delivery (Meta Cloud API)                    │
│  - Does NOT make runtime decisions                      │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│  LAYER 3 — Llama AI (Generation Only)                   │
│  - Workflow graph generation from natural language      │
│  - Workflow refinement suggestions                      │
│  - Business context understanding                       │
│  - Does NOT execute runtime code                        │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│  LAYER 4 — Frontend (Visualization Only)                │
│  - React Flow canvas rendering                          │
│  - Business dashboard                                   │
│  - Operational action display                           │
│  - Does NOT control runtime state                       │
└─────────────────────────────────────────────────────────┘
```

### A.2 Deterministic Traversal Engine

The traversal engine processes user inputs through the workflow graph deterministically:

1. **Input received** → edge conditions evaluated in order
2. **Matching edge found** → target node resolved
3. **Node module executed** within atomic database savepoint
4. **Carry unit merged** monotonically (append-only, never overwrite)
5. **FSM state transitioned** if node declares `fsm_transition_to`
6. **Execution journal written** (immutable audit log)
7. **Snapshot saved** (replay checkpoint)
8. **Side effects registered** (idempotent external operation queue)
9. **Response returned** to orchestration layer

### A.3 Replay Guarantees

- Every traversal step is journaled in `ExecutionLog`
- `ReplayEngine` can reconstruct any session state from scratch using the journal
- Replays produce identical carry unit states (deterministic guarantee)
- Side effects are de-duplicated via `ExternalOperationRegistry` (exactly-once semantics)

### A.4 Carry Unit (State Container)

The Carry Unit is the append-only state namespace flowing through the session:

```json
{
  "session": {
    "session_id": "string",
    "customer_phone": "string",
    "business_id": "string",
    "workflow_version_id": "string",
    "session_started_at": "ISO-8601 string"
  },
  "data": {
    "cart_total": 0.00,
    "cart_items": [
      { "item_id": "string", "name": "string", "quantity": 1, "price": 0.00 }
    ],
    "order": {
      "order_id": "string",
      "items": [],
      "status": "string"
    },
    "customer": {
      "address": "string",
      "name": "string"
    },
    "logistics": {
      "delivery_id": "string",
      "tracking_id": "string",
      "status": "string"
    },
    "payment": {
      "transaction_id": "string",
      "payment_url": "string",
      "status": "string",
      "amount": 0.00
    }
  }
}
```

**Rules**:
- Carry unit is APPEND-ONLY. Values can be added or updated, never deleted mid-session.
- All carry mutations happen INSIDE FlowCore. n8n never writes to carry state.

---

## B. AVAILABLE MODULES

All nodes must map `module_name` to one of these registered modules.
Do not invent module names.

### B.1 show_menu
- **Purpose**: Displays business-specific welcome message and catalog/service options
- **Config Required**: `menu_header` (String) — the full message text including numbered options
- **Carry Output**: none (read-only)
- **Side Effects**: none
- **Allowed FSM States**: `START`, `MENU`, `CART`, `CANCELLED`, `CONFIRMED`
- **Operational Actions Generated**: Browse catalog, Restart
- **Notes**: Always the `entry_node_id`. Content should be dynamic and business-specific.

### B.2 collect_cart
- **Purpose**: Parses customer selection input (e.g. "1 x 2", "Option A") and stores in carry unit
- **Config Required**: `expects_user_input: true`, optional `validation_regex`
- **Carry Output**: `cart_items[]`, `selection`
- **Side Effects**: none
- **Allowed FSM States**: `MENU`, `BROWSING`, `CART`
- **Operational Actions Generated**: View Cart, Clear Cart
- **Notes**: Must have `expects_user_input: true` in config.

### B.3 calculate_total
- **Purpose**: Sums all cart item prices and writes `cart_total` to carry unit
- **Config Required**: none
- **Carry Output**: `cart_total`
- **Side Effects**: none
- **Allowed FSM States**: `CART`, `CHECKOUT`
- **Operational Actions Generated**: View Cart, Modify Order

### B.4 create_order
- **Purpose**: Persists the cart as a database order record; generates `order_id`
- **Config Required**: none
- **Carry Output**: `order.order_id`, `order.items`, `order.status`
- **Side Effects**: none
- **Allowed FSM States**: `CART`, `CHECKOUT`
- **Operational Actions Generated**: Cancel Order

### B.5 create_payment
- **Purpose**: Generates a payment transaction (Stripe checkout URL). Idempotent — reuses existing pending transaction.
- **Config Required**: `gateway` (e.g. "stripe"), `currency` (e.g. "USD" or "INR")
- **Carry Output**: `payment.transaction_id`, `payment.payment_url`, `payment.status`
- **Side Effects**: `external_gateway_handshake` (triggers n8n Stripe integration)
- **Allowed FSM States**: `CHECKOUT`, `PAYMENT`
- **Operational Actions Generated**: Retry Payment, Cancel Order

### B.6 confirm_payment
- **Purpose**: Marks the payment transaction as confirmed/completed
- **Config Required**: none
- **Carry Output**: `payment.status = "CONFIRMED"`
- **Side Effects**: none
- **Allowed FSM States**: `PAYMENT`, `CONFIRMED`
- **Operational Actions Generated**: View Receipt

### B.7 collect_address
- **Purpose**: Asks for and stores the customer's delivery address
- **Config Required**: `expects_user_input: true`
- **Carry Output**: `customer.address`
- **Side Effects**: none
- **Allowed FSM States**: `CHECKOUT`, `CONFIRMED`
- **Operational Actions Generated**: Modify Address

### B.8 create_delivery
- **Purpose**: Creates a logistics dispatch order for the customer's address
- **Config Required**: none
- **Carry Output**: `logistics.delivery_id`, `logistics.status`
- **Side Effects**: `dispatch_delivery_courier` (triggers n8n courier integration)
- **Allowed FSM States**: `CHECKOUT`, `CONFIRMED`
- **Operational Actions Generated**: Track Delivery, Contact Support

### B.9 notify_customer
- **Purpose**: Sends a final or interim status message to the customer
- **Config Required**: `message` (String) — the notification text (can reference business name, order details)
- **Carry Output**: none
- **Side Effects**: none
- **Allowed FSM States**: ALL states
- **Notes**: Use for order confirmations, booking confirmations, cancellation notices.

---

## C. CONDITION ENGINE

Edges connect nodes and define routing conditions evaluated at runtime.

### C.1 Condition Types

| Type | Matches When | Example Value |
|---|---|---|
| `always` | Unconditionally — always routes to this edge | `""` |
| `any_input` | Customer sends any text at all | `""` |
| `input_equals` | Customer input exactly matches | `"1"` or `"yes"` |
| `input_in` | Customer input is in a list | `["1","2","3"]` |
| `carry_equals` | A carry unit field equals value | `{"field": "payment.status", "value": "CONFIRMED"}` |
| `carry_greater_than` | A carry numeric field exceeds value | `{"field": "cart_total", "value": 0}` |

### C.2 Edge Structure

```json
{
  "from_node": "node_id_a",
  "to_node": "node_id_b",
  "condition": {
    "type": "input_equals",
    "value": "1"
  }
}
```

### C.3 Edge Evaluation Rules

- Edges are evaluated IN ORDER for each node
- First matching edge wins
- If no edge matches and node `expects_user_input: true`, session waits for next message
- If no edge matches and node does NOT expect input → traversal error

---

## D. FSM STATE SPACE

Valid FSM states and their semantic meaning:

| State | Meaning | Terminal? |
|---|---|---|
| `START` | Session initialized, no interaction yet | No |
| `MENU` | Customer viewing catalog/options | No |
| `BROWSING` | Customer exploring sub-categories | No |
| `CART` | Customer has selected items | No |
| `CHECKOUT` | Order being finalized | No |
| `PAYMENT` | Payment in progress | No |
| `CONFIRMED` | Order/booking confirmed | **YES** |
| `CANCELLED` | Order/session cancelled | **YES** |
| `ERROR` | Unrecoverable runtime error | **YES** |

### D.1 FSM Transition Table Format

```json
{
  "fsm_transition_table": {
    "FROM_STATE": {
      "TO_STATE": "module_name_that_triggers_transition"
    }
  }
}
```

Every transition declared in a node's `fsm_transition_to` field MUST appear in `fsm_transition_table`.

---

## E. WORKFLOW GRAPH SCHEMA

The complete JSON schema for a FlowCore workflow graph:

```json
{
  "business_id": "string (UUID)",
  "version_number": 1,
  "entry_node_id": "string (must exist in nodes)",
  "nodes": {
    "node_id": {
      "id": "string (matches key)",
      "module_name": "string (from registered modules)",
      "config": {},
      "fsm_transition_to": "string (valid FSM state)"
    }
  },
  "edges": [
    {
      "from_node": "string (node id)",
      "to_node": "string (node id)",
      "condition": {
        "type": "string (condition type)",
        "value": "any"
      }
    }
  ],
  "fsm_transition_table": {
    "FSM_STATE": {
      "NEXT_FSM_STATE": "module_name"
    }
  }
}
```

---

## F. INVALID WORKFLOW EXAMPLES (NEVER GENERATE THESE)

### F.1 FSM State Mismatch
```
INVALID: node using create_payment with fsm_transition_to: "START"
REASON: create_payment is only allowed in CHECKOUT or PAYMENT state.
CORRECT: fsm_transition_to: "PAYMENT"
```

### F.2 Dead-End Node (Loose End)
```
INVALID: leaf node (no outgoing edges) in non-terminal FSM state
         where expects_user_input is false.
REASON: Customer conversation freezes with no path forward.
CORRECT: All leaf nodes must be in CONFIRMED, CANCELLED, or ERROR state
         OR have expects_user_input: true.
```

### F.3 Traversal Cycle (Infinite Loop)
```
INVALID: node_menu → node_collect → node_menu (always condition)
REASON: Unconditional cycle creates infinite traversal loop.
CORRECT: Use input_equals conditions to break cycles:
  node_menu → node_collect (condition: any_input)
  node_collect → node_confirm (condition: always)
```

### F.4 Invalid Condition Value Type
```
INVALID: condition type "input_in" with value "5" (string)
REASON: input_in requires a JSON array.
CORRECT: value: ["5", "five", "FIVE"]
```

### F.5 Missing Entry Node
```
INVALID: entry_node_id: "node_xyz" but "node_xyz" not in nodes{}
REASON: Traversal engine cannot find starting point.
CORRECT: entry_node_id must exactly match a key in nodes{}.
```

### F.6 Payment Before Order
```
INVALID: create_payment without a preceding create_order
REASON: No order record exists to associate payment with.
CORRECT: collect_cart → calculate_total → create_order → create_payment
```

### F.7 Delivery Before Address
```
INVALID: create_delivery without preceding collect_address
REASON: No delivery address stored in carry unit.
CORRECT: collect_address → create_delivery (always)
```

### F.8 Transition Table Missing Entry
```
INVALID: node declares fsm_transition_to: "PAYMENT" but
         fsm_transition_table has no {"CHECKOUT": {"PAYMENT": ...}}
REASON: FSM validator rejects undefined transitions.
CORRECT: Every fsm_transition_to in a node MUST appear in the table.
```

---

## G. GOOD WORKFLOW PATTERNS (GENERATE THESE)

### G.1 Restaurant / Food Ordering (Full Flow)

```
show_menu [FSM: MENU]
  ↓ (any_input)
collect_cart [FSM: CART] — expects_user_input: true
  ↓ (always)
calculate_total [FSM: CHECKOUT]
  ↓ (always)
create_order [FSM: CHECKOUT]
  ↓ (always)
create_payment [FSM: PAYMENT] — gateway: stripe
  ↓ (always)
confirm_payment [FSM: CONFIRMED]
  ↓ (always)
collect_address [FSM: CONFIRMED] — expects_user_input: true
  ↓ (always)
create_delivery [FSM: CONFIRMED]
  ↓ (always)
notify_customer [FSM: CONFIRMED] — "Your order is on its way!"
```

FSM Table:
```json
{
  "START": { "MENU": "show_menu" },
  "MENU": { "CART": "collect_cart" },
  "CART": { "CHECKOUT": "calculate_total" },
  "CHECKOUT": { "PAYMENT": "create_payment" },
  "PAYMENT": { "CONFIRMED": "confirm_payment" }
}
```

### G.2 Salon / Appointment Booking

```
show_menu [FSM: MENU] — "Welcome to [Salon Name]! Our services: 1. Haircut 2. Beard 3. Facial"
  ↓ (any_input)
collect_cart [FSM: CART] — collects service selection
  ↓ (always)
create_order [FSM: CHECKOUT] — saves booking record
  ↓ (always)
create_payment [FSM: PAYMENT] — advance payment
  ↓ (always)
confirm_payment [FSM: CONFIRMED]
  ↓ (always)
notify_customer [FSM: CONFIRMED] — "Booking confirmed! See you at [time]."
```

### G.3 Clinic / Medical Consultation

```
show_menu [FSM: MENU] — "Welcome to [Clinic]! 1. Consultation 2. Follow-up 3. Lab Test"
  ↓ (any_input)
collect_cart [FSM: CART] — collects consultation type
  ↓ (always)
create_order [FSM: CHECKOUT] — registers appointment
  ↓ (always)
create_payment [FSM: PAYMENT] — consultation fee
  ↓ (always)
confirm_payment [FSM: CONFIRMED]
  ↓ (always)
notify_customer [FSM: CONFIRMED] — "Appointment confirmed. Doctor will see you at [time]."
```

### G.4 Support Escalation Flow

```
show_menu [FSM: MENU] — "Hello! How can we help? 1. Order Issue 2. Payment Problem 3. Other"
  ↓ (input_equals: "3")
collect_cart [FSM: CART] — collects issue description
  ↓ (always)
notify_customer [FSM: CONFIRMED] — "Your issue has been escalated. Our team will contact you within 2 hours."
```

### G.5 Cancellation Flow (Conditional Branch)

```
show_menu [FSM: MENU]
  ↓ (input_equals: "CANCEL_ORDER") → notify_customer [FSM: CANCELLED] — "Order cancelled."
  ↓ (input_equals: "1") → collect_cart [FSM: CART]
```

---

## H. BUSINESS CONTEXT ADAPTATION

### H.1 Principle

The same FlowCore runtime engine powers ALL business types.
The ONLY difference is the workflow graph structure and node configurations.

AI generators MUST adapt workflows per business type:

| Business | Entry Message Style | Order Noun | Catalog Noun | Key Modules |
|---|---|---|---|---|
| Restaurant | "Welcome! Here's our menu" | Order | Menu | show_menu, collect_cart, create_payment, create_delivery |
| Salon | "Welcome! Book your service" | Booking | Services | show_menu, collect_cart, create_order, create_payment |
| Clinic | "Welcome! Book consultation" | Appointment | Consultations | show_menu, collect_cart, create_order, create_payment |
| Gym | "Welcome! Choose your plan" | Membership | Plans | show_menu, collect_cart, create_payment |
| E-commerce | "Welcome! Browse our store" | Order | Products | show_menu, collect_cart, calculate_total, create_payment, create_delivery |
| Education | "Welcome! Enroll in a course" | Enrollment | Courses | show_menu, collect_cart, create_payment |

### H.2 Dynamic Operational Actions Per Business

Actions exposed to customers must be legal for the current FSM state AND relevant to the business type:

```
RESTAURANT in CONFIRMED state:
  ✓ Track Delivery
  ✓ Reorder
  ✓ Contact Support

SALON in CONFIRMED state:
  ✓ Reschedule Booking
  ✓ Cancel Booking
  ✓ Contact Stylist

CLINIC in CONFIRMED state:
  ✓ View Prescription
  ✓ Contact Reception
  ✓ Book Follow-up

GYM in CONFIRMED state:
  ✓ View Membership
  ✓ Book Trainer
  ✓ Track Workout
```

### H.3 Business-Specific Terminology in Messages

All `show_menu` and `notify_customer` messages must use terminology natural to the business:

```
WRONG (generic): "Welcome! Select an item."
RIGHT (restaurant): "Welcome to Shiva's Kitchen! 🍕 Here's our menu..."
RIGHT (salon): "Welcome to Luxe Salon! ✨ Select a service..."
RIGHT (clinic): "Welcome to Apollo Clinic! 🩺 How can we help you today?"
RIGHT (gym): "Welcome to Titan Fitness! 💪 Choose your plan..."
```

---

## I. DYNAMIC ACTION GENERATION RULES

### I.1 Operational Action IDs (Standardized)

These IDs are used as WhatsApp interactive button IDs. They map to user input strings that FlowCore dispatches:

| Action ID | Title Text | Legal FSM States |
|---|---|---|
| `VIEW_CART` | View Cart | CART, CHECKOUT |
| `CLEAR_CART` | Clear Cart | CART |
| `CANCEL_ORDER` | Cancel Order | CHECKOUT, PAYMENT |
| `RETRY_PAYMENT` | Retry Payment | PAYMENT |
| `TRACK_DELIVERY` | Track Delivery | CONFIRMED |
| `CONTACT_SUPPORT` | Contact Support | Any |
| `REORDER` | Reorder | CONFIRMED, CANCELLED |
| `RESCHEDULE_BOOKING` | Reschedule | CONFIRMED (salon/clinic) |
| `CANCEL_BOOKING` | Cancel Booking | CONFIRMED (salon/clinic) |
| `VIEW_MEMBERSHIP` | View Membership | CONFIRMED (gym) |
| `RENEW_PLAN` | Renew Plan | CONFIRMED (gym) |
| `BOOK_TRAINER` | Book Trainer | CONFIRMED (gym) |
| `TRACK_SHIPMENT` | Track Shipment | CONFIRMED (ecommerce) |
| `RETURN_PRODUCT` | Return Product | CONFIRMED (ecommerce) |

### I.2 Action Legality Rule

**The FlowCore backend is ALWAYS the source of truth for what actions are legal in any given state.**

n8n derives allowed actions from the `fsm_state` field returned by FlowCore dispatch.
AI generators pre-define which actions should appear per workflow stage.
The frontend renders only what FlowCore's runtime state permits.

---

## J. WORKFLOW VALIDATION CHECKLIST

Before submitting a generated workflow for validation, verify:

- [ ] `entry_node_id` exists as a key in `nodes{}`
- [ ] Every node's `module_name` is in the registered module list (B.1–B.9)
- [ ] Every node with payment config has `gateway` and `currency` fields
- [ ] Every `collect_*` node has `expects_user_input: true`
- [ ] No cycles exist unless broken by conditional edges
- [ ] All leaf nodes are in terminal FSM states OR have `expects_user_input: true`
- [ ] `fsm_transition_table` contains every `fsm_transition_to` declared in nodes
- [ ] `collect_address` precedes `create_delivery`
- [ ] `create_order` or `collect_cart` precedes `create_payment`
- [ ] All edge condition types are from the registered condition list
- [ ] `input_in` condition values are arrays, not strings

---

## K. CAPABILITY REGISTRY

### K.1 Overview

The Capability Registry is the **authoritative source of all workflow capabilities** in FlowCore.

Every capability (module) that can appear as a node in a workflow graph MUST be registered in the
Capability Registry before it can be used. The AI generator MUST query the registry and only generate
nodes using registered capability names.

```
Capability Registry
  ↓
Generator looks up valid capabilities
  ↓
Generator assembles workflow nodes from registry entries only
  ↓
Validator confirms every module_name is registered
```

**Key principles**:
- Capabilities are **versioned** — a capability can evolve (v1 → v2) without breaking existing workflows
- Capabilities are **categorized** into packs (see Section L)
- The registry defines what inputs, outputs, FSM states, and events each capability supports
- AI generators must NEVER invent capability names not present in the registry

### K.2 Capability Schema

Each registered capability has the following structure:

```json
{
  "module_name": "string",
  "version": "string",
  "category": "string",
  "description": "string",
  "required_config": [
    { "key": "string", "type": "string", "description": "string" }
  ],
  "optional_config": [
    { "key": "string", "type": "string", "description": "string", "default": "any" }
  ],
  "allowed_fsm_states": ["STATE_A", "STATE_B"],
  "events_emitted": ["EVENT_NAME"],
  "events_consumed": ["EVENT_NAME"]
}
```

### K.3 Currently Registered Capabilities

| module_name | version | category | allowed_fsm_states | events_emitted |
|---|---|---|---|---|
| `show_menu` | 1.0 | Core | START, MENU, CART, CANCELLED, CONFIRMED | — |
| `collect_cart` | 1.0 | Core | MENU, BROWSING, CART | — |
| `calculate_total` | 1.0 | Core | CART, CHECKOUT | — |
| `create_order` | 1.0 | Core | CART, CHECKOUT | `ORDER_CREATED` |
| `create_payment` | 1.0 | Core | CHECKOUT, PAYMENT | `PAYMENT_REQUIRED` |
| `confirm_payment` | 1.0 | Core | PAYMENT, CONFIRMED | `PAYMENT_COMPLETED` |
| `collect_address` | 1.0 | Core | CHECKOUT, CONFIRMED | — |
| `create_delivery` | 1.0 | Core | CHECKOUT, CONFIRMED | `DELIVERY_CREATED` |
| `notify_customer` | 1.0 | Core | ALL | — |

### K.4 How Generators Must Use the Registry

1. Before generating any node, the generator queries the registry for available capabilities
2. Each generated node's `module_name` must exactly match a registry entry
3. The generator uses `required_config` to ensure all mandatory config keys are populated
4. The generator uses `allowed_fsm_states` to validate `fsm_transition_to` assignments
5. The generator uses `events_emitted` to know which events follow a node execution

---

## L. CAPABILITY PACKS

### L.1 Overview

Capability Packs are curated collections of capabilities grouped by business domain.
They guide the generator toward the most appropriate modules for a given business type.

```
Business Description
  ↓
Business Type Detection
  ↓
Capability Pack Selection
  ↓
Workflow Generation using Pack Capabilities
```

Generators MUST prefer capabilities from the matching pack before selecting generic capabilities.

### L.2 Core Pack (Universal — Available to All Business Types)

These capabilities are available to every business type and form the foundation of all workflows:

| Capability | Purpose |
|---|---|
| `show_menu` | Display menu / catalog / options |
| `collect_cart` | Collect customer selection / input |
| `calculate_total` | Sum cart items |
| `create_order` | Persist order to database |
| `create_payment` | Generate payment link |
| `confirm_payment` | Confirm payment received |
| `collect_address` | Collect delivery address |
| `create_delivery` | Dispatch delivery |
| `notify_customer` | Send status notification |

### L.3 Restaurant Pack

**Recommended for**: Food ordering, cafes, cloud kitchens, food trucks, pizza delivery

**Recommended workflow flow**:
```
show_menu → collect_cart → calculate_total → create_order
  → create_payment → confirm_payment → collect_address
  → create_delivery → notify_customer
```

**Pack Capabilities**:
- `show_menu` — display food menu with prices
- `collect_cart` — collect item and quantity selection
- `calculate_total` — sum food order total
- `create_order` — save food order record
- `create_payment` — generate Stripe/Razorpay payment link
- `collect_address` — collect delivery address
- `create_delivery` — dispatch delivery courier
- `notify_customer` — send order confirmation and delivery status

**Typical Workflows Generated**:
- Ordering Workflow (primary)
- Support Workflow
- Feedback/CSAT Workflow
- Reservation Workflow (future)

### L.4 Salon Pack

**Recommended for**: Hair salons, barbershops, nail studios, spas, wellness centers

**Recommended workflow flow**:
```
show_menu → collect_cart → create_order → create_payment
  → confirm_payment → notify_customer
```

**Pack Capabilities**:
- `show_menu` — display services and pricing
- `collect_cart` — collect service and slot selection
- `create_order` — save booking record
- `create_payment` — advance payment for booking
- `confirm_payment` — confirm booking payment
- `notify_customer` — send booking confirmation with slot details

**Typical Workflows Generated**:
- Booking Workflow (primary)
- Cancellation/Reschedule Workflow
- Feedback Workflow
- Support Workflow

### L.5 Clinic Pack

**Recommended for**: Medical clinics, physiotherapy centers, dental practices, diagnostic labs

**Recommended workflow flow**:
```
show_menu → collect_cart → create_order → create_payment
  → confirm_payment → notify_customer
```

**Pack Capabilities**:
- `show_menu` — display consultation types and specialist list
- `collect_cart` — collect consultation type and preferred slot
- `create_order` — register appointment
- `create_payment` — collect consultation fee
- `confirm_payment` — confirm payment and appointment
- `notify_customer` — send appointment confirmation with doctor details

**Typical Workflows Generated**:
- Appointment Workflow (primary)
- Lab Test Booking Workflow
- Follow-up Workflow
- Support Workflow

### L.6 Hospital Pack

**Recommended for**: Hospitals, multispecialty centers, surgical centers, emergency departments

**Pack Capabilities**: All Clinic Pack capabilities plus:
- `create_order` — admission registration
- `create_payment` — billing/deposit

**Typical Workflows Generated**:
- Appointment Workflow
- Admission Workflow
- Billing Workflow
- Lab Test Workflow
- Support Workflow

### L.7 Gym Pack

**Recommended for**: Fitness centers, CrossFit gyms, yoga studios, personal training studios

**Recommended workflow flow**:
```
show_menu → collect_cart → create_order → create_payment
  → confirm_payment → notify_customer
```

**Pack Capabilities**:
- `show_menu` — display membership plans, class schedules
- `collect_cart` — collect plan or class selection
- `create_order` — record membership or class booking
- `create_payment` — collect membership fee
- `confirm_payment` — confirm enrollment
- `notify_customer` — send membership activation confirmation

**Typical Workflows Generated**:
- Membership Enrollment Workflow (primary)
- Class Booking Workflow
- Personal Training Booking Workflow
- Support Workflow

### L.8 Ecommerce Pack

**Recommended for**: Online stores, product marketplaces, electronics, fashion, consumer goods

**Recommended workflow flow**:
```
show_menu → collect_cart → calculate_total → create_order
  → create_payment → confirm_payment → collect_address
  → create_delivery → notify_customer
```

**Pack Capabilities**: All Restaurant Pack capabilities.

**Typical Workflows Generated**:
- Product Ordering Workflow (primary)
- Return/Refund Workflow
- Support Workflow
- Feedback Workflow

### L.9 Real Estate Pack

**Recommended for**: Property agencies, rental services, property tours, housing projects

**Recommended workflow flow**:
```
show_menu → collect_cart → create_order → notify_customer
```

**Pack Capabilities**:
- `show_menu` — display available properties or tour slots
- `collect_cart` — collect property interest and contact details
- `create_order` — record tour/viewing request
- `notify_customer` — confirm tour scheduling with agent contact

**Typical Workflows Generated**:
- Property Tour Booking Workflow (primary)
- Site Visit Scheduling Workflow
- Support Workflow

### L.10 Education Pack

**Recommended for**: Online courses, coaching centers, tutoring services, universities

**Recommended workflow flow**:
```
show_menu → collect_cart → create_order → create_payment
  → confirm_payment → notify_customer
```

**Pack Capabilities**:
- `show_menu` — display courses or programs available
- `collect_cart` — collect course selection and batch preference
- `create_order` — register enrollment
- `create_payment` — collect course fee
- `confirm_payment` — confirm enrollment payment
- `notify_customer` — send enrollment confirmation with access details

**Typical Workflows Generated**:
- Course Enrollment Workflow (primary)
- Batch Scheduling Workflow
- Support Workflow

### L.11 Service Business Pack

**Recommended for**: Home services, repairs, cleaning, plumbing, electricians, event management

**Recommended workflow flow**:
```
show_menu → collect_cart → create_order → notify_customer
```

**Pack Capabilities**:
- `show_menu` — display services and pricing
- `collect_cart` — collect service type and address
- `create_order` — record service request
- `notify_customer` — confirm service appointment with technician ETA

**Typical Workflows Generated**:
- Service Request Workflow (primary)
- Support Workflow
- Feedback Workflow

### L.12 Future Packs (Planned)

The following packs are planned for future FlowCore releases:

| Pack | Business Types |
|---|---|
| Hotel Pack | Hotels, hostels, resort booking |
| Travel Pack | Tour operators, flight queries, travel agents |
| Pharmacy Pack | Prescription orders, medicine delivery |
| Legal Pack | Law firms, consultation booking |
| Insurance Pack | Policy inquiries, claim registration |
| Finance Pack | Loan applications, account queries |

> **Generator rule**: If no matching pack exists for a business type, fall back to the **Service Business Pack** and use Core capabilities only.

---

## M. EVENT REGISTRY

### M.1 Overview

The Event Registry is the authoritative list of platform-defined events in FlowCore.

Events are the communication backbone between workflows. When one workflow completes an action
(e.g., ORDER_DELIVERED), it emits an event that can trigger another workflow (e.g., Feedback Workflow).

**Generator rules**:
- AI generators MUST use only registered event names
- Never invent event names (e.g., `ORDER_DONE`, `BOOKING_OK` are INVALID)
- Use the exact registered event name (case-sensitive, SCREAMING_SNAKE_CASE)
- A capability's `events_emitted` list defines which events that node can emit

### M.2 Event Schema

```json
{
  "event_name": "string",
  "payload_schema": {
    "field_name": "type"
  },
  "description": "string"
}
```

### M.3 Registered Events

#### Order Events

| Event Name | Payload Fields | Description |
|---|---|---|
| `ORDER_CREATED` | `order_id`, `business_id`, `customer_phone`, `items`, `total` | Emitted when a customer order is persisted |
| `ORDER_UPDATED` | `order_id`, `field_updated`, `new_value` | Emitted when order details are modified |
| `ORDER_CANCELLED` | `order_id`, `reason` | Emitted when an order is cancelled |

#### Payment Events

| Event Name | Payload Fields | Description |
|---|---|---|
| `PAYMENT_REQUIRED` | `order_id`, `amount`, `currency`, `payment_url` | Emitted when a payment link is generated |
| `PAYMENT_COMPLETED` | `order_id`, `transaction_id`, `amount` | Emitted when payment is confirmed |
| `PAYMENT_FAILED` | `order_id`, `reason`, `retry_allowed` | Emitted when payment verification fails |

#### Delivery Events

| Event Name | Payload Fields | Description |
|---|---|---|
| `DELIVERY_CREATED` | `delivery_id`, `order_id`, `address`, `carrier` | Emitted when a delivery dispatch is registered |
| `DELIVERY_COMPLETED` | `delivery_id`, `order_id`, `delivered_at` | Emitted when delivery is confirmed complete |

#### Booking Events

| Event Name | Payload Fields | Description |
|---|---|---|
| `BOOKING_CREATED` | `booking_id`, `service`, `date`, `slot`, `customer_phone` | Emitted when a service booking is created |
| `BOOKING_CANCELLED` | `booking_id`, `reason` | Emitted when a booking is cancelled |

#### Support Events

| Event Name | Payload Fields | Description |
|---|---|---|
| `SUPPORT_REQUESTED` | `session_id`, `issue`, `customer_phone` | Emitted when a customer initiates a support ticket |
| `SUPPORT_ESCALATED` | `ticket_id`, `priority`, `assigned_to` | Emitted when a ticket is escalated to a human agent |

#### Approval Events

| Event Name | Payload Fields | Description |
|---|---|---|
| `APPROVAL_REQUESTED` | `context_id`, `context_type`, `requestor` | Emitted when an action requires human approval |
| `APPROVAL_GRANTED` | `context_id`, `approved_by` | Emitted when an approval action is confirmed |
| `APPROVAL_REJECTED` | `context_id`, `reason` | Emitted when an approval is rejected |

#### Customer Events

| Event Name | Payload Fields | Description |
|---|---|---|
| `CUSTOMER_CREATED` | `customer_id`, `customer_phone`, `business_id` | Emitted when a new customer context is created |

### M.4 Event-Driven Workflow Composition

Events are the preferred mechanism for connecting workflows across a portfolio:

```
Workflow A emits: ORDER_DELIVERED
         ↓
Event Bus routes to subscribers
         ↓
Feedback Workflow triggered (subscribed to ORDER_DELIVERED)
```

This is PREFERRED over embedding feedback logic inside the ordering workflow.

---

## N. WORKFLOW PORTFOLIO ARCHITECTURE

### N.1 Overview

FlowCore is designed around a **multi-workflow portfolio model**, not a single monolithic workflow per business.

```
One Business
  ↓
Many Focused Workflows
  ↓
Event-Driven Composition
```

Each business should have a portfolio of small, focused workflows — each handling a single
business concern — connected through the Event Registry.

### N.2 Portfolio Principle

**WRONG**: One giant workflow handling ordering + feedback + support + cancellation in one graph.

**CORRECT**: Separate focused workflows triggered by events.

| | Wrong | Correct |
|---|---|---|
| Complexity | One 20-node graph | Multiple 4–8 node graphs |
| Testability | Hard to test in isolation | Each workflow independently testable |
| Reusability | Support logic locked inside ordering | Support Workflow reusable by all workflows |
| Event composition | Not supported | Workflows compose via events naturally |
| Maintainability | Entire graph must be redeployed for any change | Only affected workflow needs redeployment |

### N.3 Restaurant Portfolio Example

```
Restaurant Business
  ├── Ordering Workflow        ← Primary: handles customer ordering
  ├── Support Workflow         ← Triggered by: SUPPORT_REQUESTED
  ├── Feedback Workflow        ← Triggered by: DELIVERY_COMPLETED
  └── Reservation Workflow     ← Triggered by: direct session or BOOKING_CREATED
```

Event connections:
```
Ordering Workflow
  → emits ORDER_CREATED
  → emits PAYMENT_COMPLETED
  → emits DELIVERY_CREATED
  → emits DELIVERY_COMPLETED  →  Feedback Workflow (auto-triggered)
```

### N.4 Hospital Portfolio Example

```
Hospital Business
  ├── Appointment Workflow     ← Primary: doctor appointment booking
  ├── Admission Workflow       ← Handles inpatient registration
  ├── Billing Workflow         ← Triggered by: APPROVAL_GRANTED
  ├── Lab Test Workflow        ← Triggered by: BOOKING_CREATED (lab type)
  └── Support Workflow         ← Triggered by: SUPPORT_REQUESTED
```

Event connections:
```
Appointment Workflow
  → emits BOOKING_CREATED     →  Lab Test Workflow (if lab test type)
  → emits APPROVAL_REQUESTED  →  Billing Workflow
```

### N.5 Portfolio Generation Strategy

When generating a workflow portfolio for a business, follow this sequence:

1. **Identify the primary transaction** (ordering, booking, enrollment) → generate primary workflow
2. **Generate Support Workflow** — always include for every business type
3. **Generate Feedback Workflow** — triggered by completion events from primary workflow
4. **Generate domain-specific secondary workflows** (e.g., Reservation, Lab Test, Return/Refund)
5. **Map event connections** — specify which events trigger which secondary workflows
6. **Validate each workflow independently** before combining into the portfolio

---

## O. BUSINESS CONFIGURATION MODEL

### O.1 Overview

FlowCore separates **workflow structure** (generated by AI) from **business configuration**
(supplied by the business operator via the FlowCore dashboard).

AI generators MUST NOT hardcode business-specific data into workflow graphs.

```
AI Generator                   Business Operator
  ↓                                  ↓
Workflow Structure         Business Configuration
(graph, nodes, edges)      (catalog, providers, branding,
                            credentials, settings)
  ↓                                  ↓
          FlowCore Platform
              (combines both at runtime)
```

### O.2 Business Configuration Schema

```json
{
  "business": {
    "business_id": "string (UUID)",
    "business_name": "string",
    "business_type": "string (Restaurant | Salon | Clinic | ...)",
    "branding": {
      "logo_url": "string",
      "theme_color": "string (hex)",
      "welcome_message": "string"
    },
    "providers": {
      "payment": {
        "gateway": "stripe | razorpay | cod",
        "currency": "USD | INR | EUR | ...",
        "credentials": "INJECTED_BY_PLATFORM"
      },
      "delivery": {
        "provider": "porter | shiprocket | custom",
        "credentials": "INJECTED_BY_PLATFORM"
      },
      "notification": {
        "provider": "meta_cloud | twilio",
        "credentials": "INJECTED_BY_PLATFORM"
      }
    },
    "catalog": {
      "items": [
        {
          "id": "string",
          "name": "string",
          "price": 0.00,
          "category": "string",
          "description": "string"
        }
      ]
    },
    "settings": {
      "timezone": "string",
      "language": "en | hi | ...",
      "auto_reply": true
    }
  }
}
```

### O.3 What Generators Must NOT Do

| ❌ WRONG — Generator doing this | ✅ CORRECT — Platform supplies this |
|---|---|
| Hardcoding `"gateway": "stripe"` in workflow config | `gateway` comes from provider config |
| Writing `"menu_header": "1. Margherita Pizza $12"` | Catalog items come from business catalog |
| Including API keys or credentials in nodes | Credentials are injected by platform at runtime |
| Writing `"theme_color": "#00FF00"` in messages | Branding comes from business branding config |
| Inventing product names in menu messages | Use placeholder like `[CATALOG_ITEMS_HERE]` |

> **Exception**: The generator may use generic placeholder text like `"Welcome to {business_name}! Here are your options:"` where `{business_name}` is a template variable resolved at runtime.

### O.4 Separation of Concerns Summary

| Concern | Owned By |
|---|---|
| Workflow DAG structure | AI Generator |
| Node module selection | AI Generator (from registry) |
| FSM transition table | AI Generator |
| Edge routing conditions | AI Generator |
| Catalog / product list | Business Operator |
| Payment gateway credentials | Business Operator |
| Delivery provider config | Business Operator |
| Branding / logo / colors | Business Operator |
| Welcome message content | Business Operator |
| Provider API credentials | Platform (never exposed to generator) |

---

## P. PROVIDER REGISTRY

### P.1 Overview

The Provider Registry manages all external service integrations available to FlowCore workflows.
Providers are categorized by function: Payment, Delivery, and Notification.

**Critical generator rule**: Generators MUST use generic capability names, not provider-specific names.
Provider selection is a configuration concern handled by the business operator, not the generator.

### P.2 Provider Categories

#### Payment Providers

| Provider | Internal ID | Currencies Supported |
|---|---|---|
| Stripe | `stripe` | USD, EUR, GBP, AUD, CAD |
| Razorpay | `razorpay` | INR |
| Cash on Delivery | `cod` | Any |
| PayPal | `paypal` | USD, EUR |

#### Delivery Providers

| Provider | Internal ID | Supported Regions |
|---|---|---|
| Porter | `porter` | India |
| Shiprocket | `shiprocket` | India |
| Custom Courier | `custom` | Any |
| Dunzo | `dunzo` | India (hyperlocal) |

#### Notification Providers

| Provider | Internal ID | Channel |
|---|---|---|
| Meta Cloud API | `meta_cloud` | WhatsApp |
| Twilio | `twilio` | WhatsApp, SMS |

### P.3 Generator Rules for Providers

**Always use generic capability names in workflow nodes:**

```
✅ CORRECT:
  module_name: "create_payment"    ← generic
  module_name: "create_delivery"   ← generic
  module_name: "notify_customer"   ← generic

❌ WRONG:
  module_name: "create_stripe_payment"      ← provider-specific
  module_name: "create_razorpay_payment"    ← provider-specific
  module_name: "create_porter_delivery"     ← provider-specific
  module_name: "create_shiprocket_delivery" ← provider-specific
  module_name: "send_whatsapp_message"      ← provider-specific
```

**In `create_payment` config, use a placeholder or default:**

```json
{
  "module_name": "create_payment",
  "config": {
    "gateway": "cod",
    "currency": "USD"
  }
}
```

The platform replaces `"cod"` with the business-configured gateway at runtime.

### P.4 Provider Abstraction Model

```
Generated Workflow
  ↓ uses generic: create_payment
FlowCore Runtime
  ↓ resolves business provider config
Provider Registry
  ↓ selects configured provider (e.g., Stripe for US, Razorpay for India)
n8n Orchestration
  ↓ executes provider-specific API call
External Provider API
```

The generator never needs to know which provider is used. It only specifies the capability.

---

## Q. WORKFLOW GENERATION PIPELINE

### Q.1 Official Generation Process

The complete generation pipeline that AI generators must follow:

```
Step 1: BUSINESS DESCRIPTION RECEIVED
   "I run a pizza restaurant in Mumbai. We sell Margherita, 
    Pepperoni, and Veggie pizzas. Customers pay via Razorpay."
  ↓

Step 2: BUSINESS TYPE DETECTION
   Keywords: pizza, restaurant, menu → Category: Restaurant
   Detected Pack: Restaurant Pack
  ↓

Step 3: CAPABILITY PACK SELECTION
   Load Restaurant Pack capabilities:
   show_menu, collect_cart, calculate_total, create_order,
   create_payment, confirm_payment, collect_address,
   create_delivery, notify_customer
  ↓

Step 4: CAPABILITY REGISTRY LOOKUP
   For each selected capability, verify:
   - Is it registered? ✓
   - What FSM states does it allow? ✓
   - What config is required? ✓
   - What events does it emit? ✓
  ↓

Step 5: EVENT REGISTRY LOOKUP
   Identify events the portfolio should emit and consume:
   - Primary: ORDER_CREATED, PAYMENT_COMPLETED, DELIVERY_COMPLETED
   - Cross-workflow: DELIVERY_COMPLETED → Feedback Workflow
   - SUPPORT_REQUESTED → Support Workflow
  ↓

Step 6: WORKFLOW PORTFOLIO GENERATION
   Generate each workflow in the portfolio:
   a) Ordering Workflow (primary)
   b) Support Workflow
   c) Feedback Workflow
   d) Reservation Workflow (optional)
  ↓

Step 7: STATIC VALIDATION (per workflow)
   For each workflow:
   - Acyclic graph check
   - FSM transition table completeness check
   - Module contract compliance check
   - Carry dependency ordering check
   - Dead-end node detection
  ↓

Step 8: REPAIR (if validation errors found)
   Attempt to auto-repair common errors:
   - Add missing fsm_transition_table entries
   - Fix FSM state mismatches
   - Add missing collect_address before create_delivery
   - Add missing create_order before create_payment
  ↓

Step 9: DEPLOYMENT
   Register validated workflows to FlowCore platform:
   POST /api/v1/workflows/register (for each workflow)
   POST /api/v1/workflows/activate/{version_id} (for primary)
```

### Q.2 Generator Mindset

The generator is NOT inventing workflows from scratch.

The generator is **assembling workflows** from registered platform primitives, following established
patterns for the detected business type, respecting FSM rules, and connecting workflows through
the Event Registry.

```
WRONG mindset: "I will create a unique workflow for this business"
RIGHT mindset: "I will select the right capabilities from the Restaurant Pack,
               arrange them in the proven ordering flow pattern,
               and connect the portfolio through standard events"
```

---

## R. MULTI-WORKFLOW EXAMPLES

### R.1 Restaurant Portfolio — Full Example

**Business**: "Pizza Planet" — pizza restaurant with delivery

#### Ordering Workflow (Primary)

```
show_menu [FSM: MENU]
  "🍕 Welcome to Pizza Planet! Our Menu:
   1. Margherita Pizza - [price]
   2. Pepperoni Pizza - [price]
   3. Veggie Delight - [price]
   Reply with item & quantity (e.g. '1 x 2')"
  ↓ (any_input)
collect_cart [FSM: CART] — expects_user_input: true
  ↓ (always)
calculate_total [FSM: CHECKOUT]
  ↓ (always)
create_order [FSM: CHECKOUT]       → emits: ORDER_CREATED
  ↓ (always)
create_payment [FSM: PAYMENT]      → emits: PAYMENT_REQUIRED
  ↓ (input_equals: "CONFIRM_PAYMENT")
confirm_payment [FSM: CONFIRMED]   → emits: PAYMENT_COMPLETED
  ↓ (always)
collect_address [FSM: CONFIRMED] — expects_user_input: true
  ↓ (always)
create_delivery [FSM: CONFIRMED]   → emits: DELIVERY_CREATED
  ↓ (always)
notify_customer [FSM: CONFIRMED]
  "📦 Your order is confirmed and on its way! Track via TRACK_DELIVERY."
```

#### Support Workflow (Triggered by: SUPPORT_REQUESTED)

```
show_menu [FSM: MENU]
  "🛠️ Pizza Planet Support — How can we help?
   1. Order Issue  2. Payment Problem  3. Other"
  ↓ (any_input)
collect_cart [FSM: CART] — expects_user_input: true
  ↓ (always)
notify_customer [FSM: CONFIRMED]   → emits: SUPPORT_ESCALATED
  "✅ Ticket logged! Our team will contact you within 30 minutes."
```

#### Feedback Workflow (Triggered by: DELIVERY_COMPLETED)

```
show_menu [FSM: MENU]
  "🌟 Hi! How was your Pizza Planet experience?
   Rate us 1–5 (1=Poor, 5=Excellent)"
  ↓ (any_input)
collect_cart [FSM: CART] — expects_user_input: true
  ↓ (always)
notify_customer [FSM: CONFIRMED]
  "🙏 Thank you for your feedback! Enjoy your next order with us."
```

#### Event Connections

```
ORDER_CREATED         → Logged to operations dashboard
PAYMENT_COMPLETED     → Triggers delivery dispatch
DELIVERY_COMPLETED    → Auto-triggers Feedback Workflow
SUPPORT_REQUESTED     → Auto-triggers Support Workflow
```

---

### R.2 Hospital Portfolio — Full Example

**Business**: "Apollo Health Center" — multispecialty hospital

#### Appointment Workflow (Primary)

```
show_menu [FSM: MENU]
  "🏥 Welcome to Apollo Health Center!
   1. General Consultation
   2. Specialist Visit
   3. Lab Test Booking
   4. Follow-up Appointment"
  ↓ (any_input)
collect_cart [FSM: CART] — expects_user_input: true
  ↓ (always)
create_order [FSM: CHECKOUT]       → emits: BOOKING_CREATED
  ↓ (always)
create_payment [FSM: PAYMENT]      → emits: PAYMENT_REQUIRED
  ↓ (input_equals: "CONFIRM_PAYMENT")
confirm_payment [FSM: CONFIRMED]   → emits: PAYMENT_COMPLETED
  ↓ (always)
notify_customer [FSM: CONFIRMED]
  "✅ Appointment confirmed! Your doctor will see you on [date] at [slot]."
```

#### Lab Test Workflow (Triggered by: BOOKING_CREATED with type=lab)

```
show_menu [FSM: MENU]
  "🔬 Apollo Lab Services — Select your test:
   1. Blood Panel  2. X-Ray  3. MRI  4. Urine Analysis"
  ↓ (any_input)
collect_cart [FSM: CART] — expects_user_input: true
  ↓ (always)
create_order [FSM: CHECKOUT]       → emits: BOOKING_CREATED
  ↓ (always)
create_payment [FSM: PAYMENT]      → emits: PAYMENT_REQUIRED
  ↓ (input_equals: "CONFIRM_PAYMENT")
confirm_payment [FSM: CONFIRMED]   → emits: PAYMENT_COMPLETED
  ↓ (always)
notify_customer [FSM: CONFIRMED]
  "🧪 Lab test booked! Report collection at Apollo Lab, Gate 3."
```

#### Billing Workflow (Triggered by: APPROVAL_GRANTED)

```
show_menu [FSM: MENU]
  "💳 Apollo Billing — Your consultation has been approved.
   Total due: [amount]
   Reply 'PAY' to proceed."
  ↓ (input_equals: "PAY")
create_payment [FSM: PAYMENT]      → emits: PAYMENT_REQUIRED
  ↓ (input_equals: "CONFIRM_PAYMENT")
confirm_payment [FSM: CONFIRMED]   → emits: PAYMENT_COMPLETED
  ↓ (always)
notify_customer [FSM: CONFIRMED]
  "✅ Payment received. Your invoice has been sent."
```

#### Support Workflow (Triggered by: SUPPORT_REQUESTED)

```
show_menu [FSM: MENU]
  "🏥 Apollo Support — Please describe your concern:"
  ↓ (any_input)
collect_cart [FSM: CART] — expects_user_input: true
  ↓ (always)
notify_customer [FSM: CONFIRMED]   → emits: SUPPORT_ESCALATED
  "✅ Your concern has been escalated to our patient relations desk."
```

#### Event Connections

```
BOOKING_CREATED (type=lab)     → Lab Test Workflow
APPROVAL_REQUESTED             → Billing Workflow
SUPPORT_REQUESTED              → Support Workflow
PAYMENT_COMPLETED              → Receipt notification
```

---

## S. GENERATOR RULES (MANDATORY)

The following rules are absolute. Any generated workflow that violates them WILL be rejected
by the FlowCore validation pipeline.

### S.1 Module Rules

| Rule | Description |
|---|---|
| **USE REGISTERED MODULES ONLY** | Every `module_name` must exist in the Capability Registry (Section K) |
| **NO INVENTED MODULES** | Never create module names like `send_sms`, `check_stock`, `create_ticket` — these are not registered |
| **RESPECT MODULE CONTRACTS** | Every required config key for a module must be present |
| **RESPECT FSM STATE CONSTRAINTS** | A module can only be used in its declared `allowed_fsm_states` |

### S.2 Event Rules

| Rule | Description |
|---|---|
| **USE REGISTERED EVENTS ONLY** | Every event name must exist in the Event Registry (Section M) |
| **NO INVENTED EVENTS** | Never use names like `ORDER_DONE`, `BOOKING_OK`, `CUSTOMER_PAID` |
| **EXACT CASE** | Event names are SCREAMING_SNAKE_CASE — `ORDER_CREATED` not `order_created` |
| **CROSS-WORKFLOW VIA EVENTS** | Workflows communicate through events, never through direct chaining |

### S.3 Capability Pack Rules

| Rule | Description |
|---|---|
| **PREFER PACK CAPABILITIES** | Always start with the matching capability pack for the business type |
| **PACK FIRST, CORE SECOND** | Use pack-recommended capabilities before generic alternatives |
| **NO MIXING UNRELATED PACKS** | Do not use Salon Pack capabilities inside a Restaurant workflow |

### S.4 FSM Rules

| Rule | Description |
|---|---|
| **VALID STATES ONLY** | Use only: START, MENU, BROWSING, CART, CHECKOUT, PAYMENT, CONFIRMED, CANCELLED, ERROR |
| **NO INVENTED FSM STATES** | Never use states like `PROCESSING`, `WAITING`, `PENDING` |
| **COMPLETE TRANSITION TABLE** | Every `fsm_transition_to` in nodes must appear in `fsm_transition_table` |
| **TERMINAL STATE LEAVES** | All leaf nodes must be in CONFIRMED, CANCELLED, or ERROR — or have `expects_user_input: true` |
| **NO TERMINAL STATE ESCAPE** | Once in CONFIRMED/CANCELLED/ERROR, no outgoing edges allowed |

### S.5 Portfolio Rules

| Rule | Description |
|---|---|
| **PREFER PORTFOLIOS** | Generate multiple focused workflows over one monolithic workflow |
| **EVENT-DRIVEN COMPOSITION** | Use events to trigger secondary workflows, not internal graph branches |
| **ALWAYS INCLUDE SUPPORT** | Every business portfolio must include a Support Workflow |
| **FEEDBACK WHERE APPLICABLE** | Delivery-based businesses should include a Feedback Workflow triggered by DELIVERY_COMPLETED |

### S.6 Provider Rules

| Rule | Description |
|---|---|
| **USE GENERIC CAPABILITIES** | Always `create_payment`, never `create_stripe_payment` |
| **NO PROVIDER CREDENTIALS** | Never include API keys, secrets, or tokens in workflow config |
| **NO HARDCODED URLS** | Never hardcode Stripe URLs, webhook endpoints, or provider endpoints |

### S.7 Business Data Rules

| Rule | Description |
|---|---|
| **NO CATALOG HARDCODING** | Never embed specific product names or prices in workflow graph nodes |
| **NO CREDENTIAL EMBEDDING** | Payment gateways, phone numbers, and API tokens are operator-supplied |
| **NO BRANDING EMBEDDING** | Colors, logos, and brand styles come from business branding config |
| **USE PLACEHOLDERS** | Use `{business_name}`, `{catalog_items}` as template references in message text |

### S.8 Validation Rules

| Rule | Description |
|---|---|
| **VALIDATE BEFORE SUBMITTING** | Run all checks from Section J before registering the workflow |
| **NEVER BYPASS VALIDATION** | Do not attempt to circumvent static validation — fix the graph instead |
| **REPAIR BEFORE ESCALATING** | Auto-repair common structural errors before returning failure to the user |

---

## T. QUICK REFERENCE — V2 ARCHITECTURE ADDITIONS

This section summarizes the new systems added in v2 and their generator implications:

| System | Reference | Generator Implication |
|---|---|---|
| Capability Registry | Section K | Only use registered `module_name` values |
| Capability Packs | Section L | Select pack by business type, use pack capabilities first |
| Event Registry | Section M | Only use registered event names (SCREAMING_SNAKE_CASE) |
| Portfolio Architecture | Section N | Generate multiple workflows per business, not one giant graph |
| Business Config Model | Section O | Never hardcode catalog, credentials, or branding in graphs |
| Provider Registry | Section P | Use generic capability names (`create_payment` not `create_stripe_payment`) |
| Generation Pipeline | Section Q | Follow 9-step pipeline: Detect → Pack → Registry → Generate → Validate → Deploy |
| Multi-Workflow Examples | Section R | Reference Restaurant and Hospital examples for portfolio patterns |
| Generator Rules | Section S | Follow all mandatory rules — violations cause compile-time rejection |

---

*FlowCore Runtime and Validation Specification Context v2.0*
*Governed by the FlowCore Platform Team*
*All AI generation engines must comply with this document.*
*Violations are rejected at compile time by the FlowCore Validation Pipeline.*

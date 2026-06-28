# FlowCore Runtime and Validation Specification Context (v1)

**Version**: 1.0 | **Applies To**: All AI workflow generation engines (Llama, GPT-compatible) | **Governed By**: FlowCore Runtime Team

This document is the authoritative AI training context for the FlowCore Conversational Workflow Platform.
It defines every schema, constraint, module contract, FSM rule, and workflow pattern that AI generators must respect.

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

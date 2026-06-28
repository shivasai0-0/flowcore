# FlowCore Architecture Specification (System 1)

This document defines the formal data structures, JSON schemas, database layouts, and execution mechanics for the Main Execution Backend (System 1).

## 1. Schema Specifications

### 1.1 Carry Unit Schema
The Carry Unit is a state context map flowing through the graph. The execution engine must ensure it is monotonic and append-only.

```json
{
  "customer_phone": "string",
  "business_id": "string",
  "session_id": "string",
  "workflow_version_id": "string",
  "session_started_at": "string (ISO-8601)",
  "version": 1,
  "data": {
    "cart_total": 120.50,
    "cart_items": [
      {"item_id": "burger_01", "quantity": 2}
    ]
  }
}
```

### 1.2 Module Contract Schema
Every module in the registry exposes a schema contract:

```json
{
  "module_name": "string",
  "display_name": "string",
  "version": "string (semver)",
  "domain": "string (e.g. restaurant, clinic, or * for generic)",
  "requires": ["string"],
  "produces": ["string"],
  "allowed_fsm_states": ["string"],
  "side_effects": ["string"],
  "is_idempotent": true,
  "retry_config": {
    "max_retries": 3,
    "backoff_strategy": "exponential",
    "idempotency_key_fields": ["string"]
  }
}
```

### 1.3 Workflow Graph Schema
Workflows are represented as a JSON DAG:

```json
{
  "workflow_version_id": "string",
  "business_id": "string",
  "version_number": 1,
  "entry_node_id": "string",
  "nodes": {
    "node_id_1": {
      "id": "node_id_1",
      "module_name": "show_menu",
      "config": {
        "menu_header": "Welcome to our Restaurant!"
      },
      "fsm_transition_to": "MENU"
    },
    "node_id_2": {
      "id": "node_id_2",
      "module_name": "collect_cart",
      "config": {},
      "fsm_transition_to": "CART"
    }
  },
  "edges": [
    {
      "from_node": "node_id_1",
      "to_node": "node_id_2",
      "condition": {
        "type": "input_equals",
        "value": "1"
      }
    }
  ],
  "fsm_transition_table": {
    "START": {
      "MENU": "show_menu"
    },
    "MENU": {
      "CART": "collect_cart",
      "CANCELLED": "cancel_flow"
    },
    "CART": {
      "CHECKOUT": "calculate_total"
    }
  }
}
```

## 2. Database Schema Definition

We use standard SQLAlchemy mappings. All tables contain a `business_id` to enforce INV-06 (Business Isolation) at the query wrapper layer.

### 2.1 `businesses`
* `id` (VARCHAR(36), PK)
* `whatsapp_number` (VARCHAR(20), Unique)
* `name` (VARCHAR(255))
* `created_at` (TIMESTAMP)

### 2.2 `workflow_versions`
* `id` (VARCHAR(36), PK)
* `business_id` (VARCHAR(36), FK -> businesses.id)
* `version_number` (INTEGER)
* `status` (VARCHAR(50)) - `DRAFT`, `VALIDATING`, `SIMULATING`, `APPROVED`, `ACTIVE`, `DEPRECATED`, `FAILED`
* `graph_json` (TEXT / JSON)
* `is_current` (BOOLEAN)
* `created_at` (TIMESTAMP)

### 2.3 `sessions`
* `id` (VARCHAR(36), PK)
* `business_id` (VARCHAR(36), FK -> businesses.id)
* `customer_phone` (VARCHAR(20))
* `fsm_state` (VARCHAR(50))
* `current_node_id` (VARCHAR(50), Nullable)
* `carry_unit_json` (TEXT / JSON)
* `workflow_version_id` (VARCHAR(36), FK -> workflow_versions.id)
* `updated_at` (TIMESTAMP)

### 2.4 `execution_logs` (Append-Only)
* `id` (VARCHAR(36), PK)
* `session_id` (VARCHAR(36), FK -> sessions.id)
* `business_id` (VARCHAR(36), FK -> businesses.id)
* `node_id` (VARCHAR(50))
* `module_name` (VARCHAR(100))
* `inputs_json` (TEXT / JSON)
* `outputs_json` (TEXT / JSON)
* `fsm_state_before` (VARCHAR(50))
* `fsm_state_after` (VARCHAR(50))
* `executed_at` (TIMESTAMP)

## 3. Traversal and Execution Logic

Given a session, incoming message payload $I$, and current workflow version graph $G$:

1. **Input Normalization**: Parse payload $I$ to extract textual intent or structured metadata.
2. **Execution Context Setup**:
   * Load Session state $S$ (State $F$, Current Node $N_{curr}$, Context $C$).
   * If session does not exist, create $S_0$ with state `START` and seed Carry Unit $C_0$ with initial fields.
3. **Traversing Edges**:
   * Evaluate conditions on all outgoing edges from $N_{curr}$ using input $I$ and context $C$.
   * Identify next node $N_{next}$.
4. **Safety Checks**:
   * Verify $N_{next}$'s module is allowed in FSM state $F$.
   * Verify $C$ satisfies all dependencies required by $N_{next}$'s module contract.
   * If non-idempotent module: check `execution_logs` for $N_{next}$ execution in this session. If already executed, retrieve cached outputs instead of executing handler.
5. **Execution**:
   * Execute module handler, passing context $C$ and node static config.
   * On failure, execute retry strategy (exponential backoff).
6. **State Mutation**:
   * Perform Carry Unit merge: $C_{new} = C \cup O$ where $O$ is the output of the module. Carry unit version increases by 1.
   * Transition FSM state using FSM transition rules if `fsm_transition_to` is declared.
7. **Write-Back**:
   * Update session record.
   * Write execution log row.

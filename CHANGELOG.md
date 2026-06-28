# Changelog - FlowCore Backend Platform

All notable changes to this project will be documented in this file.

## [1.0.0] - 2026-05-24

### Added
- **Core Database Layer**: Implemented full declarative models and async SQLAlchemy setup supporting SQLite for development and PostgreSQL for production. Added business isolation checks on all queries.
- **Carry Unit namespaces**: Created typed Pydantic sub-namespace validations (`session`, `customer`, `order`, `payment`, `workflow`, `logistics`, `analytics`, `metadata`) and implemented strict merge logic (immutability, append-only order items, locked payment SUCCESS status).
- **Centralized FSM Engine**: Implemented centralized state transitions with transition table validation and terminal state locks.
- **Module Registry**: Established modular contracts with Pydantic schemas checking requirements and produces types, and loaded 10 built-in mock modules (`show_menu`, `collect_cart`, `calculate_total`, `create_order`, `collect_address`, `create_payment`, `confirm_payment`, `create_delivery`, `send_message`, `notify_customer`).
- **Graph Traversal & Cascades**: Built traversal resolver for conditional edges supporting automatic `"always"` cascades.
- **DAG Compiler & Validator**: Implemented reachability, FSM triggers, cycle checks, and static compile-time dataflow dependency checks.
- **Dry-run Simulation**: Implemented sequential simulation within db savepoints with rollback.
- **Trace Replay**: Created execution logs mapping to construct chronological audits.
- **FastAPI Endpoint APIs**: Built routes `/api/v1/businesses`, `/api/v1/workflows`, `/api/v1/sessions`, and `/api/v1/modules`.
- **E2E Test Suite**: Designed comprehensive testing with `pytest-asyncio` on in-memory SQLite database.

### Fixed
- **Type Imports**: Resolved missing type annotations (`Any` from `typing` in compiler).
- **HTTPX v0.28+ AsyncClient Support**: Migrated `AsyncClient(app=app)` calls in tests to `AsyncClient(transport=ASGITransport(app=app))` to fix HTTPX compatibility.
- **FSM State Mappings**: Aligned default restaurant workflow nodes to correct FSM state definitions.
- **Transaction Rollbacks**: Moved `db_session.commit()` from the internal Traversal Engine to API router handlers. This allows the simulation engine to roll back nested savepoint transactions cleanly without encountering `ResourceClosedError`.

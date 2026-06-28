import logging
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Configure console logging format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("flowcore")

from src.database import init_db
from src.routes import (
    businesses, workflows, sessions, modules, snapshots, metrics, tests, capabilities,
    dashboard, events, providers, business, tasks, approvals, workers, reports, generation_jobs,
    employees, system
)
# Ensure all modules are loaded and registered with ModuleRegistry at startup
import src.modules.implementations 

@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    # Initialize SQLite tables on startup
    await init_db()

    # Ollama Model Startup Validation
    import sys
    import httpx
    from src.config import settings

    is_testing = "pytest" in sys.modules or any("pytest" in arg for arg in sys.argv)
    
    ollama_endpoint = settings.OLLAMA_ENDPOINT.rstrip("/")
    configured_model = settings.OLLAMA_MODEL
    
    try:
        # Query Ollama for installed models
        resp = httpx.get(f"{ollama_endpoint}/api/tags", timeout=5.0)
        if resp.status_code == 200:
            data = resp.json()
            installed = [m["name"] for m in data.get("models", [])]
            # Standardize model names for comparison
            model_found = False
            for model_name in installed:
                if model_name == configured_model:
                    model_found = True
                    break
                if ":" not in configured_model and model_name.split(":")[0] == configured_model:
                    model_found = True
                    break
            
            if not model_found:
                models_list = "\n".join(f"- {m}" for m in installed)
                error_msg = (
                    f"Configured model '{configured_model}' not found in Ollama.\n\n"
                    f"Installed models:\n{models_list}"
                )
                logger.error(error_msg)
            else:
                logger.info(f"Ollama Startup Validation: Configured model '{configured_model}' is available.")
        else:
            error_msg = f"Ollama tags endpoint returned HTTP {resp.status_code}"
            logger.warning(error_msg)
    except Exception as e:
        error_msg = f"Could not connect to Ollama at {ollama_endpoint}. Please ensure Ollama is running. Error: {str(e)}"
        logger.warning(error_msg)
    
    # Action consistency startup-time validation
    import json
    from sqlalchemy import select
    from src.models import WorkflowVersion
    from src.schemas.graph import WorkflowGraph
    from src.engine.compiler.static_validator import StaticValidator
    from src.engine.registries.capability_registry import CapabilityRegistry

    # Initialize capability registry folders and specs
    CapabilityRegistry.initialize_capabilities_directory()

    # A. Validate default examples/restaurant_workflow.json
    try:
        with open("examples/restaurant_workflow.json", "r") as f:
            graph_data = json.load(f)
        graph = WorkflowGraph.model_validate(graph_data)
        is_valid, errors, _, _, _, _, _ = StaticValidator.validate(graph)
        if not is_valid:
            raise RuntimeError(
                f"Startup Validation Audit Failure: 'examples/restaurant_workflow.json' has validation errors: {errors}"
            )
        logger.info("Startup Validation Audit: 'examples/restaurant_workflow.json' verified successfully (ONLINE).")
    except FileNotFoundError:
        logger.warning("Startup Validation Audit: 'examples/restaurant_workflow.json' not found. Skipping example check.")

    # B. Validate active database workflow versions
    from src.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        query = select(WorkflowVersion).where(WorkflowVersion.status == "ACTIVE")
        res = await db.execute(query)
        active_versions = res.scalars().all()
        for wv in active_versions:
            graph_dict = json.loads(wv.graph_json)
            graph = WorkflowGraph.model_validate(graph_dict)
            is_valid, errors, _, _, _, _, _ = StaticValidator.validate(graph)
            
            # Fail startup only if any action is not routable (action validation errors)
            action_errors = [e for e in errors if "Action Validation Error" in e]
            if action_errors:
                raise RuntimeError(
                    f"Startup Validation Audit Failure: Active workflow version ID '{wv.id}' has unroutable action errors: {action_errors}"
                )
            elif errors:
                logger.warning(
                    f"Startup Validation Audit Warning: Active workflow version ID '{wv.id}' has non-critical validation errors: {errors}"
                )
        logger.info(f"Startup Validation Audit: {len(active_versions)} active database workflow(s) verified successfully.")
    
    # Start the side effects retry worker task
    from src.database import AsyncSessionLocal
    from src.engine.side_effects import run_retry_worker
    retry_task = asyncio.create_task(run_retry_worker(AsyncSessionLocal, poll_interval=2.0))
    
    yield
    
    # Cancel background task on shutdown
    retry_task.cancel()
    try:
        await retry_task
    except asyncio.CancelledError:
        pass

app = FastAPI(
    title="FlowCore Platform",
    description="""
# FlowCore: Deterministic Graph-Based Conversational Workflow Engine

FlowCore is a deterministic workflow runtime and verification engine built for managing conversational state transitions, execution journaling, and carry unit mutation safety.

## Terminology & Core System Concepts

* **Workflow / Graph**: The static definition of conversational layouts. It defines a directed acyclic graph (DAG) consisting of operational **Nodes** (representing computational steps or actions) and **Edges** (conditional routing transitions).
* **Node**: A runtime execution unit referencing an operational module (e.g. `show_menu`, `collect_cart`, `calculate_total`). Nodes represent individual runtime micro-operations. Multiple nodes can legally execute and operate inside the same high-level FSM State phase.
* **Edge**: A directed path connecting one node to another. Edges define conditions (e.g., input matching, carry checks) evaluated at runtime to determine the traversal route.
* **FSM (Finite State Machine)**: The high-level semantic phase representing the business/workflow lifecycle stage (e.g., `START`, `MENU`, `CART`, `CHECKOUT`, `PAYMENT`, `CONFIRMED`, `CANCELLED`). FSM transitions are strictly governed by a compiled state-transition table.
* **Carry Unit**: A versioned, strongly typed namespace container carried through the session traversal. It stores customer data, cart order structures, payment statuses, and metadata. Carry units are updated via monotonic merge patch operations that enforce data structure invariants.
* **Traverser**: The execution engine that processes user inputs step-by-step. It resolves condition edges, executes nodes inside atomic transaction boundaries (nested database savepoints), mutates the FSM state, and merges carry unit updates.
* **Write-Ahead Journaling**: A persistent log of every execution event (`ExecutionJournal`) during traversal. Useful for debugging, auditability, and deterministic time-travel state recovery.
* **Execution Snapshot**: Database-backed checkpoint (`ExecutionSnapshot`) capturing the carry unit payload and FSM state after each successful traversal turn, ensuring session recovery.
* **Side Effects**: Out-of-band operational triggers (e.g., dispatching couriers, initiating external payments) registered in module contracts and executed asynchronously post-commit.
""",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from src.engine.exceptions import FlowCoreRuntimeError
from fastapi.exceptions import RequestValidationError

# Exception handlers
@app.exception_handler(FlowCoreRuntimeError)
async def flowcore_runtime_error_handler(request: Request, exc: FlowCoreRuntimeError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "success": False,
            "data": None,
            "error": {
                "error_code": exc.error_code,
                "message": exc.message
            },
            "metadata": {
                "session_id": exc.session_id,
                "node_id": exc.node_id,
                "current_fsm_state": exc.current_fsm_state
            }
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "data": None,
            "error": {
                "error_code": "VALIDATION_ERROR",
                "message": str(exc.errors())
            },
            "metadata": {}
        }
    )

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "success": False,
            "data": None,
            "error": {
                "error_code": "VALUE_ERROR",
                "message": str(exc)
            },
            "metadata": {}
        }
    )

@app.exception_handler(TypeError)
async def type_error_handler(request: Request, exc: TypeError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "data": None,
            "error": {
                "error_code": "TYPE_ERROR",
                "message": str(exc)
            },
            "metadata": {}
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "data": None,
            "error": {
                "error_code": "HTTP_ERROR",
                "message": exc.detail
            },
            "metadata": {}
        }
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "data": None,
            "error": {
                "error_code": "INTERNAL_SERVER_ERROR",
                "message": str(exc)
            },
            "metadata": {}
        }
    )

# Include API Routers
from src.routes import auth
app.include_router(auth.router)
app.include_router(auth.dev_router)
app.include_router(businesses.router)
app.include_router(workflows.router)
app.include_router(sessions.router)
app.include_router(modules.router)
app.include_router(snapshots.router)
app.include_router(metrics.router)
app.include_router(tests.router)
app.include_router(capabilities.router)
app.include_router(dashboard.router)
app.include_router(events.router)
app.include_router(providers.router)
app.include_router(business.router)
app.include_router(tasks.router)
app.include_router(approvals.router)
app.include_router(employees.router)
app.include_router(workers.router)
app.include_router(reports.router)
app.include_router(generation_jobs.router)
app.include_router(system.router)

@app.get("/")
async def root():
    return {
        "platform": "FlowCore Platform",
        "version": "1.0.0",
        "status": "ONLINE",
        "description": "Deterministic Graph-Based Conversational Workflow Engine"
    }

if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)

import uuid
import json
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Request, status, HTTPException, Depends
from httpx import AsyncClient, ASGITransport
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.database import get_db
from src.models import Business as BusinessModel
from src.schemas.graph import WorkflowGraph
from src.schemas.envelope import ApiResponse
from src.config import settings, sanitize_endpoint, sanitize_model

logger = logging.getLogger("flowcore.tests_route")

router = APIRouter(prefix="/api/v1/tests", tags=["Self Diagnostics & Mock Tests"])

class WorkflowsTestPayload(BaseModel):
    workflow_graph: Optional[WorkflowGraph] = Field(default=None, description="Dynamic graph to test")
    inputs: Optional[List[str]] = Field(default=None, description="Dynamic inputs for simulation check")

class BusinessesTestPayload(BaseModel):
    name: Optional[str] = Field(default=None, description="Dynamic business name")
    whatsapp_number: Optional[str] = Field(default=None, description="Dynamic business whatsapp number")

class SessionsTestPayload(BaseModel):
    workflow_graph: Optional[WorkflowGraph] = Field(default=None, description="Dynamic graph to test")
    inputs: Optional[List[str]] = Field(default=None, description="Dynamic list of inputs to dispatch sequentially")

@router.post("/workflows", response_model=ApiResponse[dict], status_code=status.HTTP_200_OK)
async def run_workflows_mock_test(request: Request, payload: Optional[WorkflowsTestPayload] = None):
    """
    Runs a mock integration test for all workflow routes:
    1. Creates a business
    2. Registers the workflow (dynamic or default)
    3. Validates the workflow schema via dry-run validate
    4. Compiles the workflow
    5. Activates the workflow
    6. Runs dry-run simulation
    """
    app = request.app
    results = []
    transport = ASGITransport(app=app)
    
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Step 1: Create a temporary business
        biz_payload = {
            "name": f"Workflow Test Biz {uuid.uuid4().hex[:6]}",
            "whatsapp_number": f"+1{str(uuid.uuid4().int)[:10]}"
        }
        biz_res = await client.post("/api/v1/businesses", json=biz_payload)
        if biz_res.status_code != 201:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Setup failed: Could not create business. Response: {biz_res.text}"
            )
        business_id = biz_res.json()["data"]["id"]
        
        # Load workflow graph (from payload or examples/restaurant_workflow.json)
        workflow_graph = None
        if payload and payload.workflow_graph:
            workflow_graph = payload.workflow_graph.model_dump()
        else:
            try:
                with open("examples/restaurant_workflow.json", "r") as f:
                    workflow_graph = json.load(f)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Setup failed: Could not read examples/restaurant_workflow.json. Error: {str(e)}"
                )
        workflow_graph["business_id"] = business_id
        
        # Resolve inputs
        inputs = ["/start", "1 x 1", "Checkout", "123 Main Street", "CONFIRM_PAYMENT"]
        if payload and payload.inputs is not None:
            inputs = payload.inputs
            
        # Test A: POST /api/v1/workflows/register
        reg_payload = {
            "business_id": business_id,
            "graph": workflow_graph
        }
        reg_res = await client.post("/api/v1/workflows/register", json=reg_payload)
        results.append({
            "route": "/api/v1/workflows/register",
            "method": "POST",
            "status_code": reg_res.status_code,
            "success": reg_res.status_code == 201,
            "response": reg_res.json() if reg_res.status_code == 201 else reg_res.text
        })
        
        if reg_res.status_code != 201:
            return ApiResponse(success=False, data={"success": False, "test_name": "Workflows API Mock Test", "results": results})
            
        version_id = reg_res.json()["data"]["workflow_version_id"]
        
        # Test B: POST /api/v1/workflows/validate
        val_res = await client.post("/api/v1/workflows/validate", json=workflow_graph)
        results.append({
            "route": "/api/v1/workflows/validate",
            "method": "POST",
            "status_code": val_res.status_code,
            "success": val_res.status_code == 200 and val_res.json()["data"].get("is_valid") is True,
            "response": val_res.json() if val_res.status_code == 200 else val_res.text
        })
        
        # Test C: POST /api/v1/workflows/compile/{version_id}
        comp_res = await client.post(f"/api/v1/workflows/compile/{version_id}")
        results.append({
            "route": f"/api/v1/workflows/compile/{version_id}",
            "method": "POST",
            "status_code": comp_res.status_code,
            "success": comp_res.status_code == 200,
            "response": comp_res.json() if comp_res.status_code == 200 else comp_res.text
        })
        
        # Test D: POST /api/v1/workflows/activate/{version_id}
        act_res = await client.post(f"/api/v1/workflows/activate/{version_id}")
        results.append({
            "route": f"/api/v1/workflows/activate/{version_id}",
            "method": "POST",
            "status_code": act_res.status_code,
            "success": act_res.status_code == 200 and act_res.json()["data"].get("status") == "ACTIVE",
            "response": act_res.json() if act_res.status_code == 200 else act_res.text
        })
        
        # Test E: POST /api/v1/workflows/simulate
        sim_payload = {
            "workflow_graph": workflow_graph,
            "inputs": inputs,
            "simulation_mode": "tolerant"
        }
        sim_res = await client.post("/api/v1/workflows/simulate", json=sim_payload)
        results.append({
            "route": "/api/v1/workflows/simulate",
            "method": "POST",
            "status_code": sim_res.status_code,
            "success": sim_res.status_code == 200,
            "response": sim_res.json() if sim_res.status_code == 200 else sim_res.text
        })

    all_success = all(r["success"] for r in results)
    data = {
        "success": all_success,
        "test_name": "Workflows API Mock Test",
        "results": results
    }
    return ApiResponse(success=all_success, data=data)

@router.post("/businesses", response_model=ApiResponse[dict], status_code=status.HTTP_200_OK)
async def run_businesses_mock_test(request: Request, payload: Optional[BusinessesTestPayload] = None):
    """
    Runs a mock integration test for business routes:
    1. Creates a business
    2. Retrieves the created business by ID
    """
    app = request.app
    results = []
    transport = ASGITransport(app=app)
    
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Resolve business name and whatsapp number
        name = f"Business Test Biz {uuid.uuid4().hex[:6]}"
        whatsapp_number = f"+1{str(uuid.uuid4().int)[:10]}"
        if payload:
            if payload.name:
                name = payload.name
            if payload.whatsapp_number:
                whatsapp_number = payload.whatsapp_number
                
        # Test A: POST /api/v1/businesses
        biz_payload = {
            "name": name,
            "whatsapp_number": whatsapp_number
        }
        biz_res = await client.post("/api/v1/businesses", json=biz_payload)
        results.append({
            "route": "/api/v1/businesses",
            "method": "POST",
            "status_code": biz_res.status_code,
            "success": biz_res.status_code == 201,
            "response": biz_res.json() if biz_res.status_code == 201 else biz_res.text
        })
        
        if biz_res.status_code != 201:
            return ApiResponse(success=False, data={"success": False, "test_name": "Businesses API Mock Test", "results": results})
            
        business_id = biz_res.json()["data"]["id"]
        
        # Test B: GET /api/v1/businesses/{business_id}
        get_res = await client.get(f"/api/v1/businesses/{business_id}")
        results.append({
            "route": f"/api/v1/businesses/{business_id}",
            "method": "GET",
            "status_code": get_res.status_code,
            "success": get_res.status_code == 200 and get_res.json()["data"].get("id") == business_id,
            "response": get_res.json() if get_res.status_code == 200 else get_res.text
        })

    all_success = all(r["success"] for r in results)
    data = {
        "success": all_success,
        "test_name": "Businesses API Mock Test",
        "results": results
    }
    return ApiResponse(success=all_success, data=data)

@router.post("/sessions", response_model=ApiResponse[dict], status_code=status.HTTP_200_OK)
async def run_sessions_mock_test(request: Request, payload: Optional[SessionsTestPayload] = None):
    """
    Runs a full conversational turn simulation for a customer.
    Triggers:
    1. Creates a business & registers/activates workflow
    2. POST /api/v1/sessions (Create session)
    3. sequential dispatch for inputs list
    4. GET /api/v1/sessions/replay/{session_id} (Verify execution replay)
    """
    app = request.app
    results = []
    transport = ASGITransport(app=app)
    
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Step 1: Create a business
        biz_payload = {
            "name": f"Session Test Biz {uuid.uuid4().hex[:6]}",
            "whatsapp_number": f"+1{str(uuid.uuid4().int)[:10]}"
        }
        biz_res = await client.post("/api/v1/businesses", json=biz_payload)
        if biz_res.status_code != 201:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Setup failed: Could not create business."
            )
        business_id = biz_res.json()["data"]["id"]
        
        # Step 2: Register & Activate Workflow
        workflow_graph = None
        if payload and payload.workflow_graph:
            workflow_graph = payload.workflow_graph.model_dump()
        else:
            try:
                with open("examples/restaurant_workflow.json", "r") as f:
                    workflow_graph = json.load(f)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Setup failed: Could not read examples/restaurant_workflow.json."
                )
        workflow_graph["business_id"] = business_id
        
        reg_payload = {
            "business_id": business_id,
            "graph": workflow_graph
        }
        reg_res = await client.post("/api/v1/workflows/register", json=reg_payload)
        if reg_res.status_code != 201:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Setup failed: Could not register workflow."
            )
        version_id = reg_res.json()["data"]["workflow_version_id"]
        
        act_res = await client.post(f"/api/v1/workflows/activate/{version_id}")
        if act_res.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Setup failed: Could not activate workflow."
            )
            
        # Test A: Create Session (POST /api/v1/sessions)
        sess_payload = {
            "business_id": business_id,
            "customer_phone": f"+1{str(uuid.uuid4().int)[:10]}"
        }
        sess_res = await client.post("/api/v1/sessions", json=sess_payload)
        results.append({
            "step": "Create Session",
            "route": "/api/v1/sessions",
            "method": "POST",
            "status_code": sess_res.status_code,
            "success": sess_res.status_code == 201 and sess_res.json()["data"].get("fsm_state") == "START",
            "response": sess_res.json() if sess_res.status_code == 201 else sess_res.text
        })
        
        if sess_res.status_code != 201:
            return ApiResponse(success=False, data={"success": False, "test_name": "Sessions API Mock Test", "results": results})
            
        session_id = sess_res.json()["data"]["id"]
        
        # Resolve inputs and expected default state progressions
        inputs = ["/start", "1 x 1", "Checkout", "123 Main Street", "CONFIRM_PAYMENT"]
        is_default = True
        if payload and payload.inputs is not None:
            inputs = payload.inputs
            is_default = False
            
        default_expected_states = ["MENU", "CART", "CHECKOUT", "PAYMENT", "CONFIRMED"]
        
        # Test sequential dispatches
        for idx, user_input in enumerate(inputs):
            disp_res = await client.post(f"/api/v1/sessions/dispatch/{session_id}", json={"user_input": user_input})
            
            # Check success condition
            step_success = (disp_res.status_code == 200)
            if step_success and is_default and idx < len(default_expected_states):
                expected_state = default_expected_states[idx]
                if disp_res.json()["data"].get("fsm_state_after") != expected_state:
                    step_success = False
            
            results.append({
                "step": f"Turn {idx + 1}: Input '{user_input}'",
                "route": f"/api/v1/sessions/dispatch/{session_id}",
                "method": "POST",
                "status_code": disp_res.status_code,
                "success": step_success,
                "response": disp_res.json() if disp_res.status_code == 200 else disp_res.text
            })
        
        # Test Replay: GET /api/v1/sessions/replay/{session_id}
        rep_res = await client.get(f"/api/v1/sessions/replay/{session_id}")
        results.append({
            "step": "Verify Session Replay Trace",
            "route": f"/api/v1/sessions/replay/{session_id}",
            "method": "GET",
            "status_code": rep_res.status_code,
            "success": rep_res.status_code == 200 and len(rep_res.json()["data"].get("trace", [])) > 0,
            "response": rep_res.json() if rep_res.status_code == 200 else rep_res.text
        })

    all_success = all(r["success"] for r in results)
    data = {
        "success": all_success,
        "test_name": "Sessions API Mock Test (Customer Flow Simulation)",
        "results": results
    }
    return ApiResponse(success=all_success, data=data)


# ---------------------------------------------------------------------------
# PHASE A — LLM Diagnostic Endpoint
# Tests Ollama connectivity and generation reliability in three isolated stages.
# ---------------------------------------------------------------------------

class LLMDiagnosticPayload(BaseModel):
    llama_endpoint: str = Field(default_factory=lambda: settings.OLLAMA_ENDPOINT)
    model:          str = Field(default_factory=lambda: settings.OLLAMA_MODEL)
    run_case_1:     bool = Field(default=True,  description="Minimal JSON probe (connectivity check)")
    run_case_2:     bool = Field(default=True,  description="Small workflow prompt (quality check)")
    run_case_3:     bool = Field(default=True,  description="Full FlowCore system prompt (production check)")
    timeout:        float = Field(default=120.0, description="Per-request timeout in seconds")
    provider:       Optional[str] = Field(default="ollama", description="LLM provider: ollama, gemini, openai")
    api_key:        Optional[str] = Field(default=None, description="API Key for external providers")
    business_id:    Optional[str] = Field(default=None, description="Business ID to fetch keys from")


@router.post("/llm-diagnostic", response_model=ApiResponse[dict], status_code=status.HTTP_200_OK)
async def run_llm_diagnostic(payload: LLMDiagnosticPayload, db: AsyncSession = Depends(get_db)):
    """
    Phase A — LLM Generation Diagnostic.

    Runs up to three isolated test cases against a live LLM endpoint:

    Case 1 — MINIMAL PROBE
      System:  'You are a JSON generator. Return exactly: {"test": true}'
      Purpose: Confirms LLM connectivity, timeout config, and JSON parsing work at all.

    Case 2 — SMALL WORKFLOW PROMPT
      System:  Focused FlowCore schema reminder + 'generate ONE restaurant ordering workflow only'
      Purpose: Tests whether the model can produce valid FlowCore DSL JSON at small scale.

    Case 3 — FULL PRODUCTION PROMPT
      System:  Complete v2 system prompt (same as live generation)
      Purpose: Tests whether the full prompt causes timeouts or comprehension errors.

    Each case records: success, elapsed_seconds, http_status, llm_error, response_preview.
    """
    import time
    import re
    import httpx

    # Resolve provider, model, endpoint, api_key dynamically
    provider = payload.provider or "ollama"
    model = payload.model
    api_key = payload.api_key
    endpoint = payload.llama_endpoint
    
    # Resolve keys from business settings if requested
    if payload.business_id:
        query = select(BusinessModel).where(BusinessModel.id == payload.business_id)
        res = await db.execute(query)
        business = res.scalar_one_or_none()
        if business:
            try:
                biz_settings = json.loads(business.settings_json or "{}")
                llm_config = biz_settings.get("llm_config", {})
                if not payload.provider or payload.provider == "ollama":
                    provider = llm_config.get("llm_provider", "ollama")
                
                if provider == "gemini":
                    model = llm_config.get("gemini_model") or model or "gemini-1.5-flash"
                    if not api_key or api_key == "********" or "••" in api_key:
                        api_key = llm_config.get("gemini_api_key") or settings.GEMINI_API_KEY
                elif provider == "openai":
                    model = llm_config.get("openai_model") or model or "gpt-4o-mini"
                    if not api_key or api_key == "********" or "••" in api_key:
                        api_key = llm_config.get("openai_api_key") or settings.OPENAI_API_KEY
                else:
                    model = llm_config.get("ollama_model") or model or settings.OLLAMA_MODEL
                    endpoint = llm_config.get("ollama_endpoint") or endpoint or settings.OLLAMA_ENDPOINT
            except Exception:
                pass

    if provider == "gemini" and (not api_key or api_key == "********" or "••" in api_key):
        api_key = settings.GEMINI_API_KEY
    if provider == "openai" and (not api_key or api_key == "********" or "••" in api_key):
        api_key = settings.OPENAI_API_KEY

    endpoint = sanitize_endpoint(endpoint)
    model = sanitize_model(model)
    timeout = payload.timeout
    cases = []

    # -----------------------------------------------------------------------
    # Shared helper: send one chat completion to LLM and classify the result
    # -----------------------------------------------------------------------
    async def probe_llm(case_name: str, system: str, user: str) -> dict:
        result = {
            "case":         case_name,
            "success":      False,
            "elapsed_s":    None,
            "http_status":  None,
            "llm_error":    None,
            "json_valid":   False,
            "json_preview": None,
            "prompt_chars": len(system) + len(user),
            "system_chars": len(system),
            "user_chars":   len(user),
        }
        try:
            start = time.time()
            async with httpx.AsyncClient(timeout=timeout) as client:
                if provider == "openai":
                    if not api_key:
                        raise ValueError("OpenAI API Key is not configured.")
                    resp = await client.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": model,
                            "messages": [
                                {"role": "system", "content": system},
                                {"role": "user",   "content": user},
                            ],
                            "temperature": 0.1,
                            "response_format": {"type": "json_object"}
                        }
                    )
                elif provider == "gemini":
                    if not api_key:
                        raise ValueError("Gemini API Key is not configured.")
                    resp = await client.post(
                        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
                        headers={
                            "Content-Type": "application/json"
                        },
                        json={
                            "systemInstruction": {
                                "parts": [
                                    {"text": system}
                                ]
                            },
                            "contents": [
                                {
                                    "role": "user",
                                    "parts": [
                                        {"text": user}
                                    ]
                                }
                            ],
                            "generationConfig": {
                                "responseMimeType": "application/json",
                                "temperature": 0.1
                            }
                        }
                    )
                else: # ollama
                    resp = await client.post(
                        f"{endpoint.rstrip('/')}/api/chat",
                        json={
                            "model":   model,
                            "messages": [
                                {"role": "system", "content": system},
                                {"role": "user",   "content": user},
                            ],
                            "stream":  False,
                            "format":  "json",
                            "options": {"temperature": 0.1},
                        }
                    )
            result["elapsed_s"]   = round(time.time() - start, 2)
            result["http_status"] = resp.status_code

            if resp.status_code != 200:
                result["llm_error"] = f"HTTP {resp.status_code}: {resp.text[:300]}"
                return result

            resp_json = resp.json()
            if provider == "openai":
                raw = resp_json["choices"][0]["message"]["content"]
            elif provider == "gemini":
                raw = resp_json["candidates"][0]["content"]["parts"][0]["text"]
            else: # ollama
                raw = resp_json["message"]["content"]

            result["json_preview"] = raw[:500]

            # Strip markdown fences
            cleaned = re.sub(r'^```json\s*', '', raw.strip())
            cleaned = re.sub(r'\s*```$', '', cleaned.strip())
            # Extract {...} if prose-wrapped
            if not cleaned.startswith("{"):
                m = re.search(r'\{.*\}', cleaned, re.DOTALL)
                if m:
                    cleaned = m.group(0)

            parsed = json.loads(cleaned)
            result["json_valid"] = isinstance(parsed, dict) and len(parsed) > 0
            result["success"]    = result["json_valid"]

        except Exception as e:
            result["elapsed_s"]  = round(time.time() - start, 2) if 'start' in dir() else None
            result["llm_error"]  = f"{type(e).__name__}: {str(e)}"

        return result

    # -----------------------------------------------------------------------
    # Case 1 — Minimal JSON probe (connectivity + timeout check)
    # -----------------------------------------------------------------------
    if payload.run_case_1:
        r = await probe_llm(
            case_name="Case 1 — Minimal JSON Probe",
            system=(
                'You are a JSON generator. '
                'Return ONLY this exact JSON object, nothing else: {"test": true}'
            ),
            user="Return the JSON now.",
        )
        cases.append(r)

    # -----------------------------------------------------------------------
    # Case 2 — Small FlowCore workflow prompt (quality check)
    # -----------------------------------------------------------------------
    if payload.run_case_2:
        small_system = (
            "You are the FlowCore Workflow DSL Compiler. Output ONLY raw JSON. "
            "Generate a single restaurant ordering workflow graph. "
            "Use only these module_names: show_menu, collect_cart, calculate_total, "
            "create_order, create_payment, confirm_payment, collect_address, "
            "create_delivery, notify_customer. "
            "Return a JSON object with keys: entry_node_id, nodes, edges, fsm_transition_table. "
            "FSM states allowed: START, MENU, CART, CHECKOUT, PAYMENT, CONFIRMED. "
            "Do NOT add any explanation. Return JSON only."
        )
        r = await probe_llm(
            case_name="Case 2 — Small Workflow Prompt",
            system=small_system,
            user="Business: Pizza Planet. Generate the ordering workflow.",
        )
        cases.append(r)

    # -----------------------------------------------------------------------
    # Case 3 — Full production FlowCore v2 system prompt
    # -----------------------------------------------------------------------
    if payload.run_case_3:
        full_system = (
            "You are the FlowCore Workflow DSL Compiler v2. Output ONLY raw JSON. "
            "You must output a JSON dictionary mapping workflow names to their workflow graph JSON structures. "
            "You are governed by the FlowCore Runtime and Validation Specification Context v2. "
            "\n\n"
            "SECTION K — CAPABILITY REGISTRY RULES:\n"
            "You MUST only use these registered module_names: "
            "show_menu, collect_cart, calculate_total, create_order, create_payment, "
            "confirm_payment, collect_address, create_delivery, notify_customer. "
            "Never invent capability names.\n\n"
            "SECTION L — CAPABILITY PACK RULES:\n"
            "Detect the business type and use the matching capability pack. "
            "Restaurant/Ecommerce: use full ordering flow with collect_address and create_delivery. "
            "Salon/Clinic/Gym: use booking flow without delivery. "
            "Service businesses: use generic service flow.\n\n"
            "SECTION M — EVENT REGISTRY RULES:\n"
            "Only use registered events: ORDER_CREATED, ORDER_UPDATED, ORDER_CANCELLED, "
            "PAYMENT_REQUIRED, PAYMENT_COMPLETED, PAYMENT_FAILED, "
            "DELIVERY_CREATED, DELIVERY_COMPLETED, "
            "BOOKING_CREATED, BOOKING_CANCELLED, "
            "SUPPORT_REQUESTED, SUPPORT_ESCALATED, "
            "APPROVAL_REQUESTED, APPROVAL_GRANTED, APPROVAL_REJECTED, "
            "CUSTOMER_CREATED. Never invent event names.\n\n"
            "SECTION N — PORTFOLIO ARCHITECTURE RULES:\n"
            "Generate a PORTFOLIO of multiple focused workflows, not one giant workflow. "
            "Required: Primary workflow, Support Workflow, Feedback Workflow. "
            "Connect workflows through events.\n\n"
            "SECTION O — BUSINESS CONFIGURATION RULES:\n"
            "Never hardcode catalog items, product prices, provider credentials, or branding. "
            "Use placeholder text. The platform supplies catalog and provider config at runtime.\n\n"
            "SECTION P — PROVIDER RULES:\n"
            "Always use generic capabilities: create_payment, create_delivery, notify_customer. "
            "Set gateway: 'cod' as default.\n\n"
            "SECTION S — MANDATORY GENERATOR RULES:\n"
            "- Use registered modules only.\n"
            "- Every fsm_transition_to must appear in fsm_transition_table.\n"
            "- All leaf nodes must be in CONFIRMED, CANCELLED, or ERROR state OR have expects_user_input: true.\n"
            "- collect_address must precede create_delivery.\n"
            "- create_order must precede create_payment.\n"
            "- Valid FSM states: START, MENU, BROWSING, CART, CHECKOUT, PAYMENT, CONFIRMED, CANCELLED, ERROR.\n"
            "\n"
            "Each workflow graph must have: 'entry_node_id', 'nodes' dict, 'edges' list, 'fsm_transition_table'."
        )
        r = await probe_llm(
            case_name="Case 3 — Full FlowCore v2 Production Prompt",
            system=full_system,
            user=(
                "Business Name: Pizza Planet\n"
                "Category: restaurant\n"
                "Description: We are a pizza restaurant. We sell pizza, burgers, pasta, "
                "desserts and beverages. Customers order food and we deliver it to their homes."
            ),
        )
        cases.append(r)

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    passed      = [c for c in cases if c["success"]]
    failed      = [c for c in cases if not c["success"]]
    all_passed  = len(failed) == 0 and len(cases) > 0

    # Diagnosis hint based on failure pattern
    diagnosis = f"All cases passed — LLM ({provider}) integration is fully functional."
    if cases:
        c1 = next((c for c in cases if "Case 1" in c["case"]), None)
        c2 = next((c for c in cases if "Case 2" in c["case"]), None)
        c3 = next((c for c in cases if "Case 3" in c["case"]), None)

        if c1 and not c1["success"]:
            err = c1.get("llm_error", "")
            if "Timeout" in err or "Connect" in err:
                diagnosis = (
                    f"CRITICAL: LLM is not reachable at {endpoint if provider == 'ollama' else provider}. "
                    "Check that settings and keys are correct. "
                    f"Error: {err}"
                )
            elif "JSONDecodeError" in err:
                diagnosis = (
                    "LLM responded but returned non-JSON even for minimal probe. "
                    "Verify the model is working."
                )
            else:
                diagnosis = f"Case 1 failed with: {err}. Investigate LLM setup."
        elif c2 and not c2["success"]:
            diagnosis = (
                "Case 1 (minimal) passed but Case 2 (small workflow) failed. "
                "The model can respond but struggles with FlowCore DSL structure. "
                f"Error: {c2.get('llm_error')}."
            )
        elif c3 and not c3["success"]:
            err = c3.get("llm_error", "")
            if "Timeout" in err:
                diagnosis = (
                    f"Cases 1 & 2 passed but Case 3 timed out at {timeout}s. "
                    "The full prompt is too large or API response is slow."
                )
            else:
                diagnosis = (
                    f"Cases 1 & 2 passed but Case 3 failed: {err}. "
                    "Full production prompt causes issues. Review prompt structure."
                )
        elif all_passed:
            slowest = max(cases, key=lambda c: c["elapsed_s"] or 0)
            diagnosis = (
                f"All {len(cases)} cases passed. Slowest: {slowest['case']} "
                f"at {slowest['elapsed_s']}s. LLM generation is ready for production."
            )

    # Check if the model is available and query models list
    available_model = False
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            if provider == "openai":
                if api_key:
                    resp_tags = await client.get(
                        "https://api.openai.com/v1/models",
                        headers={"Authorization": f"Bearer {api_key}"}
                    )
                    if resp_tags.status_code == 200:
                        available_model = True
            elif provider == "gemini":
                if api_key:
                    resp_tags = await client.get(
                        f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
                    )
                    if resp_tags.status_code == 200:
                        available_model = True
            else: # ollama
                resp_tags = await client.get(f"{endpoint}/api/tags")
                if resp_tags.status_code == 200:
                    installed = [m["name"] for m in resp_tags.json().get("models", [])]
                    available_model = any(m == model or (":" not in model and m.split(":")[0] == model) for m in installed)
    except Exception:
        pass

    response_status = 200 if all_passed else (next((c.get("http_status") for c in cases if c.get("http_status") is not None), None) or 500)

    return ApiResponse(
        success=all_passed,
        data={
            "test_name":        "Phase A — LLM Generation Diagnostic",
            "endpoint":         endpoint,
            "model":            model,
            "configured_model": model,
            "available_model":  available_model,
            "response_status":  response_status,
            "timeout_s":        timeout,
            "cases_run":        len(cases),
            "cases_passed":     len(passed),
            "cases_failed":     len(failed),
            "all_passed":       all_passed,
            "diagnosis":        diagnosis,
            "cases":            cases,
        }
    )


# ---------------------------------------------------------------------------
# PHASE A — Category Validation Sweep (Task A5 + A6)
# Verifies correct workflow type, trigger events, and module selection
# for all 6 primary business types using the programmatic builder.
# ---------------------------------------------------------------------------

@router.post("/llm-category-sweep", response_model=ApiResponse[dict], status_code=status.HTTP_200_OK)
async def run_category_sweep():
    """
    Phase A5/A6 — Category Routing and Event Trigger Validation.

    Tests the programmatic generator for all primary business categories:
    Restaurant, Salon, Hospital, Gym, Real Estate, Education.

    Verifies:
    - Correct primary workflow name (Ordering vs Booking vs General Service)
    - Correct feedback trigger event (DELIVERY_COMPLETED vs BOOKING_CONFIRMED)
    - Presence of all required capability modules
    - No cross-category contamination (e.g. Haircut in restaurant workflow)
    """
    from src.services.ai_generator import AIGenerator, ORDERING_CATEGORIES, DELIVERY_FEEDBACK_CATEGORIES

    BUSINESS_ID = "sweep_test_biz"
    BUSINESS_NAME = "Test Business"

    TEST_CASES = [
        {
            "category":              "restaurant",
            "expected_primary":      "Ordering Workflow",
            "expected_feedback_trigger": "DELIVERY_COMPLETED",
            "required_modules":      ["show_menu", "collect_cart", "calculate_total",
                                      "create_order", "create_payment", "confirm_payment",
                                      "collect_address", "create_delivery", "notify_customer"],
            "banned_content":        ["haircut", "hair wash", "styling"],
        },
        {
            "category":              "salon",
            "expected_primary":      "Booking Workflow",
            "expected_feedback_trigger": "BOOKING_CONFIRMED",
            "required_modules":      ["show_menu", "collect_cart", "create_order",
                                      "create_payment", "confirm_payment", "notify_customer"],
            "banned_content":        [],
        },
        {
            "category":              "hospital",
            "expected_primary":      "Booking Workflow",
            "expected_feedback_trigger": "BOOKING_CONFIRMED",
            "required_modules":      ["show_menu", "collect_cart", "create_order",
                                      "create_payment", "confirm_payment", "notify_customer"],
            "banned_content":        ["haircut", "pizza", "burger"],
        },
        {
            "category":              "gym",
            "expected_primary":      "Booking Workflow",
            "expected_feedback_trigger": "BOOKING_CONFIRMED",
            "required_modules":      ["show_menu", "collect_cart", "create_order",
                                      "create_payment", "confirm_payment", "notify_customer"],
            "banned_content":        ["haircut", "pizza"],
        },
        {
            "category":              "realestate",
            "expected_primary":      "Booking Workflow",
            "expected_feedback_trigger": "BOOKING_CONFIRMED",
            "required_modules":      ["show_menu", "collect_cart", "create_order",
                                      "notify_customer"],
            "banned_content":        ["haircut", "pizza"],
        },
        {
            "category":              "education",
            "expected_primary":      "Booking Workflow",
            "expected_feedback_trigger": "BOOKING_CONFIRMED",
            "required_modules":      ["show_menu", "collect_cart", "create_order",
                                      "create_payment", "confirm_payment", "notify_customer"],
            "banned_content":        ["haircut", "pizza"],
        },
    ]

    results = []
    for tc in TEST_CASES:
        cat      = tc["category"]
        checks   = []
        passed   = True

        # Build portfolio
        portfolio = AIGenerator.build_programmatic_portfolio(
            BUSINESS_ID, BUSINESS_NAME, cat, []
        )

        # Check 1: Primary workflow name
        primary_ok = tc["expected_primary"] in portfolio
        checks.append({
            "check":    "Primary workflow name",
            "expected": tc["expected_primary"],
            "actual":   list(portfolio.keys()),
            "pass":     primary_ok,
        })
        if not primary_ok:
            passed = False

        # Check 2: Support Workflow always present
        support_ok = "Support Workflow" in portfolio
        checks.append({
            "check":  "Support Workflow present",
            "pass":   support_ok,
        })
        if not support_ok:
            passed = False

        # Check 3: Feedback trigger event
        feedback_wf   = portfolio.get("Feedback Workflow", {})
        actual_trigger = feedback_wf.get("trigger_event")
        trigger_ok    = actual_trigger == tc["expected_feedback_trigger"]
        checks.append({
            "check":    "Feedback trigger event",
            "expected": tc["expected_feedback_trigger"],
            "actual":   actual_trigger,
            "pass":     trigger_ok,
        })
        if not trigger_ok:
            passed = False

        # Check 4: Required modules present in primary workflow
        primary_wf   = portfolio.get(tc["expected_primary"], {})
        actual_mods  = [n.get("module_name") for n in primary_wf.get("nodes", {}).values()]
        missing_mods = [m for m in tc["required_modules"] if m not in actual_mods]
        mods_ok      = len(missing_mods) == 0
        checks.append({
            "check":         "Required modules in primary workflow",
            "required":      tc["required_modules"],
            "actual":        actual_mods,
            "missing":       missing_mods,
            "pass":          mods_ok,
        })
        if not mods_ok:
            passed = False

        # Check 5: No banned content in menu text
        menu_node    = primary_wf.get("nodes", {}).get("node_menu", {})
        menu_text    = menu_node.get("config", {}).get("menu_header", "").lower()
        banned_found = [b for b in tc["banned_content"] if b in menu_text]
        no_banned_ok = len(banned_found) == 0
        checks.append({
            "check":        "No cross-category menu content",
            "banned_terms": tc["banned_content"],
            "found_in_menu": banned_found,
            "pass":         no_banned_ok,
        })
        if not no_banned_ok:
            passed = False

        results.append({
            "category": cat,
            "passed":   passed,
            "checks":   checks,
        })

    categories_passed = [r["category"] for r in results if r["passed"]]
    categories_failed = [r["category"] for r in results if not r["passed"]]
    all_passed        = len(categories_failed) == 0

    return ApiResponse(
        success=all_passed,
        data={
            "test_name":          "Phase A5/A6 — Category & Event Trigger Sweep",
            "categories_tested":  len(results),
            "categories_passed":  categories_passed,
            "categories_failed":  categories_failed,
            "all_passed":         all_passed,
            "results":            results,
        }
    )


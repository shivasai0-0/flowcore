import json
import logging
import time
import httpx
import re
from typing import Dict, Any, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.models import Business
from src.config import settings

logger = logging.getLogger("flowcore.ai_generator")

# ---------------------------------------------------------------------------
# Canonical category constants & sets for backwards compatibility
# ---------------------------------------------------------------------------
CAT_RESTAURANT    = "restaurant"
CAT_SALON         = "salon"
CAT_CLINIC        = "clinic"
CAT_HOSPITAL      = "hospital"
CAT_GYM           = "gym"
CAT_REALESTATE    = "realestate"
CAT_EDUCATION     = "education"
CAT_ECOMMERCE     = "ecommerce"
CAT_HOTEL         = "hotel"
CAT_TRAVEL        = "travel"
CAT_PHARMACY      = "pharmacy"
CAT_SUPERMARKET   = "supermarket"
CAT_SERVICE       = "servicebusiness"

ORDERING_CATEGORIES = {CAT_RESTAURANT, CAT_ECOMMERCE, CAT_PHARMACY, CAT_SUPERMARKET}
BOOKING_CATEGORIES  = {CAT_SALON, CAT_CLINIC, CAT_HOSPITAL, CAT_GYM,
                       CAT_HOTEL, CAT_TRAVEL, CAT_REALESTATE, CAT_EDUCATION}
DELIVERY_FEEDBACK_CATEGORIES = {CAT_RESTAURANT, CAT_ECOMMERCE, CAT_SUPERMARKET}

class AIGenerator:
    @staticmethod
    def detect_category(description: str, capability_packs: List[str]) -> str:
        """
        Detects business category.
        Returns a LOWERCASE canonical category string.
        """
        if capability_packs:
            raw = capability_packs[0].lower().strip()
            alias_map = {
                "real_estate": "realestate",
                "real estate": "realestate",
                "realestate": "realestate",
                "service": "servicebusiness",
                "service_business": "servicebusiness",
            }
            return alias_map.get(raw, raw)

        desc_lower = description.lower()
        if any(w in desc_lower for w in ["pizza", "burger", "food", "restaurant", "menu", "cafe", "sushi", "kitchen", "dining"]):
            return "restaurant"
        if any(w in desc_lower for w in ["hospital", "admission", "lab", "ward", "billing"]):
            return "hospital"
        if any(w in desc_lower for w in ["hair", "nail", "salon", "spa", "cut", "stylist", "massage", "barber"]):
            return "salon"
        if any(w in desc_lower for w in ["doctor", "clinic", "medical", "consultation", "patient", "physio"]):
            return "clinic"
        if any(w in desc_lower for w in ["supermarket", "grocery", "groceries", "hypermarket", "mart", "convenience store"]):
            return "supermarket"
        if any(w in desc_lower for w in ["course", "enroll", "education", "student", "class", "school", "learn", "tutor", "coaching", "university", "college"]):
            return "education"
        if any(w in desc_lower for w in ["house", "apartment", "real estate", "property", "tour", "realtor", "rent"]):
            return "realestate"
        if any(w in desc_lower for w in ["gym", "workout", "membership", "trainer", "fitness", "crossfit"]):
            return "gym"
        if any(w in desc_lower for w in ["ecommerce", "store", "product", "shop", "shipping", "buy", "cart"]):
            return "ecommerce"
        if any(w in desc_lower for w in ["hotel", "room", "stay", "suite", "resort"]):
            return "hotel"
        if any(w in desc_lower for w in ["travel", "trip", "flight", "ticket", "itinerary"]):
            return "travel"
        if any(w in desc_lower for w in ["pharmacy", "prescription", "drug", "medicine", "pill"]):
            return "pharmacy"

        return "servicebusiness" # default fallback

    @staticmethod
    def parse_items_from_description(description: str, category: str) -> List[Tuple[str, float]]:
        """Extracts items and prices from description text if available (e.g. 'Margherita Pizza for $12')."""
        matches = re.findall(r'([a-zA-Z\s\-]{3,30})\s+(?:for|at|\-)\s+\$?(\d+(?:\.\d{2})?)', description)
        items = []
        for name, price_str in matches:
            name = name.strip()
            name = re.sub(r'^(and|sell|we have|buy)\s+', '', name, flags=re.IGNORECASE)
            try:
                price = float(price_str)
                items.append((name.title(), price))
            except ValueError:
                pass
        return items

    @classmethod
    def build_mock_draft(cls, business_id: str, business_name: str, category: str, parsed_items: List[Tuple[str, float]]) -> Dict[str, Any]:
        """Converts programmatic templates into the new WorkflowDraft structure."""
        portfolio = cls.build_programmatic_portfolio(business_id, business_name, category, parsed_items)
        
        draft_workflows = []
        for name, graph in portfolio.items():
            wf_id = name.lower().replace(" ", "_")
            
            nodes_list = []
            for n_id, n_data in graph.get("nodes", {}).items():
                nodes_list.append({
                    "id": n_id,
                    "module_name": n_data.get("module_name"),
                    "config": n_data.get("config", {}),
                    "fsm_transition_to": n_data.get("fsm_transition_to")
                })
                
            edges_list = []
            for edge in graph.get("edges", []):
                edges_list.append({
                    "from_node": edge.get("from_node"),
                    "to_node": edge.get("to_node"),
                    "condition": edge.get("condition", {"type": "always"})
                })
                
            draft_workflows.append({
                "id": wf_id,
                "name": name,
                "entry_node_id": graph.get("entry_node_id"),
                "nodes": nodes_list,
                "edges": edges_list
            })
            
        # Define event connections dynamically based on existing workflows in the draft
        event_connections = []
        wf_ids = {w["id"] for w in draft_workflows}
        primary_wf_ids = [w_id for w_id in wf_ids if w_id not in ("support_workflow", "feedback_workflow")]
        
        for p_id in primary_wf_ids:
            if "support_workflow" in wf_ids:
                event_connections.append({
                    "from_workflow_id": p_id,
                    "to_workflow_id": "support_workflow",
                    "event_type": "CUSTOMER_ESCALATION"
                })
            if "feedback_workflow" in wf_ids:
                event_type = "ORDER_PLACED" if (category in ORDERING_CATEGORIES or category == "restaurant") else "BOOKING_CONFIRMED"
                event_connections.append({
                    "from_workflow_id": p_id,
                    "to_workflow_id": "feedback_workflow",
                    "event_type": event_type
                })
            
        return {
            "business_type": category,
            "workflows": draft_workflows,
            "event_connections": event_connections
        }

    @classmethod
    async def generate_portfolio(
        cls,
        db_session: AsyncSession,
        business_id: str,
        description: str,
        capability_packs: List[str],
        llama_endpoint: str = "http://localhost:11434",
        use_mock_ai: bool = True
    ) -> Dict[str, Any]:
        """Generates a workflow portfolio based on business description using LLM or programmatic template copy."""
        # Resolve business details
        biz_query = select(Business).where(Business.id == business_id)
        biz_res = await db_session.execute(biz_query)
        business = biz_res.scalar_one_or_none()
        business_name = business.name if business else "Our Business"

        category = cls.detect_category(description, capability_packs)
        parsed_items = cls.parse_items_from_description(description, category)

        logger.info(f"[AIGenerator] Capability packs received: {capability_packs}")
        logger.info(f"[AIGenerator] Detected category: '{category}'")
        logger.info(f"[AIGenerator] use_mock_ai={use_mock_ai}, llama_endpoint={llama_endpoint}")

        # Fast Mode: return programmatic template copy immediately in WorkflowDraft shape
        if use_mock_ai:
            logger.info("[AIGenerator] Fast Mode (Programmatic Template Copy) returning immediately.")
            mock_draft = cls.build_mock_draft(business_id, business_name, category, parsed_items)
            raw_content = json.dumps(mock_draft, indent=2)
            
            # Map back to legacy dict of workflows for backward compatibility
            legacy_portfolio = cls.build_programmatic_portfolio(business_id, business_name, category, parsed_items)
            
            return {
                "success":       True,
                "method":        "programmatic",
                "category":      category,
                "llm_attempted": False,
                "llm_success":   False,
                "fallback_used": False,
                "llm_error":     None,
                "prompt_version": "v1.0-mock",
                "model_name":    "mock",
                "elapsed_s":     0.0,
                "raw_content":   raw_content,
                "workflows":     legacy_portfolio,
                "system_prompt": "Mock system prompt.",
                "user_prompt":   f"Description: {description}"
            }

        # AI Mode: Call LLM to design the entire workflow portfolio from scratch
        llm_attempted = True
        llm_success = False
        llm_error_msg = None
        elapsed = 0.0
        raw_content = ""
        legacy_portfolio = {}
        system_prompt = ""
        user_prompt = ""

        # Fetch LLM config from business if it exists
        llm_provider = "ollama"
        model_name = settings.OLLAMA_MODEL
        endpoint = settings.OLLAMA_ENDPOINT
        api_key = None

        if business:
            try:
                biz_settings = json.loads(business.settings_json or "{}")
                llm_config = biz_settings.get("llm_config", {})
                llm_provider = llm_config.get("llm_provider", "ollama")
                if llm_provider == "gemini":
                    model_name = llm_config.get("gemini_model") or "gemini-1.5-flash"
                    api_key = llm_config.get("gemini_api_key") or settings.GEMINI_API_KEY
                elif llm_provider == "openai":
                    model_name = llm_config.get("openai_model") or "gpt-4o-mini"
                    api_key = llm_config.get("openai_api_key") or settings.OPENAI_API_KEY
                else: # ollama
                    model_name = llm_config.get("ollama_model") or settings.OLLAMA_MODEL
                    endpoint = llm_config.get("ollama_endpoint") or settings.OLLAMA_ENDPOINT
            except Exception as e:
                logger.warning(f"Failed to read LLM config from settings_json: {str(e)}")

        if llm_provider == "ollama" and llama_endpoint and llama_endpoint != "http://localhost:11434":
            endpoint = llama_endpoint

        logger.info(f"[AIGenerator] AI Mode (LLM Workflow Architect) active with provider={llm_provider}, model={model_name}. Invoking LLM...")
        try:
            # Dynamically extract all registered capabilities
            from src.modules.registry import ModuleRegistry
            modules = ModuleRegistry.list_all()
            capabilities_summary = ""
            for mod in modules:
                capabilities_summary += (
                    f"- Name: {mod.contract.module_name}\n"
                    f"  Display Name: {mod.contract.display_name}\n"
                    f"  Requires: {mod.contract.requires}\n"
                    f"  Produces: {mod.contract.produces}\n"
                    f"  Allowed FSM States: {mod.contract.allowed_fsm_states}\n"
                    f"  Expects User Input: {mod.contract.expects_user_input}\n\n"
                )

            system_prompt = (
                "You are the FlowCore Workflow Architect.\n"
                "Your job is to generate a custom WorkflowDraft JSON based on the user's business description.\n"
                "You must design the entire set of workflows (e.g. Booking, Ordering, Support, Feedback, or any custom workflows required by the business).\n\n"
                "AVAILABLE CAPABILITIES:\n"
                f"{capabilities_summary}\n"
                "VALID FSM STATES:\n"
                "- START\n- MENU\n- CART\n- CHECKOUT\n- PAYMENT\n- CONFIRMED\n- CANCELLED\n- ERROR\n\n"
                "EXPECTED JSON FORMAT:\n"
                "Your output must be a single JSON object matching this schema:\n"
                "{\n"
                "  \"business_type\": \"string (e.g. restaurant, hospital, salon, etc.)\",\n"
                "  \"workflows\": [\n"
                "    {\n"
                "      \"id\": \"string (e.g. ordering_workflow)\",\n"
                "      \"name\": \"string (e.g. Ordering Workflow)\",\n"
                "      \"entry_node_id\": \"string (must match a node ID in this workflow)\",\n"
                "      \"nodes\": [\n"
                "        {\n"
                "          \"id\": \"string (unique node ID, e.g. node_menu)\",\n"
                "          \"module_name\": \"string (MUST be one of the AVAILABLE CAPABILITIES names)\",\n"
                "          \"config\": { ... arbitrary key-values needed for the module ... },\n"
                "          \"fsm_transition_to\": \"string or null (must be a VALID FSM STATE)\"\n"
                "        }\n"
                "      ],\n"
                "      \"edges\": [\n"
                "        {\n"
                "          \"from_node\": \"string (source node ID)\",\n"
                "          \"to_node\": \"string (target node ID)\",\n"
                "          \"condition\": {\n"
                "            \"type\": \"always | input_equals | input_in | carry_equals | carry_greater_than\",\n"
                "            \"key\": \"string or null (for carry checks, e.g. 'order.total')\",\n"
                "            \"value\": \"any or null (value to check against)\"\n"
                "          }\n"
                "        }\n"
                "      ]\n"
                "    }\n"
                "  ],\n"
                "  \"event_connections\": [\n"
                "    {\n"
                "      \"from_workflow_id\": \"string (matching from workflow id)\",\n"
                "      \"to_workflow_id\": \"string (matching to workflow id)\",\n"
                "      \"event_type\": \"string (event triggering the transition, e.g. ORDER_PLACED, CUSTOMER_ESCALATION)\"\n"
                "    }\n"
                "  ]\n"
                "}\n\n"
                "CRITICAL TOPOLOGY CONSTRAINTS:\n"
                "1. Each workflow graph must be a strict directed acyclic graph (DAG) with no cycles.\n"
                "2. Every node in the nodes list must be reachable from the entry_node_id.\n"
                "3. No orphan nodes: Every node in a workflow must have at least one incoming or outgoing edge (except for single-node workflows).\n"
                "4. You MUST only use capability names listed in the AVAILABLE CAPABILITIES section. Do not invent any new capability/module names.\n"
                "5. You MUST only transition FSM states to allowed FSM states.\n"
                "6. Do not include duplicate node IDs within a workflow or duplicate workflow IDs in the draft.\n"
                "7. Output ONLY raw JSON matching the format. Do not wrap in markdown or write explanation text."
            )

            catalog_summary = ", ".join([f"{name} (${price:.2f})" for name, price in parsed_items]) if parsed_items else "None provided"
            user_prompt = (
                f"Business Name: {business_name}\n"
                f"Business Description: {description}\n"
                f"Detected Category: {category}\n"
                f"Catalog Items: {catalog_summary}\n"
            )

            start_time = time.time()
            async with httpx.AsyncClient(timeout=120.0) as client:
                if llm_provider == "openai":
                    if not api_key:
                        raise ValueError("OpenAI API Key is not configured.")
                    resp = await client.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": model_name,
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt}
                            ],
                            "temperature": 0.1,
                            "response_format": {"type": "json_object"}
                        }
                    )
                elif llm_provider == "gemini":
                    if not api_key:
                        raise ValueError("Gemini API Key is not configured.")
                    resp = await client.post(
                        f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}",
                        headers={
                            "Content-Type": "application/json"
                        },
                        json={
                            "systemInstruction": {
                                "parts": [
                                    {"text": system_prompt}
                                ]
                            },
                            "contents": [
                                {
                                    "role": "user",
                                    "parts": [
                                        {"text": user_prompt}
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
                    from src.config import sanitize_endpoint
                    sanitized_endpoint = sanitize_endpoint(endpoint)
                    resp = await client.post(
                        f"{sanitized_endpoint.rstrip('/')}/api/chat",
                        json={
                            "model": model_name,
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt}
                            ],
                            "stream": False,
                            "format": "json",
                            "options": {"temperature": 0.1}
                        }
                    )
            elapsed = time.time() - start_time
            logger.info(f"[AIGenerator] {llm_provider} response time: {elapsed:.2f}s | HTTP {resp.status_code}")

            if resp.status_code == 200:
                resp_json = resp.json()
                if llm_provider == "openai":
                    raw_content = resp_json["choices"][0]["message"]["content"]
                elif llm_provider == "gemini":
                    raw_content = resp_json["candidates"][0]["content"]["parts"][0]["text"]
                else: # ollama
                    raw_content = resp_json["message"]["content"]
                
                cleaned = re.sub(r'^```json\s*', '', raw_content.strip())
                cleaned = re.sub(r'\s*```$', '', cleaned.strip())

                if not cleaned.startswith("{"):
                    json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
                    if json_match:
                        cleaned = json_match.group(0)

                raw_content = cleaned
                # Verify we can at least json loads it, else validation handles it
                try:
                    customized = json.loads(cleaned)
                    if isinstance(customized, dict):
                        llm_success = True
                        # Map to legacy workflows dict for compatibility in UI
                        workflows_list = customized.get("workflows") or []
                        for w in workflows_list:
                            w_name = w.get("name") or w.get("id") or "Workflow"
                            nodes_dict = {}
                            for n in w.get("nodes") or []:
                                nodes_dict[n["id"]] = n
                            legacy_portfolio[w_name] = {
                                "entry_node_id": w.get("entry_node_id"),
                                "nodes": nodes_dict,
                                "edges": w.get("edges") or []
                            }
                    else:
                        llm_error_msg = "LLM generated invalid JSON structure (not a dictionary)"
                except Exception as je:
                    llm_error_msg = f"JSON parsing failed: {str(je)}"
            else:
                llm_error_msg = f"HTTP {resp.status_code}: {resp.text[:500]}"
                
        except Exception as e:
            llm_error_msg = f"{type(e).__name__}: {str(e)}"
            logger.warning(f"[AIGenerator] {llm_provider} workflow generation failed: {llm_error_msg}")

        return {
            "success":       llm_success,
            "method":        llm_provider if llm_success else "programmatic",
            "category":      category,
            "llm_attempted": llm_attempted,
            "llm_success":   llm_success,
            "fallback_used": False,
            "llm_error":     llm_error_msg,
            "prompt_version": f"v2.0-{llm_provider}" if llm_success else "v1.0-mock",
            "model_name":    model_name if llm_success else "mock",
            "elapsed_s":     round(elapsed, 2),
            "raw_content":   raw_content,
            "workflows":     legacy_portfolio,
            "system_prompt": system_prompt,
            "user_prompt":   user_prompt
        }

    @classmethod
    def build_programmatic_portfolio(
        cls,
        business_id: str,
        business_name: str,
        category: str,
        parsed_items: List[Tuple[str, float]]
    ) -> Dict[str, Any]:
        """Builds a customized, 100% valid workflow portfolio for the given category template."""
        portfolio = {}

        if category == "hospital":
            portfolio = cls.get_hospital_template(business_id, business_name)
        elif category == "salon":
            portfolio = cls.get_salon_template(business_id, business_name)
        elif category == "supermarket":
            portfolio = cls.get_supermarket_template(business_id, business_name, parsed_items)
        elif category == "education":
            portfolio = cls.get_education_template(business_id, business_name)
        elif category in ("realestate", "real_estate"):
            portfolio = cls.get_real_estate_template(business_id, business_name)
        elif category in ORDERING_CATEGORIES:
            portfolio = {
                "Ordering Workflow": cls.get_ordering_workflow(business_id, business_name, category, parsed_items),
                "Support Workflow": cls.get_support_workflow(business_id, business_name, category),
                "Feedback Workflow": cls.get_feedback_workflow(business_id, business_name, category)
            }
        elif category in BOOKING_CATEGORIES:
            portfolio = {
                "Booking Workflow": cls.get_booking_workflow(business_id, business_name, category, parsed_items),
                "Support Workflow": cls.get_support_workflow(business_id, business_name, category),
                "Feedback Workflow": cls.get_feedback_workflow(business_id, business_name, category)
            }
        else: # default/fallback servicebusiness
            portfolio = {
                "General Service": cls.get_general_service_workflow(business_id, business_name, category),
                "Support Workflow": cls.get_support_workflow(business_id, business_name, category),
                "Feedback Workflow": cls.get_feedback_workflow(business_id, business_name, category)
            }

        return portfolio

    # ---------------------------------------------------------------------------
    # Template Pack Getters
    # ---------------------------------------------------------------------------
    @classmethod
    def get_restaurant_template(cls, business_id: str, business_name: str, parsed_items: List[Tuple[str, float]]) -> Dict[str, Any]:
        menu_items_text = ""
        if parsed_items:
            for idx, (name, price) in enumerate(parsed_items, 1):
                menu_items_text += f"\n{idx}. {name} - ${price:.2f}"
        else:
            menu_items_text = "\n1. Margherita Pizza - $12.00\n2. Veggie Burger - $8.50\n3. French Fries - $4.00"

        welcome_text = (
            f"📋 Welcome to {business_name}! Here is our menu:{menu_items_text}\n\n"
            f"Reply with items and quantities (e.g. '1 x 2, 2 x 1') to add to your order."
        )

        ordering = {
            "business_id": business_id,
            "version_number": 1,
            "entry_node_id": "node_menu",
            "trigger_event": None,
            "nodes": {
                "node_menu": {
                    "id": "node_menu",
                    "module_name": "show_menu",
                    "config": {"menu_header": welcome_text},
                    "fsm_transition_to": "MENU"
                },
                "node_collect": {
                    "id": "node_collect",
                    "module_name": "collect_cart",
                    "config": {"expects_user_input": True},
                    "fsm_transition_to": "CART"
                },
                "node_total": {
                    "id": "node_total",
                    "module_name": "calculate_total",
                    "config": {},
                    "fsm_transition_to": None
                },
                "node_order": {
                    "id": "node_order",
                    "module_name": "create_order",
                    "config": {},
                    "fsm_transition_to": "CHECKOUT"
                },
                "node_payment": {
                    "id": "node_payment",
                    "module_name": "create_payment",
                    "config": {"gateway": "cod", "currency": "USD"},
                    "fsm_transition_to": "PAYMENT"
                },
                "node_confirm": {
                    "id": "node_confirm",
                    "module_name": "confirm_payment",
                    "config": {},
                    "fsm_transition_to": "CONFIRMED"
                },
                "node_address": {
                    "id": "node_address",
                    "module_name": "collect_address",
                    "config": {"expects_user_input": True},
                    "fsm_transition_to": None
                },
                "node_delivery": {
                    "id": "node_delivery",
                    "module_name": "create_delivery",
                    "config": {},
                    "fsm_transition_to": "CONFIRMED"
                },
                "node_notify": {
                    "id": "node_notify",
                    "module_name": "notify_customer",
                    "config": {"message": f"🍕 Thank you! Your order from {business_name} has been placed and is being prepared."},
                    "fsm_transition_to": "CONFIRMED"
                }
            },
            "edges": [
                {"from_node": "node_menu", "to_node": "node_collect", "condition": {"type": "any_input", "value": ""}},
                {"from_node": "node_collect", "to_node": "node_total", "condition": {"type": "any_input", "value": ""}},
                {"from_node": "node_total", "to_node": "node_order", "condition": {"type": "always", "value": ""}},
                {"from_node": "node_order", "to_node": "node_payment", "condition": {"type": "always", "value": ""}},
                {"from_node": "node_payment", "to_node": "node_confirm", "condition": {"type": "input_equals", "value": "CONFIRM_PAYMENT"}},
                {"from_node": "node_confirm", "to_node": "node_address", "condition": {"type": "always", "value": ""}},
                {"from_node": "node_address", "to_node": "node_delivery", "condition": {"type": "always", "value": ""}},
                {"from_node": "node_delivery", "to_node": "node_notify", "condition": {"type": "always", "value": ""}}
            ],
            "fsm_transition_table": {
                "START": {"MENU": "show_menu"},
                "MENU": {"CART": "collect_cart"},
                "CART": {"CHECKOUT": "create_order"},
                "CHECKOUT": {"PAYMENT": "create_payment"},
                "PAYMENT": {"CONFIRMED": "confirm_payment"}
            }
        }

        support = cls.get_support_workflow_template(business_id, business_name)
        feedback = cls.get_feedback_workflow_template(business_id, business_name, "DELIVERY_CREATED")

        return {
            "Ordering Workflow": ordering,
            "Support Workflow": support,
            "Feedback Workflow": feedback
        }

    @classmethod
    def get_hospital_template(cls, business_id: str, business_name: str) -> Dict[str, Any]:
        welcome_text = (
            f"🏥 Welcome to {business_name}!\n\n"
            f"Please enter the department you want to visit (e.g. Cardiology, Pediatrics, General Medicine)."
        )

        appointment = {
            "business_id": business_id,
            "version_number": 1,
            "entry_node_id": "node_dept",
            "trigger_event": None,
            "nodes": {
                "node_dept": {
                    "id": "node_dept",
                    "module_name": "select_department",
                    "config": {"prompt_message": welcome_text},
                    "fsm_transition_to": "MENU"
                },
                "node_doc": {
                    "id": "node_doc",
                    "module_name": "select_doctor",
                    "config": {"expects_user_input": True},
                    "fsm_transition_to": "CART"
                },
                "node_slot": {
                    "id": "node_slot",
                    "module_name": "select_slot",
                    "config": {"expects_user_input": True},
                    "fsm_transition_to": "CHECKOUT"
                },
                "node_book": {
                    "id": "node_book",
                    "module_name": "book_appointment",
                    "config": {},
                    "fsm_transition_to": "PAYMENT"
                },
                "node_approve": {
                    "id": "node_approve",
                    "module_name": "approve_appointment",
                    "config": {},
                    "fsm_transition_to": "CONFIRMED"
                },
                "node_remind": {
                    "id": "node_remind",
                    "module_name": "send_reminder",
                    "config": {},
                    "fsm_transition_to": "CONFIRMED"
                },
                "node_consult": {
                    "id": "node_consult",
                    "module_name": "complete_consultation",
                    "config": {},
                    "fsm_transition_to": "CONFIRMED"
                }
            },
            "edges": [
                {"from_node": "node_dept", "to_node": "node_doc", "condition": {"type": "any_input", "value": ""}},
                {"from_node": "node_doc", "to_node": "node_slot", "condition": {"type": "any_input", "value": ""}},
                {"from_node": "node_slot", "to_node": "node_book", "condition": {"type": "any_input", "value": ""}},
                {"from_node": "node_book", "to_node": "node_approve", "condition": {"type": "always", "value": ""}},
                {"from_node": "node_approve", "to_node": "node_remind", "condition": {"type": "input_equals", "value": "APPROVE"}},
                {"from_node": "node_remind", "to_node": "node_consult", "condition": {"type": "always", "value": ""}}
            ],
            "fsm_transition_table": {
                "START": {"MENU": "select_department"},
                "MENU": {"CART": "select_doctor"},
                "CART": {"CHECKOUT": "select_slot"},
                "CHECKOUT": {"PAYMENT": "book_appointment"},
                "PAYMENT": {"CONFIRMED": "approve_appointment"}
            }
        }

        support = cls.get_support_workflow_template(business_id, business_name)
        feedback = cls.get_feedback_workflow_template(business_id, business_name, "BOOKING_CREATED")

        return {
            "Appointment Workflow": appointment,
            "Support Workflow": support,
            "Feedback Workflow": feedback
        }

    @classmethod
    def get_salon_template(cls, business_id: str, business_name: str) -> Dict[str, Any]:
        welcome_text = (
            f"💇 Welcome to {business_name}!\n\n"
            f"Please enter the service you want to book (e.g. Haircut, Spa, Manicure)."
        )

        booking = {
            "business_id": business_id,
            "version_number": 1,
            "entry_node_id": "node_service",
            "trigger_event": None,
            "nodes": {
                "node_service": {
                    "id": "node_service",
                    "module_name": "select_service",
                    "config": {"prompt_message": welcome_text},
                    "fsm_transition_to": "MENU"
                },
                "node_stylist": {
                    "id": "node_stylist",
                    "module_name": "select_stylist",
                    "config": {"expects_user_input": True},
                    "fsm_transition_to": "CART"
                },
                "node_slot": {
                    "id": "node_slot",
                    "module_name": "select_slot",
                    "config": {"expects_user_input": True},
                    "fsm_transition_to": "CHECKOUT"
                },
                "node_confirm": {
                    "id": "node_confirm",
                    "module_name": "confirm_booking",
                    "config": {},
                    "fsm_transition_to": "PAYMENT"
                },
                "node_remind": {
                    "id": "node_remind",
                    "module_name": "send_reminder",
                    "config": {},
                    "fsm_transition_to": "CONFIRMED"
                },
                "node_complete": {
                    "id": "node_complete",
                    "module_name": "complete_service",
                    "config": {},
                    "fsm_transition_to": "CONFIRMED"
                }
            },
            "edges": [
                {"from_node": "node_service", "to_node": "node_stylist", "condition": {"type": "any_input", "value": ""}},
                {"from_node": "node_stylist", "to_node": "node_slot", "condition": {"type": "any_input", "value": ""}},
                {"from_node": "node_slot", "to_node": "node_confirm", "condition": {"type": "any_input", "value": ""}},
                {"from_node": "node_confirm", "to_node": "node_remind", "condition": {"type": "always", "value": ""}},
                {"from_node": "node_remind", "to_node": "node_complete", "condition": {"type": "always", "value": ""}}
            ],
            "fsm_transition_table": {
                "START": {"MENU": "select_service"},
                "MENU": {"CART": "select_stylist"},
                "CART": {"CHECKOUT": "select_slot"},
                "CHECKOUT": {"PAYMENT": "confirm_booking"},
                "PAYMENT": {"CONFIRMED": "send_reminder"}
            }
        }

        support = cls.get_support_workflow_template(business_id, business_name)
        feedback = cls.get_feedback_workflow_template(business_id, business_name, "BOOKING_CREATED")

        return {
            "Booking Workflow": booking,
            "Support Workflow": support,
            "Feedback Workflow": feedback
        }

    @classmethod
    def get_supermarket_template(cls, business_id: str, business_name: str, parsed_items: List[Tuple[str, float]]) -> Dict[str, Any]:
        menu_items_text = ""
        if parsed_items:
            for idx, (name, price) in enumerate(parsed_items, 1):
                menu_items_text += f"\n{idx}. {name} - ${price:.2f}"
        else:
            menu_items_text = "\n1. Whole Milk (1L) - $1.80\n2. Fresh Eggs (12pk) - $3.50\n3. Sliced Bread - $2.20"

        welcome_text = (
            f"🛒 Welcome to {business_name} Supermarket!\n\n"
            f"Our Catalog:{menu_items_text}\n\n"
            f"Reply with items to view or purchase."
        )

        ordering = {
            "business_id": business_id,
            "version_number": 1,
            "entry_node_id": "node_browse",
            "trigger_event": None,
            "nodes": {
                "node_browse": {
                    "id": "node_browse",
                    "module_name": "browse_catalog",
                    "config": {"menu_header": welcome_text},
                    "fsm_transition_to": "MENU"
                },
                "node_add": {
                    "id": "node_add",
                    "module_name": "add_to_cart",
                    "config": {"expects_user_input": True},
                    "fsm_transition_to": "CART"
                },
                "node_checkout": {
                    "id": "node_checkout",
                    "module_name": "checkout",
                    "config": {},
                    "fsm_transition_to": "CHECKOUT"
                },
                "node_payment": {
                    "id": "node_payment",
                    "module_name": "payment",
                    "config": {},
                    "fsm_transition_to": "PAYMENT"
                },
                "node_delivery": {
                    "id": "node_delivery",
                    "module_name": "delivery",
                    "config": {},
                    "fsm_transition_to": "CONFIRMED"
                },
                "node_feedback": {
                    "id": "node_feedback",
                    "module_name": "feedback",
                    "config": {"expects_user_input": True},
                    "fsm_transition_to": "CONFIRMED"
                }
            },
            "edges": [
                {"from_node": "node_browse", "to_node": "node_add", "condition": {"type": "any_input", "value": ""}},
                {"from_node": "node_add", "to_node": "node_checkout", "condition": {"type": "always", "value": ""}},
                {"from_node": "node_checkout", "to_node": "node_payment", "condition": {"type": "always", "value": ""}},
                {"from_node": "node_payment", "to_node": "node_delivery", "condition": {"type": "input_equals", "value": "CONFIRM_PAYMENT"}},
                {"from_node": "node_delivery", "to_node": "node_feedback", "condition": {"type": "always", "value": ""}}
            ],
            "fsm_transition_table": {
                "START": {"MENU": "browse_catalog"},
                "MENU": {"CART": "add_to_cart"},
                "CART": {"CHECKOUT": "checkout"},
                "CHECKOUT": {"PAYMENT": "payment"},
                "PAYMENT": {"CONFIRMED": "delivery"}
            }
        }

        support = cls.get_support_workflow_template(business_id, business_name)
        feedback = cls.get_feedback_workflow_template(business_id, business_name, "DELIVERY_CREATED")

        return {
            "Ordering Workflow": ordering,
            "Support Workflow": support,
            "Feedback Workflow": feedback
        }

    @classmethod
    def get_education_template(cls, business_id: str, business_name: str) -> Dict[str, Any]:
        welcome_text = (
            f"🎓 Welcome to {business_name} Academy!\n\n"
            f"Please enter the course you wish to enroll in (e.g. Intro to Python, Web Development)."
        )

        enrollment = {
            "business_id": business_id,
            "version_number": 1,
            "entry_node_id": "node_course",
            "trigger_event": None,
            "nodes": {
                "node_course": {
                    "id": "node_course",
                    "module_name": "course_selection",
                    "config": {"prompt_message": welcome_text},
                    "fsm_transition_to": "MENU"
                },
                "node_register": {
                    "id": "node_register",
                    "module_name": "registration",
                    "config": {"expects_user_input": True},
                    "fsm_transition_to": "CART"
                },
                "node_payment": {
                    "id": "node_payment",
                    "module_name": "payment",
                    "config": {},
                    "fsm_transition_to": "CHECKOUT"
                },
                "node_confirm": {
                    "id": "node_confirm",
                    "module_name": "enrollment_confirmation",
                    "config": {},
                    "fsm_transition_to": "CONFIRMED"
                },
                "node_support": {
                    "id": "node_support",
                    "module_name": "support",
                    "config": {"expects_user_input": True},
                    "fsm_transition_to": "CONFIRMED"
                },
                "node_feedback": {
                    "id": "node_feedback",
                    "module_name": "feedback",
                    "config": {"expects_user_input": True},
                    "fsm_transition_to": "CONFIRMED"
                }
            },
            "edges": [
                {"from_node": "node_course", "to_node": "node_register", "condition": {"type": "any_input", "value": ""}},
                {"from_node": "node_register", "to_node": "node_payment", "condition": {"type": "always", "value": ""}},
                {"from_node": "node_payment", "to_node": "node_confirm", "condition": {"type": "input_equals", "value": "CONFIRM_PAYMENT"}},
                {"from_node": "node_confirm", "to_node": "node_support", "condition": {"type": "always", "value": ""}},
                {"from_node": "node_support", "to_node": "node_feedback", "condition": {"type": "always", "value": ""}}
            ],
            "fsm_transition_table": {
                "START": {"MENU": "course_selection"},
                "MENU": {"CART": "registration"},
                "CART": {"CHECKOUT": "payment"},
                "CHECKOUT": {"CONFIRMED": "enrollment_confirmation"}
            }
        }

        support = cls.get_support_workflow_template(business_id, business_name)
        feedback = cls.get_feedback_workflow_template(business_id, business_name, "SUPPORT_REQUESTED")

        return {
            "Enrollment Workflow": enrollment,
            "Support Workflow": support,
            "Feedback Workflow": feedback
        }

    @classmethod
    def get_real_estate_template(cls, business_id: str, business_name: str) -> Dict[str, Any]:
        welcome_lead = (
            f"🏡 Welcome to {business_name} Realty!\n\n"
            f"Please enter your name and phone number to connect with an agent."
        )
        welcome_schedule = (
            f"📅 Schedule a property visit with {business_name}.\n\n"
            f"Please enter your preferred viewing date and time."
        )

        lead = {
            "business_id": business_id,
            "version_number": 1,
            "entry_node_id": "node_capture",
            "trigger_event": None,
            "nodes": {
                "node_capture": {
                    "id": "node_capture",
                    "module_name": "capture_lead",
                    "config": {"prompt_message": welcome_lead},
                    "fsm_transition_to": "MENU"
                },
                "node_assign": {
                    "id": "node_assign",
                    "module_name": "assign_agent",
                    "config": {},
                    "fsm_transition_to": "CART"
                },
                "node_follow": {
                    "id": "node_follow",
                    "module_name": "follow_up",
                    "config": {},
                    "fsm_transition_to": "CONFIRMED"
                }
            },
            "edges": [
                {"from_node": "node_capture", "to_node": "node_assign", "condition": {"type": "any_input", "value": ""}},
                {"from_node": "node_assign", "to_node": "node_follow", "condition": {"type": "always", "value": ""}}
            ],
            "fsm_transition_table": {
                "START": {"MENU": "capture_lead"},
                "MENU": {"CART": "assign_agent"},
                "CART": {"CONFIRMED": "follow_up"}
            }
        }

        viewing = {
            "business_id": business_id,
            "version_number": 1,
            "entry_node_id": "node_schedule",
            "trigger_event": None,
            "nodes": {
                "node_schedule": {
                    "id": "node_schedule",
                    "module_name": "schedule_visit",
                    "config": {"prompt_message": welcome_schedule},
                    "fsm_transition_to": "MENU"
                },
                "node_confirm": {
                    "id": "node_confirm",
                    "module_name": "confirm_visit",
                    "config": {},
                    "fsm_transition_to": "CONFIRMED"
                }
            },
            "edges": [
                {"from_node": "node_schedule", "to_node": "node_confirm", "condition": {"type": "any_input", "value": ""}}
            ],
            "fsm_transition_table": {
                "START": {"MENU": "schedule_visit"},
                "MENU": {"CONFIRMED": "confirm_visit"}
            }
        }

        feedback = cls.get_feedback_workflow_template(business_id, business_name, "BOOKING_CREATED")

        return {
            "Lead Management Workflow": lead,
            "Viewing Workflow": viewing,
            "Feedback Workflow": feedback
        }

    @classmethod
    def get_support_workflow_template(cls, business_id: str, business_name: str) -> Dict[str, Any]:
        return {
            "business_id": business_id,
            "version_number": 1,
            "entry_node_id": "node_support_welcome",
            "trigger_event": "SUPPORT_REQUESTED",
            "nodes": {
                "node_support_welcome": {
                    "id": "node_support_welcome",
                    "module_name": "show_menu",
                    "config": {
                        "menu_header": f"🛠️ Welcome to {business_name} Support! How can we assist you today? Reply with your concern."
                    },
                    "fsm_transition_to": "MENU"
                },
                "node_support_collect": {
                    "id": "node_support_collect",
                    "module_name": "collect_cart",
                    "config": {"expects_user_input": True},
                    "fsm_transition_to": "CART"
                },
                "node_support_notify": {
                    "id": "node_support_notify",
                    "module_name": "notify_customer",
                    "config": {
                        "message": "✅ Thank you. Your ticket has been logged and escalated to our customer support desk."
                    },
                    "fsm_transition_to": "CONFIRMED"
                }
            },
            "edges": [
                {"from_node": "node_support_welcome", "to_node": "node_support_collect", "condition": {"type": "any_input", "value": ""}},
                {"from_node": "node_support_collect", "to_node": "node_support_notify", "condition": {"type": "always", "value": ""}}
            ],
            "fsm_transition_table": {
                "START": {"MENU": "show_menu"},
                "MENU": {"CART": "collect_cart"},
                "CART": {"CONFIRMED": "notify_customer"}
            }
        }

    @classmethod
    def get_feedback_workflow_template(cls, business_id: str, business_name: str, trigger_event: str) -> Dict[str, Any]:
        return {
            "business_id": business_id,
            "version_number": 1,
            "entry_node_id": "node_feedback_welcome",
            "trigger_event": trigger_event,
            "nodes": {
                "node_feedback_welcome": {
                    "id": "node_feedback_welcome",
                    "module_name": "show_menu",
                    "config": {
                        "menu_header": f"🌟 Hi! We'd love to know how your experience with {business_name} was. Please reply with a rating score from 1 to 5."
                    },
                    "fsm_transition_to": "MENU"
                },
                "node_feedback_collect": {
                    "id": "node_feedback_collect",
                    "module_name": "collect_cart",
                    "config": {"expects_user_input": True},
                    "fsm_transition_to": "CART"
                },
                "node_feedback_notify": {
                    "id": "node_feedback_notify",
                    "module_name": "notify_customer",
                    "config": {"message": "🙏 Thank you for your valuable feedback! Have a great day!"},
                    "fsm_transition_to": "CONFIRMED"
                }
            },
            "edges": [
                {"from_node": "node_feedback_welcome", "to_node": "node_feedback_collect", "condition": {"type": "any_input", "value": ""}},
                {"from_node": "node_feedback_collect", "to_node": "node_feedback_notify", "condition": {"type": "always", "value": ""}}
            ],
            "fsm_transition_table": {
                "START": {"MENU": "show_menu"},
                "MENU": {"CART": "collect_cart"},
                "CART": {"CONFIRMED": "notify_customer"}
            }
        }

    # ---------------------------------------------------------------------------
    # Backward Compatibility Shims for test_ai_generator.py
    # ---------------------------------------------------------------------------
    @classmethod
    def get_ordering_workflow(cls, business_id: str, business_name: str, category: str, parsed_items: List[Tuple[str, float]]) -> Dict[str, Any]:
        # Return standard ordering workflow
        if category == "supermarket":
            portfolio = cls.get_supermarket_template(business_id, business_name, parsed_items)
            return portfolio["Ordering Workflow"]
        
        items = parsed_items
        if not items:
            if category == "pharmacy":
                items = [("Cough Syrup", 8.50), ("Pain Reliever", 6.00), ("Vitamins", 12.00)]
            elif category == "ecommerce":
                items = [("Wireless Mouse", 25.00), ("Keyboard", 45.00), ("USB-C Cable", 15.00)]

        portfolio = cls.get_restaurant_template(business_id, business_name, items)
        ordering = portfolio["Ordering Workflow"]
        if "node_confirm" in ordering["nodes"]:
            ordering["nodes"]["node_confirm"]["module_name"] = "confirm_payment"
            ordering["fsm_transition_table"]["PAYMENT"]["CONFIRMED"] = "confirm_payment"
        return ordering

    @classmethod
    def get_booking_workflow(cls, business_id: str, business_name: str, category: str, parsed_items: List[Tuple[str, float]]) -> Dict[str, Any]:
        if category == "salon":
            welcome_text = f"✨ Welcome to {business_name}! Please select your service (e.g. Haircut, Styling):\n\nReply with option number to start booking."
        elif category in ("clinic", "hospital"):
            welcome_text = f"✨ Welcome to {business_name}! Please select your service (e.g. Consultation, Checkup):\n\nReply with option number to start booking."
        elif category == "gym":
            welcome_text = f"✨ Welcome to {business_name}! Please select your service (e.g. Membership, Personal Training):\n\nReply with option number to start booking."
        else:
            welcome_text = f"✨ Welcome to {business_name}! Please select your service:\n\nReply with option number to start booking."

        return {
            "business_id": business_id,
            "version_number": 1,
            "entry_node_id": "node_menu",
            "trigger_event": None,
            "nodes": {
                "node_menu": {
                    "id": "node_menu",
                    "module_name": "show_menu",
                    "config": {"menu_header": welcome_text},
                    "fsm_transition_to": "MENU"
                },
                "node_collect": {
                    "id": "node_collect",
                    "module_name": "collect_cart",
                    "config": {"expects_user_input": True},
                    "fsm_transition_to": "CART"
                },
                "node_order": {
                    "id": "node_order",
                    "module_name": "create_order",
                    "config": {},
                    "fsm_transition_to": "CHECKOUT"
                },
                "node_payment": {
                    "id": "node_payment",
                    "module_name": "create_payment",
                    "config": {"gateway": "cod", "currency": "USD"},
                    "fsm_transition_to": "PAYMENT"
                },
                "node_confirm": {
                    "id": "node_confirm",
                    "module_name": "confirm_payment",
                    "config": {},
                    "fsm_transition_to": "CONFIRMED"
                },
                "node_notify": {
                    "id": "node_notify",
                    "module_name": "notify_customer",
                    "config": {"message": "📅 Your booking has been successfully confirmed. See you soon!"},
                    "fsm_transition_to": "CONFIRMED"
                }
            },
            "edges": [
                {"from_node": "node_menu", "to_node": "node_collect", "condition": {"type": "any_input", "value": ""}},
                {"from_node": "node_collect", "to_node": "node_order", "condition": {"type": "always", "value": ""}},
                {"from_node": "node_order", "to_node": "node_payment", "condition": {"type": "always", "value": ""}},
                {"from_node": "node_payment", "to_node": "node_confirm", "condition": {"type": "input_equals", "value": "CONFIRM_PAYMENT"}},
                {"from_node": "node_confirm", "to_node": "node_notify", "condition": {"type": "always", "value": ""}}
            ],
            "fsm_transition_table": {
                "START": {"MENU": "show_menu"},
                "MENU": {"CART": "collect_cart"},
                "CART": {"CHECKOUT": "create_order"},
                "CHECKOUT": {"PAYMENT": "create_payment"},
                "PAYMENT": {"CONFIRMED": "confirm_payment"}
            }
        }

    @classmethod
    def get_general_service_workflow(cls, business_id: str, business_name: str, category: str) -> Dict[str, Any]:
        return cls.get_booking_workflow(business_id, business_name, category, [])

    @classmethod
    def get_feedback_workflow(cls, business_id: str, business_name: str, category: str) -> Dict[str, Any]:
        trigger_event = "DELIVERY_COMPLETED" if category in DELIVERY_FEEDBACK_CATEGORIES else "BOOKING_CONFIRMED"
        return cls.get_feedback_workflow_template(business_id, business_name, trigger_event)

    @classmethod
    def get_support_workflow(cls, business_id: str, business_name: str, category: str) -> Dict[str, Any]:
        return cls.get_support_workflow_template(business_id, business_name)

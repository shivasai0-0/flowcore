import uuid
from typing import Any, Dict, List
from src.modules.base import BaseModule, ModuleOutput
from src.modules.registry import ModuleRegistry
from src.schemas.carry_unit import CarryUnit, OrderItem
from src.schemas.contract import ModuleContract, RetryConfig
from src.engine.exceptions import FlowCoreRuntimeError

ALL_FSM_STATES = ["START", "MENU", "BROWSING", "CART", "CART_REVIEW", "CHECKOUT", "ADDRESS", "PAYMENT", "CONFIRMED", "CANCELLED", "ERROR"]

class ShowMenuModule(BaseModule):
    def __init__(self):
        self.contract = ModuleContract(
            module_name="show_menu",
            display_name="Show Menu",
            version="1.0.0",
            domain="restaurant",
            requires={},
            produces={},
            allowed_fsm_states=["START", "MENU", "CART", "CANCELLED", "CONFIRMED", "CART_REVIEW"],
            side_effects=[],
            is_idempotent=True
        )

    async def execute(self, carry_unit: CarryUnit, config: Dict[str, Any], user_input: str) -> ModuleOutput:
        catalog = config.get("_business_catalog", {})
        biz_settings = config.get("_business_settings", {})
        
        # Determine business name
        biz_name = biz_settings.get("name") if biz_settings else None
        if not biz_name and catalog and isinstance(catalog, dict):
            biz_name = catalog.get("title") or catalog.get("name")
        if not biz_name:
            biz_name = "Our Store"
            
        menu_lines = [f"📋 --- {biz_name.upper()} MENU ---"]
        
        has_items = False
        if catalog and isinstance(catalog, dict):
            items = catalog.get("items")
            if items and isinstance(items, list):
                has_items = True
                for idx, item in enumerate(items, 1):
                    if isinstance(item, dict):
                        item_id = str(item.get("id") or item.get("item_id") or "")
                        name = item.get("name", item_id)
                        price = float(item.get("price", 10.00))
                        menu_lines.append(f"{idx}. {name} - ${price:.2f}")
            elif isinstance(catalog, dict) and len(catalog) > 0 and not any(k in catalog for k in ("items", "settings")):
                # Alternate key-value format fallback
                has_items = True
                for idx, (item_id, item_data) in enumerate(catalog.items(), 1):
                    if isinstance(item_data, dict):
                        name = item_data.get("name", item_id)
                        price = float(item_data.get("price", 10.00))
                    else:
                        name = item_id
                        price = float(item_data)
                    menu_lines.append(f"{idx}. {name} - ${price:.2f}")
                    
        if not has_items:
            # Fallback restaurant catalog
            menu_lines = [
                "🍔 --- RESTAURANT MENU ---",
                "1. Margherita Pizza - $12.00",
                "2. Veggie Burger - $8.50",
                "3. French Fries - $4.00",
                "4. Soft Drink - $2.50"
            ]
            
        menu_lines.append("Reply with items and quantities, e.g., '1 x 2, 2 x 1'")
        menu_text = "\n".join(menu_lines)
        
        return ModuleOutput(
            outputs={},
            messages=[menu_text],
            ui={
                "text": menu_text,
                "actions": []
            }
        )

class CollectCartModule(BaseModule):
    emitted_actions = ["VIEW_CART", "CALCULATE_TOTAL"]

    def __init__(self):
        self.contract = ModuleContract(
            module_name="collect_cart",
            display_name="Collect Cart Items",
            version="1.0.0",
            domain="restaurant",
            requires={},
            produces={"order.items": "list"},
            allowed_fsm_states=["MENU", "BROWSING", "CART"],
            side_effects=[],
            is_idempotent=True,
            expects_user_input=True
        )

    async def execute(self, carry_unit: CarryUnit, config: Dict[str, Any], user_input: str) -> ModuleOutput:
        import re
        
        # Check config for dynamic catalog
        catalog = config.get("_business_catalog", {})
        menu_prices = {}
        name_to_menu = {}
        if catalog and isinstance(catalog, dict):
            items = catalog.get("items")
            if items and isinstance(items, list):
                for idx, item in enumerate(items, 1):
                    if isinstance(item, dict):
                        item_id = str(item.get("id") or item.get("item_id") or "")
                        name = item.get("name", item_id)
                        price = float(item.get("price", 10.00))
                        menu_prices[item_id] = (name, price)
                        name_to_menu[name.lower()] = (item_id, price)
                        name_to_menu[str(idx)] = (item_id, price) # Allow index matching
                        for syn in item.get("synonyms", []):
                            if isinstance(syn, str):
                                name_to_menu[syn.lower()] = (item_id, price)
            elif len(catalog) > 0 and not any(k in catalog for k in ("items", "settings")):
                for idx, (item_id, item_data) in enumerate(catalog.items(), 1):
                    if isinstance(item_data, dict):
                        name = item_data.get("name", item_id)
                        price = float(item_data.get("price", 10.00))
                    else:
                        name = item_id
                        price = float(item_data)
                    menu_prices[item_id] = (name, price)
                    name_to_menu[name.lower()] = (item_id, price)
                    name_to_menu[str(idx)] = (item_id, price) # Allow index matching
        
        if not menu_prices:
            # Mock item mapper fallback
            menu_prices = {
                "1": ("Margherita Pizza", 12.00),
                "2": ("Veggie Burger", 8.50),
                "3": ("French Fries", 4.00),
                "4": ("Soft Drink", 2.50)
            }
            name_to_menu = {
                "margherita pizza": ("1", 12.00),
                "pizza": ("1", 12.00),
                "veggie burger": ("2", 8.50),
                "burger": ("2", 8.50),
                "french fries": ("3", 4.00),
                "fries": ("3", 4.00),
                "soft drink": ("4", 2.50),
                "drink": ("4", 2.50),
                "1": ("1", 12.00),
                "2": ("2", 8.50),
                "3": ("3", 4.00),
                "4": ("4", 2.50)
            }
        
        items_list = []
        parts = user_input.split(",")
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            # Require separator (x, X, *) to be surrounded by spaces
            match = re.split(r'\s+[xX\*]\s+', part)
            if len(match) != 2:
                raise FlowCoreRuntimeError(
                    error_code="INVALID_CART_INPUT",
                    message=f"Invalid cart input format: '{part}'. Please use the format: 1 x 2",
                    session_id=carry_unit.session.session_id,
                    node_id=None,
                    current_fsm_state="MENU"
                )
            
            left = match[0].strip()
            right = match[1].strip()
            
            if not right.isdigit():
                raise FlowCoreRuntimeError(
                    error_code="INVALID_CART_INPUT",
                    message=f"Invalid quantity in cart input: '{right}'.",
                    session_id=carry_unit.session.session_id,
                    node_id=None,
                    current_fsm_state="MENU"
                )
            
            qty = int(right)
            if qty <= 0:
                raise FlowCoreRuntimeError(
                    error_code="INVALID_QUANTITY",
                    message=f"Invalid quantity: '{qty}'. Quantity must be positive.",
                    session_id=carry_unit.session.session_id,
                    node_id=None,
                    current_fsm_state="MENU"
                )
                
            matched_id = None
            matched_price = None
            
            lower_left = left.lower()
            if left in menu_prices:
                matched_id = left
                _, matched_price = menu_prices[left]
            elif lower_left in name_to_menu:
                matched_id, matched_price = name_to_menu[lower_left]
            else:
                # Disable partial match on short inputs to prevent "d" matching "drink"
                if len(lower_left) >= 3:
                    for key, (m_id, m_price) in name_to_menu.items():
                        if lower_left in key or key in lower_left:
                            matched_id = m_id
                            matched_price = m_price
                            break
                            
            if not matched_id:
                raise FlowCoreRuntimeError(
                    error_code="UNKNOWN_PRODUCT",
                    message=f"Unknown product: '{left}'. Please select an item from the menu.",
                    session_id=carry_unit.session.session_id,
                    node_id=None,
                    current_fsm_state="MENU"
                )
                
            items_list.append({
                "item_id": matched_id,
                "quantity": qty,
                "price": matched_price
            })

        if not items_list:
            raise FlowCoreRuntimeError(
                error_code="INVALID_CART_INPUT",
                message="No items found in cart input.",
                session_id=carry_unit.session.session_id,
                node_id=None,
                current_fsm_state="MENU"
            )

        total_val = sum(item["price"] * item["quantity"] for item in items_list)
        item_lines = []
        for item in items_list:
            item_name = menu_prices.get(item["item_id"], (item["item_id"], item["price"]))[0]
            item_lines.append(f"{item_name} x{item['quantity']}")
        items_str = "\n".join(item_lines)
        return ModuleOutput(
            outputs={"order": {"items": items_list}},
            messages=[],
            ui={
                "text": "",
                "actions": []
            }
        )

class CalculateTotalModule(BaseModule):
    emitted_actions = ["ADD_MORE_ITEMS", "CHECKOUT", "CANCEL_ORDER"]

    def __init__(self):
        self.contract = ModuleContract(
            module_name="calculate_total",
            display_name="Calculate Cart Total",
            version="1.0.0",
            domain="restaurant",
            requires={"order.items": "list"},
            produces={"order.total": "float"},
            allowed_fsm_states=["CART"],
            side_effects=[],
            is_idempotent=True
        )

    async def execute(self, carry_unit: CarryUnit, config: Dict[str, Any], user_input: str) -> ModuleOutput:
        total = 0.0
        for item in carry_unit.order.items:
            total += item.price * item.quantity

        # Extract friendly item names from business catalog
        catalog = config.get("_business_catalog", {})
        menu_prices = {}
        if catalog and isinstance(catalog, dict):
            items = catalog.get("items")
            if items and isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        item_id = str(item.get("id") or item.get("item_id") or "")
                        name = item.get("name", item_id)
                        menu_prices[item_id] = name
            elif len(catalog) > 0 and not any(k in catalog for k in ("items", "settings")):
                for item_id, item_data in catalog.items():
                    if isinstance(item_data, dict):
                        name = item_data.get("name", item_id)
                    else:
                        name = item_id
                    menu_prices[item_id] = name

        if not menu_prices:
            menu_prices = {
                "1": "Margherita Pizza",
                "2": "Veggie Burger",
                "3": "French Fries",
                "4": "Soft Drink"
            }

        item_lines = []
        for item in carry_unit.order.items:
            item_name = menu_prices.get(item.item_id, item.item_id)
            item_lines.append(f"{item_name} x{item.quantity}")
        items_str = "\n".join(item_lines)

        msg = f"🛒 Cart Summary\n\n{items_str}\n\nCurrent Total: ${total:.2f}"
        return ModuleOutput(
            outputs={"order": {"total": total}},
            messages=[msg],
            ui={
                "text": msg,
                "actions": [
                    {"label": "Add More Items", "action": "ADD_MORE_ITEMS"},
                    {"label": "Checkout", "action": "CHECKOUT"},
                    {"label": "Cancel Order", "action": "CANCEL_ORDER"}
                ]
            }
        )

class CreateOrderModule(BaseModule):
    def __init__(self):
        self.contract = ModuleContract(
            module_name="create_order",
            display_name="Create Order",
            version="1.0.0",
            domain="restaurant",
            requires={"order.items": "list", "order.total": "float"},
            produces={"order.status": "str"},
            allowed_fsm_states=["CART", "CART_REVIEW"],
            side_effects=["persist_order"],
            is_idempotent=False,
            retry_config=RetryConfig(max_retries=3)
        )

    async def execute(self, carry_unit: CarryUnit, config: Dict[str, Any], user_input: str) -> ModuleOutput:
        msg = "📝 Order Placed\n\nYour order has been recorded. Preparing details..."
        return ModuleOutput(
            outputs={"order": {"status": "PLACED"}},
            messages=[msg],
            ui={
                "text": msg,
                "actions": []
            },
            side_effects=[
                {
                    "type": "PERSIST_ORDER",
                    "payload": {
                        "items": [
                            {"item_id": i.item_id, "quantity": i.quantity, "price": i.price}
                            for i in carry_unit.order.items
                        ],
                        "total": carry_unit.order.total
                    }
                }
            ]
        )

class CreatePaymentModule(BaseModule):
    emitted_actions = ["CONFIRM_PAYMENT"]

    def __init__(self):
        self.contract = ModuleContract(
            module_name="create_payment",
            display_name="Create Payment Link",
            version="1.0.0",
            domain="*",
            requires={"order.total": "float"},
            produces={
                "payment.payment_url": "str",
                "payment.transaction_id": "str",
                "payment.status": "str"
            },
            allowed_fsm_states=["CHECKOUT", "ADDRESS", "PAYMENT"],
            side_effects=["external_gateway_handshake"],
            is_idempotent=False
        )

    async def execute(self, carry_unit: CarryUnit, config: Dict[str, Any], user_input: str) -> ModuleOutput:
        # Resolve payment provider from injected config
        providers = config.get("_business_providers", {})
        provider_name = providers.get("payment_provider", "COD")

        is_retry = user_input.strip().upper() in {"RETRY_PAYMENT", "RETRY PAYMENT"}
        if carry_unit.payment.transaction_id and carry_unit.payment.payment_url and not is_retry:
            tx_id = carry_unit.payment.transaction_id
            pay_url = carry_unit.payment.payment_url
            status = carry_unit.payment.status or "PENDING"
        else:
            tx_id = f"tx_{uuid.uuid4().hex[:10]}"
            from src.services.provider_adapters import PaymentAdapter
            res = await PaymentAdapter.create_payment(provider_name, carry_unit.order.total or 0.0, tx_id)
            pay_url = res["payment_url"]
            status = res["status"]
            
        msg = f"💳 Payment Required ({provider_name})\n\nPlease pay here: {pay_url}\n\nReply PAY after completing payment.\nOr select Cancel Order."
        return ModuleOutput(
            outputs={
                "payment": {
                    "payment_url": pay_url,
                    "transaction_id": tx_id,
                    "status": status
                }
            },
            messages=[msg],
            ui={
                "text": msg,
                "actions": [
                    {"label": "Confirm Payment", "action": "CONFIRM_PAYMENT"}
                ]
            },
            side_effects=[
                {
                    "type": "CREATE_PAYMENT_LINK",
                    "payload": {
                        "transaction_id": tx_id,
                        "amount": carry_unit.order.total,
                        "payment_url": pay_url,
                        "provider": provider_name
                    }
                }
            ]
        )

class ConfirmPaymentModule(BaseModule):
    def __init__(self):
        self.contract = ModuleContract(
            module_name="confirm_payment",
            display_name="Confirm Payment Status",
            version="1.0.0",
            domain="*",
            requires={"payment.transaction_id": "str"},
            produces={"payment.status": "str"},
            allowed_fsm_states=["PAYMENT"],
            side_effects=["notify_finance"],
            is_idempotent=False,
            expects_user_input=True
        )

    async def execute(self, carry_unit: CarryUnit, config: Dict[str, Any], user_input: str) -> ModuleOutput:
        if carry_unit.payment.status == "SUCCESS":
            raise FlowCoreRuntimeError(
                error_code="PAYMENT_ALREADY_COMPLETED",
                message="Payment has already been successfully confirmed.",
                session_id=carry_unit.session.session_id,
                node_id=None,
                current_fsm_state="PAYMENT"
            )

        # Resolve payment provider from injected config
        providers = config.get("_business_providers", {})
        provider_name = providers.get("payment_provider", "COD")

        from src.services.provider_adapters import PaymentAdapter
        res_status = await PaymentAdapter.verify_payment(provider_name, carry_unit.payment.transaction_id, user_input)

        if res_status == "SUCCESS":
            status = "SUCCESS"
            msg = "✅ Payment Received\n\nYour order has been confirmed."
        else:
            status = "FAILED"
            msg = "❌ Payment verification failed. Please try again."
            
        return ModuleOutput(
            outputs={"payment": {"status": status}},
            messages=[msg],
            ui={
                "text": msg,
                "actions": []
            },
            side_effects=[
                {
                    "type": "SEND_NOTIFICATION",
                    "payload": {
                        "status": status,
                        "message": msg
                    }
                }
            ]
        )

class SendMessageModule(BaseModule):
    def __init__(self):
        self.contract = ModuleContract(
            module_name="send_message",
            display_name="Send Custom Message",
            version="1.0.0",
            domain="*",
            requires={},
            produces={},
            allowed_fsm_states=ALL_FSM_STATES,
            side_effects=[],
            is_idempotent=True
        )

    async def execute(self, carry_unit: CarryUnit, config: Dict[str, Any], user_input: str) -> ModuleOutput:
        text = config.get("text", "Default FlowCore Message")
        return ModuleOutput(
            outputs={},
            messages=[text]
        )

class CollectAddressModule(BaseModule):
    def __init__(self):
        self.contract = ModuleContract(
            module_name="collect_address",
            display_name="Collect Customer Address",
            version="1.0.0",
            domain="*",
            requires={},
            produces={"customer.address": "str"},
            allowed_fsm_states=["CHECKOUT", "CONFIRMED"],
            side_effects=[],
            is_idempotent=True,
            expects_user_input=True
        )

    async def execute(self, carry_unit: CarryUnit, config: Dict[str, Any], user_input: str) -> ModuleOutput:
        address = user_input.strip()
        
        # Reject control words, cart inputs, greetings, etc.
        rejected = {"pay", "hello", "yes", "no", "ok", "cancel", "checkout", "hi", "support", "menu", "start"}
        
        is_invalid = False
        if not address or len(address) < 3:
            is_invalid = True
        elif address.lower() in rejected:
            is_invalid = True
        elif any(char.isalpha() for char in address) is False:
            is_invalid = True
        else:
            # Check cart format: e.g. "1 x 2"
            import re
            if re.search(r'\d+\s*[xX\*]\s*\d+', address):
                is_invalid = True
                
        if is_invalid:
            raise FlowCoreRuntimeError(
                error_code="INVALID_ADDRESS",
                message="📍 Please enter a valid delivery address.\n\nExample:\n\nHouse No 4-56\nNear Bus Stand\nKamareddy",
                session_id=carry_unit.session.session_id,
                node_id=None,
                current_fsm_state="CHECKOUT"
            )

        msg = f"📍 Delivery Address Confirmed\n\nYour order will be delivered here:\n{address}"
        return ModuleOutput(
            outputs={
                "customer": {"address": address},
                "logistics": {"address": address}
            },
            messages=[msg],
            ui={
                "text": msg,
                "actions": [],
                "form": {
                    "type": "form",
                    "title": "Delivery Details",
                    "fields": [
                        {"name": "address", "type": "string", "label": "Delivery Address", "required": True}
                    ]
                },
                "metadata": {
                    "form": {
                        "type": "form",
                        "title": "Delivery Details",
                        "fields": [
                            {"name": "address", "type": "string", "label": "Delivery Address", "required": True}
                        ]
                    }
                }
            }
        )

class CreateDeliveryModule(BaseModule):
    def __init__(self):
        self.contract = ModuleContract(
            module_name="create_delivery",
            display_name="Create Logistics Delivery",
            version="1.0.0",
            domain="*",
            requires={"customer.address": "str"},
            produces={
                "logistics.delivery_id": "str",
                "logistics.status": "str"
            },
            allowed_fsm_states=["CHECKOUT", "CONFIRMED"],
            side_effects=["dispatch_delivery_courier"],
            is_idempotent=False
        )

    async def execute(self, carry_unit: CarryUnit, config: Dict[str, Any], user_input: str) -> ModuleOutput:
        # Resolve delivery provider from injected config
        providers = config.get("_business_providers", {})
        provider_name = providers.get("delivery_provider", "Self Delivery")

        from src.services.provider_adapters import DeliveryAdapter
        res = await DeliveryAdapter.create_delivery(provider_name, carry_unit.customer.address or "Address on file", carry_unit.order.total or 0.0)
        dlv_id = res["delivery_id"]
        status = res["status"]

        msg = f"🚚 Delivery Partner Assigned ({provider_name})\n\nYour order is being prepared."
        return ModuleOutput(
            outputs={
                "logistics": {
                    "delivery_id": dlv_id,
                    "status": status
                }
            },
            messages=[msg],
            ui={
                "text": msg,
                "actions": []
            },
            side_effects=[
                {
                    "type": "CREATE_DELIVERY",
                    "payload": {
                        "delivery_id": dlv_id,
                        "address": carry_unit.customer.address or "Address on file",
                        "provider": provider_name
                    }
                }
            ]
        )

class NotifyCustomerModule(BaseModule):
    def __init__(self):
        self.contract = ModuleContract(
            module_name="notify_customer",
            display_name="Notify Customer",
            version="1.0.0",
            domain="*",
            requires={},
            produces={},
            allowed_fsm_states=ALL_FSM_STATES,
            side_effects=[],
            is_idempotent=True
        )

    async def execute(self, carry_unit: CarryUnit, config: Dict[str, Any], user_input: str) -> ModuleOutput:
        # Resolve notification provider from config
        providers = config.get("_business_providers", {})
        provider_name = providers.get("notification_provider", "WhatsApp")

        msg = f"📦 Order Confirmed\n\nWe'll notify you via {provider_name} when your order is on the way."
        from src.services.provider_adapters import NotificationAdapter
        await NotificationAdapter.send_notification(provider_name, carry_unit.session.customer_phone, msg)

        return ModuleOutput(
            outputs={},
            messages=[msg],
            ui={
                "text": msg,
                "actions": []
            },
            side_effects=[
                {
                    "type": "SEND_NOTIFICATION",
                    "payload": {
                        "message": msg,
                        "provider": provider_name
                    }
                }
            ]
        )

# Automatically register modules with the registry
ModuleRegistry.register(ShowMenuModule)
ModuleRegistry.register(CollectCartModule)
ModuleRegistry.register(CalculateTotalModule)
ModuleRegistry.register(CreateOrderModule)
ModuleRegistry.register(CreatePaymentModule)
ModuleRegistry.register(ConfirmPaymentModule)
ModuleRegistry.register(SendMessageModule)
ModuleRegistry.register(CollectAddressModule)
ModuleRegistry.register(CreateDeliveryModule)
ModuleRegistry.register(NotifyCustomerModule)

class RequestApprovalModule(BaseModule):
    def __init__(self):
        self.contract = ModuleContract(
            module_name="request_approval",
            display_name="Request Manager Approval",
            version="1.0.0",
            domain="*",
            requires={},
            produces={"approval.status": "str"},
            allowed_fsm_states=ALL_FSM_STATES,
            side_effects=[],
            is_idempotent=False
        )

    async def execute(self, carry_unit: CarryUnit, config: Dict[str, Any], user_input: str) -> ModuleOutput:
        from src.database import AsyncSessionLocal
        from src.models import Approval
        import json
        
        session_id = carry_unit.session.session_id
        business_id = carry_unit.session.business_id
        
        req_type = config.get("request_type", "general")
        details = {
            "amount": carry_unit.order.total if carry_unit.order else 0.0,
            "items_count": len(carry_unit.order.items) if carry_unit.order else 0,
            "customer_phone": carry_unit.session.customer_phone,
            "trigger_node": config.get("_node_id", "unknown")
        }
        
        from src.database import db_session_context
        db = db_session_context.get()
        if db is not None:
            approval = Approval(
                business_id=business_id,
                session_id=session_id,
                node_id=config.get("_node_id", "unknown"),
                request_type=req_type,
                details_json=json.dumps(details),
                status="PENDING"
            )
            db.add(approval)
            await db.flush()
        else:
            async with AsyncSessionLocal() as db:
                approval = Approval(
                    business_id=business_id,
                    session_id=session_id,
                    node_id=config.get("_node_id", "unknown"),
                    request_type=req_type,
                    details_json=json.dumps(details),
                    status="PENDING"
                )
                db.add(approval)
                await db.commit()
            
        msg = "⏳ Your request requires manager approval. We will notify you once it's reviewed."
        return ModuleOutput(
            outputs={"approval": {"status": "PENDING"}},
            messages=[msg],
            ui={"text": msg, "actions": []}
        )

class AssignTaskModule(BaseModule):
    def __init__(self):
        self.contract = ModuleContract(
            module_name="assign_task",
            display_name="Assign Task to Staff",
            version="1.0.0",
            domain="*",
            requires={},
            produces={"task.id": "str"},
            allowed_fsm_states=ALL_FSM_STATES,
            side_effects=[],
            is_idempotent=False
        )

    async def execute(self, carry_unit: CarryUnit, config: Dict[str, Any], user_input: str) -> ModuleOutput:
        from src.database import AsyncSessionLocal
        from src.models import Worker, Task
        from sqlalchemy import select, func
        
        session_id = carry_unit.session.session_id
        business_id = carry_unit.session.business_id
        
        task_title = config.get("task_title", "Execute Order/Booking Task")
        task_desc = config.get("task_description", f"Process session {session_id}")
        priority = config.get("priority", "MEDIUM")
        
        assigned_worker_id = None
        
        from src.database import db_session_context
        db = db_session_context.get()
        if db is not None:
            workers_query = select(Worker).where(Worker.business_id == business_id)
            workers_res = await db.execute(workers_query)
            workers = workers_res.scalars().all()
            
            if workers:
                worker_loads = {}
                for w in workers:
                    tasks_query = select(func.count(Task.id)).where(Task.assigned_worker_id == w.id, Task.status != "COMPLETED", Task.status != "CANCELLED")
                    tasks_res = await db.execute(tasks_query)
                    count = tasks_res.scalar() or 0
                    worker_loads[w.id] = count
                
                best_worker_id = min(worker_loads, key=worker_loads.get)
                assigned_worker_id = best_worker_id
            
            task = Task(
                business_id=business_id,
                session_id=session_id,
                title=task_title,
                description=task_desc,
                priority=priority.upper(),
                assigned_worker_id=assigned_worker_id,
                status="PENDING"
            )
            db.add(task)
            await db.flush()
            await db.refresh(task)
            task_id = task.id
        else:
            async with AsyncSessionLocal() as db:
                workers_query = select(Worker).where(Worker.business_id == business_id)
                workers_res = await db.execute(workers_query)
                workers = workers_res.scalars().all()
                
                if workers:
                    worker_loads = {}
                    for w in workers:
                        tasks_query = select(func.count(Task.id)).where(Task.assigned_worker_id == w.id, Task.status != "COMPLETED", Task.status != "CANCELLED")
                        tasks_res = await db.execute(tasks_query)
                        count = tasks_res.scalar() or 0
                        worker_loads[w.id] = count
                    
                    best_worker_id = min(worker_loads, key=worker_loads.get)
                    assigned_worker_id = best_worker_id
                
                task = Task(
                    business_id=business_id,
                    session_id=session_id,
                    title=task_title,
                    description=task_desc,
                    priority=priority.upper(),
                    assigned_worker_id=assigned_worker_id,
                    status="PENDING"
                )
                db.add(task)
                await db.commit()
                await db.refresh(task)
                task_id = task.id
            
        msg = f"📋 Task Assigned (Task ID: {task_id})"
        return ModuleOutput(
            outputs={"task": {"id": task_id}},
            messages=[msg],
            ui={"text": msg, "actions": []}
        )

class GenerateReportModule(BaseModule):
    def __init__(self):
        self.contract = ModuleContract(
            module_name="generate_report",
            display_name="Generate Business Report",
            version="1.0.0",
            domain="*",
            requires={},
            produces={"report.id": "str"},
            allowed_fsm_states=ALL_FSM_STATES,
            side_effects=[],
            is_idempotent=False
        )

    async def execute(self, carry_unit: CarryUnit, config: Dict[str, Any], user_input: str) -> ModuleOutput:
        report_type = config.get("report_type", "Daily Orders")
        report_id = f"rpt_{uuid.uuid4().hex[:8]}"
        msg = f"📊 Report Generated: {report_type} (ID: {report_id})"
        return ModuleOutput(
            outputs={"report": {"id": report_id}},
            messages=[msg],
            ui={"text": msg, "actions": []}
        )

class SendReportWhatsappModule(BaseModule):
    def __init__(self):
        self.contract = ModuleContract(
            module_name="send_report_whatsapp",
            display_name="Send Report via WhatsApp",
            version="1.0.0",
            domain="*",
            requires={},
            produces={},
            allowed_fsm_states=ALL_FSM_STATES,
            side_effects=[],
            is_idempotent=True
        )

    async def execute(self, carry_unit: CarryUnit, config: Dict[str, Any], user_input: str) -> ModuleOutput:
        msg = "📱 Report delivered via WhatsApp."
        return ModuleOutput(
            outputs={},
            messages=[msg],
            ui={"text": msg, "actions": []}
        )

ModuleRegistry.register(RequestApprovalModule)
ModuleRegistry.register(AssignTaskModule)
ModuleRegistry.register(GenerateReportModule)
ModuleRegistry.register(SendReportWhatsappModule)

# Define and register mocks for all other capabilities in CapabilityRegistry
class MockCapabilityModule(BaseModule):
    def __init__(self, spec: Dict[str, Any]):
        reqs = {}
        for r in spec.get("required_config", []):
            reqs[f"config.{r}"] = "str"
        prods = {}
        for key, val in spec.get("outputs", {}).items():
            prods[key] = val
        self.contract = ModuleContract(
            module_name=spec["module_name"],
            display_name=spec["description"],
            version=spec["version"],
            domain=spec["category"],
            requires=reqs,
            produces=prods,
            allowed_fsm_states=ALL_FSM_STATES,
            is_idempotent=True
        )

    async def execute(self, carry_unit: CarryUnit, config: Dict[str, Any], user_input: str) -> ModuleOutput:
        msg = f"Capability executed: {self.contract.display_name} ({self.contract.module_name})"
        outputs = {}
        for key in self.contract.produces:
            parts = key.split(".")
            if len(parts) == 2:
                parent, child = parts
                if parent not in outputs:
                    outputs[parent] = {}
                outputs[parent][child] = f"mock_{child}_{uuid.uuid4().hex[:6]}"
        return ModuleOutput(
            outputs=outputs,
            messages=[msg],
            ui={"text": msg, "actions": []}
        )

from src.engine.registries.capability_registry import CapabilityRegistry
for spec in CapabilityRegistry.list_all():
    if not ModuleRegistry.exists(spec["module_name"]):
        mock_class = type(
            f"Mock{spec['module_name'].title().replace('_', '')}Module",
            (MockCapabilityModule,),
            {
                "__init__": lambda self, s=spec: MockCapabilityModule.__init__(self, s)
            }
        )
        ModuleRegistry.register(mock_class)

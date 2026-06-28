import logging
from enum import Enum
from typing import Dict, Set, Optional

logger = logging.getLogger("flowcore.actions")

class ActionEnum(str, Enum):
    CHECKOUT = "CHECKOUT"
    ADD_MORE_ITEMS = "ADD_MORE_ITEMS"
    CANCEL_ORDER = "CANCEL_ORDER"
    CONTACT_SUPPORT = "CONTACT_SUPPORT"
    VIEW_CART = "VIEW_CART"
    CALCULATE_TOTAL = "CALCULATE_TOTAL"
    CONFIRM_PAYMENT = "CONFIRM_PAYMENT"
    RETRY_PAYMENT = "RETRY_PAYMENT"
    TRACK_DELIVERY = "TRACK_DELIVERY"
    VIEW_ORDER = "VIEW_ORDER"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    MODIFY = "MODIFY"
    ESCALATE = "ESCALATE"

ACTION_LABELS: Dict[str, str] = {
    "CHECKOUT": "Checkout",
    "ADD_MORE_ITEMS": "Add More Items",
    "CANCEL_ORDER": "Cancel Order",
    "CONTACT_SUPPORT": "Contact Support",
    "VIEW_CART": "View Cart",
    "CALCULATE_TOTAL": "Calculate Total",
    "CONFIRM_PAYMENT": "Confirm Payment",
    "RETRY_PAYMENT": "Retry Payment",
    "TRACK_DELIVERY": "Track Delivery",
    "VIEW_ORDER": "View Order",
    "APPROVE": "Approve",
    "REJECT": "Reject",
    "MODIFY": "Modify",
    "ESCALATE": "Escalate",
}

ACTION_SYNONYMS: Dict[str, Set[str]] = {
    "CHECKOUT": {"checkout"},
    "ADD_MORE_ITEMS": {"add more items", "add_more_items"},
    "CANCEL_ORDER": {"cancel order", "cancel_order"},
    "CONTACT_SUPPORT": {"contact support", "contact_support"},
    "VIEW_CART": {"view cart", "view_cart"},
    "CALCULATE_TOTAL": {"calculate total", "calculate_total"},
    "CONFIRM_PAYMENT": {"confirm payment", "confirm_payment", "pay"},
    "RETRY_PAYMENT": {"retry payment", "retry_payment"},
    "TRACK_DELIVERY": {"track delivery", "track_delivery"},
    "VIEW_ORDER": {"view order", "view_order"},
    "APPROVE": {"approve", "approved"},
    "REJECT": {"reject", "rejected"},
    "MODIFY": {"modify", "modified"},
    "ESCALATE": {"escalate", "escalated"},
}

REGISTERED_ACTIONS: Set[str] = {action.value for action in ActionEnum}

def get_action_for_input(user_input: str) -> Optional[str]:
    if not user_input:
        return None
    clean = user_input.strip().lower()
    for action, synonyms in ACTION_SYNONYMS.items():
        if clean == action.lower() or clean in synonyms:
            return action
    return None

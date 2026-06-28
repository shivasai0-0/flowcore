import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("flowcore.event_registry")

EVENT_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "ORDER_CREATED": {
        "description": "Triggered when a new order is recorded",
        "required_fields": ["order_id", "total"]
    },
    "ORDER_UPDATED": {
        "description": "Triggered when order attributes are updated",
        "required_fields": ["order_id"]
    },
    "ORDER_CANCELLED": {
        "description": "Triggered when order is cancelled",
        "required_fields": ["order_id"]
    },
    "PAYMENT_REQUIRED": {
        "description": "Triggered when checkout completes and payment URL is ready",
        "required_fields": ["transaction_id", "amount", "payment_url"]
    },
    "PAYMENT_COMPLETED": {
        "description": "Triggered when payment is successfully confirmed",
        "required_fields": ["transaction_id"]
    },
    "PAYMENT_FAILED": {
        "description": "Triggered when payment attempt fails",
        "required_fields": ["transaction_id"]
    },
    "DELIVERY_CREATED": {
        "description": "Triggered when delivery is created and partner is assigned",
        "required_fields": ["delivery_id", "address"]
    },
    "DELIVERY_COMPLETED": {
        "description": "Triggered when order has been delivered",
        "required_fields": ["delivery_id"]
    },
    "BOOKING_CREATED": {
        "description": "Triggered when appointment booking is scheduled",
        "required_fields": ["booking_id"]
    },
    "BOOKING_CANCELLED": {
        "description": "Triggered when appointment booking is cancelled",
        "required_fields": ["booking_id"]
    },
    "SUPPORT_REQUESTED": {
        "description": "Triggered when support ticket is created",
        "required_fields": ["ticket_id"]
    },
    "SUPPORT_ESCALATED": {
        "description": "Triggered when ticket is escalated to support",
        "required_fields": ["ticket_id"]
    },
    "APPROVAL_REQUESTED": {
        "description": "Triggered when manager approval is requested",
        "required_fields": ["approval_id"]
    },
    "APPROVAL_GRANTED": {
        "description": "Triggered when manager approves request",
        "required_fields": ["approval_id"]
    },
    "APPROVAL_REJECTED": {
        "description": "Triggered when manager rejects request",
        "required_fields": ["approval_id"]
    },
    "CUSTOMER_CREATED": {
        "description": "Triggered when a new customer profile is created",
        "required_fields": ["customer_phone"]
    }
}

class EventRegistry:
    @classmethod
    def get_definition(cls, event_type: str) -> Optional[Dict[str, Any]]:
        return EVENT_SCHEMAS.get(event_type)

    @classmethod
    def list_all(cls) -> List[str]:
        return list(EVENT_SCHEMAS.keys())

    @classmethod
    def validate_payload(cls, event_type: str, payload: Dict[str, Any]) -> bool:
        """
        Validates event payload against required fields registry schema.
        Raises ValueError if fields are missing.
        """
        schema = cls.get_definition(event_type)
        if not schema:
            # Custom event types are allowed but warned
            logger.warning(f"Unregistered event type: '{event_type}'. Skipping payload schema validation.")
            return True
            
        required = schema.get("required_fields", [])
        missing = [field for field in required if field not in payload]
        if missing:
            raise ValueError(f"Event payload validation failed for type '{event_type}': missing required fields: {missing}")
            
        return True

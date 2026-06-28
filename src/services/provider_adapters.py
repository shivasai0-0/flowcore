import uuid
import logging
from typing import Any, Dict

logger = logging.getLogger("flowcore.provider_adapters")

class DeliveryAdapter:
    @staticmethod
    async def create_delivery(provider_name: str, address: str, amount: float = 0.0) -> Dict[str, Any]:
        """
        Adapts delivery creation requests to specific providers.
        Supports: Self Delivery, Porter, Shiprocket, Shadowfax.
        """
        logger.info(f"[DeliveryAdapter] Creating delivery using provider '{provider_name}' to address '{address}'")
        delivery_id = f"dlv_{provider_name.lower().replace(' ', '_')}_{uuid.uuid4().hex[:8]}"
        
        # Simulating provider-specific output structures
        if provider_name.lower() == "self delivery":
            status = "ASSIGNED"
        elif provider_name.lower() == "porter":
            status = "ASSIGNED"
        elif provider_name.lower() == "shiprocket":
            status = "ASSIGNED"
        elif provider_name.lower() == "shadowfax":
            status = "ASSIGNED"
        else:
            logger.warning(f"Unknown delivery provider '{provider_name}'. Defaulting to Self Delivery.")
            status = "ASSIGNED"
            
        return {
            "delivery_id": delivery_id,
            "status": status,
            "provider": provider_name,
            "address": address
        }

    @staticmethod
    async def track_delivery(provider_name: str, delivery_id: str) -> str:
        """Tracks delivery status."""
        logger.info(f"[DeliveryAdapter] Tracking status for delivery '{delivery_id}' via provider '{provider_name}'")
        return "IN_TRANSIT"

class PaymentAdapter:
    @staticmethod
    async def create_payment(provider_name: str, amount: float, transaction_id: str) -> Dict[str, Any]:
        """
        Adapts payment link creation to specific payment gateways.
        Supports: COD, Razorpay, Stripe.
        """
        logger.info(f"[PaymentAdapter] Creating payment link for transaction '{transaction_id}' of amount ${amount} using provider '{provider_name}'")
        
        if provider_name.lower() == "cod":
            payment_url = f"https://pay.flowcore.io/link/cod/{transaction_id}"
            status = "PENDING"
        elif provider_name.lower() == "razorpay":
            payment_url = f"https://api.razorpay.com/v1/checkout/{transaction_id}"
            status = "PENDING"
        elif provider_name.lower() == "stripe":
            payment_url = f"https://checkout.stripe.com/pay/{transaction_id}"
            status = "PENDING"
        else:
            logger.warning(f"Unknown payment provider '{provider_name}'. Defaulting to COD.")
            payment_url = f"https://pay.flowcore.io/link/cod/{transaction_id}"
            status = "PENDING"
            
        return {
            "payment_url": payment_url,
            "transaction_id": transaction_id,
            "status": status,
            "provider": provider_name
        }

    @staticmethod
    async def verify_payment(provider_name: str, transaction_id: str, user_input: str = "") -> str:
        """Verifies payment status."""
        logger.info(f"[PaymentAdapter] Verifying payment for transaction '{transaction_id}' using provider '{provider_name}'")
        # For simulation, match user confirmation text
        if user_input.upper() in {"PAY", "CONFIRM_PAYMENT", "CONFIRM PAYMENT"}:
            return "SUCCESS"
        return "FAILED"

class NotificationAdapter:
    @staticmethod
    async def send_notification(provider_name: str, recipient: str, message: str) -> bool:
        """
        Adapts notification sends to specific notification gateways.
        Supports: WhatsApp, SMS, Email.
        """
        logger.info(f"[NotificationAdapter] Sending message to '{recipient}' via provider '{provider_name}': '{message}'")
        return True

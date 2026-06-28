from typing import Any, Dict, List, Optional

PROVIDER_METADATA: Dict[str, Dict[str, Any]] = {
    "delivery": {
        "providers": ["Self Delivery", "Porter", "Shiprocket", "Shadowfax"],
        "required_config": {
            "Self Delivery": [],
            "Porter": ["api_key", "base_url"],
            "Shiprocket": ["email", "password"],
            "Shadowfax": ["token", "client_id"]
        }
    },
    "payment": {
        "providers": ["COD", "Razorpay", "Stripe"],
        "required_config": {
            "COD": [],
            "Razorpay": ["key_id", "key_secret"],
            "Stripe": ["secret_key", "webhook_secret"]
        }
    },
    "notification": {
        "providers": ["WhatsApp", "SMS", "Email"],
        "required_config": {
            "WhatsApp": ["phone_number_id", "access_token"],
            "SMS": ["twilio_sid", "twilio_token"],
            "Email": ["smtp_host", "smtp_port", "smtp_user", "smtp_password"]
        }
    }
}

class ProviderRegistry:
    @classmethod
    def get_categories(cls) -> List[str]:
        return list(PROVIDER_METADATA.keys())

    @classmethod
    def get_providers_in_category(cls, category: str) -> List[str]:
        data = PROVIDER_METADATA.get(category.lower())
        return data["providers"] if data else []

    @classmethod
    def get_required_config(cls, category: str, provider_name: str) -> List[str]:
        data = PROVIDER_METADATA.get(category.lower())
        if not data:
            return []
        # Match case-insensitively
        for name, config_fields in data["required_config"].items():
            if name.lower() == provider_name.lower():
                return config_fields
        return []

    @classmethod
    def validate_provider_config(cls, category: str, provider_name: str, config: Dict[str, Any]) -> bool:
        required = cls.get_required_config(category, provider_name)
        missing = [field for field in required if field not in config]
        if missing:
            raise ValueError(f"Provider config validation failed for category '{category}' provider '{provider_name}': missing required fields: {missing}")
        return True

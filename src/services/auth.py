import base64
import json
import hmac
import hashlib
import uuid
import datetime
from typing import Optional, List
from fastapi import Request, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db

JWT_SECRET = "flowcore_jwt_secret_key_sprint_refactor_2026"

def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')

def base64url_decode(data: str) -> bytes:
    padding = '=' * (4 - (len(data) % 4))
    return base64.urlsafe_b64decode(data + padding)

def encode_jwt(payload: dict, secret: str = JWT_SECRET) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = base64url_encode(json.dumps(header).encode())
    payload_b64 = base64url_encode(json.dumps(payload).encode())
    sig = hmac.new(secret.encode(), f"{header_b64}.{payload_b64}".encode(), hashlib.sha256).digest()
    sig_b64 = base64url_encode(sig)
    return f"{header_b64}.{payload_b64}.{sig_b64}"

def decode_jwt(token: str, secret: str = JWT_SECRET) -> dict:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid token structure")
    header_b64, payload_b64, signature_b64 = parts
    expected_sig = hmac.new(secret.encode(), f"{header_b64}.{payload_b64}".encode(), hashlib.sha256).digest()
    if not hmac.compare_digest(base64url_decode(signature_b64), expected_sig):
        raise ValueError("Signature validation failed")
    payload = json.loads(base64url_decode(payload_b64).decode())
    
    # Check expiry if present
    if "exp" in payload:
        if datetime.datetime.utcnow().timestamp() > payload["exp"]:
            raise ValueError("Token expired")
            
    return payload

def generate_salt() -> str:
    return uuid.uuid4().hex[:16]

def hash_password(password: str, salt: str) -> str:
    return hashlib.sha256(password.encode() + salt.encode()).hexdigest()

def create_tokens(employee_id: str, role: str, business_id: str, phone: str) -> dict:
    now = datetime.datetime.utcnow().timestamp()
    access_payload = {
        "sub": employee_id,
        "employee_id": employee_id,
        "role": role.lower(),
        "business_id": business_id,
        "phone": phone,
        "exp": now + 3600  # 1 hour
    }
    refresh_payload = {
        "sub": employee_id,
        "employee_id": employee_id,
        "exp": now + 86400 * 30  # 30 days
    }
    return {
        "access_token": encode_jwt(access_payload),
        "refresh_token": encode_jwt(refresh_payload),
        "token_type": "bearer",
        "expires_in": 3600
    }

async def get_current_user_context(request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    from src.config import settings
    # 1. Look for Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
        try:
            payload = decode_jwt(token)
            context = {
                "employee_id": payload.get("employee_id"),
                "role": payload.get("role"),
                "business_id": payload.get("business_id"),
                "phone": payload.get("phone")
            }
            if settings.DEVELOPMENT_WORKSPACE_MODE and settings.ACTIVE_DEV_WORKSPACE:
                context["business_id"] = settings.ACTIVE_DEV_WORKSPACE
            return context
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid or expired credentials: {str(e)}"
            )
            
    # 2. Development/Testing Header Fallbacks
    role = request.headers.get("X-FlowCore-Role")
    business_id = request.headers.get("X-FlowCore-Business-Id")
    employee_id = request.headers.get("X-FlowCore-Employee-Id")
    phone = request.headers.get("X-FlowCore-Phone")
    
    if role or business_id or employee_id or phone:
        # Fallback to dev context
        context = {
            "employee_id": employee_id or "dev_employee_id",
            "role": (role or "owner").lower(),
            "business_id": business_id or "dev_business_id",
            "phone": phone or "+919652778472"
        }
        if settings.DEVELOPMENT_WORKSPACE_MODE and settings.ACTIVE_DEV_WORKSPACE:
            context["business_id"] = settings.ACTIVE_DEV_WORKSPACE
        return context
        
    # No auth credentials provided
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication credentials not found."
    )

class PermissionChecker:
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = [r.lower() for r in allowed_roles]

    def __call__(self, user_context: dict = Depends(get_current_user_context)) -> dict:
        role = user_context.get("role")
        if not role or role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted. Insufficient permissions."
            )
        return user_context

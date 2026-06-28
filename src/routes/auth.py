from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List

from src.database import get_db
from src.models import Employee, Business, UserBusinessAccess
from src.schemas.envelope import ApiResponse
from src.services.auth import create_tokens, hash_password, decode_jwt, get_current_user_context

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])
dev_router = APIRouter(prefix="/api/v1/dev", tags=["Development Switcher"])

class LoginRequest(BaseModel):
    phone: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)

class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)

class SwitchBusinessRequest(BaseModel):
    phone: str = Field(..., min_length=1)
    business_id: str = Field(..., min_length=1)

@router.post("/login", response_model=ApiResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    # Look up employee by phone
    query = select(Employee).where(Employee.phone == payload.phone)
    res = await db.execute(query)
    employee = res.scalar_one_or_none()
    
    if not employee or employee.status != "ACTIVE" or not employee.login_enabled:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed. Invalid phone number or account disabled."
        )
        
    # Check password
    hashed = hash_password(payload.password, employee.salt)
    if hashed != employee.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed. Invalid password."
        )
        
    # Generate tokens
    tokens = create_tokens(
        employee_id=employee.id,
        role=employee.role,
        business_id=employee.business_id,
        phone=employee.phone
    )
    
    return ApiResponse(
        success=True,
        data={
            "tokens": tokens,
            "employee": {
                "id": employee.id,
                "name": employee.name,
                "phone": employee.phone,
                "role": employee.role,
                "business_id": employee.business_id,
                "force_password_change": employee.force_password_change
            }
        }
    )

@router.post("/refresh", response_model=ApiResponse)
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        decoded = decode_jwt(payload.refresh_token)
        employee_id = decoded.get("employee_id")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid refresh token: {str(e)}"
        )
        
    query = select(Employee).where(Employee.id == employee_id)
    res = await db.execute(query)
    employee = res.scalar_one_or_none()
    
    if not employee or employee.status != "ACTIVE" or not employee.login_enabled:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is suspended or disabled."
        )
        
    tokens = create_tokens(
        employee_id=employee.id,
        role=employee.role,
        business_id=employee.business_id,
        phone=employee.phone
    )
    
    return ApiResponse(success=True, data={"tokens": tokens})

@router.get("/me", response_model=ApiResponse)
async def get_me(user_context: dict = Depends(get_current_user_context)):
    return ApiResponse(success=True, data=user_context)

@dev_router.post("/switch-business", response_model=ApiResponse)
async def switch_business(payload: SwitchBusinessRequest, db: AsyncSession = Depends(get_db)):
    # ISOLATE behind developer control
    if payload.phone != "+919652778472" and payload.phone != "+91 9652778472":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation forbidden. Developer switcher is restricted."
        )
        
    # Check if target business exists
    biz_query = select(Business).where(Business.id == payload.business_id)
    biz_res = await db.execute(biz_query)
    business = biz_res.scalar_one_or_none()
    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target business not found."
        )
        
    # Verify or dynamically register access for dev phone in user_business_access
    access_query = select(UserBusinessAccess).where(
        UserBusinessAccess.phone == payload.phone,
        UserBusinessAccess.business_id == payload.business_id
    )
    access_res = await db.execute(access_query)
    access = access_res.scalar_one_or_none()
    if not access:
        access = UserBusinessAccess(
            phone=payload.phone,
            business_id=payload.business_id,
            role="owner"
        )
        db.add(access)
        await db.commit()
        
    # Find employee profile or create dummy dev employee profile for the target business
    emp_query = select(Employee).where(Employee.phone == payload.phone, Employee.business_id == payload.business_id)
    emp_res = await db.execute(emp_query)
    employee = emp_res.scalar_one_or_none()
    if not employee:
        employee = Employee(
            business_id=payload.business_id,
            name="Developer Account",
            phone=payload.phone,
            role="owner",
            status="ACTIVE",
            login_enabled=True,
            password_hash="",
            salt=""
        )
        db.add(employee)
        await db.commit()
        await db.refresh(employee)
        
    # Generate token scoped to target business
    tokens = create_tokens(
        employee_id=employee.id,
        role="owner",
        business_id=payload.business_id,
        phone=payload.phone
    )
    
    return ApiResponse(
        success=True,
        data={
            "tokens": tokens,
            "business_id": payload.business_id,
            "role": "owner"
        }
    )

@dev_router.get("/businesses", response_model=ApiResponse)
async def list_switcher_businesses(db: AsyncSession = Depends(get_db)):
    # Return all registered businesses in the system for developer switcher lookup
    biz_query = select(Business).order_by(Business.name)
    biz_res = await db.execute(biz_query)
    businesses = biz_res.scalars().all()
    
    data = []
    for b in businesses:
        data.append({
            "id": b.id,
            "name": b.name,
            "business_type": b.business_type
        })
        
    return ApiResponse(success=True, data=data)

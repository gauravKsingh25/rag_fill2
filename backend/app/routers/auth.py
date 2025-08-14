"""
Authentication router for user registration, login, and logout.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPAuthorizationCredentials
from datetime import timedelta
from typing import Dict, Any

from ..models import User, UserCreate, UserLogin, Token, UserInDB
from ..core.auth import (
    get_password_hash, 
    authenticate_user, 
    create_access_token, 
    get_current_active_user,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    security
)
from ..database import user_repo

router = APIRouter()

@router.post("/register", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate):
    """
    Register a new user account.
    
    - **email**: Valid email address
    - **password**: Password (minimum 8 characters)
    """
    try:
        # Check if user already exists
        existing_user = await user_repo.get_user_by_email(user.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        
        # Hash password and create user
        hashed_password = get_password_hash(user.password)
        user_data = {
            "email": user.email,
            "hashed_password": hashed_password
        }
        
        user_id = await user_repo.create_user(user_data)
        
        return {
            "message": "User registered successfully",
            "user_id": user_id,
            "email": user.email
        }
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register user"
        )

@router.post("/login", response_model=Token)
async def login_user(user_credentials: UserLogin):
    """
    Authenticate user and return access token.
    
    - **email**: User email address
    - **password**: User password
    """
    user = await authenticate_user(user_credentials.email, user_credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.post("/logout")
async def logout_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Logout user (invalidate token).
    
    Note: In a production environment, you would typically maintain a blacklist 
    of invalidated tokens or use short-lived tokens with refresh tokens.
    """
    return {"message": "Successfully logged out"}

@router.get("/me", response_model=User)
async def get_current_user_info(current_user: UserInDB = Depends(get_current_active_user)):
    """
    Get current authenticated user information.
    """
    return User(
        id=current_user.id,
        email=current_user.email,
        created_at=current_user.created_at,
        is_active=current_user.is_active
    )

@router.get("/verify-token")
async def verify_token(current_user: UserInDB = Depends(get_current_active_user)):
    """
    Verify if the current token is valid.
    """
    return {
        "valid": True,
        "user_id": current_user.id,
        "email": current_user.email
    }

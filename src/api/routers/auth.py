"""
Authentication Router
Handles user registration, login, and token management
"""
from fastapi import APIRouter, HTTPException, status, Depends
from src.api.models import UserCreate, UserLogin, UserResponse, TokenResponse
from src.api.auth import (
    create_user, authenticate_user, create_access_token,
    create_refresh_token, get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES
)
from datetime import timedelta

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate):
    """Register a new user (student, teacher, admin)"""
    try:
        user = create_user(
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name,
            role=user_data.role,
            school_id=user_data.school_id,
            class_level=user_data.class_level
        )

        return UserResponse(
            id=user["id"],
            email=user["email"],
            full_name=user["full_name"],
            role=user["role"],
            school_id=user.get("school_id"),
            class_level=user.get("class_level"),
            created_at=user["created_at"],
            is_active=user["is_active"]
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    """Login and receive access token"""
    user = authenticate_user(credentials.email, credentials.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create tokens
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user["id"],
            "email": user["email"],
            "role": user["role"],
            "full_name": user["full_name"]
        },
        expires_delta=access_token_expires
    )

    refresh_token = create_refresh_token(
        data={"sub": user["id"], "email": user["email"]}
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current authenticated user information"""
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        full_name=current_user["full_name"],
        role=current_user["role"],
        school_id=current_user.get("school_id"),
        class_level=current_user.get("class_level"),
        created_at=current_user["created_at"],
        is_active=current_user["is_active"]
    )


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """Logout (client should delete tokens)"""
    return {"message": "Successfully logged out"}

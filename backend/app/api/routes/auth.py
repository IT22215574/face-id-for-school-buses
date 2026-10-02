from datetime import datetime, timedelta, timezone
from hashlib import sha256

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.security import decode_token, get_current_parent
from app.models.parent import Parent
from app.models.refresh_token import RefreshToken
from app.schemas.auth import AuthTokenResponse, ParentLogin, ParentRegister, RefreshTokenRequest
from app.services.auth_service import login_parent, logout_parent, refresh_token_pair, register_parent

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=AuthTokenResponse, status_code=status.HTTP_201_CREATED)
def register_user(payload: ParentRegister, db: Session = Depends(get_db)):
    parent = register_parent(db, payload.name, payload.phone, payload.email, payload.password)
    access, refresh, _, _ = login_parent(db, payload.email, payload.password)
    return AuthTokenResponse(access_token=access, refresh_token=refresh, token_type="bearer", expires_in_minutes=30, refresh_expires_days=30)


@router.post("/login", response_model=AuthTokenResponse)
def login_user(payload: ParentLogin, db: Session = Depends(get_db)):
    access, refresh, _, _ = login_parent(db, payload.email, payload.password)
    return AuthTokenResponse(access_token=access, refresh_token=refresh, token_type="bearer", expires_in_minutes=30, refresh_expires_days=30)


@router.post("/refresh", response_model=AuthTokenResponse)
def refresh_user(payload: RefreshTokenRequest, db: Session = Depends(get_db)):
    access, refresh = refresh_token_pair(db, payload.refresh_token)
    return AuthTokenResponse(access_token=access, refresh_token=refresh, token_type="bearer", expires_in_minutes=30, refresh_expires_days=30)


@router.post("/logout")
def logout_user(payload: RefreshTokenRequest | None = None, current_parent=Depends(get_current_parent), db: Session = Depends(get_db)):
    refresh_value = payload.refresh_token if payload else None
    logout_parent(db, current_parent.id, refresh_value)
    return {"message": "Logged out successfully"}

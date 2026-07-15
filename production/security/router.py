"""production/security/router.py — /api/auth/* endpoints (login, whoami)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from production.security.auth import authenticate_user, create_access_token, get_current_user, TokenData

router = APIRouter(prefix="/api/auth", tags=["authentication"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


@router.post("/login", response_model=TokenResponse,
            summary="Obtain a JWT access token",
            responses={401: {"description": "Invalid username or password"}})
async def login(form: OAuth2PasswordRequestForm = Depends()) -> TokenResponse:
    user = authenticate_user(form.username, form.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                           detail="Invalid username or password",
                           headers={"WWW-Authenticate": "Bearer"})
    token = create_access_token(user)
    return TokenResponse(access_token=token, role=user.role)


@router.get("/me", summary="Current authenticated user")
async def whoami(current: TokenData = Depends(get_current_user)) -> dict:
    return {"username": current.username, "role": current.role}

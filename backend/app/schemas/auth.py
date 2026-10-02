from pydantic import BaseModel, EmailStr, Field


class ParentRegister(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    phone: str = Field(..., min_length=8, max_length=32)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class ParentLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class AuthTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    refresh_expires_days: int

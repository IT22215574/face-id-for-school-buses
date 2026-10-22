from pydantic import BaseModel, EmailStr, Field, field_validator


class ParentRegister(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    phone: str = Field(..., min_length=8, max_length=32)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("name", "phone", "email", mode="before")
    @classmethod
    def strip_contact(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value):
        import re
        if not re.fullmatch(r"\+?[0-9]{8,15}", value):
            raise ValueError("Enter 8–15 digits, optionally starting with +")
        return value

    @field_validator("password")
    @classmethod
    def validate_password_bytes(cls, value):
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be at most 72 bytes")
        return value


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

import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    full_name: str = Field(default="", max_length=200)

    @field_validator("password")
    @classmethod
    def _password_strength(cls, v: str) -> str:
        if len(v.encode("utf-8")) > 72:
            raise ValueError("password too long (max 72 bytes)")
        if v.isalpha() or v.isdigit():
            raise ValueError("password must mix letters with numbers or symbols")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=10, max_length=200)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str

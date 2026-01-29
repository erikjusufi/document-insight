from typing import Annotated

from pydantic import BaseModel, EmailStr, StringConstraints

PasswordStr = Annotated[str, StringConstraints(min_length=8, max_length=72)]


class RegisterRequest(BaseModel):
    email: EmailStr
    password: PasswordStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: PasswordStr


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: EmailStr

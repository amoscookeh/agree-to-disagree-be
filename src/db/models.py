from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class User(BaseModel):
    id: UUID
    username: str
    email: str | None = None
    created_at: datetime


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=20, pattern="^[a-zA-Z0-9_]+$")
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: str
    email: str | None = None
    username: str
    max_researches: int
    researches_used: int
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class WaitlistJoin(BaseModel):
    email: EmailStr


class Query(BaseModel):
    id: UUID
    user_id: UUID
    query_text: str
    is_completed: bool = False
    created_at: datetime


class Report(BaseModel):
    id: UUID
    query_id: UUID
    summary: str
    left_perspective: str
    right_perspective: str
    citations: list[dict[str, Any]]
    created_at: datetime

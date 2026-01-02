from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class User(BaseModel):
    id: UUID
    username: str
    email: str
    verified: bool = False
    created_at: datetime


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

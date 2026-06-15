from datetime import datetime
from typing import Optional
from pydantic import BaseModel, validator


class PasteCreate(BaseModel):
    title: Optional[str] = None
    content: str
    language: str = "plaintext"
    password: Optional[str] = None
    expiry: str = "never"

    @validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Content cannot be empty")
        return v


class PasteResponse(BaseModel):
    short_code: str
    title: Optional[str]
    content: str
    language: str
    views: int
    created_at: datetime
    expires_at: Optional[datetime]
    is_protected: bool

    class Config:
        from_attributes = True

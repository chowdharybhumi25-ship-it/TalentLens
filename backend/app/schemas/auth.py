from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class RecruiterCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    company: Optional[str] = None
    password: str = Field(..., min_length=8)


class RecruiterLogin(BaseModel):
    email: EmailStr
    password: str


class RecruiterOut(BaseModel):
    id: int
    email: str
    full_name: str
    company: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    recruiter: RecruiterOut


class TokenData(BaseModel):
    user_id: Optional[int] = None

from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime


class JobCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    company: str = Field(..., min_length=2, max_length=255)
    description: str = Field(..., min_length=10)
    required_skills: List[str] = []
    preferred_skills: List[str] = []
    min_experience: float = 0
    max_experience: Optional[float] = None
    education_requirements: List[str] = []
    employment_type: str = "Full-time"
    location: Optional[str] = None
    mandatory_requirements: List[str] = []
    responsibilities: List[str] = []
    is_active: bool = True


class JobUpdate(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    description: Optional[str] = None
    required_skills: Optional[List[str]] = None
    preferred_skills: Optional[List[str]] = None
    min_experience: Optional[float] = None
    max_experience: Optional[float] = None
    education_requirements: Optional[List[str]] = None
    employment_type: Optional[str] = None
    location: Optional[str] = None
    mandatory_requirements: Optional[List[str]] = None
    responsibilities: Optional[List[str]] = None
    is_active: Optional[bool] = None


class JobOut(BaseModel):
    id: int
    recruiter_id: int
    title: str
    company: str
    description: str
    required_skills: List[str]
    preferred_skills: List[str]
    min_experience: float
    max_experience: Optional[float]
    education_requirements: List[str]
    employment_type: str
    location: Optional[str]
    mandatory_requirements: List[str]
    responsibilities: List[str]
    is_active: bool
    parsed_data: Optional[Any]
    created_at: datetime
    updated_at: datetime
    application_count: Optional[int] = 0

    class Config:
        from_attributes = True


class JobParseRequest(BaseModel):
    description: str

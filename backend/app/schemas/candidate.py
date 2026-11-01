from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


class CandidateSkillOut(BaseModel):
    id: int
    skill: str
    skill_type: str
    proficiency: Optional[str]

    class Config:
        from_attributes = True


class CandidateEducationOut(BaseModel):
    id: int
    degree: Optional[str]
    field_of_study: Optional[str]
    institution: Optional[str]
    start_year: Optional[int]
    end_year: Optional[int]
    gpa: Optional[float]
    is_current: bool

    class Config:
        from_attributes = True


class CandidateExperienceOut(BaseModel):
    id: int
    title: Optional[str]
    company: Optional[str]
    location: Optional[str]
    start_date: Optional[str]
    end_date: Optional[str]
    is_current: bool
    description: Optional[str]
    duration_months: int
    is_internship: bool

    class Config:
        from_attributes = True


class CandidateOut(BaseModel):
    id: int
    recruiter_id: int
    name: str
    email: Optional[str]
    phone: Optional[str]
    location: Optional[str]
    summary: Optional[str]
    technical_skills: List[str]
    programming_languages: List[str]
    certifications: List[str]
    projects: List[Any]
    total_experience_years: float
    extraction_confidence: float
    is_verified: bool
    created_at: datetime
    skills: List[CandidateSkillOut] = []
    education: List[CandidateEducationOut] = []
    experience: List[CandidateExperienceOut] = []

    class Config:
        from_attributes = True


class CandidateUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    summary: Optional[str] = None
    technical_skills: Optional[List[str]] = None
    programming_languages: Optional[List[str]] = None
    certifications: Optional[List[str]] = None
    total_experience_years: Optional[float] = None


class CompareRequest(BaseModel):
    candidate_ids: List[int]
    job_id: int

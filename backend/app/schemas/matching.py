from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


class MatchResultOut(BaseModel):
    id: int
    job_id: int
    candidate_id: int
    overall_score: float
    required_skills_score: float
    preferred_skills_score: float
    experience_score: float
    education_score: float
    project_relevance_score: float
    semantic_similarity_score: float
    matched_required_skills: List[str]
    missing_required_skills: List[str]
    matched_preferred_skills: List[str]
    missing_preferred_skills: List[str]
    is_eligible: bool
    eligibility_failures: List[str]
    recommendation_status: str
    computed_at: datetime
    candidate_name: Optional[str] = None
    candidate_email: Optional[str] = None
    explanation: Optional[Any] = None

    class Config:
        from_attributes = True


class MatchExplanationOut(BaseModel):
    strengths: List[str]
    weaknesses: List[str]
    suggestions: List[str]
    summary_text: Optional[str]
    generated_by: str

    class Config:
        from_attributes = True


class ApplicationStatusUpdate(BaseModel):
    status: str
    notes: Optional[str] = None

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.database.session import get_db
from app.models.recruiter import Recruiter
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.match_result import MatchResult
from app.models.interview import InterviewQuestion
from app.core.security import get_current_user
from app.ai.interview_generator import generate_interview_questions_template
from app.ai.llm_service import generate_interview_questions_llm, is_llm_available

router = APIRouter()


class GenerateRequest(BaseModel):
    job_id: int
    candidate_id: int
    regenerate: bool = False


@router.post("/generate")
def generate_questions(
    request: GenerateRequest,
    db: Session = Depends(get_db),
    current_user: Recruiter = Depends(get_current_user),
):
    """Generate interview questions for a candidate-job pair."""
    job = db.query(Job).filter(
        Job.id == request.job_id,
        Job.recruiter_id == current_user.id
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    candidate = db.query(Candidate).filter(
        Candidate.id == request.candidate_id,
        Candidate.recruiter_id == current_user.id
    ).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    # Check if questions already exist
    if not request.regenerate:
        existing = db.query(InterviewQuestion).filter(
            InterviewQuestion.job_id == request.job_id,
            InterviewQuestion.candidate_id == request.candidate_id,
        ).first()
        if existing:
            return {
                "questions": existing.questions,
                "generated_by": existing.generated_by,
                "llm_available": is_llm_available(),
            }

    # Get match result for missing skills
    match_result = db.query(MatchResult).filter(
        MatchResult.job_id == request.job_id,
        MatchResult.candidate_id == request.candidate_id
    ).first()

    missing_skills = match_result.missing_required_skills if match_result else []
    all_candidate_skills = list(set(
        (candidate.technical_skills or []) + (candidate.programming_languages or [])
    ))

    # Try LLM first, fallback to template
    questions = None
    generated_by = "template"

    if is_llm_available():
        questions = generate_interview_questions_llm(
            job_title=job.title,
            required_skills=job.required_skills or [],
            candidate_name=candidate.name,
            candidate_skills=all_candidate_skills,
            candidate_projects=candidate.projects or [],
            experience_years=candidate.total_experience_years,
            missing_skills=missing_skills,
        )
        if questions:
            generated_by = "llm"

    if not questions:
        questions = generate_interview_questions_template(
            job_title=job.title,
            required_skills=job.required_skills or [],
            candidate_name=candidate.name,
            candidate_skills=all_candidate_skills,
            candidate_projects=candidate.projects or [],
            experience_years=candidate.total_experience_years,
            missing_skills=missing_skills,
        )

    # Save/update
    existing = db.query(InterviewQuestion).filter(
        InterviewQuestion.job_id == request.job_id,
        InterviewQuestion.candidate_id == request.candidate_id,
    ).first()

    if existing:
        existing.questions = questions
        existing.generated_by = generated_by
    else:
        iq = InterviewQuestion(
            job_id=request.job_id,
            candidate_id=request.candidate_id,
            questions=questions,
            generated_by=generated_by,
        )
        db.add(iq)

    db.commit()

    return {
        "questions": questions,
        "generated_by": generated_by,
        "llm_available": is_llm_available(),
    }


@router.get("/{candidate_id}")
def get_questions(
    candidate_id: int,
    job_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Recruiter = Depends(get_current_user),
):
    """Get saved interview questions for a candidate."""
    query = db.query(InterviewQuestion).filter(
        InterviewQuestion.candidate_id == candidate_id
    )
    if job_id:
        query = query.filter(InterviewQuestion.job_id == job_id)

    results = query.all()
    return [
        {
            "id": r.id,
            "job_id": r.job_id,
            "candidate_id": r.candidate_id,
            "questions": r.questions,
            "generated_by": r.generated_by,
            "created_at": r.created_at,
        }
        for r in results
    ]

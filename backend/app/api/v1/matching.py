from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database.session import get_db
from app.models.recruiter import Recruiter
from app.models.job import Job
from app.models.candidate import Candidate
from app.models.application import Application
from app.models.match_result import MatchResult, MatchExplanation
from app.schemas.matching import MatchResultOut, ApplicationStatusUpdate
from app.core.security import get_current_user
from app.ai.matching_engine import compute_match_score, generate_explanation

router = APIRouter()


def candidate_to_dict(candidate: Candidate) -> dict:
    return {
        "technical_skills": candidate.technical_skills or [],
        "programming_languages": candidate.programming_languages or [],
        "total_experience_years": candidate.total_experience_years,
        "education": [
            {
                "degree": e.degree,
                "field_of_study": e.field_of_study,
                "institution": e.institution,
            }
            for e in candidate.education
        ],
        "projects": candidate.projects or [],
        "certifications": candidate.certifications or [],
        "summary": candidate.summary or "",
        "experience": [
            {
                "title": e.title,
                "company": e.company,
                "description": e.description or "",
            }
            for e in candidate.experience
        ],
        "name": candidate.name,
    }


def job_to_dict(job: Job) -> dict:
    return {
        "title": job.title,
        "description": job.description,
        "required_skills": job.required_skills or [],
        "preferred_skills": job.preferred_skills or [],
        "min_experience": job.min_experience,
        "max_experience": job.max_experience,
        "education_requirements": job.education_requirements or [],
        "mandatory_requirements": job.mandatory_requirements or [],
        "responsibilities": job.responsibilities or [],
    }


@router.post("/{job_id}")
def run_matching(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: Recruiter = Depends(get_current_user),
):
    """Run AI matching for all candidates applied to this job."""
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.recruiter_id == current_user.id
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Get all applications for this job
    applications = db.query(Application).filter(
        Application.job_id == job_id
    ).all()

    if not applications:
        return {"message": "No candidates to match", "matched": 0}

    job_dict = job_to_dict(job)
    processed = 0

    for app in applications:
        candidate = db.query(Candidate).filter(
            Candidate.id == app.candidate_id
        ).first()
        if not candidate:
            continue

        cand_dict = candidate_to_dict(candidate)

        # Compute scores
        scores = compute_match_score(cand_dict, job_dict)

        # Upsert match result
        existing = db.query(MatchResult).filter(
            MatchResult.job_id == job_id,
            MatchResult.candidate_id == candidate.id
        ).first()

        if existing:
            for k, v in scores.items():
                setattr(existing, k, v)
            match_result = existing
        else:
            match_result = MatchResult(
                job_id=job_id,
                candidate_id=candidate.id,
                **scores,
            )
            db.add(match_result)

        db.flush()

        # Generate explanation
        explanation_data = generate_explanation(scores, cand_dict, job_dict)

        if match_result.explanation:
            exp = match_result.explanation
            exp.strengths = explanation_data['strengths']
            exp.weaknesses = explanation_data['weaknesses']
            exp.suggestions = explanation_data['suggestions']
            exp.summary_text = explanation_data['summary_text']
        else:
            exp = MatchExplanation(
                match_result_id=match_result.id,
                **explanation_data,
            )
            db.add(exp)

        processed += 1

    db.commit()
    return {"message": f"Matching complete", "matched": processed}


@router.get("/{job_id}/results")
def get_matching_results(
    job_id: int,
    min_score: Optional[float] = None,
    max_score: Optional[float] = None,
    eligible_only: bool = False,
    status_filter: Optional[str] = None,
    sort_by: str = "overall_score",
    sort_order: str = "desc",
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: Recruiter = Depends(get_current_user),
):
    """Get ranked matching results for a job."""
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.recruiter_id == current_user.id
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    query = db.query(MatchResult).filter(MatchResult.job_id == job_id)

    if min_score is not None:
        query = query.filter(MatchResult.overall_score >= min_score)
    if max_score is not None:
        query = query.filter(MatchResult.overall_score <= max_score)
    if eligible_only:
        query = query.filter(MatchResult.is_eligible == True)
    if status_filter:
        query = query.filter(MatchResult.recommendation_status == status_filter)

    # Sort
    sort_col = getattr(MatchResult, sort_by, MatchResult.overall_score)
    if sort_order == "desc":
        query = query.order_by(sort_col.desc())
    else:
        query = query.order_by(sort_col.asc())

    total = query.count()
    results = query.offset(skip).limit(limit).all()

    enriched = []
    for r in results:
        candidate = db.query(Candidate).filter(Candidate.id == r.candidate_id).first()
        item = {
            "id": r.id,
            "job_id": r.job_id,
            "candidate_id": r.candidate_id,
            "overall_score": r.overall_score,
            "required_skills_score": r.required_skills_score,
            "preferred_skills_score": r.preferred_skills_score,
            "experience_score": r.experience_score,
            "education_score": r.education_score,
            "project_relevance_score": r.project_relevance_score,
            "semantic_similarity_score": r.semantic_similarity_score,
            "matched_required_skills": r.matched_required_skills,
            "missing_required_skills": r.missing_required_skills,
            "matched_preferred_skills": r.matched_preferred_skills,
            "missing_preferred_skills": r.missing_preferred_skills,
            "is_eligible": r.is_eligible,
            "eligibility_failures": r.eligibility_failures,
            "recommendation_status": r.recommendation_status,
            "computed_at": r.computed_at,
            "candidate_name": candidate.name if candidate else "Unknown",
            "candidate_email": candidate.email if candidate else None,
            "candidate_skills": (candidate.technical_skills or []) if candidate else [],
            "candidate_experience": candidate.total_experience_years if candidate else 0,
            "explanation": {
                "strengths": r.explanation.strengths if r.explanation else [],
                "weaknesses": r.explanation.weaknesses if r.explanation else [],
                "suggestions": r.explanation.suggestions if r.explanation else [],
                "summary_text": r.explanation.summary_text if r.explanation else "",
            } if r.explanation else None,
        }
        enriched.append(item)

    return {"total": total, "results": enriched}


@router.get("/{job_id}/{candidate_id}")
def get_candidate_match(
    job_id: int,
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: Recruiter = Depends(get_current_user),
):
    """Get detailed match result for a specific candidate-job pair."""
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.recruiter_id == current_user.id
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    candidate = db.query(Candidate).filter(
        Candidate.id == candidate_id,
        Candidate.recruiter_id == current_user.id
    ).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    match = db.query(MatchResult).filter(
        MatchResult.job_id == job_id,
        MatchResult.candidate_id == candidate_id
    ).first()

    if not match:
        # Compute on the fly
        cand_dict = candidate_to_dict(candidate)
        job_dict = job_to_dict(job)
        scores = compute_match_score(cand_dict, job_dict)
        exp_data = generate_explanation(scores, cand_dict, job_dict)
        return {**scores, "explanation": exp_data}

    return {
        "overall_score": match.overall_score,
        "required_skills_score": match.required_skills_score,
        "preferred_skills_score": match.preferred_skills_score,
        "experience_score": match.experience_score,
        "education_score": match.education_score,
        "project_relevance_score": match.project_relevance_score,
        "semantic_similarity_score": match.semantic_similarity_score,
        "matched_required_skills": match.matched_required_skills,
        "missing_required_skills": match.missing_required_skills,
        "matched_preferred_skills": match.matched_preferred_skills,
        "missing_preferred_skills": match.missing_preferred_skills,
        "is_eligible": match.is_eligible,
        "eligibility_failures": match.eligibility_failures,
        "recommendation_status": match.recommendation_status,
        "explanation": {
            "strengths": match.explanation.strengths if match.explanation else [],
            "weaknesses": match.explanation.weaknesses if match.explanation else [],
            "suggestions": match.explanation.suggestions if match.explanation else [],
            "summary_text": match.explanation.summary_text if match.explanation else "",
        } if match.explanation else None,
    }


@router.put("/applications/{application_id}/status")
def update_application_status(
    application_id: int,
    update: ApplicationStatusUpdate,
    db: Session = Depends(get_db),
    current_user: Recruiter = Depends(get_current_user),
):
    """Update application status (shortlist, reject, etc.)."""
    app = db.query(Application).join(Job).filter(
        Application.id == application_id,
        Job.recruiter_id == current_user.id
    ).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    valid_statuses = ["pending", "under_review", "shortlisted", "rejected", "hired"]
    if update.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")

    app.status = update.status
    if update.notes:
        app.notes = update.notes
    db.commit()

    return {"application_id": application_id, "status": app.status, "message": "Status updated"}

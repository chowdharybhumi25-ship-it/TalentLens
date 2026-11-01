from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional

from app.database.session import get_db
from app.models.recruiter import Recruiter
from app.models.job import Job
from app.models.application import Application
from app.schemas.job import JobCreate, JobUpdate, JobOut, JobParseRequest
from app.core.security import get_current_user
from app.parsers.jd_parser import parse_job_description

router = APIRouter()


@router.post("", response_model=JobOut, status_code=201)
def create_job(
    job_data: JobCreate,
    db: Session = Depends(get_db),
    current_user: Recruiter = Depends(get_current_user),
):
    # Parse JD to auto-extract if not provided
    parsed = parse_job_description(job_data.description)

    job = Job(
        recruiter_id=current_user.id,
        title=job_data.title,
        company=job_data.company,
        description=job_data.description,
        required_skills=job_data.required_skills or parsed.get('required_skills', []),
        preferred_skills=job_data.preferred_skills or parsed.get('preferred_skills', []),
        min_experience=job_data.min_experience,
        max_experience=job_data.max_experience,
        education_requirements=job_data.education_requirements or parsed.get('education_requirements', []),
        employment_type=job_data.employment_type,
        location=job_data.location or parsed.get('location'),
        mandatory_requirements=job_data.mandatory_requirements or parsed.get('mandatory_requirements', []),
        responsibilities=job_data.responsibilities or parsed.get('responsibilities', []),
        is_active=job_data.is_active,
        parsed_data=parsed,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    result = JobOut.model_validate(job)
    result.application_count = 0
    return result


@router.get("", response_model=List[JobOut])
def list_jobs(
    skip: int = 0,
    limit: int = 50,
    active_only: bool = False,
    db: Session = Depends(get_db),
    current_user: Recruiter = Depends(get_current_user),
):
    query = db.query(Job).filter(Job.recruiter_id == current_user.id)
    if active_only:
        query = query.filter(Job.is_active == True)
    jobs = query.order_by(Job.created_at.desc()).offset(skip).limit(limit).all()

    results = []
    for job in jobs:
        j = JobOut.model_validate(job)
        j.application_count = db.query(Application).filter(Application.job_id == job.id).count()
        results.append(j)
    return results


@router.get("/{job_id}", response_model=JobOut)
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: Recruiter = Depends(get_current_user),
):
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.recruiter_id == current_user.id
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    result = JobOut.model_validate(job)
    result.application_count = db.query(Application).filter(Application.job_id == job_id).count()
    return result


@router.put("/{job_id}", response_model=JobOut)
def update_job(
    job_id: int,
    job_data: JobUpdate,
    db: Session = Depends(get_db),
    current_user: Recruiter = Depends(get_current_user),
):
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.recruiter_id == current_user.id
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    update_data = job_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(job, field, value)

    db.commit()
    db.refresh(job)

    result = JobOut.model_validate(job)
    result.application_count = db.query(Application).filter(Application.job_id == job_id).count()
    return result


@router.delete("/{job_id}", status_code=204)
def delete_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: Recruiter = Depends(get_current_user),
):
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.recruiter_id == current_user.id
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    db.delete(job)
    db.commit()


@router.post("/parse", summary="Parse a job description")
def parse_jd(request: JobParseRequest):
    parsed = parse_job_description(request.description)
    return {"parsed": parsed}

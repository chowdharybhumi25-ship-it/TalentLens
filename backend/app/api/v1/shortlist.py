from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
import csv
import io

from app.database.session import get_db
from app.models.recruiter import Recruiter
from app.models.candidate import Candidate
from app.models.application import Application
from app.models.job import Job
from app.schemas.matching import ApplicationStatusUpdate
from app.core.security import get_current_user

router = APIRouter()


@router.get("")
def get_shortlist(
    job_id: Optional[int] = None,
    status: str = "shortlisted",
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: Recruiter = Depends(get_current_user),
):
    """Get shortlisted candidates, optionally filtered by job."""
    query = db.query(Application).join(Job).filter(
        Job.recruiter_id == current_user.id,
        Application.status == status,
    )

    if job_id:
        query = query.filter(Application.job_id == job_id)

    total = query.count()
    applications = query.order_by(Application.updated_at.desc()).offset(skip).limit(limit).all()

    results = []
    for app in applications:
        candidate = db.query(Candidate).filter(Candidate.id == app.candidate_id).first()
        job = db.query(Job).filter(Job.id == app.job_id).first()

        if candidate and job:
            results.append({
                "application_id": app.id,
                "status": app.status,
                "notes": app.notes,
                "applied_at": app.applied_at,
                "updated_at": app.updated_at,
                "candidate": {
                    "id": candidate.id,
                    "name": candidate.name,
                    "email": candidate.email,
                    "phone": candidate.phone,
                    "technical_skills": candidate.technical_skills or [],
                    "total_experience_years": candidate.total_experience_years,
                },
                "job": {
                    "id": job.id,
                    "title": job.title,
                    "company": job.company,
                },
            })

    return {"total": total, "results": results}


@router.post("")
def add_to_shortlist(
    candidate_id: int,
    job_id: int,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Recruiter = Depends(get_current_user),
):
    """Add a candidate to shortlist for a job."""
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

    # Check if application exists
    app = db.query(Application).filter(
        Application.job_id == job_id,
        Application.candidate_id == candidate_id
    ).first()

    if app:
        app.status = "shortlisted"
        if notes:
            app.notes = notes
    else:
        app = Application(
            job_id=job_id,
            candidate_id=candidate_id,
            status="shortlisted",
            notes=notes,
        )
        db.add(app)

    db.commit()
    return {"message": "Candidate shortlisted successfully", "application_id": app.id}


@router.put("/applications/{application_id}/status")
def update_shortlist_status(
    application_id: int,
    update: ApplicationStatusUpdate,
    db: Session = Depends(get_db),
    current_user: Recruiter = Depends(get_current_user),
):
    """Update shortlist application status."""
    app = db.query(Application).join(Job).filter(
        Application.id == application_id,
        Job.recruiter_id == current_user.id
    ).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    valid_statuses = ["pending", "under_review", "shortlisted", "rejected", "hired"]
    if update.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status")

    app.status = update.status
    if update.notes:
        app.notes = update.notes
    db.commit()

    return {"application_id": application_id, "status": app.status}


@router.get("/export/csv")
def export_shortlist_csv(
    job_id: Optional[int] = None,
    status: str = "shortlisted",
    db: Session = Depends(get_db),
    current_user: Recruiter = Depends(get_current_user),
):
    """Export shortlisted candidates to CSV."""
    query = db.query(Application).join(Job).filter(
        Job.recruiter_id == current_user.id,
        Application.status == status,
    )
    if job_id:
        query = query.filter(Application.job_id == job_id)

    applications = query.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Candidate Name", "Email", "Phone", "Job Title", "Company",
        "Status", "Notes", "Applied At", "Experience (Years)", "Skills",
    ])

    for app in applications:
        candidate = db.query(Candidate).filter(Candidate.id == app.candidate_id).first()
        job = db.query(Job).filter(Job.id == app.job_id).first()
        if candidate and job:
            writer.writerow([
                candidate.name,
                candidate.email or "",
                candidate.phone or "",
                job.title,
                job.company,
                app.status,
                app.notes or "",
                app.applied_at.strftime("%Y-%m-%d") if app.applied_at else "",
                candidate.total_experience_years,
                ", ".join((candidate.technical_skills or [])[:8]),
            ])

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=shortlist.csv"},
    )

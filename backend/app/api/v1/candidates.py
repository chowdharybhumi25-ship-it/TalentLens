import os
import uuid
import shutil
from typing import List, Optional
from fastapi import (
    APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
)
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import csv
import io

from app.database.session import get_db
from app.models.recruiter import Recruiter
from app.models.candidate import Candidate, CandidateSkill, CandidateEducation, CandidateExperience
from app.models.resume import Resume
from app.models.application import Application
from app.schemas.candidate import CandidateOut, CandidateUpdate, CompareRequest
from app.core.security import get_current_user
from app.core.config import settings
from app.parsers.resume_parser import parse_resume, compute_checksum

router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc"}
MAX_FILE_SIZE = settings.MAX_FILE_SIZE_MB * 1024 * 1024  # bytes


def save_candidate_from_parsed(db: Session, parsed: dict, recruiter_id: int) -> Candidate:
    """Create Candidate record and related records from parsed resume data."""
    candidate = Candidate(
        recruiter_id=recruiter_id,
        name=parsed.get('name', 'Unknown'),
        email=parsed.get('email'),
        phone=parsed.get('phone'),
        linkedin=parsed.get('linkedin'),
        github=parsed.get('github'),
        location=parsed.get('location'),
        summary=parsed.get('summary'),
        technical_skills=parsed.get('technical_skills', []),
        programming_languages=parsed.get('programming_languages', []),
        certifications=parsed.get('certifications', []),
        projects=parsed.get('projects', []),
        total_experience_years=parsed.get('total_experience_years', 0.0),
        extraction_confidence=parsed.get('extraction_confidence', 0.5),
    )
    db.add(candidate)
    db.flush()  # Get ID

    # Skills
    all_skills = list(set(
        parsed.get('technical_skills', []) + parsed.get('programming_languages', [])
    ))
    for skill in all_skills[:30]:
        db.add(CandidateSkill(
            candidate_id=candidate.id,
            skill=skill,
            skill_type="technical",
        ))

    # Education
    for edu in parsed.get('education', []):
        db.add(CandidateEducation(
            candidate_id=candidate.id,
            degree=edu.get('degree'),
            field_of_study=edu.get('field_of_study'),
            institution=edu.get('institution'),
            start_year=edu.get('start_year'),
            end_year=edu.get('end_year'),
            gpa=edu.get('gpa'),
        ))

    # Experience
    for exp in parsed.get('experience', []):
        db.add(CandidateExperience(
            candidate_id=candidate.id,
            title=exp.get('title'),
            company=exp.get('company'),
            start_date=str(exp.get('start_date', '')) if exp.get('start_date') else None,
            end_date=str(exp.get('end_date', '')) if exp.get('end_date') else None,
            is_current=exp.get('is_current', False),
            description=exp.get('description', ''),
            duration_months=exp.get('duration_months', 0),
            is_internship=exp.get('is_internship', False),
        ))

    return candidate


@router.post("/upload")
async def upload_resumes(
    files: List[UploadFile] = File(...),
    job_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: Recruiter = Depends(get_current_user),
):
    """Upload and process one or more resume files."""
    results = []

    for file in files:
        result = {
            "filename": file.filename,
            "status": "error",
            "candidate_id": None,
            "candidate_name": None,
            "error": None,
        }

        try:
            # Validate extension
            _, ext = os.path.splitext(file.filename or "")
            if ext.lower() not in ALLOWED_EXTENSIONS:
                result["error"] = f"Unsupported file type: {ext}"
                results.append(result)
                continue

            # Read file content
            content = await file.read()

            # Validate size
            if len(content) > MAX_FILE_SIZE:
                result["error"] = f"File too large (max {settings.MAX_FILE_SIZE_MB}MB)"
                results.append(result)
                continue

            if len(content) == 0:
                result["error"] = "File is empty"
                results.append(result)
                continue

            # Save to disk
            recruiter_dir = os.path.join(settings.UPLOAD_DIR, str(current_user.id))
            os.makedirs(recruiter_dir, exist_ok=True)

            stored_name = f"{uuid.uuid4()}{ext.lower()}"
            file_path = os.path.join(recruiter_dir, stored_name)

            with open(file_path, "wb") as f:
                f.write(content)

            # Compute checksum for duplicate detection
            checksum = compute_checksum(file_path)

            # Check for duplicate
            existing_resume = db.query(Resume).filter(
                Resume.checksum == checksum,
                Resume.recruiter_id == current_user.id
            ).first()

            if existing_resume:
                os.remove(file_path)
                result["status"] = "duplicate"
                result["candidate_id"] = existing_resume.candidate_id
                result["error"] = "Duplicate resume detected"
                results.append(result)
                continue

            # Parse resume
            file_type = ext.lower().strip(".")
            parsed = parse_resume(file_path, file_type)

            if parsed.get('error') and not parsed.get('raw_text'):
                os.remove(file_path)
                result["error"] = f"Parsing failed: {parsed.get('error')}"
                results.append(result)
                continue

            # Save candidate and related data
            candidate = save_candidate_from_parsed(db, parsed, current_user.id)

            # Save resume record
            resume = Resume(
                candidate_id=candidate.id,
                recruiter_id=current_user.id,
                original_filename=file.filename,
                stored_filename=stored_name,
                file_path=file_path,
                file_type=file_type,
                file_size=len(content),
                raw_text=parsed.get('raw_text', '')[:50000],
                processing_status="done" if not parsed.get('error') else "failed",
                processing_error=parsed.get('error'),
                checksum=checksum,
            )
            db.add(resume)
            db.flush()

            # Create application if job_id provided
            if job_id:
                application = Application(
                    job_id=job_id,
                    candidate_id=candidate.id,
                    resume_id=resume.id,
                    status="pending",
                )
                db.add(application)

            db.commit()

            result["status"] = "success"
            result["candidate_id"] = candidate.id
            result["candidate_name"] = candidate.name
            result["extraction_confidence"] = parsed.get('extraction_confidence', 0)

        except Exception as e:
            db.rollback()
            result["error"] = f"Unexpected error: {str(e)}"

        results.append(result)

    return {"results": results, "total": len(results)}


@router.get("", response_model=List[CandidateOut])
def list_candidates(
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Recruiter = Depends(get_current_user),
):
    query = db.query(Candidate).filter(Candidate.recruiter_id == current_user.id)
    if search:
        query = query.filter(Candidate.name.ilike(f"%{search}%"))
    candidates = query.order_by(Candidate.created_at.desc()).offset(skip).limit(limit).all()
    return candidates


@router.get("/{candidate_id}", response_model=CandidateOut)
def get_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: Recruiter = Depends(get_current_user),
):
    candidate = db.query(Candidate).filter(
        Candidate.id == candidate_id,
        Candidate.recruiter_id == current_user.id
    ).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate


@router.put("/{candidate_id}", response_model=CandidateOut)
def update_candidate(
    candidate_id: int,
    update_data: CandidateUpdate,
    db: Session = Depends(get_db),
    current_user: Recruiter = Depends(get_current_user),
):
    candidate = db.query(Candidate).filter(
        Candidate.id == candidate_id,
        Candidate.recruiter_id == current_user.id
    ).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(candidate, field, value)
    candidate.is_verified = True

    db.commit()
    db.refresh(candidate)
    return candidate


@router.post("/compare")
def compare_candidates(
    request: CompareRequest,
    db: Session = Depends(get_db),
    current_user: Recruiter = Depends(get_current_user),
):
    """Compare multiple candidates for a specific job."""
    from app.models.job import Job
    from app.models.match_result import MatchResult
    from app.ai.matching_engine import compute_match_score

    job = db.query(Job).filter(
        Job.id == request.job_id,
        Job.recruiter_id == current_user.id
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    candidates_data = []
    for cid in request.candidate_ids[:3]:  # Max 3
        candidate = db.query(Candidate).filter(
            Candidate.id == cid,
            Candidate.recruiter_id == current_user.id
        ).first()
        if not candidate:
            continue

        # Get or compute match result
        match_result = db.query(MatchResult).filter(
            MatchResult.job_id == request.job_id,
            MatchResult.candidate_id == cid
        ).first()

        if not match_result:
            # Compute on the fly
            cand_dict = {
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
                    {"title": e.title, "company": e.company, "description": e.description}
                    for e in candidate.experience
                ],
            }
            job_dict = {
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
            scores = compute_match_score(cand_dict, job_dict)
        else:
            scores = {
                "overall_score": match_result.overall_score,
                "required_skills_score": match_result.required_skills_score,
                "preferred_skills_score": match_result.preferred_skills_score,
                "experience_score": match_result.experience_score,
                "education_score": match_result.education_score,
                "project_relevance_score": match_result.project_relevance_score,
                "semantic_similarity_score": match_result.semantic_similarity_score,
                "matched_required_skills": match_result.matched_required_skills,
                "missing_required_skills": match_result.missing_required_skills,
                "matched_preferred_skills": match_result.matched_preferred_skills,
                "missing_preferred_skills": match_result.missing_preferred_skills,
                "is_eligible": match_result.is_eligible,
                "eligibility_failures": match_result.eligibility_failures,
                "recommendation_status": match_result.recommendation_status,
            }

        candidates_data.append({
            "candidate": {
                "id": candidate.id,
                "name": candidate.name,
                "email": candidate.email,
                "technical_skills": candidate.technical_skills or [],
                "programming_languages": candidate.programming_languages or [],
                "total_experience_years": candidate.total_experience_years,
                "education": [
                    {
                        "degree": e.degree,
                        "field_of_study": e.field_of_study,
                        "institution": e.institution,
                        "end_year": e.end_year,
                    }
                    for e in candidate.education
                ],
                "certifications": candidate.certifications or [],
                "projects": candidate.projects or [],
            },
            "scores": scores,
        })

    return {
        "job": {
            "id": job.id,
            "title": job.title,
            "required_skills": job.required_skills,
            "preferred_skills": job.preferred_skills,
            "min_experience": job.min_experience,
        },
        "candidates": candidates_data,
    }


@router.get("/export/csv")
def export_candidates_csv(
    job_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Recruiter = Depends(get_current_user),
):
    """Export candidates to CSV."""
    query = db.query(Candidate).filter(Candidate.recruiter_id == current_user.id)

    if job_id:
        query = query.join(Application, Application.candidate_id == Candidate.id).filter(
            Application.job_id == job_id
        )
        if status:
            query = query.filter(Application.status == status)

    candidates = query.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Name", "Email", "Phone", "Location", "Experience (Years)",
        "Technical Skills", "Education", "Certifications",
    ])

    for c in candidates:
        edu_str = "; ".join([
            f"{e.degree or ''} {e.field_of_study or ''} - {e.institution or ''}".strip()
            for e in c.education[:2]
        ])
        writer.writerow([
            c.name, c.email or "", c.phone or "", c.location or "",
            c.total_experience_years,
            ", ".join((c.technical_skills or [])[:10]),
            edu_str,
            ", ".join((c.certifications or [])[:5]),
        ])

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=candidates.csv"},
    )

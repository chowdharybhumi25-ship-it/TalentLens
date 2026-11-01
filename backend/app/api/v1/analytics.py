from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from collections import Counter

from app.database.session import get_db
from app.models.recruiter import Recruiter
from app.models.job import Job
from app.models.candidate import Candidate, CandidateSkill
from app.models.application import Application
from app.models.match_result import MatchResult
from app.models.resume import Resume
from app.core.security import get_current_user

router = APIRouter()


@router.get("/dashboard")
def get_dashboard_analytics(
    db: Session = Depends(get_db),
    current_user: Recruiter = Depends(get_current_user),
):
    """Get dashboard statistics."""
    recruiter_id = current_user.id

    # Basic counts
    total_jobs = db.query(Job).filter(Job.recruiter_id == recruiter_id).count()
    active_jobs = db.query(Job).filter(
        Job.recruiter_id == recruiter_id, Job.is_active == True
    ).count()
    total_candidates = db.query(Candidate).filter(
        Candidate.recruiter_id == recruiter_id
    ).count()
    total_resumes = db.query(Resume).filter(
        Resume.recruiter_id == recruiter_id
    ).count()

    # Shortlisted and pending
    shortlisted = db.query(Application).join(Job).filter(
        Job.recruiter_id == recruiter_id,
        Application.status == "shortlisted"
    ).count()
    pending = db.query(Application).join(Job).filter(
        Job.recruiter_id == recruiter_id,
        Application.status == "pending"
    ).count()
    under_review = db.query(Application).join(Job).filter(
        Job.recruiter_id == recruiter_id,
        Application.status == "under_review"
    ).count()
    rejected = db.query(Application).join(Job).filter(
        Job.recruiter_id == recruiter_id,
        Application.status == "rejected"
    ).count()
    hired = db.query(Application).join(Job).filter(
        Job.recruiter_id == recruiter_id,
        Application.status == "hired"
    ).count()

    # Score distribution
    match_results = db.query(MatchResult).join(Job).filter(
        Job.recruiter_id == recruiter_id
    ).all()

    score_distribution = {
        "90-100": 0, "75-89": 0, "60-74": 0, "40-59": 0, "0-39": 0
    }
    for mr in match_results:
        s = mr.overall_score
        if s >= 90:
            score_distribution["90-100"] += 1
        elif s >= 75:
            score_distribution["75-89"] += 1
        elif s >= 60:
            score_distribution["60-74"] += 1
        elif s >= 40:
            score_distribution["40-59"] += 1
        else:
            score_distribution["0-39"] += 1

    # Top skills distribution
    all_skills = []
    candidates = db.query(Candidate).filter(
        Candidate.recruiter_id == recruiter_id
    ).all()
    for c in candidates:
        if c.technical_skills:
            all_skills.extend(c.technical_skills[:5])
    skill_counts = Counter(all_skills).most_common(10)

    # Jobs with applicant counts
    jobs = db.query(Job).filter(Job.recruiter_id == recruiter_id).all()
    job_stats = []
    for job in jobs[:10]:
        count = db.query(Application).filter(Application.job_id == job.id).count()
        job_stats.append({
            "job_id": job.id,
            "title": job.title,
            "applicants": count,
            "is_active": job.is_active,
        })

    # Application trend (last 7 days)
    from datetime import datetime, timedelta
    trend_data = []
    for i in range(6, -1, -1):
        day = datetime.utcnow() - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        count = db.query(Application).join(Job).filter(
            Job.recruiter_id == recruiter_id,
            Application.applied_at >= day_start,
            Application.applied_at < day_end,
        ).count()
        trend_data.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "day": day_start.strftime("%a"),
            "applications": count,
        })

    return {
        "stats": {
            "total_jobs": total_jobs,
            "active_jobs": active_jobs,
            "total_candidates": total_candidates,
            "resumes_processed": total_resumes,
            "shortlisted": shortlisted,
            "pending_reviews": pending + under_review,
            "rejected": rejected,
            "hired": hired,
        },
        "score_distribution": [
            {"range": k, "count": v} for k, v in score_distribution.items()
        ],
        "top_skills": [{"skill": s, "count": c} for s, c in skill_counts],
        "job_stats": job_stats,
        "application_trend": trend_data,
        "pipeline": {
            "applied": total_candidates,
            "under_review": under_review,
            "shortlisted": shortlisted,
            "rejected": rejected,
            "hired": hired,
        },
    }


@router.get("/recruitment")
def get_recruitment_analytics(
    db: Session = Depends(get_db),
    current_user: Recruiter = Depends(get_current_user),
):
    """Detailed recruitment analytics."""
    recruiter_id = current_user.id

    # All match results for this recruiter
    match_results = db.query(MatchResult).join(Job).filter(
        Job.recruiter_id == recruiter_id
    ).all()

    if not match_results:
        return {
            "avg_score": 0,
            "score_bins": [],
            "skill_gaps": [],
            "conversion_rate": 0,
            "recommendations_by_status": {},
        }

    scores = [mr.overall_score for mr in match_results]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0

    # Score bins for histogram
    bins = list(range(0, 101, 10))
    score_bins = []
    for i in range(len(bins) - 1):
        low, high = bins[i], bins[i + 1]
        count = sum(1 for s in scores if low <= s < high)
        score_bins.append({"range": f"{low}-{high}", "count": count})

    # Common missing skills (gaps)
    missing_skills_counter = Counter()
    for mr in match_results:
        if mr.missing_required_skills:
            for skill in mr.missing_required_skills:
                missing_skills_counter[skill] += 1
    skill_gaps = [
        {"skill": s, "count": c}
        for s, c in missing_skills_counter.most_common(10)
    ]

    # Recommendation status distribution
    status_dist = Counter(mr.recommendation_status for mr in match_results)

    # Conversion rate
    total_apps = db.query(Application).join(Job).filter(
        Job.recruiter_id == recruiter_id
    ).count()
    shortlisted = db.query(Application).join(Job).filter(
        Job.recruiter_id == recruiter_id,
        Application.status == "shortlisted"
    ).count()
    conversion_rate = round(shortlisted / total_apps * 100, 1) if total_apps > 0 else 0

    return {
        "avg_score": avg_score,
        "total_matches": len(match_results),
        "score_bins": score_bins,
        "skill_gaps": skill_gaps,
        "conversion_rate": conversion_rate,
        "recommendations_by_status": dict(status_dist),
    }

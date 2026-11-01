"""
Hybrid AI Matching Engine

Combines:
1. Keyword matching (TF-IDF + Cosine Similarity + exact skill matching)
2. Semantic matching (Sentence Transformers - all-MiniLM-L6-v2)
3. Rule-based matching (mandatory requirements, experience, education)

Weighted scoring:
- Required Skills: 35%
- Preferred Skills: 15%
- Experience: 20%
- Education: 10%
- Project Relevance: 10%
- Semantic Similarity: 10%
"""

import re
import logging
from typing import Optional
from functools import lru_cache

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.ai.skill_normalizer import find_matched_skills, normalize_skills_list

logger = logging.getLogger(__name__)

# Configurable weights
DEFAULT_WEIGHTS = {
    "required_skills": 0.35,
    "preferred_skills": 0.15,
    "experience": 0.20,
    "education": 0.10,
    "project_relevance": 0.10,
    "semantic_similarity": 0.10,
}

EDUCATION_HIERARCHY = {
    "ph.d": 7, "doctorate": 7,
    "m.tech": 6, "m.sc": 6, "mba": 6, "mca": 6, "master": 6, "master's": 6,
    "b.tech": 5, "b.e": 5, "b.sc": 5, "bca": 4, "bachelor": 5, "bachelor's": 5,
    "diploma": 3,
    "12th": 2, "hsc": 2,
    "10th": 1, "ssc": 1,
}

# Singleton for sentence transformer model
_sentence_model = None


def get_sentence_model():
    """Lazy-load sentence transformer model."""
    global _sentence_model
    if _sentence_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _sentence_model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("Sentence transformer model loaded successfully")
        except Exception as e:
            logger.warning(f"Could not load sentence transformer: {e}. Semantic matching disabled.")
            _sentence_model = False  # Mark as failed
    return _sentence_model if _sentence_model is not False else None


# ------------------------------------------------------------------ #
# Individual scoring functions
# ------------------------------------------------------------------ #

def score_required_skills(candidate_skills: list, required_skills: list) -> tuple:
    """
    Returns (score 0-1, matched_skills, missing_skills).
    Uses both exact and normalized matching.
    """
    if not required_skills:
        return 1.0, [], []

    # Combine all candidate skill representations
    all_candidate_skills = list(set(candidate_skills))

    matched, missing = find_matched_skills(all_candidate_skills, required_skills)
    score = len(matched) / len(required_skills) if required_skills else 1.0
    return score, matched, missing


def score_preferred_skills(candidate_skills: list, preferred_skills: list) -> tuple:
    """Returns (score 0-1, matched, missing)."""
    if not preferred_skills:
        return 1.0, [], []

    all_candidate_skills = list(set(candidate_skills))
    matched, missing = find_matched_skills(all_candidate_skills, preferred_skills)
    score = len(matched) / len(preferred_skills) if preferred_skills else 1.0
    return score, matched, missing


def score_experience(
    candidate_years: float,
    min_exp: float,
    max_exp: Optional[float],
) -> float:
    """
    Returns experience score (0-1).
    Candidates meeting minimum get full score; below minimum is penalized.
    Above maximum gets slightly penalized (overqualified, configurable).
    """
    if min_exp <= 0 and max_exp is None:
        return 1.0  # No experience requirement

    if candidate_years >= min_exp:
        if max_exp is None or candidate_years <= max_exp:
            return 1.0
        else:
            # Overqualified - slight penalty
            over = candidate_years - max_exp
            return max(0.7, 1.0 - (over * 0.05))
    else:
        # Under minimum
        if min_exp <= 0:
            return 1.0
        ratio = candidate_years / max(min_exp, 0.1)
        return max(0.0, min(ratio, 1.0))


def score_education(candidate_edu: list, required_edu: list) -> float:
    """
    Returns education score (0-1).
    Checks if candidate meets at least one education requirement.
    """
    if not required_edu:
        return 1.0

    if not candidate_edu:
        return 0.3  # Unknown - not penalized fully

    # Get highest education level of candidate
    candidate_max_level = 0
    for edu in candidate_edu:
        degree = (edu.get('degree', '') or '').lower()
        for key, level in EDUCATION_HIERARCHY.items():
            if key in degree:
                candidate_max_level = max(candidate_max_level, level)
                break

    # Get minimum required education level
    required_min_level = 0
    for req in required_edu:
        req_lower = req.lower()
        for key, level in EDUCATION_HIERARCHY.items():
            if key in req_lower:
                required_min_level = max(required_min_level, level)
                break

    if required_min_level == 0:
        return 1.0

    if candidate_max_level >= required_min_level:
        return 1.0
    elif candidate_max_level == required_min_level - 1:
        return 0.7
    else:
        return max(0.3, candidate_max_level / max(required_min_level, 1))


def score_projects(candidate_projects: list, job_required_skills: list, job_description: str) -> float:
    """
    Returns project relevance score (0-1).
    Checks how many project technologies align with job requirements.
    """
    if not candidate_projects:
        return 0.3  # No projects - not penalized heavily

    if not job_required_skills:
        return 0.7

    all_project_skills = []
    all_project_text = ""

    for project in candidate_projects:
        techs = project.get('technologies', [])
        all_project_skills.extend(techs)
        all_project_text += " " + project.get('description', '') + " " + project.get('name', '')

    # Skill overlap between projects and job requirements
    if all_project_skills:
        matched, _ = find_matched_skills(all_project_skills, job_required_skills)
        skill_match_ratio = len(matched) / len(job_required_skills)
    else:
        skill_match_ratio = 0.0

    # TF-IDF match between project descriptions and job description
    tfidf_score = 0.0
    if all_project_text.strip() and job_description.strip():
        try:
            vectorizer = TfidfVectorizer(stop_words='english', max_features=500)
            tfidf_matrix = vectorizer.fit_transform([all_project_text, job_description])
            sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            tfidf_score = float(sim)
        except Exception:
            pass

    # Combine
    return min(1.0, 0.6 * skill_match_ratio + 0.4 * tfidf_score + 0.1)


def score_semantic_similarity(candidate_text: str, job_text: str) -> float:
    """
    Returns semantic similarity score (0-1) using Sentence Transformers.
    Falls back to TF-IDF cosine similarity if model not available.
    """
    if not candidate_text.strip() or not job_text.strip():
        return 0.5

    model = get_sentence_model()

    if model:
        try:
            embeddings = model.encode([candidate_text[:2000], job_text[:2000]])
            sim = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
            return float(max(0.0, min(1.0, sim)))
        except Exception as e:
            logger.warning(f"Semantic similarity failed: {e}")

    # Fallback: TF-IDF cosine similarity
    try:
        vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
        tfidf_matrix = vectorizer.fit_transform([candidate_text[:3000], job_text[:3000]])
        sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        return float(max(0.0, min(1.0, sim)))
    except Exception:
        return 0.5


# ------------------------------------------------------------------ #
# Rule-based eligibility checker
# ------------------------------------------------------------------ #

def check_eligibility(
    candidate: dict,
    job: dict,
) -> tuple:
    """
    Check mandatory eligibility criteria.
    Returns (is_eligible, list_of_failures).
    """
    failures = []

    # Mandatory skills check
    mandatory_reqs = job.get('mandatory_requirements', [])
    all_candidate_skills = (
        candidate.get('technical_skills', []) +
        candidate.get('programming_languages', [])
    )
    for req in mandatory_reqs:
        req_lower = req.lower()
        found = any(req_lower in s.lower() or s.lower() in req_lower
                    for s in all_candidate_skills)
        if not found:
            failures.append(f"Missing mandatory requirement: {req}")

    # Minimum experience check (hard failure only if significantly below)
    min_exp = job.get('min_experience', 0)
    cand_exp = candidate.get('total_experience_years', 0)
    if min_exp > 0 and cand_exp < min_exp * 0.5:
        failures.append(
            f"Experience {cand_exp}y is significantly below minimum {min_exp}y requirement"
        )

    return len(failures) == 0, failures


# ------------------------------------------------------------------ #
# Candidate text builder (for semantic matching)
# ------------------------------------------------------------------ #

def build_candidate_text(candidate: dict) -> str:
    """Build a comprehensive text representation of the candidate."""
    parts = []

    if candidate.get('summary'):
        parts.append(candidate['summary'])

    skills = candidate.get('technical_skills', []) + candidate.get('programming_languages', [])
    if skills:
        parts.append("Skills: " + ", ".join(skills))

    for exp in candidate.get('experience', [])[:3]:
        title = exp.get('title', '')
        company = exp.get('company', '')
        desc = exp.get('description', '')
        if title or company:
            parts.append(f"{title} at {company}: {desc}"[:300])

    for proj in candidate.get('projects', [])[:3]:
        name = proj.get('name', '')
        desc = proj.get('description', '')
        techs = ", ".join(proj.get('technologies', []))
        if name:
            parts.append(f"Project: {name} ({techs}): {desc}"[:300])

    for edu in candidate.get('education', [])[:2]:
        degree = edu.get('degree', '')
        field = edu.get('field_of_study', '')
        inst = edu.get('institution', '')
        if degree or inst:
            parts.append(f"Education: {degree} {field} from {inst}")

    if candidate.get('certifications'):
        parts.append("Certifications: " + ", ".join(candidate['certifications'][:5]))

    return " ".join(parts)


def build_job_text(job: dict) -> str:
    """Build a comprehensive text representation of the job."""
    parts = []

    if job.get('title'):
        parts.append(job['title'])

    if job.get('description'):
        parts.append(job['description'][:1000])

    skills = job.get('required_skills', []) + job.get('preferred_skills', [])
    if skills:
        parts.append("Required: " + ", ".join(skills))

    if job.get('responsibilities'):
        parts.append("Responsibilities: " + ", ".join(job['responsibilities'][:5]))

    return " ".join(parts)


# ------------------------------------------------------------------ #
# Main matching function
# ------------------------------------------------------------------ #

def compute_match_score(
    candidate: dict,
    job: dict,
    weights: dict = None,
) -> dict:
    """
    Compute the full hybrid match score for a candidate-job pair.

    Args:
        candidate: dict with candidate data (from DB or parsed)
        job: dict with job data (from DB)
        weights: optional custom weights dict

    Returns:
        dict with all scores, explanations, and eligibility
    """
    w = weights or DEFAULT_WEIGHTS

    # All candidate skills combined
    all_candidate_skills = list(set(
        candidate.get('technical_skills', []) +
        candidate.get('programming_languages', [])
    ))

    # 1. Required Skills Score
    req_score, matched_req, missing_req = score_required_skills(
        all_candidate_skills,
        job.get('required_skills', [])
    )

    # 2. Preferred Skills Score
    pref_score, matched_pref, missing_pref = score_preferred_skills(
        all_candidate_skills,
        job.get('preferred_skills', [])
    )

    # 3. Experience Score
    exp_score = score_experience(
        candidate.get('total_experience_years', 0),
        job.get('min_experience', 0),
        job.get('max_experience'),
    )

    # 4. Education Score
    edu_score = score_education(
        candidate.get('education', []),
        job.get('education_requirements', [])
    )

    # 5. Project Relevance Score
    proj_score = score_projects(
        candidate.get('projects', []),
        job.get('required_skills', []),
        job.get('description', '')
    )

    # 6. Semantic Similarity Score
    candidate_text = build_candidate_text(candidate)
    job_text = build_job_text(job)
    semantic_score = score_semantic_similarity(candidate_text, job_text)

    # Weighted final score
    final_score = (
        w['required_skills'] * req_score +
        w['preferred_skills'] * pref_score +
        w['experience'] * exp_score +
        w['education'] * edu_score +
        w['project_relevance'] * proj_score +
        w['semantic_similarity'] * semantic_score
    )

    final_score_pct = round(final_score * 100, 1)

    # Eligibility check
    is_eligible, eligibility_failures = check_eligibility(candidate, job)

    # Recommendation status
    if not is_eligible:
        recommendation_status = "not_recommended"
    elif final_score_pct >= 75:
        recommendation_status = "recommended"
    elif final_score_pct >= 50:
        recommendation_status = "consider"
    else:
        recommendation_status = "not_recommended"

    return {
        "overall_score": final_score_pct,
        "required_skills_score": round(req_score * 100, 1),
        "preferred_skills_score": round(pref_score * 100, 1),
        "experience_score": round(exp_score * 100, 1),
        "education_score": round(edu_score * 100, 1),
        "project_relevance_score": round(proj_score * 100, 1),
        "semantic_similarity_score": round(semantic_score * 100, 1),
        "matched_required_skills": matched_req,
        "missing_required_skills": missing_req,
        "matched_preferred_skills": matched_pref,
        "missing_preferred_skills": missing_pref,
        "is_eligible": is_eligible,
        "eligibility_failures": eligibility_failures,
        "recommendation_status": recommendation_status,
    }


def generate_explanation(match_result: dict, candidate: dict, job: dict) -> dict:
    """
    Generate a rule-based explanation for the match result.
    Returns dict with strengths, weaknesses, suggestions, summary.
    """
    strengths = []
    weaknesses = []
    suggestions = []

    req_count = len(job.get('required_skills', []))
    matched_req_count = len(match_result.get('matched_required_skills', []))
    missing_req = match_result.get('missing_required_skills', [])
    matched_pref = match_result.get('matched_preferred_skills', [])
    missing_pref = match_result.get('missing_preferred_skills', [])
    exp_score = match_result.get('experience_score', 0)
    edu_score = match_result.get('education_score', 0)
    semantic = match_result.get('semantic_similarity_score', 0)
    overall = match_result.get('overall_score', 0)

    # Skills analysis
    if req_count > 0:
        if matched_req_count == req_count:
            strengths.append(f"Matches all {req_count} required technical skills")
        elif matched_req_count > 0:
            strengths.append(
                f"Matches {matched_req_count} out of {req_count} required skills "
                f"({', '.join(match_result['matched_required_skills'][:4])})"
            )

    if missing_req:
        weaknesses.append(f"Missing required skills: {', '.join(missing_req[:5])}")
        suggestions.append(f"Verify if candidate has experience with: {', '.join(missing_req[:3])}")

    # Preferred skills
    if matched_pref:
        strengths.append(f"Has {len(matched_pref)} preferred skill(s): {', '.join(matched_pref[:4])}")
    if missing_pref:
        weaknesses.append(f"Missing preferred skills: {', '.join(missing_pref[:3])}")

    # Experience
    cand_exp = candidate.get('total_experience_years', 0)
    min_exp = job.get('min_experience', 0)
    if exp_score >= 100:
        strengths.append(f"Experience ({cand_exp}y) meets or exceeds requirement ({min_exp}y)")
    elif exp_score >= 70:
        strengths.append(f"Experience is close to requirement (has {cand_exp}y, required {min_exp}y)")
    elif exp_score < 70:
        weaknesses.append(f"Limited experience: {cand_exp}y vs {min_exp}y required")
        suggestions.append("Discuss relevant project experience to compensate for experience gap")

    # Education
    if edu_score >= 100:
        strengths.append("Meets educational qualification requirements")
    elif edu_score < 70:
        weaknesses.append("Educational qualification may not fully meet requirements")
        suggestions.append("Verify actual qualifications during the interview")

    # Projects
    proj_score = match_result.get('project_relevance_score', 0)
    projects = candidate.get('projects', [])
    if proj_score >= 70:
        proj_names = [p.get('name', '') for p in projects[:3] if p.get('name')]
        if proj_names:
            strengths.append(f"Relevant project experience: {', '.join(proj_names)}")
        else:
            strengths.append("Strong project relevance to the role")
    elif proj_score < 40 and not projects:
        weaknesses.append("No project details found in resume")
        suggestions.append("Ask about relevant projects during the interview")

    # Semantic
    if semantic >= 70:
        strengths.append("Strong overall contextual alignment with job requirements")
    elif semantic < 40:
        weaknesses.append("Limited contextual alignment with role description")

    # Eligibility failures
    for failure in match_result.get('eligibility_failures', []):
        weaknesses.append(f"⚠️ Eligibility concern: {failure}")
        suggestions.append(f"Clarify this requirement: {failure}")

    # Build summary
    status = match_result.get('recommendation_status', 'consider')
    if status == 'recommended':
        summary = (
            f"Strong match for this role with an overall compatibility score of {overall:.0f}%. "
            f"The candidate demonstrates {matched_req_count}/{req_count} required skills "
            f"and shows contextual alignment with the job requirements."
        )
    elif status == 'consider':
        summary = (
            f"Moderate match with a score of {overall:.0f}%. "
            f"The candidate has {matched_req_count}/{req_count} required skills. "
            f"Consider for interview with focus on skill gaps."
        )
    else:
        summary = (
            f"Below-threshold match ({overall:.0f}%). "
            f"Significant gaps in required skills or qualifications. "
            f"Recommend further review before proceeding."
        )

    return {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "suggestions": suggestions,
        "summary_text": summary,
        "generated_by": "rule_based",
    }

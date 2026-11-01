"""
LLM integration for enhanced explanations and interview question generation.
Falls back gracefully when API key is not configured.
"""
import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


def is_llm_available() -> bool:
    """Check if LLM is configured and available."""
    provider = settings.LLM_PROVIDER.lower()
    if provider == "openai" and settings.OPENAI_API_KEY:
        return True
    if provider == "google" and settings.GOOGLE_API_KEY:
        return True
    if provider == "anthropic" and settings.ANTHROPIC_API_KEY:
        return True
    return False


def call_llm(prompt: str, system_prompt: str = "", max_tokens: int = 1000) -> Optional[str]:
    """
    Call the configured LLM API.
    Returns the response text or None if unavailable.
    """
    provider = settings.LLM_PROVIDER.lower()

    try:
        if provider == "openai" and settings.OPENAI_API_KEY:
            import httpx
            response = httpx.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.LLM_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt or "You are a helpful recruitment assistant."},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": max_tokens,
                    "temperature": 0.7,
                },
                timeout=30,
            )
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            else:
                logger.warning(f"LLM API error: {response.status_code}")
                return None

        elif provider == "google" and settings.GOOGLE_API_KEY:
            import httpx
            response = httpx.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={settings.GOOGLE_API_KEY}",
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"maxOutputTokens": max_tokens},
                },
                timeout=30,
            )
            if response.status_code == 200:
                data = response.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
            return None

    except Exception as e:
        logger.warning(f"LLM call failed: {e}")
        return None

    return None


def generate_interview_questions_llm(
    job_title: str,
    required_skills: list,
    candidate_name: str,
    candidate_skills: list,
    candidate_projects: list,
    experience_years: float,
    missing_skills: list,
) -> Optional[list]:
    """
    Generate interview questions using LLM.
    Returns list of question dicts or None.
    """
    if not is_llm_available():
        return None

    projects_text = "\n".join([
        f"- {p.get('name', 'Project')}: {p.get('description', '')[:100]}"
        for p in candidate_projects[:3]
    ])

    prompt = f"""Generate interview questions for a {job_title} candidate.

Candidate: {candidate_name}
Experience: {experience_years} years
Their Skills: {', '.join(candidate_skills[:10])}
Job Required Skills: {', '.join(required_skills[:10])}
Missing Skills: {', '.join(missing_skills[:5])}
Projects: {projects_text or 'None listed'}

Generate exactly 12 questions in JSON format:
[
  {{"category": "Technical", "question": "...", "rationale": "..."}},
  ...
]

Categories: Technical, Conceptual, Project-based, Problem-solving
Return ONLY valid JSON, no markdown."""

    response = call_llm(prompt, max_tokens=1500)
    if response:
        try:
            import json
            # Try to extract JSON from response
            start = response.find('[')
            end = response.rfind(']') + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except Exception as e:
            logger.warning(f"Could not parse LLM response as JSON: {e}")
    return None


def enhance_explanation_llm(
    summary_text: str,
    strengths: list,
    weaknesses: list,
    candidate_name: str,
    job_title: str,
) -> Optional[str]:
    """Use LLM to enhance the rule-based explanation text."""
    if not is_llm_available():
        return None

    prompt = f"""Enhance this recruitment assessment for a recruiter.

Candidate: {candidate_name}
Role: {job_title}

Strengths: {'; '.join(strengths[:5])}
Areas for Review: {'; '.join(weaknesses[:5])}
Current Summary: {summary_text}

Write a concise, professional 2-3 sentence enhanced assessment.
Focus on facts from the assessment only. Do not invent information."""

    return call_llm(prompt, max_tokens=200)

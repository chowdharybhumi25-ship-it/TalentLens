"""
Job Description parser: extracts structured requirements from JD text.
Uses rule-based NLP extraction.
"""
import re
from typing import List, Optional
from app.ai.skill_normalizer import SKILL_KEYWORDS, normalize_skills_list, normalize_skill

# Section patterns for JD
JD_SECTIONS = {
    'responsibilities': r'(?i)^(responsibilities|role|duties|what you.?ll do|job duties|your role)',
    'requirements': r'(?i)^(requirements|qualifications|skills|what we.?re looking for|what you need|must have|you should have)',
    'preferred': r'(?i)^(preferred|nice to have|good to have|bonus|plus|advantageous|desirable)',
    'benefits': r'(?i)^(benefits|perks|what we offer|compensation|package)',
    'about': r'(?i)^(about|overview|description|company|who we are)',
}

EXPERIENCE_RE = re.compile(
    r'(\d+\.?\d*)\s*(?:\+|to|-|–)?\s*(?:(\d+\.?\d*)\s*)?(?:years?|yrs?)\s*'
    r'(?:of\s*)?(?:relevant\s*)?(?:work\s*)?(?:experience|exp)',
    re.I
)

EDUCATION_KEYWORDS = {
    "b.tech": "B.Tech", "btech": "B.Tech", "bachelor of technology": "B.Tech",
    "b.e": "B.E", "bachelor of engineering": "B.E",
    "b.sc": "B.Sc", "bachelor of science": "B.Sc", "bachelor": "Bachelor's Degree",
    "m.tech": "M.Tech", "master of technology": "M.Tech",
    "m.sc": "M.Sc", "master of science": "M.Sc", "master": "Master's Degree",
    "mba": "MBA", "mca": "MCA", "bca": "BCA",
    "phd": "Ph.D", "ph.d": "Ph.D", "doctorate": "Ph.D",
    "diploma": "Diploma",
}

EMPLOYMENT_TYPES = [
    "full-time", "full time", "part-time", "part time",
    "contract", "freelance", "remote", "hybrid", "on-site", "onsite",
    "internship", "temporary",
]


def extract_section_text(text: str, section_type: str) -> str:
    """Extract a specific section from JD text."""
    lines = text.split('\n')
    pattern = JD_SECTIONS.get(section_type, '')
    if not pattern:
        return ''

    start_idx = None
    end_idx = None

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if start_idx is None:
            if re.match(pattern, stripped):
                start_idx = i
        elif start_idx is not None:
            is_other_header = False
            for other_type, other_pattern in JD_SECTIONS.items():
                if other_type != section_type and re.match(other_pattern, stripped):
                    is_other_header = True
                    break
            if is_other_header and i > start_idx + 1:
                end_idx = i
                break

    if start_idx is None:
        return ''

    section_lines = lines[start_idx + 1: end_idx] if end_idx else lines[start_idx + 1: start_idx + 30]
    return '\n'.join(section_lines).strip()


def extract_skills_from_jd(text: str) -> List[str]:
    """Extract required skills from JD."""
    found = set()
    text_lower = text.lower()

    for skill in SKILL_KEYWORDS:
        pattern = r'(?<![a-z])' + re.escape(skill) + r'(?![a-z])'
        if re.search(pattern, text_lower):
            found.add(skill)

    # Also parse from requirements section
    req_section = extract_section_text(text, 'requirements')
    if req_section:
        items = re.split(r'[,\n•\-\*]', req_section)
        for item in items:
            item = item.strip()
            item_lower = item.lower()
            if item_lower in SKILL_KEYWORDS:
                found.add(item_lower)
            elif 1 < len(item) < 40 and len(item.split()) <= 3:
                for skill in SKILL_KEYWORDS:
                    if skill in item_lower:
                        found.add(skill)
                        break

    normalized = normalize_skills_list(
        [s.title() if len(s) > 3 else s.upper() for s in found]
    )
    return normalized


def extract_preferred_skills(text: str) -> List[str]:
    """Extract preferred/nice-to-have skills."""
    pref_section = extract_section_text(text, 'preferred')
    if not pref_section:
        # Look for "preferred" / "nice to have" in text
        pref_match = re.search(
            r'(?:preferred|nice.to.have|bonus|plus)[^\n]*\n((?:[^\n]+\n){1,10})',
            text, re.I
        )
        if pref_match:
            pref_section = pref_match.group(1)

    if not pref_section:
        return []

    found = set()
    pref_lower = pref_section.lower()
    for skill in SKILL_KEYWORDS:
        pattern = r'(?<![a-z])' + re.escape(skill) + r'(?![a-z])'
        if re.search(pattern, pref_lower):
            found.add(skill)

    return normalize_skills_list(
        [s.title() if len(s) > 3 else s.upper() for s in found]
    )


def extract_experience_requirement(text: str) -> tuple:
    """Returns (min_experience, max_experience) in years."""
    matches = EXPERIENCE_RE.findall(text)
    if not matches:
        return 0.0, None

    min_exp = float('inf')
    max_exp = 0.0

    for match in matches:
        val1 = float(match[0]) if match[0] else 0
        val2 = float(match[1]) if match[1] else 0
        min_exp = min(min_exp, val1)
        if val2 > 0:
            max_exp = max(max_exp, val2)
        else:
            max_exp = max(max_exp, val1)

    if min_exp == float('inf'):
        min_exp = 0.0

    return min_exp, max_exp if max_exp > 0 else None


def extract_education_requirements(text: str) -> List[str]:
    """Extract education requirements from JD."""
    found = []
    text_lower = text.lower()

    for edu_key, edu_val in EDUCATION_KEYWORDS.items():
        if edu_key in text_lower and edu_val not in found:
            found.append(edu_val)

    return found[:5]


def extract_employment_type(text: str) -> str:
    """Extract employment type from JD."""
    text_lower = text.lower()
    for emp_type in EMPLOYMENT_TYPES:
        if emp_type in text_lower:
            return emp_type.title()
    return "Full-time"


def extract_location(text: str) -> Optional[str]:
    """Extract location from JD."""
    location_patterns = [
        r'(?:location|based in|office|city)\s*:?\s*([^\n]+)',
        r'(?:remote|hybrid|on-?site)\s*(?:[\-–|]\s*([^\n,]+))?',
    ]
    for pattern in location_patterns:
        m = re.search(pattern, text, re.I)
        if m and m.group(1):
            return m.group(1).strip()[:100]

    # Check for known remote keywords
    if re.search(r'\bremote\b', text, re.I):
        return "Remote"
    if re.search(r'\bhybrid\b', text, re.I):
        return "Hybrid"

    return None


def extract_responsibilities(text: str) -> List[str]:
    """Extract job responsibilities from JD."""
    resp_section = extract_section_text(text, 'responsibilities')
    if not resp_section:
        return []

    lines = re.split(r'[•\-\*\n]', resp_section)
    responsibilities = []
    for line in lines:
        line = line.strip()
        if len(line) > 10 and len(line) < 300:
            responsibilities.append(line)

    return responsibilities[:15]


def extract_mandatory_requirements(text: str, required_skills: List[str]) -> List[str]:
    """Extract mandatory/must-have requirements."""
    mandatory = []
    lines = text.split('\n')

    for line in lines:
        line_stripped = line.strip()
        if re.search(r'\b(must|mandatory|required|essential|necessary)\b', line_stripped, re.I):
            # Check if it mentions a skill
            line_lower = line_stripped.lower()
            for skill in SKILL_KEYWORDS:
                if skill in line_lower and skill.title() in required_skills:
                    if line_stripped not in mandatory:
                        mandatory.append(line_stripped[:200])
                    break

    return mandatory[:5]


def extract_job_title(text: str) -> Optional[str]:
    """Extract job title from JD."""
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    title_patterns = [
        r'(?:job title|position|role)\s*:?\s*([^\n]+)',
        r'^([A-Z][a-zA-Z\s\/\-]+(?:Engineer|Developer|Scientist|Analyst|Manager|Lead|Architect|Designer|Intern|Consultant))',
    ]

    for pattern in title_patterns:
        for line in lines[:10]:
            m = re.match(pattern, line, re.I)
            if m:
                return m.group(1).strip()[:200]

    # First short line that looks like a title
    for line in lines[:5]:
        if len(line.split()) <= 8 and len(line) < 80:
            return line

    return None


def parse_job_description(description: str) -> dict:
    """
    Main JD parsing function.
    Returns structured job requirements.
    """
    text = description.strip()

    required_skills = extract_skills_from_jd(text)
    preferred_skills = extract_preferred_skills(text)

    # Remove preferred from required to avoid duplication
    pref_lower = {s.lower() for s in preferred_skills}
    required_skills = [s for s in required_skills if s.lower() not in pref_lower]

    min_exp, max_exp = extract_experience_requirement(text)

    return {
        'title': extract_job_title(text),
        'required_skills': required_skills,
        'preferred_skills': preferred_skills,
        'min_experience': min_exp,
        'max_experience': max_exp,
        'education_requirements': extract_education_requirements(text),
        'employment_type': extract_employment_type(text),
        'location': extract_location(text),
        'responsibilities': extract_responsibilities(text),
        'mandatory_requirements': extract_mandatory_requirements(text, required_skills),
    }

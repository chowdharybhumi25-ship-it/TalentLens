"""
TalentLens - Recommendation and Resume Analysis Engine
Handles PDF text extraction (PyMuPDF), entity parsing,
and explainable candidate matching via TF-IDF, Cosine Similarity, and skill scoring.
"""

import re
import io
import json
from datetime import datetime
import pymupdf  # Modern PyMuPDF API
from typing import Dict, List, Tuple, Any, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Standard comprehensive technical skills taxonomy for extraction
COMMON_SKILLS = [
    # Languages
    "Python", "Java", "C++", "C#", "C", "JavaScript", "TypeScript", "Go", "Golang",
    "Rust", "PHP", "Ruby", "Swift", "Kotlin", "R", "Scala", "Dart", "Perl",
    # Web & Frameworks
    "Flask", "Django", "FastAPI", "Express", "Node.js", "React", "Angular", "Vue.js",
    "Next.js", "Spring Boot", "ASP.NET", "Ruby on Rails", "Laravel", "Tailwind CSS",
    "Bootstrap", "HTML", "HTML5", "CSS", "CSS3", "REST APIs", "RESTful APIs", "GraphQL",
    # Databases & Caching
    "SQL", "PostgreSQL", "MySQL", "SQLite", "MongoDB", "Redis", "Cassandra",
    "DynamoDB", "Elasticsearch", "Oracle", "Firebase", "Neo4j",
    # Cloud & DevOps
    "AWS", "Amazon Web Services", "Azure", "Google Cloud", "GCP", "Docker", "Kubernetes",
    "CI/CD", "Jenkins", "GitHub Actions", "GitLab CI", "Terraform", "Ansible",
    "Linux", "Unix", "Bash", "Shell Scripting", "Nginx", "Apache", "Kafka", "RabbitMQ", "Celery",
    # AI / ML / Data Science
    "Machine Learning", "Deep Learning", "NLP", "Natural Language Processing",
    "Computer Vision", "Scikit-Learn", "TensorFlow", "Keras", "PyTorch", "Pandas",
    "NumPy", "OpenCV", "Matplotlib", "Seaborn", "Plotly", "HuggingFace", "LLMs",
    # Methodologies & Tools
    "Git", "GitHub", "GitLab", "Bitbucket", "Jira", "Agile", "Scrum", "TDD",
    "Unit Testing", "Microservices", "Design Patterns", "System Design"
]


def extract_text_from_pdf(file_source: Any) -> str:
    """
    Extract clean textual content from PDF using PyMuPDF.
    Accepts either file bytes, io.BytesIO, or a file system path.
    """
    try:
        if isinstance(file_source, bytes):
            doc = pymupdf.open(stream=file_source, filetype="pdf")
        elif hasattr(file_source, "read"):
            content = file_source.read()
            doc = pymupdf.open(stream=content, filetype="pdf")
        elif isinstance(file_source, str):
            doc = pymupdf.open(file_source)
        else:
            return ""

        extracted_text = []
        for page in doc:
            extracted_text.append(page.get_text("text"))
        doc.close()
        return "\n".join(extracted_text).strip()
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return ""



def _parse_resume_date(value: str):
    """Convert a resume date token into a (year, month) pair."""
    value = value.strip().lower()
    if value in {"present", "current", "now"}:
        now = datetime.now()
        return now.year, now.month

    month_names = {
        "jan": 1, "january": 1, "feb": 2, "february": 2,
        "mar": 3, "march": 3, "apr": 4, "april": 4,
        "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
        "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
        "oct": 10, "october": 10, "nov": 11, "november": 11,
        "dec": 12, "december": 12,
    }
    month_match = re.fullmatch(
        r"([a-zA-Z]+)[\s,./-]+(19\d{2}|20\d{2})", value
    )
    if month_match and month_match.group(1).lower() in month_names:
        return int(month_match.group(2)), month_names[month_match.group(1).lower()]

    numeric_match = re.fullmatch(r"(0?[1-9]|1[0-2])[/.-](19\d{2}|20\d{2})", value)
    if numeric_match:
        return int(numeric_match.group(2)), int(numeric_match.group(1))

    year_match = re.fullmatch(r"(19\d{2}|20\d{2})", value)
    if year_match:
        return int(year_match.group(1)), 1
    return None


def _merge_month_intervals(intervals: List[Tuple[int, int]]) -> int:
    """Return the number of unique months covered by possibly-overlapping intervals."""
    if not intervals:
        return 0
    intervals = sorted(intervals)
    merged = []
    for start, end in intervals:
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return sum(end - start for start, end in merged)


def _calculate_experience_breakdown(resume_text: str) -> Dict[str, float]:
    """Calculate full-time, internship, and unique total experience from resume sections.

    Dates are only counted while inside employment/internship sections. Overlapping
    periods are merged for the total, so concurrent roles are not double-counted.
    """
    lines = [line.strip() for line in (resume_text or '').splitlines() if line.strip()]

    internship_heading = re.compile(
        r"^(?:internships?|summer internships?|industrial training|"
        r"internship experience|training experience)$", re.IGNORECASE
    )
    employment_heading = re.compile(
        r"^(?:(?:professional|work|employment)\s+)?experience(?:\s+history)?$|"
        r"^employment history$|^work history$|^professional experience$|^full[- ]time experience$",
        re.IGNORECASE,
    )
    other_heading = re.compile(
        r"^(?:education|academic background|projects?|technical skills|skills|"
        r"certifications?|licenses|achievements|publications|interests|hobbies|"
        r"references|additional information)$", re.IGNORECASE
    )

    month_names = (
        r"Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
        r"Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|"
        r"Nov(?:ember)?|Dec(?:ember)?"
    )
    month_year = rf"(?:{month_names})[\s,./-]+(?:19\d{{2}}|20\d{{2}})"
    numeric_month_year = r"(?:0?[1-9]|1[0-2])[/.-](?:19\d{2}|20\d{2})"
    year_only = r"(?:19\d{2}|20\d{2})"
    date_token = rf"(?:{month_year}|{numeric_month_year}|{year_only}|present|current|now)"
    range_pattern = re.compile(
        rf"(?<![A-Za-z0-9])({date_token})\s*(?:-|–|—|to|through)\s*({date_token})(?![A-Za-z0-9])",
        re.IGNORECASE,
    )

    internship_intervals: List[Tuple[int, int]] = []
    full_time_intervals: List[Tuple[int, int]] = []
    section_kind: Optional[str] = None
    current_role_kind: Optional[str] = None

    for line in lines:
        heading = re.sub(r"^[\s•●▪*-]+", "", line).strip().rstrip(":").strip()
        heading = re.sub(r"\s+", " ", heading)

        if internship_heading.fullmatch(heading):
            section_kind = "internship"
            current_role_kind = "internship"
            continue
        if employment_heading.fullmatch(heading):
            section_kind = "employment"
            current_role_kind = "full_time"
            continue
        if other_heading.fullmatch(heading):
            section_kind = None
            current_role_kind = None
            continue

        if section_kind is None:
            continue

        if re.search(r"\b(intern(?:ship)?s?|trainee|industrial training)\b", line, re.IGNORECASE):
            current_role_kind = "internship"
        elif section_kind == "employment" and re.search(
            r"\b(full[- ]?time|engineer|developer|analyst|consultant|manager|"
            r"associate|specialist|architect|designer|administrator|scientist|lead)\b",
            line, re.IGNORECASE,
        ) and not re.search(r"\b(intern|trainee)\b", line, re.IGNORECASE):
            current_role_kind = "full_time"

        for match in range_pattern.finditer(line):
            start_date = _parse_resume_date(match.group(1))
            end_date = _parse_resume_date(match.group(2))
            if not start_date or not end_date:
                continue

            start_index = start_date[0] * 12 + start_date[1]
            end_index = end_date[0] * 12 + end_date[1]
            both_year_only = bool(
                re.fullmatch(r"(?:19|20)\d{2}", match.group(1).strip())
                and re.fullmatch(r"(?:19|20)\d{2}", match.group(2).strip())
            )
            # A month-specific end date includes that month; year-only ranges
            # use year-difference semantics (e.g. 2022–2023 = one year).
            if not both_year_only:
                end_index += 1
            if end_index < start_index or end_index - start_index > 40 * 12:
                continue

            role_kind = "internship" if (
                section_kind == "internship" or current_role_kind == "internship"
            ) else "full_time"
            target = internship_intervals if role_kind == "internship" else full_time_intervals
            target.append((start_index, end_index))

    # If no date ranges were found, allow clearly-labelled duration statements
    # within employment sections (e.g. "6 months internship experience").
    if not internship_intervals and not full_time_intervals:
        section_kind = None
        current_role_kind = None
        duration_pattern = re.compile(
            r"(?P<amount>\d+(?:\.\d+)?)\s*(?P<unit>years?|yrs?|months?|mos?)\b",
            re.IGNORECASE,
        )
        internship_durations = []
        full_time_durations = []
        for line in lines:
            heading = re.sub(r"^[\s•●▪*-]+", "", line).strip().rstrip(":").strip()
            if internship_heading.fullmatch(heading):
                section_kind, current_role_kind = "internship", "internship"
                continue
            if employment_heading.fullmatch(heading):
                section_kind, current_role_kind = "employment", "full_time"
                continue
            if other_heading.fullmatch(heading):
                section_kind, current_role_kind = None, None
                continue
            if section_kind is None:
                continue
            if re.search(r"\b(intern(?:ship)?s?|trainee|industrial training)\b", line, re.IGNORECASE):
                current_role_kind = "internship"
            for match in duration_pattern.finditer(line):
                amount = float(match.group("amount"))
                unit = match.group("unit").lower()
                years = amount / 12.0 if unit.startswith(("month", "mo")) else amount
                if not 0 < years <= 40:
                    continue
                is_internship = (
                    section_kind == "internship" or current_role_kind == "internship"
                    or bool(re.search(r"\b(intern|internship|trainee)\b", line, re.IGNORECASE))
                )
                (internship_durations if is_internship else full_time_durations).append(years)
        internship_years = max(internship_durations, default=0.0)
        full_time_years = max(full_time_durations, default=0.0)
        return {
            "full_time_experience_years": round(full_time_years, 2),
            "internship_experience_years": round(internship_years, 2),
            "experience_years": round(full_time_years + internship_years, 2),
        }

    full_time_months = _merge_month_intervals(full_time_intervals)
    internship_months = _merge_month_intervals(internship_intervals)
    total_months = _merge_month_intervals(full_time_intervals + internship_intervals)
    return {
        "full_time_experience_years": round(full_time_months / 12.0, 2),
        "internship_experience_years": round(internship_months / 12.0, 2),
        "experience_years": round(total_months / 12.0, 2),
    }


def calculate_experience_breakdown(resume_text: str) -> Dict[str, float]:
    """Public helper used by the recruiter dossier to show the experience split."""
    return _calculate_experience_breakdown(resume_text)


def _calculate_experience_years(resume_text: str) -> float:
    """Backward-compatible total experience helper."""
    return _calculate_experience_breakdown(resume_text)["experience_years"]


def extract_certifications(raw_text: str) -> str:
    """Extract certifications from the Certifications section without inventing defaults."""
    lines = [line.strip() for line in (raw_text or "").splitlines() if line.strip()]
    cert_heading = re.compile(r"^(?:professional )?certifications?|licenses? and certifications?$", re.I)
    section_heading = re.compile(
        r"^(?:education|academic background|projects?|technical skills|skills|"
        r"experience|professional experience|work experience|internships?|"
        r"additional information|achievements|publications|interests|hobbies|references)$",
        re.I,
    )
    collected = []
    in_cert_section = False
    for line in lines:
        cleaned = re.sub(r"^[\s•●▪*-]+", "", line).strip()
        normalized = cleaned.rstrip(":").strip()
        if cert_heading.fullmatch(normalized):
            in_cert_section = True
            continue
        if section_heading.fullmatch(normalized):
            in_cert_section = False
            continue
        if in_cert_section and len(cleaned) > 2:
            collected.append(cleaned)

    # Some resumes list a certification outside a dedicated section. Only use
    # lines explicitly mentioning a certificate/certification; never invent one.
    if not collected:
        collected = [
            re.sub(r"^[\s•●▪*-]+", "", line).strip()
            for line in lines
            if re.search(r"\b(certified|certification|certificate)\b", line, re.I)
        ]
    return " | ".join(collected[:6]) if collected else "Not detected"


def parse_resume(raw_text: str, filename: str = "Candidate_Resume.pdf") -> Dict[str, Any]:
    """
    Extract key structured candidate entities from raw resume text:
    - Name
    - Email
    - Phone
    - Experience in years
    - Technical skills
    - Education
    - Projects
    - Certifications
    """
    if not raw_text or len(raw_text.strip()) == 0:
        base_name = re.sub(r'[\._-]|resume|cv|\.pdf', ' ', filename, flags=re.IGNORECASE).strip().title()
        return {
            "name": base_name if base_name else "Anonymous Candidate",
            "email": "",
            "phone": "",
            "skills": [],
            "experience_years": 0.0,
            "full_time_experience_years": 0.0,
            "internship_experience_years": 0.0,
            "education": "Not detected",
            "projects": "Not detected",
            "certifications": "Not detected",
            "raw_text": ""
        }

    # 1. Email extraction
    email_match = re.search(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', raw_text)
    email = email_match.group(0).lower() if email_match else ""

    # 2. Phone extraction (international or standard formats)
    phone_match = re.search(r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', raw_text)
    phone = phone_match.group(0) if phone_match else ""

    # 3. Name extraction
    name = ""
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

    # Try looking for explicit Name: label
    name_label_match = re.search(r'(?:Name|Full Name)\s*[:\-]\s*([A-Za-z\s]{2,40})', raw_text, re.IGNORECASE)
    if name_label_match:
        name = name_label_match.group(1).strip()
    elif lines:
        # First non-trivial line often contains candidate's full name
        for line in lines[:5]:
            # Ignore lines that are emails, phone numbers, or section headers
            if ("@" not in line and not re.search(r'\d{5,}', line) and
                len(line.split()) in [2, 3, 4] and not re.search(r'(resume|curriculum|vitae|profile|summary|contact)', line, re.I)):
                name = line.strip()
                break

    if not name or len(name) < 2:
        # Clean from filename
        clean_name = re.sub(r'[\._-]|resume|cv|\.pdf', ' ', filename, flags=re.IGNORECASE).strip().title()
        name = clean_name if clean_name else "Candidate"

    # 4. Work and internship experience calculation.
    # Only employment/internship sections and explicitly labelled work durations
    # contribute; education and project dates are not treated as work experience.
    experience_breakdown = _calculate_experience_breakdown(raw_text)
    experience_years = experience_breakdown["experience_years"]

    # 5. Technical Skills Extraction
    extracted_skills = []
    text_lower = raw_text.lower()
    for skill in COMMON_SKILLS:
        # Escape skill for regex and match word boundaries
        escaped_skill = re.escape(skill)
        # Handle special cases like C++, C#, .NET
        if skill in ["C++", "C#", ".NET"]:
            pattern = rf'(?:\b|\s){escaped_skill}(?:\b|\s|,|\.|$)'
        else:
            pattern = rf'\b{escaped_skill}\b'

        if re.search(pattern, raw_text, re.IGNORECASE):
            extracted_skills.append(skill)

    # Deduplicate and normalize
    extracted_skills = sorted(list(set(extracted_skills)), key=lambda s: s.lower())

    # 6. Education Extraction
    education_lines = []
    edu_keywords = ["bachelor", "master", "phd", "b.tech", "m.tech", "b.e.", "m.e.", "bca", "mca",
                    "b.sc", "m.sc", "degree", "university", "institute", "college", "gpa", "cgpa"]
    for line in lines:
        if any(kw in line.lower() for kw in edu_keywords):
            education_lines.append(line)
            if len(education_lines) >= 3:
                break
    education = " | ".join(education_lines) if education_lines else "Not detected"

    # 7. Projects Extraction
    project_lines = []
    in_project_section = False
    for line in lines:
        lower = line.lower()
        if re.search(r'\b(projects|key projects|academic projects|technical projects)\b', lower):
            in_project_section = True
            continue
        if in_project_section:
            if re.search(r'\b(experience|education|certifications|skills|hobbies|achievements)\b', lower) and len(line.split()) < 4:
                in_project_section = False
                continue
            if len(line) > 10:
                project_lines.append(line)
            if len(project_lines) >= 4:
                break
    projects = " \n ".join(project_lines) if project_lines else "Not detected"

    # 8. Certifications: use explicit section content; never invent credentials.
    certifications = extract_certifications(raw_text)

    return {
        "name": name,
        "email": email,
        "phone": phone,
        "skills": extracted_skills,
        "experience_years": experience_years,
        "full_time_experience_years": experience_breakdown["full_time_experience_years"],
        "internship_experience_years": experience_breakdown["internship_experience_years"],
        "education": education,
        "projects": projects,
        "certifications": certifications,
        "raw_text": raw_text
    }


def match_skills(required_skills: List[str], candidate_skills: List[str]) -> Tuple[List[str], List[str]]:
    """
    Compare required or preferred skills with candidate skills using normalized matching.
    Returns: (matched_skills, missing_skills)
    """
    cand_skills_lower = {s.lower().strip(): s for s in candidate_skills}
    matched = []
    missing = []

    for req in required_skills:
        req_clean = req.strip()
        if not req_clean:
            continue
        req_lower = req_clean.lower()
        # Direct match or substring match (e.g. 'AWS' in 'Amazon Web Services (AWS)')
        found = False
        for c_lower, c_orig in cand_skills_lower.items():
            if req_lower == c_lower or req_lower in c_lower or c_lower in req_lower:
                matched.append(req_clean)
                found = True
                break
        if not found:
            missing.append(req_clean)

    return matched, missing


def compute_tfidf_similarity(job_text: str, candidate_text: str) -> float:
    """
    Compute Cosine Similarity between Job Description and Candidate Resume using Scikit-learn TF-IDF.
    Returns a normalized float between 0.0 and 1.0.
    """
    if not job_text.strip() or not candidate_text.strip():
        return 0.15

    try:
        vectorizer = TfidfVectorizer(
            stop_words="english",
            token_pattern=r'(?u)\b\w+\b',
            ngram_range=(1, 2),
            max_features=2500
        )
        tfidf_matrix = vectorizer.fit_transform([job_text, candidate_text])
        similarity = float(cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0])
        # Ensure it stays within [0.0, 1.0]
        return max(0.0, min(1.0, similarity))
    except Exception as e:
        print(f"TF-IDF computation error: {e}")
        return 0.20


def evaluate_candidate(job: Dict[str, Any], candidate: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate transparent, explainable compatibility score out of 100 based on user's exact specification:
    1. Required skills matching: 40%
    2. Resume and job-description similarity using TF-IDF and cosine similarity: 25%
    3. Preferred skills matching: 15%
    4. Experience matching: 20%

    Candidate categories:
    - Strong: >= 70
    - Moderate: 45 - 69.9
    - Low: < 45
    """
    required_skills = job.get("required_skills", [])
    preferred_skills = job.get("preferred_skills", [])
    min_exp = float(job.get("min_experience", 0.0))
    cand_exp = float(candidate.get("experience_years", 0.0))
    cand_skills = candidate.get("skills", [])

    # 1. Required Skills Match (40 Points Max)
    matched_req, missing_req = match_skills(required_skills, cand_skills)
    if len(required_skills) > 0:
        req_ratio = len(matched_req) / len(required_skills)
        score_req = req_ratio * 40.0
    else:
        score_req = 40.0

    # 2. Preferred Skills Match (15 Points Max)
    matched_pref, missing_pref = match_skills(preferred_skills, cand_skills)
    if len(preferred_skills) > 0:
        pref_ratio = len(matched_pref) / len(preferred_skills)
        score_pref = pref_ratio * 15.0
    else:
        score_pref = 15.0  # Full bonus if no preferred skills specified

    # 3. TF-IDF & Cosine Similarity (25 Points Max)
    job_full_doc = f"{job.get('title', '')} {job.get('department', '')} {job.get('description', '')} " + " ".join(required_skills + preferred_skills)
    cand_full_doc = f"{candidate.get('raw_text', '')} {' '.join(cand_skills)} {candidate.get('education', '')} {candidate.get('projects', '')}"

    cosine_sim = compute_tfidf_similarity(job_full_doc, cand_full_doc)
    score_tfidf = cosine_sim * 25.0

    # 4. Experience Match (20 Points Max)
    if min_exp <= 0.0:
        score_exp = 20.0
    else:
        if cand_exp >= min_exp:
            score_exp = 20.0
        else:
            # Proportional credit based on candidate experience
            score_exp = max(0.0, (cand_exp / min_exp) * 20.0)

    # Total Score Out of 100
    overall_score = round(score_req + score_tfidf + score_pref + score_exp, 1)
    overall_score = max(0.0, min(100.0, overall_score))

    # Category Determination
    if overall_score >= 70.0:
        category = "Strong"
    elif overall_score >= 45.0:
        category = "Moderate"
    else:
        category = "Low"

    # Explainable Strengths & Areas for Evaluation
    strengths = []
    areas_for_evaluation = []

    # Strengths logic
    if len(matched_req) == len(required_skills) and len(required_skills) > 0:
        strengths.append(f"100% match on all mandatory required skills ({', '.join(matched_req)})")
    elif len(matched_req) > 0:
        strengths.append(f"Possesses core required competencies: {', '.join(matched_req[:4])}")

    if len(matched_pref) > 0:
        strengths.append(f"Strong bonus coverage in preferred stack: {', '.join(matched_pref[:3])}")

    if cand_exp >= min_exp:
        strengths.append(f"Meets or exceeds experience requirement ({cand_exp:.1f} yrs vs {min_exp:.1f} yrs required)")

    if cosine_sim >= 0.50:
        strengths.append(f"High resume contextual alignment with job specifications ({int(cosine_sim*100)}% TF-IDF relevance)")

    # Areas for evaluation logic
    if missing_req:
        areas_for_evaluation.append(f"Missing essential required skills: {', '.join(missing_req)}")

    if cand_exp < min_exp:
        deficit = min_exp - cand_exp
        areas_for_evaluation.append(f"Under target experience requirement by {deficit:.1f} year(s)")

    if missing_pref:
        areas_for_evaluation.append(f"Lacks preferred secondary skills: {', '.join(missing_pref[:3])}")

    if cosine_sim < 0.30:
        areas_for_evaluation.append("Low overall semantic overlap between resume narrative and job description")

    if not strengths:
        strengths.append("Foundational technical literacy in basic computing concepts")
    if not areas_for_evaluation:
        areas_for_evaluation.append("Standard cultural fit and behavioral interview validation recommended")

    return {
        "overall_score": overall_score,
        "required_match_score": round(score_req, 1),
        "tfidf_score": round(score_tfidf, 1),
        "preferred_match_score": round(score_pref, 1),
        "experience_score": round(score_exp, 1),
        "cosine_similarity_raw": round(cosine_sim, 3),
        "category": category,
        "matched_required_skills": matched_req,
        "matched_preferred_skills": matched_pref,
        "missing_skills": missing_req + missing_pref,
        "strengths": strengths,
        "areas_for_evaluation": areas_for_evaluation
    }

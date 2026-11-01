"""
Resume parser: extracts structured candidate information from PDF/DOCX files.
Uses PyMuPDF, python-docx, spaCy, and rule-based extraction.
"""
import re
import os
import hashlib
from typing import Optional, Tuple
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)

# Try importing optional dependencies gracefully
try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False
    logger.warning("PyMuPDF not available - PDF parsing disabled")

try:
    from docx import Document as DocxDocument
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False
    logger.warning("python-docx not available - DOCX parsing disabled")

try:
    import spacy
    try:
        nlp = spacy.load("en_core_web_sm")
        HAS_SPACY = True
    except OSError:
        HAS_SPACY = False
        logger.warning("spaCy model not found - NER disabled")
except ImportError:
    HAS_SPACY = False
    logger.warning("spaCy not available")

from app.ai.skill_normalizer import SKILL_KEYWORDS, normalize_skill, normalize_skills_list

# ------------------------------------------------------------------ #
# Text extraction
# ------------------------------------------------------------------ #

def extract_text_from_pdf(file_path: str) -> Tuple[str, Optional[str]]:
    """Returns (text, error)"""
    if not HAS_PYMUPDF:
        return "", "PyMuPDF not installed"
    try:
        doc = fitz.open(file_path)
        texts = []
        for page in doc:
            texts.append(page.get_text("text"))
        doc.close()
        return "\n".join(texts), None
    except Exception as e:
        return "", str(e)


def extract_text_from_docx(file_path: str) -> Tuple[str, Optional[str]]:
    """Returns (text, error)"""
    if not HAS_DOCX:
        return "", "python-docx not installed"
    try:
        doc = DocxDocument(file_path)
        paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
        # Also get table text
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text.strip():
                        paragraphs.append(cell.text.strip())
        return "\n".join(paragraphs), None
    except Exception as e:
        return "", str(e)


def extract_text(file_path: str, file_type: str) -> Tuple[str, Optional[str]]:
    """Extract raw text from a resume file."""
    ft = file_type.lower().strip(".")
    if ft == "pdf":
        return extract_text_from_pdf(file_path)
    elif ft in ("docx", "doc"):
        return extract_text_from_docx(file_path)
    else:
        return "", f"Unsupported file type: {file_type}"


def compute_checksum(file_path: str) -> str:
    """Compute SHA256 checksum for duplicate detection."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


# ------------------------------------------------------------------ #
# Text preprocessing
# ------------------------------------------------------------------ #

def clean_text(text: str) -> str:
    """Remove excessive whitespace and non-printable characters."""
    text = re.sub(r'\r\n|\r', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    text = re.sub(r'[^\x20-\x7E\n]', ' ', text)
    return text.strip()


# ------------------------------------------------------------------ #
# Information extractors
# ------------------------------------------------------------------ #

EMAIL_RE = re.compile(r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b')
PHONE_RE = re.compile(r'(?:(?:\+|0{0,2})91[\s\-]?)?(?:[6-9]\d{9}|(?:\d[\s\-]?){10})')
LINKEDIN_RE = re.compile(r'(?:https?://)?(?:www\.)?linkedin\.com/in/[\w\-]+/?', re.I)
GITHUB_RE = re.compile(r'(?:https?://)?(?:www\.)?github\.com/[\w\-]+/?', re.I)
URL_RE = re.compile(r'https?://\S+', re.I)

SECTION_HEADERS = {
    'education': r'(?i)^(education|academic|qualification|degree)',
    'experience': r'(?i)^(experience|work experience|employment|professional experience|career|internship)',
    'skills': r'(?i)^(skills|technical skills|technologies|tools|programming|competencies|expertise)',
    'projects': r'(?i)^(projects?|personal projects?|academic projects?)',
    'certifications': r'(?i)^(certifications?|certificates?|courses?|training)',
    'summary': r'(?i)^(summary|profile|objective|about|overview)',
}

DEGREE_KEYWORDS = [
    'b.tech', 'btech', 'b.e', 'be ', 'bachelor', 'b.sc', 'bsc', 'b.com', 'bcom',
    'm.tech', 'mtech', 'm.e', 'master', 'm.sc', 'msc', 'mba', 'mca', 'bca',
    'phd', 'ph.d', 'doctorate', 'diploma', '12th', '10th', 'hsc', 'ssc',
    'b.a', 'ba ', 'm.a', 'ma ', 'llb', 'mbbs',
]

DEGREE_MAP = {
    'b.tech': 'B.Tech', 'btech': 'B.Tech', 'b.e': 'B.E', 'bachelor of technology': 'B.Tech',
    'bachelor of engineering': 'B.E', 'bachelor': 'Bachelor\'s',
    'm.tech': 'M.Tech', 'mtech': 'M.Tech', 'master of technology': 'M.Tech',
    'master of engineering': 'M.E', 'master of science': 'M.Sc', 'master of business administration': 'MBA',
    'master': 'Master\'s', 'mba': 'MBA', 'mca': 'MCA', 'bca': 'BCA',
    'ph.d': 'Ph.D', 'phd': 'Ph.D', 'doctorate': 'Ph.D',
    'b.sc': 'B.Sc', 'bsc': 'B.Sc', 'bachelor of science': 'B.Sc',
    'diploma': 'Diploma', '12th': '12th (Higher Secondary)', '10th': '10th (Secondary)',
}

YEAR_RE = re.compile(r'\b(19|20)\d{2}\b')
DATE_RANGE_RE = re.compile(
    r'((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*\d{4}|'
    r'\d{1,2}/\d{4}|\d{4})'
    r'\s*[-–—to]+\s*'
    r'((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*\d{4}|'
    r'\d{1,2}/\d{4}|\d{4}|present|current|now)',
    re.I
)


def extract_email(text: str) -> Optional[str]:
    m = EMAIL_RE.search(text)
    return m.group(0).lower() if m else None


def extract_phone(text: str) -> Optional[str]:
    m = PHONE_RE.search(text)
    if m:
        phone = re.sub(r'[\s\-]', '', m.group(0))
        return phone
    return None


def extract_name(text: str, email: Optional[str] = None) -> str:
    """Extract candidate name from resume text."""
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    if not lines:
        return "Unknown Candidate"

    # Use spaCy NER if available
    if HAS_SPACY:
        first_500 = text[:500]
        doc = nlp(first_500)
        persons = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]
        if persons:
            return persons[0].strip()

    # Fallback: first non-empty line that looks like a name
    for line in lines[:5]:
        line_clean = line.strip()
        # Skip lines with @, /, http, numbers-only, or common headers
        if (email and email in line_clean.lower()):
            continue
        if re.search(r'[@/|]|http|www|\d{5,}', line_clean):
            continue
        if len(line_clean.split()) in [1, 2, 3, 4] and len(line_clean) < 60:
            # Check it's mostly alphabetic
            alpha_ratio = sum(c.isalpha() or c.isspace() for c in line_clean) / max(len(line_clean), 1)
            if alpha_ratio > 0.8:
                return line_clean

    # Try email-based name
    if email:
        local = email.split('@')[0]
        name_from_email = re.sub(r'[._\-0-9]', ' ', local).strip().title()
        if name_from_email:
            return name_from_email

    return lines[0][:60] if lines else "Unknown Candidate"


def extract_skills_from_text(text: str) -> list:
    """Extract technical skills using keyword matching and NLP."""
    found = set()
    text_lower = text.lower()

    # Direct keyword scan
    for skill in SKILL_KEYWORDS:
        # Use word boundary matching
        pattern = r'(?<![a-z])' + re.escape(skill) + r'(?![a-z])'
        if re.search(pattern, text_lower):
            found.add(skill)

    # Also look for skill-section content
    # Find skills section and extract comma/bullet separated items
    skills_section = extract_section(text, 'skills')
    if skills_section:
        # Split by common delimiters
        items = re.split(r'[,\n•\-|/\\]', skills_section)
        for item in items:
            item = item.strip()
            if 1 < len(item) < 40:
                item_lower = item.lower()
                if item_lower in SKILL_KEYWORDS:
                    found.add(item_lower)
                elif len(item.split()) <= 3:
                    # Could be a multi-word skill
                    found.add(item.lower())

    # Normalize all found skills
    normalized = normalize_skills_list([s.title() if len(s) > 3 else s.upper() for s in found])
    return normalized


def extract_programming_languages(text: str) -> list:
    """Extract programming languages specifically."""
    prog_langs = {
        'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'ruby', 'go',
        'golang', 'rust', 'php', 'swift', 'kotlin', 'scala', 'r', 'matlab',
        'bash', 'shell', 'perl', 'dart', 'elixir', 'haskell', 'lua', 'html', 'css',
        'sql', 'c', 'f#', 'julia',
    }
    found = set()
    text_lower = text.lower()
    for lang in prog_langs:
        pattern = r'(?<![a-z])' + re.escape(lang) + r'(?![a-z])'
        if re.search(pattern, text_lower):
            found.add(lang)
    from app.ai.skill_normalizer import normalize_skill
    return [normalize_skill(l.title() if len(l) > 2 else l.upper()) for l in found]


def extract_section(text: str, section_type: str) -> str:
    """Extract text content of a specific section."""
    lines = text.split('\n')
    pattern = SECTION_HEADERS.get(section_type, '')
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
            # Check if we've hit another section header
            is_other_header = False
            for other_type, other_pattern in SECTION_HEADERS.items():
                if other_type != section_type and re.match(other_pattern, stripped):
                    is_other_header = True
                    break
            if is_other_header and i > start_idx + 1:
                end_idx = i
                break

    if start_idx is None:
        return ''

    section_lines = lines[start_idx + 1: end_idx] if end_idx else lines[start_idx + 1: start_idx + 50]
    return '\n'.join(section_lines).strip()


def extract_education(text: str) -> list:
    """Extract education entries."""
    edu_section = extract_section(text, 'education')
    source = edu_section if edu_section else text

    entries = []
    lines = [l.strip() for l in source.split('\n') if l.strip()]

    current_entry = {}
    for line in lines:
        line_lower = line.lower()

        # Check if it's a degree line
        degree_found = None
        for deg_key, deg_val in DEGREE_MAP.items():
            if deg_key in line_lower:
                degree_found = deg_val
                break

        if degree_found and not current_entry.get('degree'):
            if current_entry:
                entries.append(current_entry)
            current_entry = {'degree': degree_found}

            # Try to extract field of study
            field_match = re.search(
                r'(?:in|of)\s+([A-Za-z\s&]+?)(?:\s+from|\s+at|\s+,|$)',
                line, re.I
            )
            if field_match:
                current_entry['field_of_study'] = field_match.group(1).strip()

        # Institution name (typically follows degree or contains 'university', 'college', etc.)
        if any(kw in line_lower for kw in ['university', 'college', 'institute', 'school', 'iit', 'nit', 'iiit']):
            if current_entry:
                current_entry['institution'] = line[:200]
            else:
                current_entry = {'institution': line[:200]}

        # Year extraction
        years = YEAR_RE.findall(line)
        if years and current_entry:
            years_int = sorted([int(y) for y in years])
            if len(years_int) >= 2:
                current_entry['start_year'] = years_int[0]
                current_entry['end_year'] = years_int[-1]
            elif len(years_int) == 1:
                current_entry['end_year'] = years_int[0]

        # GPA
        gpa_match = re.search(r'(?:gpa|cgpa|grade)\s*:?\s*(\d+\.?\d*)\s*/\s*(\d+\.?\d*)', line_lower)
        if gpa_match and current_entry:
            try:
                gpa = float(gpa_match.group(1))
                scale = float(gpa_match.group(2))
                if scale == 10:
                    current_entry['gpa'] = round(gpa / 2.5, 2)  # Convert to 4.0 scale
                elif scale == 4:
                    current_entry['gpa'] = gpa
                else:
                    current_entry['gpa'] = gpa
            except ValueError:
                pass

    if current_entry and (current_entry.get('degree') or current_entry.get('institution')):
        entries.append(current_entry)

    # Limit to reasonable number
    return entries[:5]


def parse_duration_months(start_str: str, end_str: str) -> int:
    """Parse start/end date strings and return duration in months."""
    month_map = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
    }
    now = datetime.now()

    def parse_date(s):
        s = s.strip().lower()
        if s in ('present', 'current', 'now', 'till date', 'ongoing'):
            return now
        # Try "Month Year"
        for m_abbr, m_num in month_map.items():
            if m_abbr in s:
                year_m = re.search(r'(20|19)\d{2}', s)
                if year_m:
                    try:
                        return datetime(int(year_m.group(0)), m_num, 1)
                    except ValueError:
                        pass
        # Try just year
        year_m = re.search(r'(20|19)\d{2}', s)
        if year_m:
            try:
                return datetime(int(year_m.group(0)), 6, 1)  # mid-year estimate
            except ValueError:
                pass
        return None

    start = parse_date(start_str)
    end = parse_date(end_str)
    if start and end and end >= start:
        delta = (end.year - start.year) * 12 + (end.month - start.month)
        return max(0, delta)
    return 0


def extract_experience(text: str) -> list:
    """Extract work experience entries."""
    exp_section = extract_section(text, 'experience')
    source = exp_section if exp_section else ''

    entries = []
    if not source:
        return entries

    lines = [l.strip() for l in source.split('\n') if l.strip()]
    current = {}

    for line in lines:
        # Date range detection
        date_match = DATE_RANGE_RE.search(line)
        if date_match:
            if current and (current.get('title') or current.get('company')):
                entries.append(current)
            current = {
                'start_date': date_match.group(1),
                'end_date': date_match.group(2),
                'is_current': date_match.group(2).lower() in ('present', 'current', 'now'),
                'duration_months': parse_duration_months(date_match.group(1), date_match.group(2)),
                'description': '',
            }
            # Check if internship
            if 'intern' in line.lower():
                current['is_internship'] = True
            # Try to get title from the line
            title_text = re.sub(r'\d{4}.*$', '', line).strip()
            if title_text and len(title_text) > 2:
                current['title'] = title_text[:200]
        elif current:
            # Try to identify company / title
            if not current.get('company') and any(
                kw in line.lower() for kw in ['pvt', 'ltd', 'inc', 'corp', 'technologies', 'solutions', 'systems', 'services']
            ):
                current['company'] = line[:200]
            elif not current.get('title') and len(line.split()) <= 6 and len(line) < 100:
                if not current.get('title'):
                    current['title'] = line[:200]
            else:
                current['description'] = current.get('description', '') + ' ' + line

    if current and (current.get('title') or current.get('company')):
        entries.append(current)

    return entries[:10]


def extract_projects(text: str) -> list:
    """Extract project entries."""
    proj_section = extract_section(text, 'projects')
    if not proj_section:
        return []

    projects = []
    lines = [l.strip() for l in proj_section.split('\n') if l.strip()]
    current_project = None

    for line in lines:
        # New project starts with a title-like line (short, no sentence structure)
        if len(line) < 80 and len(line.split()) <= 8 and not line.endswith('.'):
            if current_project:
                projects.append(current_project)
            current_project = {'name': line, 'description': '', 'technologies': []}
        elif current_project:
            current_project['description'] += ' ' + line
            # Extract technologies from description
            for skill in SKILL_KEYWORDS:
                if skill in line.lower():
                    if skill not in current_project['technologies']:
                        current_project['technologies'].append(
                            normalize_skill(skill.title() if len(skill) > 2 else skill.upper())
                        )

    if current_project:
        projects.append(current_project)

    # Clean up descriptions
    for p in projects:
        p['description'] = p.get('description', '').strip()[:500]

    return projects[:10]


def extract_certifications(text: str) -> list:
    """Extract certification entries."""
    cert_section = extract_section(text, 'certifications')
    if not cert_section:
        # Fallback: look for cert patterns in full text
        cert_patterns = [
            r'(?:certified|certification|certificate)\s+(?:in\s+)?([^\n]+)',
            r'([^\n]+)\s+(?:certified|certification|certificate)',
        ]
        certs = []
        for pattern in cert_patterns:
            matches = re.findall(pattern, text, re.I)
            certs.extend([m.strip()[:200] for m in matches if len(m.strip()) > 5])
        return list(set(certs))[:10]

    lines = [l.strip() for l in cert_section.split('\n') if l.strip() and len(l.strip()) > 3]
    return [re.sub(r'^[•\-\*]\s*', '', l) for l in lines[:10]]


def calculate_total_experience(experience_entries: list) -> float:
    """Calculate total years of experience from experience entries."""
    total_months = sum(e.get('duration_months', 0) for e in experience_entries
                       if not e.get('is_internship', False))
    return round(total_months / 12, 1)


# ------------------------------------------------------------------ #
# Main parsing function
# ------------------------------------------------------------------ #

def parse_resume(file_path: str, file_type: str) -> dict:
    """
    Main resume parsing function.
    Returns a structured dictionary with extracted candidate information.
    """
    result = {
        'name': 'Unknown Candidate',
        'email': None,
        'phone': None,
        'linkedin': None,
        'github': None,
        'location': None,
        'summary': None,
        'technical_skills': [],
        'programming_languages': [],
        'certifications': [],
        'projects': [],
        'education': [],
        'experience': [],
        'total_experience_years': 0.0,
        'raw_text': '',
        'extraction_confidence': 0.5,
        'error': None,
    }

    # Extract raw text
    raw_text, error = extract_text(file_path, file_type)
    if error:
        result['error'] = error
        return result

    if not raw_text.strip():
        result['error'] = 'No text could be extracted from the file'
        return result

    cleaned_text = clean_text(raw_text)
    result['raw_text'] = cleaned_text

    # Extract fields
    email = extract_email(cleaned_text)
    result['email'] = email

    result['phone'] = extract_phone(cleaned_text)
    result['name'] = extract_name(cleaned_text, email)

    # LinkedIn/GitHub
    linkedin_m = LINKEDIN_RE.search(cleaned_text)
    if linkedin_m:
        result['linkedin'] = linkedin_m.group(0)
    github_m = GITHUB_RE.search(cleaned_text)
    if github_m:
        result['github'] = github_m.group(0)

    # Summary
    summary_section = extract_section(cleaned_text, 'summary')
    if summary_section:
        result['summary'] = summary_section[:1000]

    # Skills
    result['technical_skills'] = extract_skills_from_text(cleaned_text)
    result['programming_languages'] = extract_programming_languages(cleaned_text)

    # Education
    result['education'] = extract_education(cleaned_text)

    # Experience
    result['experience'] = extract_experience(cleaned_text)
    result['total_experience_years'] = calculate_total_experience(result['experience'])

    # Projects
    result['projects'] = extract_projects(cleaned_text)

    # Certifications
    result['certifications'] = extract_certifications(cleaned_text)

    # Confidence score based on how much was extracted
    confidence = 0.0
    if result['name'] and result['name'] != 'Unknown Candidate':
        confidence += 0.2
    if result['email']:
        confidence += 0.15
    if result['phone']:
        confidence += 0.1
    if result['technical_skills']:
        confidence += 0.2
    if result['education']:
        confidence += 0.15
    if result['experience']:
        confidence += 0.2

    result['extraction_confidence'] = min(confidence, 1.0)

    return result

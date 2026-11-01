from engine import calculate_experience_breakdown, extract_certifications, parse_resume


def test_one_year_internship_split():
    text = """AARAV MEHTA
PROFESSIONAL EXPERIENCE
Python Developer Intern | BlueOak Software Labs
June 2025 – May 2026
PROJECTS
Inventory REST API
EDUCATION
B.Tech CSE | 2022 – 2026
"""
    result = calculate_experience_breakdown(text)
    assert result == {
        "full_time_experience_years": 0.0,
        "internship_experience_years": 1.0,
        "experience_years": 1.0,
    }


def test_full_time_and_internship_both_count():
    text = """WORK EXPERIENCE
Software Engineer | Acme
Jan 2021 - Dec 2021
Python Intern | Beta
May 2023 - July 2023
EDUCATION
B.Tech 2018 - 2022
"""
    result = calculate_experience_breakdown(text)
    assert result["full_time_experience_years"] == 1.0
    assert result["internship_experience_years"] == 0.25
    assert result["experience_years"] == 1.25


def test_overlapping_roles_not_double_counted_in_total():
    text = """PROFESSIONAL EXPERIENCE
Software Engineer | Acme
Jan 2023 - Dec 2023
INTERNSHIPS
Python Intern | Beta
Jun 2023 - Aug 2023
EDUCATION
B.Tech 2019 - 2023
"""
    result = calculate_experience_breakdown(text)
    assert result["full_time_experience_years"] == 1.0
    assert result["internship_experience_years"] == 0.25
    assert result["experience_years"] == 1.0


def test_education_and_project_dates_are_ignored():
    text = """EDUCATION
B.Tech CSE | 2022 - 2026
PROJECTS
College Project | Jan 2024 - May 2024
"""
    assert calculate_experience_breakdown(text)["experience_years"] == 0.0


def test_certifications_are_extracted_without_fabricated_defaults():
    text = """CERTIFICATIONS
Python Programming Fundamentals — Example Academy, 2025
SQL Essentials — Example Academy, 2024
ADDITIONAL INFORMATION
Available immediately
"""
    extracted = extract_certifications(text)
    assert "Python Programming Fundamentals" in extracted
    assert "SQL Essentials" in extracted
    assert "AWS Certified Cloud Practitioner" not in extracted


def test_missing_certifications_are_not_fabricated():
    assert extract_certifications("No credential information in this resume.") == "Not detected"


def test_missing_contact_details_are_not_fabricated():
    profile = parse_resume(
        "AARAV MEHTA\nPROFESSIONAL EXPERIENCE\nPython Intern\nJune 2025 - May 2026"
    )
    assert profile["email"] == ""
    assert profile["phone"] == ""
    assert profile["experience_years"] == 1.0
    assert profile["internship_experience_years"] == 1.0

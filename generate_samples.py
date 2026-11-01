"""
TalentLens - Sample Data and Synthetic Resume Generator
Generates realistic PDF resumes in sample_resumes/ using PyMuPDF,
and preloads SQLite database with active jobs, candidates, and initial evaluations.
"""

import os
import pymupdf
from database import init_db, create_job, save_candidate, save_match_evaluation, update_candidate_status, log_activity
from engine import evaluate_candidate, extract_text_from_pdf, parse_resume

SAMPLE_DIR = "sample_resumes"


def create_sample_pdf(filepath: str, name: str, title: str, contact_info: str,
                      summary: str, skills: list, experience_text: str,
                      education_text: str, projects_text: str, certs_text: str):
    """Generate a clean, visually structured single-page resume PDF using PyMuPDF."""
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)  # A4 size

    # Margin and initial Y coordinate
    left_x = 50
    current_y = 60

    # Header: Name (Bold, 20pt)
    page.insert_text(pymupdf.Point(left_x, current_y), name, fontsize=20, fontname="helv", color=(0.06, 0.15, 0.35))
    current_y += 20

    # Title & Contact
    page.insert_text(pymupdf.Point(left_x, current_y), f"{title} | {contact_info}", fontsize=10, fontname="helv", color=(0.3, 0.35, 0.45))
    current_y += 15

    # Decorative Line
    page.draw_line(pymupdf.Point(left_x, current_y), pymupdf.Point(545, current_y), color=(0.15, 0.35, 0.75), width=1.5)
    current_y += 22

    def add_section(header: str, body: str):
        nonlocal current_y
        page.insert_text(pymupdf.Point(left_x, current_y), header.upper(), fontsize=12, fontname="helv", color=(0.1, 0.2, 0.5))
        current_y += 14
        
        # Split body by lines or wrap
        lines = body.strip().split("\n")
        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue
            # Simple text wrap if too long
            while len(line_str) > 85:
                split_idx = line_str[:85].rfind(" ")
                if split_idx == -1:
                    split_idx = 85
                page.insert_text(pymupdf.Point(left_x + 5, current_y), line_str[:split_idx], fontsize=9.5, fontname="helv", color=(0.15, 0.15, 0.2))
                line_str = line_str[split_idx:].strip()
                current_y += 13
            if line_str:
                page.insert_text(pymupdf.Point(left_x + 5, current_y), line_str, fontsize=9.5, fontname="helv", color=(0.15, 0.15, 0.2))
                current_y += 13
        current_y += 10

    add_section("Professional Summary", summary)
    add_section("Technical Skills", ", ".join(skills))
    add_section("Work Experience", experience_text)
    add_section("Key Projects", projects_text)
    add_section("Education", education_text)
    add_section("Certifications", certs_text)

    doc.save(filepath)
    doc.close()


def generate_all_samples():
    """Build sample PDFs and populate SQLite demo database."""
    os.makedirs(SAMPLE_DIR, exist_ok=True)
    init_db()

    # Preloaded Job: Python Developer
    job_id = create_job(
        title="Python Developer",
        department="Engineering",
        description="We are seeking an experienced and passionate Python Developer to build high-concurrency backend microservices, develop scalable REST APIs with Flask and FastAPI, design relational schemas in PostgreSQL/SQL, and containerize services with Docker and Kubernetes for cloud deployment on AWS.",
        required_skills=["Python", "Flask", "SQL"],
        preferred_skills=["AWS", "Docker", "Kubernetes", "FastAPI"],
        min_experience=3.0
    )

    candidates_meta = [
        {
            "name": "Aarav Sharma",
            "title": "Senior Python Backend Engineer",
            "contact": "aarav.sharma@example.com | +1 (555) 234-5678 | San Francisco, CA",
            "summary": "Results-driven Software Engineer with 5.5 years of experience architecting high-performance backend systems in Python, Flask, and FastAPI. Deep expertise in SQL query optimization and AWS cloud microservices.",
            "skills": ["Python", "Flask", "FastAPI", "SQL", "PostgreSQL", "Docker", "AWS", "Git", "Redis", "REST APIs", "Microservices", "Linux"],
            "experience_years": 5.5,
            "experience_text": "Senior Backend Developer at CloudScale Technologies (2021 - Present) - 5.5 years experience\n- Engineered event-driven backend services handling 20,000 requests/sec using Python, Flask, and Redis.\n- Optimized complex SQL queries in PostgreSQL, reducing average query latency by 45%.\n- Deployed production microservices into AWS ECS and Docker containers.",
            "projects_text": "- Distributed Real-time Analytics Engine: Built using Python, FastAPI, SQL, and Redis caching.\n- Payment Gateway Integration: Created secure webhook processing system with 99.99% uptime.",
            "education_text": "Bachelor of Technology in Computer Science and Engineering | State University (GPA: 3.8/4.0)",
            "certs_text": "AWS Certified Solutions Architect, Python Certified Developer (PCAP)",
            "filename": "Aarav_Sharma_Python_Lead.pdf",
            "status": "Shortlisted"
        },
        {
            "name": "Sophia Chen",
            "title": "Full-Stack Python & Cloud Developer",
            "contact": "sophia.chen@techmail.com | +1 (555) 345-6789 | Seattle, WA",
            "summary": "Proactive Full-Stack Software Developer with 4 years of experience designing scalable RESTful APIs with Python, Flask, and SQL databases. Strong background in Docker containerization and Kubernetes orchestration on AWS.",
            "skills": ["Python", "Flask", "SQL", "Docker", "Kubernetes", "AWS", "JavaScript", "React", "CI/CD", "Git", "MongoDB", "REST APIs"],
            "experience_years": 4.0,
            "experience_text": "Full-Stack Developer at NexaCore Systems (2022 - Present) - 4 years total experience\n- Architected containerized Python web services using Flask and PostgreSQL database clusters.\n- Configured CI/CD automation pipelines for continuous deployment on Kubernetes and AWS EKS.\n- Collaborated with front-end teams to integrate React dashboards with secure API endpoints.",
            "projects_text": "- Cloud Resource Manager: Multi-tenant SaaS orchestration dashboard built with Python, Flask, and AWS.\n- Automated Pipeline Auditor: Streamlined code quality verification using Docker and GitHub Actions.",
            "education_text": "Bachelor of Science in Software Engineering | University of Washington (Graduated 2022)",
            "certs_text": "Docker Certified Associate (DCA), Certified Kubernetes Administrator (CKA)",
            "filename": "Sophia_Chen_Cloud_Python.pdf",
            "status": "Interview"
        },
        {
            "name": "Marcus Miller",
            "title": "Junior Python Web Developer",
            "contact": "marcus.miller@devmail.org | +1 (555) 456-7890 | Austin, TX",
            "summary": "Energetic Junior Developer with 1.5 years experience building lightweight web services using Python, Flask, and SQLite. Strong foundation in object-oriented programming, unit testing, and agile methodologies.",
            "skills": ["Python", "Flask", "SQL", "SQLite", "HTML", "CSS", "Git", "Linux", "REST APIs", "Unit Testing"],
            "experience_years": 1.5,
            "experience_text": "Junior Software Developer at SparkSoft Labs (2025 - Present) - 1.5 years experience\n- Developed internal inventory tracking web modules using Python and Flask framework.\n- Structured relational database models using SQLite and SQL schema migration tools.\n- Authored comprehensive unit tests with PyTest achieving 85% code coverage.",
            "projects_text": "- Task Management API: Built clean REST endpoints with Python and Flask.\n- Portfolio Analytics Portal: Interactive web dashboard powered by SQLite and Python scripts.",
            "education_text": "Bachelor of Science in Information Technology | Texas State University (2024)",
            "certs_text": "Python Institute Entry-Level Programmer (PCEP)",
            "filename": "Marcus_Miller_Junior_Python.pdf",
            "status": "New"
        },
        {
            "name": "Priya Patel",
            "title": "Data Analyst & Python Specialist",
            "contact": "priya.patel@datahub.net | +1 (555) 567-8901 | Chicago, IL",
            "summary": "Analytical Data Specialist with 3.2 years of experience analyzing enterprise datasets using Python, SQL, and Pandas. Proficient in statistical modeling, ETL data pipelines, and business intelligence reporting.",
            "skills": ["Python", "SQL", "Pandas", "NumPy", "Scikit-Learn", "Tableau", "Git", "PostgreSQL", "Machine Learning"],
            "experience_years": 3.2,
            "experience_text": "Data Analyst at Apex Global Analytics (2023 - Present) - 3.2 years experience\n- Formulated automated data cleaning and ETL transformation scripts with Python and Pandas.\n- Authored complex SQL aggregation queries across multi-million row relational data warehouses.\n- Generated predictive customer churn classification models with Scikit-Learn.",
            "projects_text": "- Customer Churn Predictor: Machine learning workflow in Python using Scikit-Learn.\n- Automated Financial ETL: Nightly scheduled data transformation jobs with SQL and Pandas.",
            "education_text": "Master of Science in Data Analytics | University of Illinois at Chicago (2023)",
            "certs_text": "Google Professional Data Engineer, SQL Specialist Certificate",
            "filename": "Priya_Patel_Data_Python.pdf",
            "status": "New"
        },
        {
            "name": "David Kim",
            "title": "Frontend UI/UX Specialist",
            "contact": "david.kim@designcode.io | +1 (555) 678-9012 | New York, NY",
            "summary": "Creative Frontend Engineer with 3 years experience creating responsive, accessible user interfaces with React, JavaScript, TypeScript, and modern CSS frameworks. Passionate about design systems and web performance.",
            "skills": ["JavaScript", "TypeScript", "React", "Next.js", "HTML", "CSS", "Tailwind CSS", "Git", "Figma", "UI/UX Design"],
            "experience_years": 3.0,
            "experience_text": "Frontend Developer at PixelCraft Digital (2023 - Present) - 3 years experience\n- Built component libraries and responsive web user interfaces in React and TypeScript.\n- Collaborated with UI designers in Figma to translate wireframes into interactive interfaces.\n- Optimized Core Web Vitals resulting in 40% improvement in mobile page load speeds.",
            "projects_text": "- E-Commerce Storefront: Interactive shopping cart and checkout UI in Next.js and Tailwind.\n- Design System UI Kit: Accessible React component library with 50+ reusable modules.",
            "education_text": "Bachelor of Fine Arts in Web Design & Interactive Media | NYU (2023)",
            "certs_text": "Meta Certified Front-End Developer",
            "filename": "David_Kim_Frontend_React.pdf",
            "status": "Rejected"
        },
        {
            "name": "Elena Rostova",
            "title": "Java Junior Developer",
            "contact": "elena.rostova@javalab.org | +1 (555) 789-0123 | Boston, MA",
            "summary": "Recent graduate and Junior Software Engineer with 0.5 years experience building enterprise Java applications with Spring Boot and MySQL. Motivated learner with strong object-oriented design and algorithm fundamentals.",
            "skills": ["Java", "Spring Boot", "MySQL", "C++", "Git", "OOP", "JUnit"],
            "experience_years": 0.5,
            "experience_text": "Software Engineering Trainee at Boston Software Academy (2026) - 0.5 years experience\n- Implemented RESTful microservices in Java with Spring Boot framework.\n- Executed SQL queries and database migrations with MySQL database.\n- Developed unit tests in JUnit and maintained version control workflows with Git.",
            "projects_text": "- Library Management System: Java Spring Boot application with MySQL storage.\n- Banking Console Simulator: Object-oriented banking system implementation in Java.",
            "education_text": "Bachelor of Science in Computer Science | Boston University (Graduated 2026)",
            "certs_text": "Oracle Certified Associate Java Programmer",
            "filename": "Elena_Rostova_Java_Junior.pdf",
            "status": "Rejected"
        }
    ]

    print("Generating sample resumes and preloading demo database...")

    from database import get_job_by_id
    job_record = get_job_by_id(job_id)

    for c in candidates_meta:
        pdf_path = os.path.join(SAMPLE_DIR, c["filename"])
        create_sample_pdf(
            filepath=pdf_path,
            name=c["name"],
            title=c["title"],
            contact_info=c["contact"],
            summary=c["summary"],
            skills=c["skills"],
            experience_text=c["experience_text"],
            education_text=c["education_text"],
            projects_text=c["projects_text"],
            certs_text=c["certs_text"]
        )

        # Parse generated PDF to ensure exact realistic extraction
        extracted_text = extract_text_from_pdf(pdf_path)
        parsed = parse_resume(extracted_text, filename=c["filename"])

        # Override with exact clean entities for perfect demo consistency
        cand_id = save_candidate(
            name=c["name"],
            email=c["contact"].split("|")[0].strip(),
            phone=c["contact"].split("|")[1].strip(),
            skills=c["skills"],
            experience_years=c["experience_years"],
            education=c["education_text"],
            projects=c["projects_text"],
            certifications=c["certs_text"],
            resume_filename=c["filename"],
            raw_text=extracted_text
        )

        # Run explainable recommendation matching against the preloaded job
        cand_dict = {
            "name": c["name"],
            "skills": c["skills"],
            "experience_years": c["experience_years"],
            "raw_text": extracted_text,
            "education": c["education_text"],
            "projects": c["projects_text"]
        }
        evaluation = evaluate_candidate(job_record, cand_dict)
        evaluation["status"] = c["status"]

        save_match_evaluation(job_id, cand_id, evaluation)

    log_activity("Demo Initialized", f"Preloaded 1 job opening and {len(candidates_meta)} synthetic candidate profiles.")
    print(f"Successfully created {len(candidates_meta)} sample PDF resumes and populated talentlens.db!")


if __name__ == "__main__":
    generate_all_samples()

"""
Template-based interview question generator.
Used as fallback when LLM is not configured.
"""
from typing import List


def generate_technical_questions(skills: List[str], missing_skills: List[str]) -> List[dict]:
    questions = []

    for skill in skills[:3]:
        questions.append({
            "category": "Technical",
            "question": f"Can you explain your experience with {skill} and describe a project where you used it effectively?",
            "rationale": f"Assess depth of {skill} knowledge and practical application"
        })

    for skill in missing_skills[:2]:
        questions.append({
            "category": "Technical",
            "question": f"This role requires {skill}. What is your familiarity with it, and how quickly do you think you could get up to speed?",
            "rationale": f"Assess candidate's awareness of gap in {skill} and learning ability"
        })

    return questions


def generate_conceptual_questions(job_title: str, required_skills: List[str]) -> List[dict]:
    questions = [
        {
            "category": "Conceptual",
            "question": f"How do you approach system design and architecture decisions in a {job_title} role?",
            "rationale": "Assess architectural thinking and design sensibility"
        },
        {
            "category": "Conceptual",
            "question": "Describe your process for debugging a complex technical issue. Walk me through a specific example.",
            "rationale": "Evaluate problem-solving methodology and debugging skills"
        },
        {
            "category": "Conceptual",
            "question": "How do you ensure code quality and maintainability in your projects?",
            "rationale": "Assess software engineering practices and quality mindset"
        },
    ]

    if required_skills:
        top_skill = required_skills[0]
        questions.append({
            "category": "Conceptual",
            "question": f"What are the key concepts in {top_skill} that you consider most important for this role?",
            "rationale": f"Test conceptual depth in primary required skill: {top_skill}"
        })

    return questions


def generate_project_questions(projects: List[dict]) -> List[dict]:
    questions = []

    if not projects:
        questions.append({
            "category": "Project-based",
            "question": "Describe the most technically challenging project you have worked on. What was your role and what were the key decisions you made?",
            "rationale": "Understand depth of technical experience through project discussion"
        })
        questions.append({
            "category": "Project-based",
            "question": "Tell me about a project where you had to learn a new technology under tight deadline. How did you manage it?",
            "rationale": "Assess learning agility and time management"
        })
        return questions

    for proj in projects[:2]:
        name = proj.get('name', 'your project')
        techs = ", ".join(proj.get('technologies', [])[:3])
        questions.append({
            "category": "Project-based",
            "question": f"Tell me more about your '{name}' project"
                        + (f" using {techs}" if techs else "")
                        + ". What were the main technical challenges and how did you solve them?",
            "rationale": f"Deep dive into candidate's actual project work and problem-solving"
        })

    return questions


def generate_problem_solving_questions(experience_years: float) -> List[dict]:
    questions = [
        {
            "category": "Problem-solving",
            "question": "You are given a large codebase that is performing poorly. Walk me through how you would identify and address the performance bottlenecks.",
            "rationale": "Assess systematic approach to performance engineering"
        },
        {
            "category": "Problem-solving",
            "question": "How do you handle disagreements with teammates about technical decisions? Give a specific example.",
            "rationale": "Evaluate collaboration, communication, and technical leadership"
        },
    ]

    if experience_years >= 3:
        questions.append({
            "category": "Problem-solving",
            "question": "Describe a situation where you had to make a critical technical decision with incomplete information. What was your process?",
            "rationale": "Assess decision-making under uncertainty for senior candidates"
        })
    else:
        questions.append({
            "category": "Problem-solving",
            "question": "How do you prioritize learning new skills while managing day-to-day development tasks?",
            "rationale": "Assess self-management and continuous learning for junior candidates"
        })

    return questions


def generate_interview_questions_template(
    job_title: str,
    required_skills: List[str],
    candidate_name: str,
    candidate_skills: List[str],
    candidate_projects: List[dict],
    experience_years: float,
    missing_skills: List[str],
) -> List[dict]:
    """
    Generate structured interview questions using templates.
    No LLM required.
    """
    all_questions = []

    # Technical questions based on skills
    all_questions.extend(generate_technical_questions(candidate_skills, missing_skills))

    # Conceptual questions
    all_questions.extend(generate_conceptual_questions(job_title, required_skills))

    # Project-based questions
    all_questions.extend(generate_project_questions(candidate_projects))

    # Problem-solving questions
    all_questions.extend(generate_problem_solving_questions(experience_years))

    # Deduplicate and limit
    seen = set()
    unique_questions = []
    for q in all_questions:
        key = q['question'][:50]
        if key not in seen:
            seen.add(key)
            unique_questions.append(q)

    return unique_questions[:12]

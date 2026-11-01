"""
Skill normalization module.
Maps abbreviations and variations to canonical skill names.
"""

# Canonical skill name mappings
SKILL_ALIASES = {
    # Programming Languages
    "js": "JavaScript",
    "javascript": "JavaScript",
    "ts": "TypeScript",
    "typescript": "TypeScript",
    "py": "Python",
    "python": "Python",
    "java": "Java",
    "cpp": "C++",
    "c++": "C++",
    "csharp": "C#",
    "c#": "C#",
    "rb": "Ruby",
    "ruby": "Ruby",
    "go": "Go",
    "golang": "Go",
    "rs": "Rust",
    "rust": "Rust",
    "php": "PHP",
    "swift": "Swift",
    "kotlin": "Kotlin",
    "scala": "Scala",
    "r": "R",
    "matlab": "MATLAB",
    "sql": "SQL",
    "nosql": "NoSQL",
    "html": "HTML",
    "css": "CSS",
    "html/css": "HTML/CSS",

    # AI/ML
    "ml": "Machine Learning",
    "machine learning": "Machine Learning",
    "dl": "Deep Learning",
    "deep learning": "Deep Learning",
    "ai": "Artificial Intelligence",
    "nlp": "Natural Language Processing",
    "natural language processing": "Natural Language Processing",
    "cv": "Computer Vision",
    "computer vision": "Computer Vision",
    "rl": "Reinforcement Learning",
    "gan": "Generative Adversarial Networks",
    "llm": "Large Language Models",
    "genai": "Generative AI",
    "gen ai": "Generative AI",

    # Frameworks
    "tf": "TensorFlow",
    "tensorflow": "TensorFlow",
    "pt": "PyTorch",
    "pytorch": "PyTorch",
    "sk-learn": "scikit-learn",
    "sklearn": "scikit-learn",
    "scikit learn": "scikit-learn",
    "keras": "Keras",
    "huggingface": "HuggingFace",
    "hf": "HuggingFace",

    # Web Frameworks
    "react": "React",
    "reactjs": "React",
    "react.js": "React",
    "vue": "Vue.js",
    "vuejs": "Vue.js",
    "angular": "Angular",
    "angularjs": "Angular",
    "nextjs": "Next.js",
    "next.js": "Next.js",
    "django": "Django",
    "flask": "Flask",
    "fastapi": "FastAPI",
    "spring": "Spring",
    "springboot": "Spring Boot",
    "spring boot": "Spring Boot",
    "express": "Express.js",
    "expressjs": "Express.js",
    "node": "Node.js",
    "nodejs": "Node.js",
    "node.js": "Node.js",

    # Cloud & DevOps
    "aws": "AWS",
    "amazon web services": "AWS",
    "gcp": "Google Cloud Platform",
    "google cloud": "Google Cloud Platform",
    "azure": "Microsoft Azure",
    "ms azure": "Microsoft Azure",
    "k8s": "Kubernetes",
    "kubernetes": "Kubernetes",
    "docker": "Docker",
    "ci/cd": "CI/CD",
    "cicd": "CI/CD",
    "devops": "DevOps",
    "mlops": "MLOps",

    # Databases
    "pg": "PostgreSQL",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "mysql": "MySQL",
    "mongo": "MongoDB",
    "mongodb": "MongoDB",
    "redis": "Redis",
    "elasticsearch": "Elasticsearch",
    "es": "Elasticsearch",

    # CS Fundamentals
    "dsa": "Data Structures and Algorithms",
    "ds": "Data Structures",
    "algo": "Algorithms",
    "os": "Operating Systems",
    "dbms": "Database Management Systems",
    "oops": "Object-Oriented Programming",
    "oop": "Object-Oriented Programming",
    "object oriented programming": "Object-Oriented Programming",

    # Tools
    "git": "Git",
    "github": "GitHub",
    "gitlab": "GitLab",
    "jira": "Jira",
    "linux": "Linux",
    "bash": "Bash",
    "shell": "Shell Scripting",

    # Data
    "pandas": "Pandas",
    "numpy": "NumPy",
    "spark": "Apache Spark",
    "hadoop": "Hadoop",
    "tableau": "Tableau",
    "powerbi": "Power BI",
    "power bi": "Power BI",
    "etl": "ETL",
    "bi": "Business Intelligence",
}

# Skills to always keep as-is (already normalized)
ALWAYS_KEEP = {
    "JavaScript", "TypeScript", "Python", "Java", "C++", "C#", "Ruby", "Go",
    "Rust", "PHP", "Swift", "Kotlin", "Scala", "R", "MATLAB", "SQL", "NoSQL",
    "HTML", "CSS", "Machine Learning", "Deep Learning", "Artificial Intelligence",
    "Natural Language Processing", "Computer Vision", "TensorFlow", "PyTorch",
    "React", "Vue.js", "Angular", "Next.js", "Django", "Flask", "FastAPI",
    "AWS", "Google Cloud Platform", "Microsoft Azure", "Kubernetes", "Docker",
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "Git", "GitHub", "Linux",
    "Data Structures and Algorithms",
}

# Common technical skill keywords (for extraction)
SKILL_KEYWORDS = set([
    # Languages
    "python", "java", "javascript", "typescript", "c++", "c#", "ruby", "go", "golang",
    "rust", "php", "swift", "kotlin", "scala", "r", "matlab", "sql", "nosql",
    "html", "css", "bash", "shell", "perl", "dart", "elixir", "haskell",
    # Frameworks
    "react", "angular", "vue", "nextjs", "django", "flask", "fastapi", "spring",
    "express", "nodejs", "laravel", "rails", "gatsby", "svelte",
    # ML/AI
    "tensorflow", "pytorch", "keras", "sklearn", "scikit-learn", "huggingface",
    "transformers", "bert", "gpt", "llm", "nlp", "computer vision", "opencv",
    # Cloud
    "aws", "azure", "gcp", "google cloud", "heroku", "vercel", "netlify",
    "kubernetes", "docker", "terraform", "ansible", "jenkins", "github actions",
    # Databases
    "postgresql", "mysql", "mongodb", "redis", "elasticsearch", "cassandra",
    "sqlite", "oracle", "dynamodb", "firebase", "supabase",
    # Tools
    "git", "github", "gitlab", "jira", "confluence", "linux", "unix",
    # Data
    "pandas", "numpy", "spark", "hadoop", "tableau", "powerbi", "airflow",
    # CS
    "dsa", "data structures", "algorithms", "machine learning", "deep learning",
    "artificial intelligence", "devops", "mlops", "ci/cd", "agile", "scrum",
])


def normalize_skill(skill: str) -> str:
    """
    Normalize a skill string to its canonical form.
    Returns the normalized skill or the original (title-cased) if no alias found.
    """
    if not skill or not skill.strip():
        return skill

    cleaned = skill.strip()
    lower = cleaned.lower()

    # Direct alias lookup
    if lower in SKILL_ALIASES:
        return SKILL_ALIASES[lower]

    # Check if already canonical
    if cleaned in ALWAYS_KEEP:
        return cleaned

    # Return title-cased version for unknown skills
    return cleaned.title() if len(cleaned) > 2 else cleaned.upper()


def normalize_skills_list(skills: list) -> list:
    """Normalize a list of skills and deduplicate."""
    normalized = []
    seen = set()
    for skill in skills:
        n = normalize_skill(str(skill))
        if n and n.lower() not in seen:
            seen.add(n.lower())
            normalized.append(n)
    return normalized


def skills_match(candidate_skill: str, job_skill: str) -> bool:
    """
    Check if a candidate skill matches a job requirement.
    Uses normalized forms for comparison.
    """
    cn = normalize_skill(candidate_skill).lower()
    jn = normalize_skill(job_skill).lower()

    # Exact match after normalization
    if cn == jn:
        return True

    # Substring match (e.g., "React" matches "React.js")
    if cn in jn or jn in cn:
        return True

    return False


def find_matched_skills(candidate_skills: list, job_skills: list) -> tuple:
    """
    Return (matched, missing) for candidate vs job skill lists.
    """
    matched = []
    missing = []
    for job_skill in job_skills:
        found = False
        for cand_skill in candidate_skills:
            if skills_match(cand_skill, job_skill):
                matched.append(job_skill)
                found = True
                break
        if not found:
            missing.append(job_skill)
    return matched, missing

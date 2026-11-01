"""
TalentLens - Database Management Module
Handles SQLite schema, connection lifecycle, CRUD operations, and state persistence.
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_FILE = "talentlens.db"


def get_connection():
    """Establish and return a connection to the SQLite database with Row factory."""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database tables with constraints and indexes."""
    conn = get_connection()
    cursor = conn.cursor()

    # Jobs Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        department TEXT NOT NULL,
        description TEXT NOT NULL,
        required_skills TEXT NOT NULL, -- JSON string
        preferred_skills TEXT NOT NULL, -- JSON string
        min_experience REAL NOT NULL DEFAULT 0.0,
        is_active INTEGER DEFAULT 1,
        created_at TEXT NOT NULL
    )
    """)

    # Candidates Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS candidates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT,
        phone TEXT,
        skills TEXT NOT NULL, -- JSON string
        experience_years REAL DEFAULT 0.0,
        education TEXT,
        projects TEXT,
        certifications TEXT,
        resume_filename TEXT,
        raw_text TEXT,
        created_at TEXT NOT NULL
    )
    """)

    # Matches / Candidate Evaluation Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER NOT NULL,
        candidate_id INTEGER NOT NULL,
        overall_score REAL NOT NULL,
        required_match_score REAL NOT NULL,
        tfidf_score REAL NOT NULL,
        preferred_match_score REAL NOT NULL,
        experience_score REAL NOT NULL,
        category TEXT NOT NULL, -- 'Strong', 'Moderate', 'Low'
        matched_required_skills TEXT, -- JSON string
        matched_preferred_skills TEXT, -- JSON string
        missing_skills TEXT, -- JSON string
        strengths TEXT, -- JSON string
        areas_for_evaluation TEXT, -- JSON string
        status TEXT DEFAULT 'New', -- 'New', 'Shortlisted', 'Interview', 'Offer', 'Rejected'
        evaluated_at TEXT NOT NULL,
        FOREIGN KEY (job_id) REFERENCES jobs (id) ON DELETE CASCADE,
        FOREIGN KEY (candidate_id) REFERENCES candidates (id) ON DELETE CASCADE,
        UNIQUE (job_id, candidate_id)
    )
    """)

    # Activity Log Table for Recruiter Dashboard
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS activity_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action TEXT NOT NULL,
        details TEXT NOT NULL,
        timestamp TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()


def log_activity(action: str, details: str):
    """Log an activity event for the recruiter audit trail."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO activity_log (action, details, timestamp) VALUES (?, ?, ?)",
            (action, details, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        conn.commit()
    finally:
        conn.close()


def get_recent_activity(limit: int = 10) -> List[Dict[str, Any]]:
    """Retrieve recent recruiter activities."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT action, details, timestamp FROM activity_log ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


# ---------------- JOB OPERATIONS ----------------

def create_job(title: str, department: str, description: str,
               required_skills: List[str], preferred_skills: List[str],
               min_experience: float) -> int:
    """Create a new job posting."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO jobs (title, department, description, required_skills, preferred_skills, min_experience, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            title.strip(),
            department.strip(),
            description.strip(),
            json.dumps([s.strip() for s in required_skills if s.strip()]),
            json.dumps([s.strip() for s in preferred_skills if s.strip()]),
            float(min_experience),
            now
        ))
        conn.commit()
        job_id = cursor.lastrowid
        log_activity("Job Created", f"Created job opening '{title}' in {department}")
        return job_id
    finally:
        conn.close()


def get_all_jobs() -> List[Dict[str, Any]]:
    """Fetch all jobs."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM jobs ORDER BY id DESC")
        rows = cursor.fetchall()
        jobs = []
        for r in rows:
            d = dict(r)
            d["required_skills"] = json.loads(d["required_skills"]) if d["required_skills"] else []
            d["preferred_skills"] = json.loads(d["preferred_skills"]) if d["preferred_skills"] else []
            jobs.append(d)
        return jobs
    finally:
        conn.close()


def get_job_by_id(job_id: int) -> Optional[Dict[str, Any]]:
    """Fetch single job by its ID."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        row = cursor.fetchone()
        if not row:
            return None
        d = dict(row)
        d["required_skills"] = json.loads(d["required_skills"]) if d["required_skills"] else []
        d["preferred_skills"] = json.loads(d["preferred_skills"]) if d["preferred_skills"] else []
        return d
    finally:
        conn.close()


# ---------------- CANDIDATE OPERATIONS ----------------

def save_candidate(name: str, email: str, phone: str, skills: List[str],
                   experience_years: float, education: str, projects: str,
                   certifications: str, resume_filename: str, raw_text: str) -> int:
    """Save parsed candidate into the database, avoiding exact email duplicates."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Check existing by email if available, or by name + resume_filename
        if email and email.strip():
            cursor.execute("SELECT id FROM candidates WHERE email = ?", (email.strip().lower(),))
            existing = cursor.fetchone()
            if existing:
                candidate_id = existing["id"]
                # Update candidate information
                cursor.execute("""
                    UPDATE candidates
                    SET name = ?, phone = ?, skills = ?, experience_years = ?, education = ?,
                        projects = ?, certifications = ?, resume_filename = ?, raw_text = ?
                    WHERE id = ?
                """, (
                    name.strip(), phone.strip(), json.dumps(skills),
                    float(experience_years), education.strip(), projects.strip(),
                    certifications.strip(), resume_filename, raw_text, candidate_id
                ))
                conn.commit()
                log_activity("Candidate Updated", f"Updated details for candidate {name} ({email})")
                return candidate_id

        cursor.execute("""
            INSERT INTO candidates (name, email, phone, skills, experience_years, education, projects, certifications, resume_filename, raw_text, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            name.strip(),
            email.strip().lower() if email else "",
            phone.strip() if phone else "",
            json.dumps(skills),
            float(experience_years),
            education.strip() if education else "Not Specified",
            projects.strip() if projects else "Not Specified",
            certifications.strip() if certifications else "None",
            resume_filename,
            raw_text,
            now
        ))
        conn.commit()
        cand_id = cursor.lastrowid
        log_activity("Candidate Ingested", f"Added candidate {name} from resume {resume_filename}")
        return cand_id
    finally:
        conn.close()


def get_all_candidates() -> List[Dict[str, Any]]:
    """Retrieve all candidates."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM candidates ORDER BY id DESC")
        rows = cursor.fetchall()
        candidates = []
        for r in rows:
            d = dict(r)
            d["skills"] = json.loads(d["skills"]) if d["skills"] else []
            candidates.append(d)
        return candidates
    finally:
        conn.close()


def get_candidate_by_id(candidate_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve single candidate by ID."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM candidates WHERE id = ?", (candidate_id,))
        row = cursor.fetchone()
        if not row:
            return None
        d = dict(row)
        d["skills"] = json.loads(d["skills"]) if d["skills"] else []
        return d
    finally:
        conn.close()


# ---------------- MATCH EVALUATION OPERATIONS ----------------

def save_match_evaluation(job_id: int, candidate_id: int, match_data: Dict[str, Any]) -> int:
    """Store or update candidate evaluation score breakdown."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            INSERT INTO matches (
                job_id, candidate_id, overall_score, required_match_score,
                tfidf_score, preferred_match_score, experience_score, category,
                matched_required_skills, matched_preferred_skills, missing_skills,
                strengths, areas_for_evaluation, status, evaluated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_id, candidate_id) DO UPDATE SET
                overall_score = excluded.overall_score,
                required_match_score = excluded.required_match_score,
                tfidf_score = excluded.tfidf_score,
                preferred_match_score = excluded.preferred_match_score,
                experience_score = excluded.experience_score,
                category = excluded.category,
                matched_required_skills = excluded.matched_required_skills,
                matched_preferred_skills = excluded.matched_preferred_skills,
                missing_skills = excluded.missing_skills,
                strengths = excluded.strengths,
                areas_for_evaluation = excluded.areas_for_evaluation,
                evaluated_at = excluded.evaluated_at
        """, (
            job_id,
            candidate_id,
            match_data["overall_score"],
            match_data["required_match_score"],
            match_data["tfidf_score"],
            match_data["preferred_match_score"],
            match_data["experience_score"],
            match_data["category"],
            json.dumps(match_data.get("matched_required_skills", [])),
            json.dumps(match_data.get("matched_preferred_skills", [])),
            json.dumps(match_data.get("missing_skills", [])),
            json.dumps(match_data.get("strengths", [])),
            json.dumps(match_data.get("areas_for_evaluation", [])),
            match_data.get("status", "New"),
            now
        ))
        conn.commit()
        match_id = cursor.lastrowid
        return match_id
    finally:
        conn.close()


def get_matches_for_job(job_id: int) -> List[Dict[str, Any]]:
    """Fetch ranked candidate matches for a particular job with combined details."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                m.id AS match_id,
                m.job_id,
                m.candidate_id,
                m.overall_score,
                m.required_match_score,
                m.tfidf_score,
                m.preferred_match_score,
                m.experience_score,
                m.category,
                m.matched_required_skills,
                m.matched_preferred_skills,
                m.missing_skills,
                m.strengths,
                m.areas_for_evaluation,
                m.status,
                m.evaluated_at,
                c.name,
                c.email,
                c.phone,
                c.skills,
                c.experience_years,
                c.education,
                c.projects,
                c.certifications,
                c.resume_filename,
                c.raw_text
            FROM matches m
            JOIN candidates c ON m.candidate_id = c.id
            WHERE m.job_id = ?
            ORDER BY m.overall_score DESC, c.experience_years DESC
        """, (job_id,))
        rows = cursor.fetchall()
        matches = []
        for r in rows:
            d = dict(r)
            d["skills"] = json.loads(d["skills"]) if d["skills"] else []
            d["matched_required_skills"] = json.loads(d["matched_required_skills"]) if d["matched_required_skills"] else []
            d["matched_preferred_skills"] = json.loads(d["matched_preferred_skills"]) if d["matched_preferred_skills"] else []
            d["missing_skills"] = json.loads(d["missing_skills"]) if d["missing_skills"] else []
            d["strengths"] = json.loads(d["strengths"]) if d["strengths"] else []
            d["areas_for_evaluation"] = json.loads(d["areas_for_evaluation"]) if d["areas_for_evaluation"] else []
            matches.append(d)
        return matches
    finally:
        conn.close()


def get_match_by_candidate_and_job(job_id: int, candidate_id: int) -> Optional[Dict[str, Any]]:
    """Fetch single evaluation record for a candidate and job."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                m.*,
                c.name, c.email, c.phone, c.skills, c.experience_years,
                c.education, c.projects, c.certifications, c.resume_filename, c.raw_text
            FROM matches m
            JOIN candidates c ON m.candidate_id = c.id
            WHERE m.job_id = ? AND m.candidate_id = ?
        """, (job_id, candidate_id))
        r = cursor.fetchone()
        if not r:
            return None
        d = dict(r)
        d["skills"] = json.loads(d["skills"]) if d["skills"] else []
        d["matched_required_skills"] = json.loads(d["matched_required_skills"]) if d["matched_required_skills"] else []
        d["matched_preferred_skills"] = json.loads(d["matched_preferred_skills"]) if d["matched_preferred_skills"] else []
        d["missing_skills"] = json.loads(d["missing_skills"]) if d["missing_skills"] else []
        d["strengths"] = json.loads(d["strengths"]) if d["strengths"] else []
        d["areas_for_evaluation"] = json.loads(d["areas_for_evaluation"]) if d["areas_for_evaluation"] else []
        return d
    finally:
        conn.close()


def update_candidate_status(job_id: int, candidate_id: int, new_status: str):
    """Update pipeline status of candidate (New, Shortlisted, Interview, Offer, Rejected)."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE matches
            SET status = ?
            WHERE job_id = ? AND candidate_id = ?
        """, (new_status, job_id, candidate_id))
        conn.commit()

        # Log this pipeline transition
        cursor.execute("SELECT name FROM candidates WHERE id = ?", (candidate_id,))
        cand_row = cursor.fetchone()
        name = cand_row["name"] if cand_row else f"Candidate #{candidate_id}"
        log_activity("Pipeline Update", f"Moved {name} to stage '{new_status}'")
    finally:
        conn.close()


def get_dashboard_metrics(job_id: Optional[int] = None) -> Dict[str, Any]:
    """Calculate dashboard KPI metrics and pipeline distribution."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # Total Candidates
        cursor.execute("SELECT COUNT(*) AS total FROM candidates")
        total_candidates = cursor.fetchone()["total"]

        # Active Jobs
        cursor.execute("SELECT COUNT(*) AS total FROM jobs WHERE is_active = 1")
        active_jobs = cursor.fetchone()["total"]

        # Shortlisted & Awaiting Evaluation
        if job_id:
            cursor.execute("SELECT COUNT(*) AS total FROM matches WHERE job_id = ? AND status = 'Shortlisted'", (job_id,))
            shortlisted = cursor.fetchone()["total"]
            
            cursor.execute("SELECT COUNT(*) AS total FROM matches WHERE job_id = ? AND status = 'New'", (job_id,))
            awaiting = cursor.fetchone()["total"]

            cursor.execute("SELECT category, COUNT(*) as count FROM matches WHERE job_id = ? GROUP BY category", (job_id,))
            categories = {r["category"]: r["count"] for r in cursor.fetchall()}

            cursor.execute("SELECT status, COUNT(*) as count FROM matches WHERE job_id = ? GROUP BY status", (job_id,))
            pipeline = {r["status"]: r["count"] for r in cursor.fetchall()}
        else:
            cursor.execute("SELECT COUNT(*) AS total FROM matches WHERE status = 'Shortlisted'")
            shortlisted = cursor.fetchone()["total"]
            
            cursor.execute("SELECT COUNT(*) AS total FROM matches WHERE status = 'New'")
            awaiting = cursor.fetchone()["total"]

            cursor.execute("SELECT category, COUNT(*) as count FROM matches GROUP BY category")
            categories = {r["category"]: r["count"] for r in cursor.fetchall()}

            cursor.execute("SELECT status, COUNT(*) as count FROM matches GROUP BY status")
            pipeline = {r["status"]: r["count"] for r in cursor.fetchall()}

        return {
            "total_candidates": total_candidates,
            "active_jobs": active_jobs,
            "shortlisted": shortlisted,
            "awaiting": awaiting,
            "categories": categories,
            "pipeline": pipeline
        }
    finally:
        conn.close()


def reset_database():
    """Wipe database and reset to pristine schema."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS matches")
        cursor.execute("DROP TABLE IF EXISTS candidates")
        cursor.execute("DROP TABLE IF EXISTS jobs")
        cursor.execute("DROP TABLE IF EXISTS activity_log")
        conn.commit()
    finally:
        conn.close()
    init_db()
    log_activity("System Reset", "Database cleared and re-initialized.")

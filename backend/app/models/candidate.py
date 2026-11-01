from sqlalchemy import (
    Column, Integer, String, DateTime, Float, Text, JSON, ForeignKey, Boolean
)
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.session import Base


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    recruiter_id = Column(Integer, ForeignKey("recruiters.id"), nullable=False)

    # Personal Info
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(50), nullable=True)
    linkedin = Column(String(500), nullable=True)
    github = Column(String(500), nullable=True)
    location = Column(String(255), nullable=True)
    summary = Column(Text, nullable=True)

    # Extracted data
    technical_skills = Column(JSON, default=list)       # List[str]
    programming_languages = Column(JSON, default=list)  # List[str]
    certifications = Column(JSON, default=list)         # List[str]
    projects = Column(JSON, default=list)               # List[dict]

    # Years of experience (calculated)
    total_experience_years = Column(Float, default=0)

    # Flags
    is_verified = Column(Boolean, default=False)
    extraction_confidence = Column(Float, default=0.5)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    skills = relationship("CandidateSkill", back_populates="candidate", cascade="all, delete-orphan")
    education = relationship("CandidateEducation", back_populates="candidate", cascade="all, delete-orphan")
    experience = relationship("CandidateExperience", back_populates="candidate", cascade="all, delete-orphan")
    resumes = relationship("Resume", back_populates="candidate", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="candidate", cascade="all, delete-orphan")
    match_results = relationship("MatchResult", back_populates="candidate", cascade="all, delete-orphan")


class CandidateSkill(Base):
    __tablename__ = "candidate_skills"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    skill = Column(String(255), nullable=False)
    skill_type = Column(String(50), default="technical")  # technical, soft, language, tool
    proficiency = Column(String(50), nullable=True)  # beginner, intermediate, advanced
    is_verified = Column(Boolean, default=False)

    candidate = relationship("Candidate", back_populates="skills")


class CandidateEducation(Base):
    __tablename__ = "candidate_education"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    degree = Column(String(255), nullable=True)
    field_of_study = Column(String(255), nullable=True)
    institution = Column(String(255), nullable=True)
    start_year = Column(Integer, nullable=True)
    end_year = Column(Integer, nullable=True)
    gpa = Column(Float, nullable=True)
    is_current = Column(Boolean, default=False)

    candidate = relationship("Candidate", back_populates="education")


class CandidateExperience(Base):
    __tablename__ = "candidate_experience"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    title = Column(String(255), nullable=True)
    company = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    start_date = Column(String(50), nullable=True)
    end_date = Column(String(50), nullable=True)
    is_current = Column(Boolean, default=False)
    description = Column(Text, nullable=True)
    duration_months = Column(Integer, default=0)
    is_internship = Column(Boolean, default=False)

    candidate = relationship("Candidate", back_populates="experience")

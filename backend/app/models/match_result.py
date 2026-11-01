from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, JSON, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.session import Base


class MatchResult(Base):
    __tablename__ = "match_results"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)

    # Scores (0-1 normalized, stored as percentage 0-100)
    overall_score = Column(Float, default=0)
    required_skills_score = Column(Float, default=0)
    preferred_skills_score = Column(Float, default=0)
    experience_score = Column(Float, default=0)
    education_score = Column(Float, default=0)
    project_relevance_score = Column(Float, default=0)
    semantic_similarity_score = Column(Float, default=0)

    # Detail data
    matched_required_skills = Column(JSON, default=list)
    missing_required_skills = Column(JSON, default=list)
    matched_preferred_skills = Column(JSON, default=list)
    missing_preferred_skills = Column(JSON, default=list)

    # Eligibility
    is_eligible = Column(Boolean, default=True)
    eligibility_failures = Column(JSON, default=list)

    # Status
    recommendation_status = Column(String(50), default="pending")
    # pending, recommended, consider, not_recommended

    computed_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("Job", back_populates="match_results")
    candidate = relationship("Candidate", back_populates="match_results")
    explanation = relationship("MatchExplanation", back_populates="match_result", uselist=False, cascade="all, delete-orphan")


class MatchExplanation(Base):
    __tablename__ = "match_explanations"

    id = Column(Integer, primary_key=True, index=True)
    match_result_id = Column(Integer, ForeignKey("match_results.id"), nullable=False)

    strengths = Column(JSON, default=list)
    weaknesses = Column(JSON, default=list)
    suggestions = Column(JSON, default=list)
    summary_text = Column(Text, nullable=True)
    generated_by = Column(String(50), default="rule_based")  # rule_based or llm

    match_result = relationship("MatchResult", back_populates="explanation")

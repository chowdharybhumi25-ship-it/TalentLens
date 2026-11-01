from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean, Text, JSON, Float, ForeignKey
)
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.session import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    recruiter_id = Column(Integer, ForeignKey("recruiters.id"), nullable=False)
    title = Column(String(255), nullable=False)
    company = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    required_skills = Column(JSON, default=list)        # List[str]
    preferred_skills = Column(JSON, default=list)       # List[str]
    min_experience = Column(Float, default=0)
    max_experience = Column(Float, nullable=True)
    education_requirements = Column(JSON, default=list) # List[str]
    employment_type = Column(String(100), default="Full-time")
    location = Column(String(255), nullable=True)
    mandatory_requirements = Column(JSON, default=list) # List[str]
    responsibilities = Column(JSON, default=list)       # List[str]
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Parsed JD data
    parsed_data = Column(JSON, nullable=True)

    # Relationships
    recruiter = relationship("Recruiter", back_populates="jobs")
    applications = relationship("Application", back_populates="job", cascade="all, delete-orphan")
    match_results = relationship("MatchResult", back_populates="job", cascade="all, delete-orphan")

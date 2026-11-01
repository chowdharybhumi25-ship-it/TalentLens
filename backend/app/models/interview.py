from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.session import Base


class InterviewQuestion(Base):
    __tablename__ = "interview_questions"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)

    questions = Column(JSON, default=list)
    # List[{category: str, question: str, rationale: str}]

    generated_by = Column(String(50), default="template")  # template or llm
    created_at = Column(DateTime, default=datetime.utcnow)

# Import all models here so SQLAlchemy discovers them
from app.models.recruiter import Recruiter  # noqa
from app.models.job import Job  # noqa
from app.models.candidate import (  # noqa
    Candidate,
    CandidateSkill,
    CandidateEducation,
    CandidateExperience,
)
from app.models.resume import Resume  # noqa
from app.models.application import Application  # noqa
from app.models.match_result import MatchResult, MatchExplanation  # noqa
from app.models.interview import InterviewQuestion  # noqa

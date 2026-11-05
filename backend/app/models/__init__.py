"""SQLAlchemy tables, grouped by domain. Importing the package registers every table in Base.metadata."""

from ._ids import uid
from .accounts import AuthAttempt, AuthSession, RecoveryToken, User
from .content import CanonicalQuestion, Exam, QuestionVersion, Review
from .diagnostics import DiagnosticSession, RecommendationEvent
from .runs import ExamRun, LearningEvent

__all__ = [
    "AuthAttempt",
    "AuthSession",
    "CanonicalQuestion",
    "DiagnosticSession",
    "Exam",
    "ExamRun",
    "LearningEvent",
    "QuestionVersion",
    "RecommendationEvent",
    "RecoveryToken",
    "Review",
    "User",
    "uid",
]

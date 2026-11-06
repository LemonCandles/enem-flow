"""SQLAlchemy tables, grouped by domain. Importing the package registers every table in Base.metadata."""

from ._ids import uid
from .accounts import AuthAttempt, AuthSession, RecoveryToken, User
from .content import CanonicalQuestion, Exam, QuestionVersion, Review
from .diagnostics import DiagnosticSession, RecommendationEvent
from .runs import ExamRun, LearningEvent
from .tutor import HelpEvent, TutorMaterial

__all__ = [
    "AuthAttempt",
    "AuthSession",
    "CanonicalQuestion",
    "DiagnosticSession",
    "Exam",
    "ExamRun",
    "HelpEvent",
    "LearningEvent",
    "QuestionVersion",
    "RecommendationEvent",
    "RecoveryToken",
    "Review",
    "TutorMaterial",
    "User",
    "uid",
]

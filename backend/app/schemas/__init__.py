"""Request schemas, grouped by feature. The package exports every schema, so `backend.app.schemas` stays the import path of the JSON contract."""
from .base import Schema
from .account import Login, Preferences, Register, ResetPassword
from .content import Alternative, Asset, ContentBlock, ExamImport, ImageBlock, ImportQuestion, Labels, MathBlock, ParagraphBlock, QuestionContent, Source, TableBlock
from .runs import Answer, StartRun
from .curation import EditQuestion, ReviewRequest

__all__ = ["Alternative", "Answer", "Asset", "ContentBlock", "EditQuestion", "ExamImport", "ImageBlock", "ImportQuestion", "Labels", "Login", "MathBlock", "ParagraphBlock", "Preferences", "QuestionContent", "Register", "ResetPassword", "ReviewRequest", "Schema", "Source", "StartRun", "TableBlock"]

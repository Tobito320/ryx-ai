"""
RyxHub Exam System - Database Package
"""

from .connection import (
    engine,
    SessionLocal,
    get_db,
    get_db_context,
    init_db,
    drop_db,
    check_db_health,
    get_or_create,
)

from .models import (
    Base,
    School,
    Subject,
    Teacher,
    Thema,
    ClassTest,
    MockExam,
    Attempt,
    GradingResult,
    UploadSession,
    TeacherPattern,
)

__all__ = [
    # Connection
    "engine",
    "SessionLocal",
    "get_db",
    "get_db_context",
    "init_db",
    "drop_db",
    "check_db_health",
    "get_or_create",
    # Models
    "Base",
    "School",
    "Subject",
    "Teacher",
    "Thema",
    "ClassTest",
    "MockExam",
    "Attempt",
    "GradingResult",
    "UploadSession",
    "TeacherPattern",
]

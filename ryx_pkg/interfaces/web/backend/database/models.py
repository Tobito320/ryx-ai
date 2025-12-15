"""
RyxHub Exam System - SQLAlchemy ORM Models
Version: 1.0.0
Created based on RYXHUB_AUDIT_REPORT.json P1.2 fix
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
import uuid

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text, BigInteger,
    ForeignKey, ARRAY, JSON, Date, Index, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


# ============================================================================
# SCHOOLS & SUBJECTS
# ============================================================================

class School(Base):
    """School entity - e.g., Cuno Berufskolleg Hagen"""
    __tablename__ = "schools"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    location = Column(String(255))
    country = Column(String(100), default="Germany")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    subjects = relationship("Subject", back_populates="school", cascade="all, delete-orphan")
    teachers = relationship("Teacher", back_populates="school")

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name,
            "location": self.location,
            "country": self.country,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Subject(Base):
    """Subject entity - e.g., WBL, IT Service, Deutsch"""
    __tablename__ = "subjects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id = Column(UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)  # "WBL", "IT Service"
    full_name = Column(String(255))              # "Wirtschaft und Betriebslehre"
    lernfeld = Column(Integer)                   # Learning field number (IHK)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    school = relationship("School", back_populates="subjects")
    themas = relationship("Thema", back_populates="subject", cascade="all, delete-orphan")
    class_tests = relationship("ClassTest", back_populates="subject")
    mock_exams = relationship("MockExam", back_populates="subject")

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "school_id": str(self.school_id),
            "name": self.name,
            "full_name": self.full_name,
            "lernfeld": self.lernfeld,
        }


class Teacher(Base):
    """Teacher entity - e.g., Herr Hakim"""
    __tablename__ = "teachers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id = Column(UUID(as_uuid=True), ForeignKey("schools.id", ondelete="SET NULL"))
    name = Column(String(255), nullable=False)
    email = Column(String(255))
    subject_ids = Column(ARRAY(Text))             # Array of subject IDs
    tests_count = Column(Integer, default=0)
    pattern_learned = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    school = relationship("School", back_populates="teachers")
    class_tests = relationship("ClassTest", back_populates="teacher")
    patterns = relationship("TeacherPattern", back_populates="teacher", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "school_id": str(self.school_id) if self.school_id else None,
            "name": self.name,
            "email": self.email,
            "subject_ids": self.subject_ids or [],
            "tests_count": self.tests_count,
            "pattern_learned": self.pattern_learned,
        }


class Thema(Base):
    """Thema/Topic entity - e.g., Marktforschung, Ticketprozess"""
    __tablename__ = "themas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subject_id = Column(UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    subtopics = Column(ARRAY(Text))
    frequency = Column(Integer, default=0)        # How often this thema appears
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    subject = relationship("Subject", back_populates="themas")

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "subject_id": str(self.subject_id),
            "name": self.name,
            "description": self.description,
            "subtopics": self.subtopics or [],
            "frequency": self.frequency,
        }


# ============================================================================
# CLASS TESTS (Uploaded tests)
# ============================================================================

class ClassTest(Base):
    """Uploaded class test with OCR extraction"""
    __tablename__ = "class_tests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id = Column(UUID(as_uuid=True), ForeignKey("schools.id", ondelete="SET NULL"))
    subject_id = Column(UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="SET NULL"))
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("teachers.id", ondelete="SET NULL"))

    # OCR Data
    raw_content = Column(Text, nullable=False)
    ocr_confidence = Column(Float)
    ocr_model_used = Column(String(100))          # "paddle_ocr", "tesseract", "claude_vision"

    # Extracted Structure
    extracted_tasks = Column(JSONB, nullable=False, default=list)
    metadata_confidence = Column(JSONB, nullable=False, default=dict)

    # Verification
    verified = Column(Boolean, default=False)
    verified_at = Column(DateTime(timezone=True))
    verified_by = Column(UUID(as_uuid=True))

    # Duplicate Detection
    content_hash = Column(String(64))
    is_duplicate = Column(Boolean, default=False)
    duplicate_of = Column(UUID(as_uuid=True), ForeignKey("class_tests.id", ondelete="SET NULL"))

    # Metadata
    thema_ids = Column(ARRAY(UUID(as_uuid=True)))
    exam_date = Column(Date)
    exam_duration_minutes = Column(Integer)
    total_points = Column(Integer)

    # File Info
    original_filename = Column(String(255))
    file_type = Column(String(50))                # "pdf", "image"
    file_size_bytes = Column(BigInteger)
    file_path = Column(String(500))

    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    subject = relationship("Subject", back_populates="class_tests")
    teacher = relationship("Teacher", back_populates="class_tests")

    # Indices
    __table_args__ = (
        Index("idx_class_tests_subject", "subject_id"),
        Index("idx_class_tests_teacher", "teacher_id"),
        Index("idx_class_tests_verified", "verified"),
        Index("idx_class_tests_content_hash", "content_hash"),
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "school_id": str(self.school_id) if self.school_id else None,
            "subject_id": str(self.subject_id) if self.subject_id else None,
            "teacher_id": str(self.teacher_id) if self.teacher_id else None,
            "raw_content": self.raw_content,
            "ocr_confidence": self.ocr_confidence,
            "ocr_model_used": self.ocr_model_used,
            "extracted_tasks": self.extracted_tasks,
            "metadata_confidence": self.metadata_confidence,
            "verified": self.verified,
            "is_duplicate": self.is_duplicate,
            "thema_ids": [str(t) for t in (self.thema_ids or [])],
            "exam_date": self.exam_date.isoformat() if self.exam_date else None,
            "original_filename": self.original_filename,
            "file_type": self.file_type,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
        }


# ============================================================================
# MOCK EXAMS (AI-Generated)
# ============================================================================

class MockExam(Base):
    """AI-generated practice exam"""
    __tablename__ = "mock_exams"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id = Column(UUID(as_uuid=True), ForeignKey("schools.id", ondelete="SET NULL"))
    subject_id = Column(UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="SET NULL"))

    # Exam Content
    title = Column(String(255))
    tasks = Column(JSONB, nullable=False, default=list)
    total_points = Column(Integer, nullable=False, default=0)
    estimated_duration_minutes = Column(Integer)
    difficulty_level = Column(Integer)

    # Generation Context
    generation_context = Column(JSONB, nullable=False, default=dict)
    free_prompt_used = Column(Text)
    context_texts_used = Column(ARRAY(Text))

    # Teacher Pattern
    teacher_pattern_applied = Column(Boolean, default=False)
    teacher_pattern_id = Column(UUID(as_uuid=True), ForeignKey("teachers.id", ondelete="SET NULL"))

    # Metadata
    thema_ids = Column(ARRAY(UUID(as_uuid=True)))
    status = Column(String(50), default="ready")

    # AI Generation Info
    generator_model = Column(String(100))
    generation_time_ms = Column(Integer)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    subject = relationship("Subject", back_populates="mock_exams")
    attempts = relationship("Attempt", back_populates="mock_exam", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        CheckConstraint("difficulty_level BETWEEN 1 AND 5", name="check_difficulty"),
        Index("idx_mock_exams_subject", "subject_id"),
        Index("idx_mock_exams_difficulty", "difficulty_level"),
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "school_id": str(self.school_id) if self.school_id else None,
            "subject_id": str(self.subject_id) if self.subject_id else None,
            "title": self.title,
            "tasks": self.tasks,
            "total_points": self.total_points,
            "estimated_duration_minutes": self.estimated_duration_minutes,
            "difficulty_level": self.difficulty_level,
            "generation_context": self.generation_context,
            "thema_ids": [str(t) for t in (self.thema_ids or [])],
            "status": self.status,
            "generator_model": self.generator_model,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ============================================================================
# ATTEMPTS (Student exam attempts)
# ============================================================================

class Attempt(Base):
    """Student's exam attempt"""
    __tablename__ = "attempts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mock_exam_id = Column(UUID(as_uuid=True), ForeignKey("mock_exams.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)

    # Responses
    task_responses = Column(JSONB, nullable=False, default=dict)

    # Timing
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True))
    duration_seconds = Column(Integer)

    # Scoring
    total_score = Column(Float)
    total_points = Column(Integer)
    percentage = Column(Float)
    grade = Column(Float)                         # 1.0-6.0
    grade_text = Column(String(50))

    # Section Breakdown
    section_breakdown = Column(JSONB, default=dict)

    # Flags
    status = Column(String(50), default="in_progress")
    flags_for_review = Column(ARRAY(Text))
    overall_feedback = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    mock_exam = relationship("MockExam", back_populates="attempts")
    grading_result = relationship("GradingResult", back_populates="attempt", uselist=False)

    # Indices
    __table_args__ = (
        Index("idx_attempts_user", "user_id"),
        Index("idx_attempts_mock_exam", "mock_exam_id"),
        Index("idx_attempts_status", "status"),
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "mock_exam_id": str(self.mock_exam_id),
            "user_id": str(self.user_id),
            "task_responses": self.task_responses,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_seconds": self.duration_seconds,
            "total_score": self.total_score,
            "total_points": self.total_points,
            "percentage": self.percentage,
            "grade": self.grade,
            "grade_text": self.grade_text,
            "status": self.status,
            "overall_feedback": self.overall_feedback,
        }


# ============================================================================
# GRADING RESULTS
# ============================================================================

class GradingResult(Base):
    """AI-generated grading result"""
    __tablename__ = "grading_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attempt_id = Column(UUID(as_uuid=True), ForeignKey("attempts.id", ondelete="CASCADE"), nullable=False)
    mock_exam_id = Column(UUID(as_uuid=True), ForeignKey("mock_exams.id", ondelete="CASCADE"), nullable=False)

    # Overall Score
    total_score = Column(Float, nullable=False)
    total_points = Column(Integer, nullable=False)
    percentage = Column(Float, nullable=False)
    grade = Column(Float, nullable=False)
    grade_text = Column(String(50))

    # Per-Task Grades
    task_grades = Column(JSONB, nullable=False, default=list)

    # Feedback
    overall_feedback = Column(Text)
    strengths = Column(ARRAY(Text))
    areas_for_improvement = Column(ARRAY(Text))

    # Grader Info
    grader_model = Column(String(100))
    grader_confidence = Column(Float)
    processing_time_ms = Column(Integer)

    # Review Flags
    manual_review_flagged = Column(Boolean, default=False)
    tasks_needing_review = Column(ARRAY(Text))
    reviewed_at = Column(DateTime(timezone=True))
    reviewed_by = Column(UUID(as_uuid=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    attempt = relationship("Attempt", back_populates="grading_result")

    # Indices
    __table_args__ = (
        Index("idx_grading_attempt", "attempt_id"),
        Index("idx_grading_mock_exam", "mock_exam_id"),
        Index("idx_grading_manual_review", "manual_review_flagged"),
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "attempt_id": str(self.attempt_id),
            "mock_exam_id": str(self.mock_exam_id),
            "total_score": self.total_score,
            "total_points": self.total_points,
            "percentage": self.percentage,
            "grade": self.grade,
            "grade_text": self.grade_text,
            "task_grades": self.task_grades,
            "overall_feedback": self.overall_feedback,
            "grader_model": self.grader_model,
            "grader_confidence": self.grader_confidence,
            "manual_review_flagged": self.manual_review_flagged,
            "tasks_needing_review": self.tasks_needing_review,
        }


# ============================================================================
# UPLOAD SESSIONS (Temporary)
# ============================================================================

class UploadSession(Base):
    """Temporary storage during OCR/review flow"""
    __tablename__ = "upload_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # File Info
    original_filename = Column(String(255))
    file_type = Column(String(50))
    file_size_bytes = Column(BigInteger)
    temp_file_path = Column(String(500))
    content_hash = Column(String(64))

    # OCR Results
    ocr_text = Column(Text)
    ocr_confidence = Column(Float)
    ocr_model_used = Column(String(100))

    # Classification Results
    classification = Column(JSONB, default=dict)
    confidence_scores = Column(JSONB, default=dict)
    extracted_tasks = Column(JSONB, default=list)

    # Review Status
    status = Column(String(50), default="pending_review")
    requires_review = Column(Boolean, default=True)

    # Timing
    expires_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Indices
    __table_args__ = (
        Index("idx_upload_sessions_status", "status"),
        Index("idx_upload_sessions_expires", "expires_at"),
        Index("idx_upload_sessions_hash", "content_hash"),
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "original_filename": self.original_filename,
            "file_type": self.file_type,
            "content_hash": self.content_hash,
            "ocr_text": self.ocr_text,
            "ocr_confidence": self.ocr_confidence,
            "classification": self.classification,
            "confidence_scores": self.confidence_scores,
            "extracted_tasks": self.extracted_tasks,
            "status": self.status,
            "requires_review": self.requires_review,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


# ============================================================================
# TEACHER PATTERNS
# ============================================================================

class TeacherPattern(Base):
    """Learned exam patterns from uploaded tests"""
    __tablename__ = "teacher_patterns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False)
    subject_id = Column(UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)

    # Pattern Data
    tests_analyzed = Column(Integer, default=0)
    task_type_distribution = Column(JSONB, default=dict)
    common_themas = Column(ARRAY(Text))
    average_difficulty = Column(Float)
    average_points_per_task = Column(Float)

    # Style Preferences
    prefers_case_studies = Column(Boolean, default=False)
    prefers_calculations = Column(Boolean, default=False)
    prefers_diagrams = Column(Boolean, default=False)
    typical_exam_duration = Column(Integer)
    typical_task_count = Column(Integer)

    # Example Questions
    example_questions = Column(JSONB, default=list)

    last_updated_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    teacher = relationship("Teacher", back_populates="patterns")

    # Indices
    __table_args__ = (
        Index("idx_teacher_patterns_teacher", "teacher_id"),
        Index("idx_teacher_patterns_subject", "subject_id"),
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "teacher_id": str(self.teacher_id),
            "subject_id": str(self.subject_id),
            "tests_analyzed": self.tests_analyzed,
            "task_type_distribution": self.task_type_distribution,
            "common_themas": self.common_themas,
            "average_difficulty": self.average_difficulty,
            "typical_exam_duration": self.typical_exam_duration,
            "typical_task_count": self.typical_task_count,
        }

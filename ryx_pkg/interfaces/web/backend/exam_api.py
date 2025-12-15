"""
RyxHub Exam System API

FastAPI endpoints for the German Berufsschule exam preparation system.
Handles OCR, teacher pattern learning, mock exam generation, and auto-grading.
"""

from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
import json
import hashlib

router = APIRouter(prefix="/api/exam", tags=["exam"])

# ============================================================================
# Data Models
# ============================================================================

class School(BaseModel):
    id: str
    name: str
    location: str
    subjects: List[str] = []
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class Subject(BaseModel):
    id: str
    school_id: str
    name: str
    full_name: Optional[str] = None
    teacher_ids: List[str] = []
    thema_ids: List[str] = []
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class Teacher(BaseModel):
    id: str
    name: str
    subject_ids: List[str] = []
    tests_count: int = 0
    exam_pattern_profile: Optional[Dict[str, Any]] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class Thema(BaseModel):
    id: str
    subject_id: str
    name: str
    parent_thema_id: Optional[str] = None
    frequency: int = 0
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class Task(BaseModel):
    id: str
    type: str  # MC_SingleChoice, ShortAnswer, CaseStudy, etc.
    task_number: int
    question_text: str
    question_image: Optional[str] = None
    options: Optional[List[Dict[str, Any]]] = None
    correct_answer: Optional[str] = None
    model_answer: Optional[str] = None
    grading_rubric: Dict[str, Any]
    points: int
    difficulty: int = 3
    time_estimate_minutes: int = 5
    source: str = "ai_generated"

class MockExam(BaseModel):
    id: str
    subject_id: str
    thema_ids: List[str]
    title: str
    description: Optional[str] = None
    tasks: List[Task]
    total_points: int
    estimated_duration_minutes: int
    difficulty_level: int
    teacher_pattern_used: Optional[str] = None
    generated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    status: str = "ready"

class Attempt(BaseModel):
    id: str
    mock_exam_id: str
    user_id: str = "default-user"
    started_at: str
    finished_at: Optional[str] = None
    duration_seconds: int = 0
    task_responses: List[Dict[str, Any]] = []
    total_score: int = 0
    total_points: int = 0
    grade: float = 0.0
    grade_text: str = "Ungenügend"
    percentage: float = 0.0
    status: str = "in_progress"

# Request/Response Models
class CreateMockExamRequest(BaseModel):
    subject_id: str
    thema_ids: List[str]
    teacher_id: Optional[str] = None
    difficulty_level: int = 3
    task_count: int = 15
    duration_minutes: int = 90

class SubmitAnswerRequest(BaseModel):
    task_id: str
    user_answer: Any  # Can be string, list, or dict

class GradingResult(BaseModel):
    attempt_id: str
    total_score: int
    total_points: int
    grade: float
    grade_text: str
    percentage: float
    task_grades: List[Dict[str, Any]]
    overall_feedback: str
    strengths: List[str]
    areas_for_improvement: List[str]

class OCRResult(BaseModel):
    success: bool
    class_test_id: Optional[str] = None
    confidence_score: Optional[int] = None
    extracted_text: Optional[str] = None
    detected_metadata: Optional[Dict[str, Any]] = None
    suggested_themas: Optional[List[str]] = None
    requires_verification: bool = False
    verification_prompts: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None

# ============================================================================
# In-Memory Storage (Replace with PostgreSQL in production)
# ============================================================================

# Storage
_schools: Dict[str, School] = {}
_subjects: Dict[str, Subject] = {}
_teachers: Dict[str, Teacher] = {}
_themas: Dict[str, Thema] = {}
_class_tests: Dict[str, Dict] = {}
_mock_exams: Dict[str, MockExam] = {}
_attempts: Dict[str, Attempt] = {}

# Initialize default data
def _init_default_data():
    # Default school
    school = School(
        id="cuno-berufskolleg",
        name="Cuno Berufskolleg Hagen",
        location="Hagen, NRW",
        subjects=["wbl", "bwl", "deutsch", "mathe"]
    )
    _schools[school.id] = school
    
    # Default subjects
    subjects = [
        Subject(id="wbl", school_id="cuno-berufskolleg", name="WBL", full_name="Wirtschaft und Betriebslehre"),
        Subject(id="bwl", school_id="cuno-berufskolleg", name="BWL", full_name="Betriebswirtschaftslehre"),
        Subject(id="deutsch", school_id="cuno-berufskolleg", name="Deutsch", full_name="Deutsch / Kommunikation"),
        Subject(id="mathe", school_id="cuno-berufskolleg", name="Mathe", full_name="Mathematik"),
    ]
    for s in subjects:
        _subjects[s.id] = s
    
    # Default themas for WBL
    themas = [
        Thema(id="marktforschung", subject_id="wbl", name="Marktforschung"),
        Thema(id="marketingmix", subject_id="wbl", name="Marketingmix (4Ps)"),
        Thema(id="kundenakquisition", subject_id="wbl", name="Kundenakquisition"),
        Thema(id="preismanagement", subject_id="wbl", name="Preismanagement"),
        Thema(id="werbung", subject_id="wbl", name="Werbung & Kommunikation"),
    ]
    for t in themas:
        _themas[t.id] = t

_init_default_data()

# ============================================================================
# Helper Functions
# ============================================================================

def calculate_grade(percentage: float) -> tuple[float, str]:
    """Convert percentage to German grade (1-6 scale)."""
    if percentage >= 90:
        return (1.0, "Sehr gut")
    elif percentage >= 85:
        return (1.5, "Sehr gut")
    elif percentage >= 80:
        return (2.0, "Gut")
    elif percentage >= 75:
        return (2.5, "Gut")
    elif percentage >= 70:
        return (3.0, "Befriedigend")
    elif percentage >= 65:
        return (3.5, "Befriedigend")
    elif percentage >= 60:
        return (4.0, "Ausreichend")
    elif percentage >= 55:
        return (4.5, "Ausreichend")
    elif percentage >= 50:
        return (5.0, "Mangelhaft")
    elif percentage >= 40:
        return (5.5, "Mangelhaft")
    else:
        return (6.0, "Ungenügend")

def generate_task_id() -> str:
    return f"task-{uuid.uuid4().hex[:8]}"

def generate_sample_tasks(thema_ids: List[str], count: int, difficulty: int) -> List[Task]:
    """Generate sample exam tasks for given themas."""
    tasks = []
    
    # Sample questions by type
    mc_questions = [
        "Was ist die Definition von Marktforschung?",
        "Welche der folgenden Aussagen über den Marketing-Mix ist korrekt?",
        "Was versteht man unter Primärforschung?",
        "Welche Methode gehört zur Sekundärforschung?",
        "Was ist das Ziel der Kundensegmentierung?",
    ]
    
    short_answer_questions = [
        "Erklären Sie den Unterschied zwischen qualitativer und quantitativer Marktforschung.",
        "Nennen Sie drei Methoden der Datenerhebung in der Marktforschung.",
        "Was sind die 4Ps des Marketing-Mix?",
        "Beschreiben Sie den Prozess der Preisfindung.",
    ]
    
    case_study_questions = [
        "Ein Einzelhandelsbetrieb möchte ein neues Produkt einführen. Entwickeln Sie eine Marktforschungsstrategie.",
        "Die Firma MüllTech AG plant eine Expansion. Analysieren Sie die Marktbedingungen und erstellen Sie eine SWOT-Analyse.",
    ]
    
    # Generate tasks
    task_types = ["MC_SingleChoice", "MC_SingleChoice", "ShortAnswer", "CaseStudy", "DiagramAnalysis"]
    
    for i in range(count):
        task_type = task_types[i % len(task_types)]
        task_difficulty = min(5, max(1, difficulty + (i // 5) - 1))
        
        if task_type == "MC_SingleChoice":
            question = mc_questions[i % len(mc_questions)]
            options = [
                {"id": "A", "text": "Falsche Antwort A", "isCorrect": False},
                {"id": "B", "text": "Richtige Antwort B", "isCorrect": True},
                {"id": "C", "text": "Falsche Antwort C", "isCorrect": False},
                {"id": "D", "text": "Falsche Antwort D", "isCorrect": False},
            ]
            points = 2
            time_estimate = 2
            correct_answer = "B"
        elif task_type == "ShortAnswer":
            question = short_answer_questions[i % len(short_answer_questions)]
            options = None
            points = 5
            time_estimate = 5
            correct_answer = None
        elif task_type == "CaseStudy":
            question = case_study_questions[i % len(case_study_questions)]
            options = None
            points = 10
            time_estimate = 20
            correct_answer = None
        else:  # DiagramAnalysis
            question = "Analysieren Sie das folgende Balkendiagramm zum Marktanteil."
            options = None
            points = 5
            time_estimate = 10
            correct_answer = None
        
        task = Task(
            id=generate_task_id(),
            type=task_type,
            task_number=i + 1,
            question_text=question,
            options=options,
            correct_answer=correct_answer,
            points=points,
            difficulty=task_difficulty,
            time_estimate_minutes=time_estimate,
            grading_rubric={
                "max_points": points,
                "criteria": [{"name": "Vollständigkeit", "description": "Alle Aspekte behandelt", "max_points": points}],
                "auto_gradable": task_type.startswith("MC"),
                "partial_credit_allowed": not task_type.startswith("MC"),
            }
        )
        tasks.append(task)
    
    return tasks

# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/schools")
async def list_schools():
    """List all schools."""
    return {"schools": list(_schools.values())}

@router.get("/schools/{school_id}")
async def get_school(school_id: str):
    """Get school by ID."""
    if school_id not in _schools:
        raise HTTPException(status_code=404, detail="School not found")
    return _schools[school_id]

@router.get("/subjects")
async def list_subjects(school_id: Optional[str] = None):
    """List all subjects, optionally filtered by school."""
    subjects = list(_subjects.values())
    if school_id:
        subjects = [s for s in subjects if s.school_id == school_id]
    return {"subjects": subjects}

@router.get("/subjects/{subject_id}")
async def get_subject(subject_id: str):
    """Get subject by ID."""
    if subject_id not in _subjects:
        raise HTTPException(status_code=404, detail="Subject not found")
    return _subjects[subject_id]

@router.get("/themas")
async def list_themas(subject_id: Optional[str] = None):
    """List all themas, optionally filtered by subject."""
    themas = list(_themas.values())
    if subject_id:
        themas = [t for t in themas if t.subject_id == subject_id]
    return {"themas": themas}

@router.get("/teachers")
async def list_teachers(subject_id: Optional[str] = None):
    """List all teachers, optionally filtered by subject."""
    teachers = list(_teachers.values())
    if subject_id:
        teachers = [t for t in teachers if subject_id in t.subject_ids]
    return {"teachers": teachers}

@router.post("/teachers")
async def create_teacher(name: str, subject_ids: List[str]):
    """Create a new teacher."""
    teacher = Teacher(
        id=f"teacher-{uuid.uuid4().hex[:8]}",
        name=name,
        subject_ids=subject_ids,
    )
    _teachers[teacher.id] = teacher
    return teacher

# ============================================================================
# Test Upload & OCR Endpoints
# ============================================================================

@router.post("/upload-test")
async def upload_test(
    file: UploadFile = File(...),
    subject_id: Optional[str] = None,
    background_tasks: BackgroundTasks = None,
) -> OCRResult:
    """
    Upload a class test (PDF or image) for OCR processing.
    Returns extracted text and suggested metadata.
    """
    # Validate file type
    allowed_types = ["application/pdf", "image/png", "image/jpeg", "image/webp"]
    if file.content_type not in allowed_types:
        return OCRResult(
            success=False,
            error=f"Unsupported file type: {file.content_type}. Allowed: PDF, PNG, JPG"
        )
    
    # Generate class test ID
    class_test_id = f"test-{uuid.uuid4().hex[:8]}"
    
    # Read file content
    content = await file.read()
    content_hash = hashlib.md5(content).hexdigest()
    
    # Check for duplicates
    for existing_id, existing_test in _class_tests.items():
        if existing_test.get("content_hash") == content_hash:
            return OCRResult(
                success=True,
                class_test_id=existing_id,
                confidence_score=100,
                requires_verification=True,
                verification_prompts=[{
                    "field": "duplicate",
                    "detected": f"Diese Datei wurde bereits hochgeladen (ID: {existing_id})",
                    "confidence": 100,
                    "required": True,
                }],
            )
    
    # TODO: Implement actual OCR using Tesseract/PaddleOCR
    # For now, return mock result
    mock_ocr_text = """
    Klassenarbeit
    Herr Hakim
    WBL - Wirtschaft und Betriebslehre
    Datum: 15.11.2024
    Thema: Marktforschung & Kundenakquisition
    
    Aufgabe 1 (5 Punkte):
    Erklären Sie den Unterschied zwischen Primär- und Sekundärforschung.
    
    Aufgabe 2 (10 Punkte):
    Ein Unternehmen möchte ein neues Produkt einführen...
    """
    
    # Store class test
    _class_tests[class_test_id] = {
        "id": class_test_id,
        "filename": file.filename,
        "content_type": file.content_type,
        "content_hash": content_hash,
        "subject_id": subject_id or "wbl",
        "status": "processing",
        "uploaded_at": datetime.utcnow().isoformat(),
        "ocr_text": mock_ocr_text,
    }
    
    return OCRResult(
        success=True,
        class_test_id=class_test_id,
        confidence_score=85,
        extracted_text=mock_ocr_text,
        detected_metadata={
            "teacher": "Herr Hakim",
            "subject": "WBL",
            "date": "2024-11-15",
        },
        suggested_themas=["Marktforschung", "Kundenakquisition"],
        requires_verification=True,
        verification_prompts=[
            {
                "field": "teacher",
                "detected": "Herr Hakim",
                "confidence": 90,
                "suggestions": ["Herr Hakim", "Frau Müller", "Herr Schmidt"],
                "required": True,
            },
            {
                "field": "subject",
                "detected": "WBL",
                "confidence": 95,
                "required": True,
            },
            {
                "field": "date",
                "detected": "2024-11-15",
                "confidence": 80,
                "required": False,
            },
        ],
    )

@router.post("/verify-test/{class_test_id}")
async def verify_test(class_test_id: str, corrections: Dict[str, str]):
    """Verify and confirm uploaded test metadata."""
    if class_test_id not in _class_tests:
        raise HTTPException(status_code=404, detail="Class test not found")
    
    test = _class_tests[class_test_id]
    test["status"] = "ready"
    test["verified_metadata"] = corrections
    
    # Create/update teacher if needed
    teacher_name = corrections.get("teacher")
    if teacher_name:
        existing = next((t for t in _teachers.values() if t.name == teacher_name), None)
        if not existing:
            teacher = Teacher(
                id=f"teacher-{uuid.uuid4().hex[:8]}",
                name=teacher_name,
                subject_ids=[test["subject_id"]],
                tests_count=1,
            )
            _teachers[teacher.id] = teacher
        else:
            existing.tests_count += 1
    
    return {"success": True, "class_test_id": class_test_id}

# ============================================================================
# Mock Exam Generation Endpoints
# ============================================================================

@router.post("/generate-exam")
async def generate_mock_exam(request: CreateMockExamRequest) -> MockExam:
    """
    Generate a new mock exam based on subject, themas, and optionally teacher pattern.
    Uses AI (Claude/Ollama) to create realistic exam questions.
    """
    # Get thema names
    thema_names = [_themas[tid].name for tid in request.thema_ids if tid in _themas]
    if not thema_names:
        thema_names = ["Marktforschung"]  # Default
    
    # Generate tasks
    tasks = generate_sample_tasks(
        request.thema_ids,
        request.task_count,
        request.difficulty_level
    )
    
    # Calculate total points
    total_points = sum(t.points for t in tasks)
    
    # Create mock exam
    mock_exam = MockExam(
        id=f"mock-{uuid.uuid4().hex[:8]}",
        subject_id=request.subject_id,
        thema_ids=request.thema_ids,
        title=f"Übungsklausur: {', '.join(thema_names)}",
        tasks=tasks,
        total_points=total_points,
        estimated_duration_minutes=request.duration_minutes,
        difficulty_level=request.difficulty_level,
        teacher_pattern_used=request.teacher_id,
    )
    
    _mock_exams[mock_exam.id] = mock_exam
    return mock_exam

@router.get("/mock-exams")
async def list_mock_exams(subject_id: Optional[str] = None, thema_id: Optional[str] = None):
    """List all mock exams, optionally filtered."""
    exams = list(_mock_exams.values())
    if subject_id:
        exams = [e for e in exams if e.subject_id == subject_id]
    if thema_id:
        exams = [e for e in exams if thema_id in e.thema_ids]
    return {"mock_exams": exams}

@router.get("/mock-exams/{exam_id}")
async def get_mock_exam(exam_id: str):
    """Get mock exam by ID."""
    if exam_id not in _mock_exams:
        raise HTTPException(status_code=404, detail="Mock exam not found")
    return _mock_exams[exam_id]

# ============================================================================
# Attempt & Grading Endpoints
# ============================================================================

@router.post("/start-attempt/{exam_id}")
async def start_attempt(exam_id: str) -> Attempt:
    """Start a new attempt for a mock exam."""
    if exam_id not in _mock_exams:
        raise HTTPException(status_code=404, detail="Mock exam not found")
    
    exam = _mock_exams[exam_id]
    
    attempt = Attempt(
        id=f"attempt-{uuid.uuid4().hex[:8]}",
        mock_exam_id=exam_id,
        started_at=datetime.utcnow().isoformat(),
        total_points=exam.total_points,
    )
    
    _attempts[attempt.id] = attempt
    return attempt

@router.post("/attempts/{attempt_id}/submit-answer")
async def submit_answer(attempt_id: str, request: SubmitAnswerRequest):
    """Submit an answer for a task in an attempt."""
    if attempt_id not in _attempts:
        raise HTTPException(status_code=404, detail="Attempt not found")
    
    attempt = _attempts[attempt_id]
    
    # Find existing response or create new
    response = next((r for r in attempt.task_responses if r["task_id"] == request.task_id), None)
    
    new_response = {
        "task_id": request.task_id,
        "user_answer": request.user_answer,
        "answered_at": datetime.utcnow().isoformat(),
    }
    
    if response:
        attempt.task_responses = [
            r if r["task_id"] != request.task_id else new_response
            for r in attempt.task_responses
        ]
    else:
        attempt.task_responses.append(new_response)
    
    return {"success": True}

@router.post("/attempts/{attempt_id}/finish")
async def finish_attempt(attempt_id: str) -> GradingResult:
    """
    Finish an attempt and grade all answers.
    Uses AI for open-ended questions, auto-grades MC.
    """
    if attempt_id not in _attempts:
        raise HTTPException(status_code=404, detail="Attempt not found")
    
    attempt = _attempts[attempt_id]
    exam = _mock_exams.get(attempt.mock_exam_id)
    
    if not exam:
        raise HTTPException(status_code=404, detail="Mock exam not found")
    
    # Grade each task
    task_grades = []
    total_score = 0
    
    for task in exam.tasks:
        response = next((r for r in attempt.task_responses if r["task_id"] == task.id), None)
        
        if task.type.startswith("MC"):
            # Auto-grade MC
            is_correct = response and response.get("user_answer") == task.correct_answer
            earned_points = task.points if is_correct else 0
            confidence = 100
            feedback = "Richtig!" if is_correct else f"Falsch. Die richtige Antwort ist {task.correct_answer}."
        else:
            # AI-grade open-ended (mock for now)
            # In production, call Claude/Ollama with rubric
            earned_points = task.points // 2 if response else 0  # Mock: give half points
            confidence = 75
            feedback = "Teilweise korrekt. Mehr Details wären hilfreich."
        
        total_score += earned_points
        
        task_grades.append({
            "task_id": task.id,
            "earned_points": earned_points,
            "max_points": task.points,
            "auto_graded": task.type.startswith("MC"),
            "confidence": confidence,
            "feedback": feedback,
            "is_correct": earned_points == task.points,
        })
    
    # Calculate grade
    percentage = (total_score / exam.total_points) * 100 if exam.total_points > 0 else 0
    grade, grade_text = calculate_grade(percentage)
    
    # Update attempt
    attempt.finished_at = datetime.utcnow().isoformat()
    attempt.total_score = total_score
    attempt.grade = grade
    attempt.grade_text = grade_text
    attempt.percentage = percentage
    attempt.status = "graded"
    
    return GradingResult(
        attempt_id=attempt_id,
        total_score=total_score,
        total_points=exam.total_points,
        grade=grade,
        grade_text=grade_text,
        percentage=percentage,
        task_grades=task_grades,
        overall_feedback=f"Gute Leistung mit {percentage:.0f}%! Note: {grade_text} ({grade:.1f})",
        strengths=["Multiple Choice", "Wissensaufgaben"],
        areas_for_improvement=["Fallstudien", "Berechnungen"],
    )

@router.get("/attempts")
async def list_attempts(mock_exam_id: Optional[str] = None):
    """List all attempts, optionally filtered by exam."""
    attempts = list(_attempts.values())
    if mock_exam_id:
        attempts = [a for a in attempts if a.mock_exam_id == mock_exam_id]
    return {"attempts": attempts}

@router.get("/attempts/{attempt_id}")
async def get_attempt(attempt_id: str):
    """Get attempt by ID."""
    if attempt_id not in _attempts:
        raise HTTPException(status_code=404, detail="Attempt not found")
    return _attempts[attempt_id]

# ============================================================================
# Teacher Pattern Learning Endpoints
# ============================================================================

@router.get("/teachers/{teacher_id}/pattern")
async def get_teacher_pattern(teacher_id: str):
    """Get learned exam pattern for a teacher."""
    if teacher_id not in _teachers:
        raise HTTPException(status_code=404, detail="Teacher not found")
    
    teacher = _teachers[teacher_id]
    
    if not teacher.exam_pattern_profile:
        # Generate default pattern if not enough data
        return {
            "teacher_id": teacher_id,
            "pattern_available": False,
            "tests_needed": max(0, 3 - teacher.tests_count),
            "message": "Lade mindestens 3 Tests hoch, um das Muster dieses Lehrers zu lernen.",
        }
    
    return {
        "teacher_id": teacher_id,
        "pattern_available": True,
        "pattern": teacher.exam_pattern_profile,
    }

@router.post("/teachers/{teacher_id}/learn-pattern")
async def learn_teacher_pattern(teacher_id: str):
    """
    Analyze uploaded tests for a teacher and learn their exam pattern.
    Requires at least 3 tests.
    """
    if teacher_id not in _teachers:
        raise HTTPException(status_code=404, detail="Teacher not found")
    
    teacher = _teachers[teacher_id]
    
    # Get all tests for this teacher
    teacher_tests = [t for t in _class_tests.values() if t.get("verified_metadata", {}).get("teacher") == teacher.name]
    
    if len(teacher_tests) < 3:
        raise HTTPException(
            status_code=400,
            detail=f"Mindestens 3 Tests erforderlich. Aktuell: {len(teacher_tests)}"
        )
    
    # TODO: Implement actual pattern learning with Claude/Ollama
    # For now, generate mock pattern
    pattern = {
        "question_type_distribution": {
            "multiple_choice": 20,
            "short_answer": 30,
            "case_study": 40,
            "diagram_analysis": 10,
        },
        "avg_difficulty": 3.2,
        "avg_points_per_test": 100,
        "avg_duration_minutes": 90,
        "point_distribution": {
            "knowledge_section": 40,
            "application_section": 60,
        },
        "grading_rubric_inference": {
            "case_study": "Analyse 40%, Empfehlung 40%, Kommunikation 20%",
            "short_answer": "3+ vollständige Sätze = volle Punkte; 1-2 Sätze = halbe Punkte",
        },
        "confidence": 85,
        "tests_analyzed": len(teacher_tests),
    }
    
    teacher.exam_pattern_profile = pattern
    
    return {
        "success": True,
        "teacher_id": teacher_id,
        "pattern": pattern,
    }

# ============================================================================
# Statistics Endpoints
# ============================================================================

@router.get("/statistics")
async def get_statistics(subject_id: Optional[str] = None, thema_id: Optional[str] = None):
    """Get exam statistics for a user."""
    completed_attempts = [a for a in _attempts.values() if a.status == "graded"]
    
    if subject_id:
        completed_attempts = [
            a for a in completed_attempts
            if _mock_exams.get(a.mock_exam_id, MockExam).subject_id == subject_id
        ]
    
    if thema_id:
        completed_attempts = [
            a for a in completed_attempts
            if thema_id in _mock_exams.get(a.mock_exam_id, MockExam).thema_ids
        ]
    
    if not completed_attempts:
        return {
            "total_attempts": 0,
            "average_grade": 0,
            "average_percentage": 0,
            "best_grade": 0,
            "total_study_time_minutes": 0,
        }
    
    return {
        "total_attempts": len(completed_attempts),
        "average_grade": sum(a.grade for a in completed_attempts) / len(completed_attempts),
        "average_percentage": sum(a.percentage for a in completed_attempts) / len(completed_attempts),
        "best_grade": min(a.grade for a in completed_attempts),
        "total_study_time_minutes": sum(a.duration_seconds for a in completed_attempts) // 60,
        "progress_over_time": [
            {"date": a.finished_at, "grade": a.grade, "percentage": a.percentage}
            for a in sorted(completed_attempts, key=lambda x: x.finished_at or "")
        ],
    }

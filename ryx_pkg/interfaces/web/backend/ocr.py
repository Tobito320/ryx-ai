"""
OCR Module for Exam System - Stage 2: Image Analysis & Layout Detection

Implements comprehensive document analysis:
- Text extraction (printed + handwritten)
- Layout detection (question boundaries, answer fields)
- Student marking detection (checkboxes, X marks)
- Confidence scoring per element
- Handwriting quality assessment

Uses Tesseract (primary) with Claude Vision fallback.
"""

import logging
import os
import tempfile
import hashlib
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import re

logger = logging.getLogger(__name__)

# Try imports (graceful degradation)
try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logger.warning("Tesseract not available - will use fallback OCR")

try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    logger.warning("PyPDF2 not available - PDF text extraction limited")

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    logger.warning("httpx not available - Claude Vision fallback disabled")


class QuestionType(str, Enum):
    """Detected question types from layout analysis"""
    MULTIPLE_CHOICE = "multiple_choice"
    MATCHING = "matching"
    SHORT_ANSWER = "short_answer"
    LONG_ANSWER = "long_answer"
    DIAGRAM = "diagram"
    CALCULATION = "calculation"


@dataclass
class ExtractedQuestion:
    """Structured question data from OCR"""
    question_id: str
    question_text: str
    question_type: QuestionType
    options: List[Dict[str, Any]]  # For MC: [{id: "a", text: "...", marked: bool}]
    student_answer: str  # Extracted text or selected option
    extraction_confidence: float  # 0.0-1.0
    issues: List[str]  # Flags like "handwriting_unclear", "multiple_marks"
    max_points: Optional[int] = None


@dataclass
class OCRResult:
    """Complete OCR analysis result"""
    text: str  # Full extracted text
    confidence: float  # Overall confidence score
    model_used: str  # "tesseract", "claude-vision", "mock"
    questions: List[ExtractedQuestion] = None  # Structured question data
    metadata: Dict[str, Any] = None  # Document metadata (teacher, date, etc.)
    handwriting_quality: str = "unknown"  # "high", "medium", "low"
    requires_manual_review: bool = False


def compute_content_hash(content: bytes) -> str:
    """Compute hash for deduplication"""
    return hashlib.md5(content).hexdigest()


async def perform_ocr(file_path: str, use_vision: bool = True) -> OCRResult:
    """
    Main OCR entry point - Stage 2 implementation.
    
    Args:
        file_path: Path to PDF/image file
        use_vision: Whether to use vision models for layout detection
    
    Returns:
        OCRResult with text, confidence, and structured questions
    """
    
    logger.info(f"OCR: Starting analysis of {file_path}")
    
    # Determine file type
    file_ext = os.path.splitext(file_path)[1].lower()
    
    try:
        # Try Tesseract first (fast, good for printed text)
        if TESSERACT_AVAILABLE and file_ext in [".png", ".jpg", ".jpeg"]:
            result = await _tesseract_ocr(file_path)
            if result and result.confidence > 0.7:
                logger.info(f"OCR: Tesseract success, confidence={result.confidence:.2f}")
                return result
        
        # Try PDF text extraction
        if PDF_AVAILABLE and file_ext == ".pdf":
            result = await _pdf_text_extraction(file_path)
            if result and result.confidence > 0.8:
                logger.info(f"OCR: PDF extraction success, confidence={result.confidence:.2f}")
                return result
        
        # Fallback to Claude Vision (comprehensive but slower)
        if use_vision and HTTPX_AVAILABLE:
            result = await _claude_vision_ocr(file_path)
            if result:
                logger.info(f"OCR: Claude Vision success, confidence={result.confidence:.2f}")
                return result
        
        # Last resort: mock data
        logger.warning("OCR: All methods failed, using mock data")
        return _mock_ocr_result()
        
    except Exception as e:
        logger.error(f"OCR: Failed with error: {e}")
        return _mock_ocr_result()


async def _tesseract_ocr(file_path: str) -> Optional[OCRResult]:
    """Extract text using Tesseract OCR"""
    
    if not TESSERACT_AVAILABLE:
        return None
    
    try:
        # Load image
        image = Image.open(file_path)
        
        # Get text with confidence data
        text = pytesseract.image_to_string(image, lang='deu')
        
        # Get per-word confidence (more granular)
        data = pytesseract.image_to_data(image, lang='deu', output_type=pytesseract.Output.DICT)
        confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
        avg_confidence = sum(confidences) / len(confidences) / 100 if confidences else 0.5
        
        # Basic quality checks
        if len(text.strip()) < 50:
            logger.warning("Tesseract: Extracted text too short")
            return None
        
        # Detect layout and structure questions
        questions = _parse_questions_from_text(text)
        
        return OCRResult(
            text=text,
            confidence=avg_confidence,
            model_used="tesseract",
            questions=questions,
            handwriting_quality="unknown",  # Tesseract doesn't detect handwriting
            requires_manual_review=avg_confidence < 0.75
        )
        
    except Exception as e:
        logger.error(f"Tesseract OCR failed: {e}")
        return None


async def _pdf_text_extraction(file_path: str) -> Optional[OCRResult]:
    """Extract text from PDF (for scanned/text-based PDFs)"""
    
    if not PDF_AVAILABLE:
        return None
    
    try:
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            
            # Extract all text
            all_text = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    all_text.append(text)
            
            full_text = "\n".join(all_text)
            
            if len(full_text.strip()) < 50:
                logger.warning("PDF: Extracted text too short (might be image-based PDF)")
                return None
            
            # Parse questions
            questions = _parse_questions_from_text(full_text)
            
            # PDF text extraction is reliable if text exists
            confidence = 0.9 if len(full_text) > 200 else 0.6
            
            return OCRResult(
                text=full_text,
                confidence=confidence,
                model_used="pypdf2",
                questions=questions,
                handwriting_quality="not_applicable",
                requires_manual_review=False
            )
            
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        return None


async def _claude_vision_ocr(file_path: str) -> Optional[OCRResult]:
    """
    Use Claude Vision API for comprehensive document analysis.
    
    This is the most advanced method - extracts text, detects layout,
    identifies handwriting, marks checkboxes, etc.
    """
    
    if not HTTPX_AVAILABLE:
        return None
    
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        logger.warning("Claude Vision: No API key, skipping")
        return None
    
    try:
        # Read file as base64
        import base64
        with open(file_path, 'rb') as f:
            content = f.read()
        
        file_ext = os.path.splitext(file_path)[1].lower()
        media_type = "image/jpeg" if file_ext in [".jpg", ".jpeg"] else "image/png"
        if file_ext == ".pdf":
            # For PDF, we'd need to convert to image first
            logger.warning("Claude Vision: PDF not directly supported, needs conversion")
            return None
        
        image_data = base64.standard_b64encode(content).decode('utf-8')
        
        # Call Claude with vision prompt
        prompt = """Analyze this German exam document and extract ALL information in JSON format:

{
  "full_text": "Complete extracted text",
  "metadata": {
    "teacher": "Teacher name or null",
    "subject": "Subject detected",
    "date": "Exam date or null",
    "class": "Class name or null"
  },
  "questions": [
    {
      "question_id": "1.1",
      "question_text": "Full question text",
      "question_type": "multiple_choice|short_answer|long_answer|matching|diagram|calculation",
      "max_points": 5,
      "options": [
        {"id": "a", "text": "Option A", "marked_by_student": true}
      ],
      "student_answer": "Text written by student",
      "extraction_confidence": 0.95,
      "issues": ["handwriting_unclear"]
    }
  ],
  "handwriting_quality": "high|medium|low",
  "overall_confidence": 0.90
}

Be thorough - extract all questions, detect all student markings, flag unclear areas."""
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": "claude-3-5-sonnet-20241022",
                    "max_tokens": 4000,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": media_type,
                                        "data": image_data
                                    }
                                },
                                {
                                    "type": "text",
                                    "text": prompt
                                }
                            ]
                        }
                    ]
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Claude Vision: API error {response.status_code}")
                return None
            
            result = response.json()
            content_text = result["content"][0]["text"]
            
            # Parse JSON from response
            import json
            data = json.loads(content_text)
            
            # Convert to structured format
            questions = []
            for q_data in data.get("questions", []):
                questions.append(ExtractedQuestion(
                    question_id=q_data.get("question_id", "unknown"),
                    question_text=q_data.get("question_text", ""),
                    question_type=QuestionType(q_data.get("question_type", "short_answer")),
                    options=q_data.get("options", []),
                    student_answer=q_data.get("student_answer", ""),
                    extraction_confidence=q_data.get("extraction_confidence", 0.85),
                    issues=q_data.get("issues", []),
                    max_points=q_data.get("max_points")
                ))
            
            return OCRResult(
                text=data.get("full_text", ""),
                confidence=data.get("overall_confidence", 0.85),
                model_used="claude-vision",
                questions=questions,
                metadata=data.get("metadata", {}),
                handwriting_quality=data.get("handwriting_quality", "medium"),
                requires_manual_review=data.get("overall_confidence", 0.85) < 0.75
            )
            
    except Exception as e:
        logger.error(f"Claude Vision failed: {e}")
        return None


def _parse_questions_from_text(text: str) -> List[ExtractedQuestion]:
    """
    Parse structured questions from plain text.
    
    Detects:
    - Question numbers (Aufgabe 1, 1., 1), etc.)
    - Point values (8 Punkte, (5P), etc.)
    - MC options (A), B), a., b., etc.)
    - Answer fields
    """
    
    questions = []
    
    # Split by question patterns
    question_pattern = r'(?:Aufgabe|Frage|Nr\.?)\s*(\d+[a-z]?)[:\).]?\s*(?:\((\d+)\s*Punkte?\))?'
    matches = list(re.finditer(question_pattern, text, re.IGNORECASE))
    
    for i, match in enumerate(matches):
        question_id = match.group(1)
        max_points_str = match.group(2)
        max_points = int(max_points_str) if max_points_str else None
        
        # Extract text until next question
        start_pos = match.end()
        end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        question_text = text[start_pos:end_pos].strip()
        
        # Detect question type
        question_type = _detect_question_type(question_text)
        
        # Extract MC options if present
        options = []
        if question_type == QuestionType.MULTIPLE_CHOICE:
            options = _extract_mc_options(question_text)
        
        # Try to find student answer (basic heuristic)
        student_answer = _extract_student_answer(question_text)
        
        questions.append(ExtractedQuestion(
            question_id=question_id,
            question_text=question_text[:500],  # Limit length
            question_type=question_type,
            options=options,
            student_answer=student_answer,
            extraction_confidence=0.7,  # Medium confidence for text parsing
            issues=[],
            max_points=max_points
        ))
    
    return questions


def _detect_question_type(text: str) -> QuestionType:
    """Heuristically detect question type from text"""
    
    text_lower = text.lower()
    
    # MC indicators
    mc_patterns = ['a)', 'b)', 'c)', 'd)', 'multiple choice', 'richtig', 'falsch']
    if any(p in text_lower for p in mc_patterns):
        return QuestionType.MULTIPLE_CHOICE
    
    # Matching indicators
    if 'ordnen sie zu' in text_lower or 'zuordnung' in text_lower:
        return QuestionType.MATCHING
    
    # Calculation indicators
    if 'berechnen' in text_lower or 'rechnen' in text_lower or 'formel' in text_lower:
        return QuestionType.CALCULATION
    
    # Diagram indicators
    if 'diagramm' in text_lower or 'grafik' in text_lower or 'abbildung' in text_lower:
        return QuestionType.DIAGRAM
    
    # Short vs long answer (by keywords)
    short_keywords = ['nennen sie', 'listen sie', 'definieren sie']
    if any(k in text_lower for k in short_keywords) or len(text) < 300:
        return QuestionType.SHORT_ANSWER
    
    return QuestionType.LONG_ANSWER


def _extract_mc_options(text: str) -> List[Dict[str, Any]]:
    """Extract multiple choice options"""
    
    options = []
    
    # Match patterns like "A) Text" or "a. Text"
    option_pattern = r'([A-Ea-e])[).]\s*([^\n]+)'
    matches = re.findall(option_pattern, text)
    
    for letter, option_text in matches:
        options.append({
            "id": letter.upper(),
            "text": option_text.strip(),
            "marked_by_student": False  # Can't detect from plain text
        })
    
    return options


def _extract_student_answer(text: str) -> str:
    """Try to extract student's written answer (basic)"""
    
    # Look for common answer patterns
    answer_pattern = r'(?:Antwort|Lösung)[:\s]*(.+?)(?:\n\n|\Z)'
    match = re.search(answer_pattern, text, re.IGNORECASE | re.DOTALL)
    
    if match:
        return match.group(1).strip()
    
    return ""


def _mock_ocr_result() -> OCRResult:
    """Fallback mock OCR for development/testing"""
    
    mock_text = """
Klassenarbeit IT Service Management
Lehrer: Herr Hakim
Datum: 15.12.2024
Klasse: FI23a

Aufgabe 1 (5 Punkte):
Was ist der Hauptunterschied zwischen Incident und Problem Management?

Aufgabe 2 (8 Punkte):
Erläutern Sie den Zweck eines SLA und nennen Sie drei typische Kennzahlen.

Aufgabe 3 (12 Punkte):
Ein Nutzer meldet einen Systemausfall.
a) Welche ITIL-Prozesse greifen hier?
b) Wie priorisieren Sie diesen Incident?
c) Wann eskalieren Sie zu Problem Management?
"""
    
    questions = _parse_questions_from_text(mock_text)
    
    return OCRResult(
        text=mock_text,
        confidence=0.3,  # Low confidence for mock
        model_used="mock",
        questions=questions,
        handwriting_quality="not_applicable",
        requires_manual_review=True
    )

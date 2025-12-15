"""
RyxHub OCR Engine
Real OCR implementation using:
1. Tesseract (primary, lightweight)
2. Claude Vision API (fallback for poor quality scans)
"""

import os
import io
import base64
import hashlib
import tempfile
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
import logging

# Optional imports - graceful degradation if not available
try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

try:
    from pdf2image import convert_from_path, convert_from_bytes
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

try:
    import anthropic
    CLAUDE_AVAILABLE = True
except ImportError:
    CLAUDE_AVAILABLE = False


logger = logging.getLogger(__name__)


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class OCRResult:
    """Result from OCR processing"""
    text: str
    confidence: float  # 0.0 - 1.0
    model_used: str  # "tesseract", "claude_vision", "mock"
    pages: int = 1
    processing_time_ms: int = 0
    layout_data: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "confidence": self.confidence,
            "model_used": self.model_used,
            "pages": self.pages,
            "processing_time_ms": self.processing_time_ms,
            "layout_data": self.layout_data,
            "warnings": self.warnings,
            "error": self.error,
        }


@dataclass
class TextBlock:
    """A block of text with position and confidence"""
    text: str
    confidence: float
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    page: int = 1


# ============================================================================
# OCR Engine
# ============================================================================

class OCREngine:
    """
    Main OCR engine with multiple backend support.

    Usage:
        engine = OCREngine()
        result = await engine.process_file("/path/to/file.pdf")
        print(result.text)
        print(f"Confidence: {result.confidence * 100}%")
    """

    def __init__(
        self,
        tesseract_path: Optional[str] = None,
        claude_api_key: Optional[str] = None,
        preferred_backend: str = "tesseract",  # "tesseract", "claude", "auto"
        language: str = "deu",  # German
    ):
        self.tesseract_path = tesseract_path
        self.claude_api_key = claude_api_key or os.getenv("ANTHROPIC_API_KEY")
        self.preferred_backend = preferred_backend
        self.language = language

        # Configure Tesseract path if provided
        if tesseract_path and TESSERACT_AVAILABLE:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path

        # Initialize Claude client if available
        self.claude_client = None
        if CLAUDE_AVAILABLE and self.claude_api_key:
            self.claude_client = anthropic.Anthropic(api_key=self.claude_api_key)

    @property
    def available_backends(self) -> List[str]:
        """List available OCR backends"""
        backends = []
        if TESSERACT_AVAILABLE:
            backends.append("tesseract")
        if CLAUDE_AVAILABLE and self.claude_api_key:
            backends.append("claude_vision")
        backends.append("mock")  # Always available as fallback
        return backends

    async def process_file(
        self,
        file_path: Union[str, Path],
        force_backend: Optional[str] = None,
    ) -> OCRResult:
        """
        Process a file (PDF or image) and extract text.

        Args:
            file_path: Path to PDF or image file
            force_backend: Force specific backend ("tesseract", "claude", "mock")

        Returns:
            OCRResult with extracted text and metadata
        """
        import time
        start_time = time.time()

        file_path = Path(file_path)
        if not file_path.exists():
            return OCRResult(
                text="",
                confidence=0.0,
                model_used="error",
                error=f"File not found: {file_path}",
            )

        # Determine file type
        suffix = file_path.suffix.lower()
        is_pdf = suffix == ".pdf"
        is_image = suffix in [".png", ".jpg", ".jpeg", ".webp", ".tiff", ".bmp"]

        if not is_pdf and not is_image:
            return OCRResult(
                text="",
                confidence=0.0,
                model_used="error",
                error=f"Unsupported file type: {suffix}",
            )

        # Choose backend
        backend = force_backend or self.preferred_backend
        if backend == "auto":
            backend = self._choose_best_backend()

        # Process based on backend
        try:
            if backend == "tesseract" and TESSERACT_AVAILABLE:
                result = await self._process_with_tesseract(file_path, is_pdf)
            elif backend == "claude" and self.claude_client:
                result = await self._process_with_claude(file_path, is_pdf)
            else:
                result = self._process_mock(file_path)

            # Calculate processing time
            result.processing_time_ms = int((time.time() - start_time) * 1000)

            # If confidence is too low with tesseract, try Claude as fallback
            if (
                result.confidence < 0.5
                and backend == "tesseract"
                and self.claude_client
                and force_backend is None
            ):
                logger.info(f"Low confidence ({result.confidence}), trying Claude Vision fallback")
                claude_result = await self._process_with_claude(file_path, is_pdf)
                if claude_result.confidence > result.confidence:
                    result = claude_result
                    result.warnings.append("Used Claude Vision fallback due to low Tesseract confidence")

            return result

        except Exception as e:
            logger.error(f"OCR processing failed: {e}")
            return OCRResult(
                text="",
                confidence=0.0,
                model_used="error",
                error=str(e),
                processing_time_ms=int((time.time() - start_time) * 1000),
            )

    def _choose_best_backend(self) -> str:
        """Choose best available backend"""
        if TESSERACT_AVAILABLE:
            return "tesseract"
        elif self.claude_client:
            return "claude"
        return "mock"

    async def _process_with_tesseract(
        self,
        file_path: Path,
        is_pdf: bool,
    ) -> OCRResult:
        """Process file using Tesseract OCR"""
        if not TESSERACT_AVAILABLE:
            raise RuntimeError("Tesseract not available")

        all_text = []
        all_confidence = []
        layout_data = []
        pages = 0

        # Convert to images if PDF
        if is_pdf:
            if not PDF2IMAGE_AVAILABLE:
                raise RuntimeError("pdf2image not available for PDF processing")

            images = convert_from_path(str(file_path), dpi=300)
            pages = len(images)
        else:
            images = [Image.open(file_path)]
            pages = 1

        # Process each page/image
        for page_num, image in enumerate(images, 1):
            # Get detailed OCR data
            ocr_data = pytesseract.image_to_data(
                image,
                lang=self.language,
                output_type=pytesseract.Output.DICT,
            )

            # Extract text and confidence
            page_text = []
            page_blocks = []

            for i, text in enumerate(ocr_data["text"]):
                if text.strip():
                    conf = ocr_data["conf"][i]
                    if conf > 0:  # -1 means no confidence
                        page_text.append(text)
                        all_confidence.append(conf / 100.0)

                        page_blocks.append({
                            "text": text,
                            "confidence": conf / 100.0,
                            "x": ocr_data["left"][i],
                            "y": ocr_data["top"][i],
                            "width": ocr_data["width"][i],
                            "height": ocr_data["height"][i],
                        })

            all_text.append(" ".join(page_text))
            layout_data.append({
                "page": page_num,
                "text": " ".join(page_text),
                "blocks": page_blocks,
            })

        # Calculate overall confidence
        avg_confidence = sum(all_confidence) / len(all_confidence) if all_confidence else 0.0

        return OCRResult(
            text="\n\n".join(all_text),
            confidence=avg_confidence,
            model_used="tesseract",
            pages=pages,
            layout_data=layout_data,
        )

    async def _process_with_claude(
        self,
        file_path: Path,
        is_pdf: bool,
    ) -> OCRResult:
        """Process file using Claude Vision API"""
        if not self.claude_client:
            raise RuntimeError("Claude client not available")

        # Convert to images
        if is_pdf:
            if not PDF2IMAGE_AVAILABLE:
                raise RuntimeError("pdf2image not available for PDF processing")

            images = convert_from_path(str(file_path), dpi=200)
        else:
            images = [Image.open(file_path)]

        all_text = []
        pages = len(images)

        # Process each page with Claude
        for page_num, image in enumerate(images, 1):
            # Convert image to base64
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            image_data = base64.standard_b64encode(buffer.getvalue()).decode("utf-8")

            # Call Claude Vision
            message = self.claude_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": image_data,
                                },
                            },
                            {
                                "type": "text",
                                "text": """Extract ALL text from this German exam document.
                                Include:
                                - Header information (teacher, date, subject)
                                - All questions numbered exactly as shown
                                - Point values for each question
                                - Any tables or diagrams described

                                Return ONLY the extracted text, preserving the original formatting.
                                Do not add any commentary.""",
                            },
                        ],
                    }
                ],
            )

            page_text = message.content[0].text
            all_text.append(page_text)

        # Claude doesn't provide confidence, estimate based on text quality
        full_text = "\n\n".join(all_text)
        confidence = self._estimate_text_quality(full_text)

        return OCRResult(
            text=full_text,
            confidence=confidence,
            model_used="claude_vision",
            pages=pages,
        )

    def _estimate_text_quality(self, text: str) -> float:
        """Estimate text quality/confidence based on content analysis"""
        if not text:
            return 0.0

        # Count indicators of good extraction
        score = 0.5  # Base score

        # Check for expected exam elements
        german_indicators = [
            "Klassenarbeit", "Klausur", "Prüfung", "Aufgabe", "Punkte",
            "Lehrer", "Schüler", "Datum", "Note", "Bewertung",
            "Thema", "Fach", "Klasse", "Name",
        ]

        for indicator in german_indicators:
            if indicator.lower() in text.lower():
                score += 0.03

        # Check for numbered questions
        import re
        questions = re.findall(r'\d+[\.\)]\s*\w+', text)
        if len(questions) >= 3:
            score += 0.1

        # Check for point values
        points = re.findall(r'\d+\s*(Punkt|Pkt|P\.)', text, re.IGNORECASE)
        if len(points) >= 2:
            score += 0.1

        # Penalize very short text
        if len(text) < 100:
            score -= 0.2

        return min(1.0, max(0.0, score))

    def _process_mock(self, file_path: Path) -> OCRResult:
        """Fallback mock processing when no OCR backend is available"""
        logger.warning("Using mock OCR - no real OCR backend available")

        # Generate semi-realistic mock text based on filename
        filename = file_path.stem.lower()

        # Detect subject from filename
        subject = "Allgemein"
        if "wbl" in filename or "wirtschaft" in filename:
            subject = "WBL"
        elif "it" in filename or "service" in filename:
            subject = "IT Service Management"
        elif "deutsch" in filename:
            subject = "Deutsch"
        elif "mathe" in filename:
            subject = "Mathematik"

        # Detect teacher from filename
        teacher = "Unbekannt"
        teachers = ["hakim", "müller", "schmidt", "meyer", "schulz"]
        for t in teachers:
            if t in filename:
                teacher = f"Herr/Frau {t.capitalize()}"
                break

        mock_text = f"""KLASSENARBEIT
Fach: {subject}
Lehrer: {teacher}
Datum: [OCR konnte Datum nicht lesen]
Klasse: [OCR konnte Klasse nicht lesen]

HINWEIS: Dies ist ein MOCK-TEXT.
Echter OCR-Dienst (Tesseract) nicht verfügbar.
Bitte installieren Sie: pip install pytesseract pdf2image
Und: apt-get install tesseract-ocr tesseract-ocr-deu poppler-utils

Aufgabe 1 (10 Punkte)
[OCR-Text hier einfügen]

Aufgabe 2 (15 Punkte)
[OCR-Text hier einfügen]

Aufgabe 3 (10 Punkte)
[OCR-Text hier einfügen]

Gesamtpunktzahl: 35 Punkte
"""

        return OCRResult(
            text=mock_text,
            confidence=0.3,  # Low confidence for mock
            model_used="mock",
            pages=1,
            warnings=[
                "Using mock OCR - Tesseract not installed",
                "Install real OCR: pip install pytesseract pdf2image",
                "System dependency: apt-get install tesseract-ocr tesseract-ocr-deu",
            ],
        )


# ============================================================================
# Utility Functions
# ============================================================================

def compute_content_hash(file_path: Union[str, Path]) -> str:
    """Compute MD5 hash of file content for duplicate detection"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


# ============================================================================
# Global Instance
# ============================================================================

# Create global OCR engine instance
_ocr_engine: Optional[OCREngine] = None


def get_ocr_engine() -> OCREngine:
    """Get or create global OCR engine instance"""
    global _ocr_engine
    if _ocr_engine is None:
        _ocr_engine = OCREngine()
    return _ocr_engine


async def perform_ocr(file_path: Union[str, Path]) -> OCRResult:
    """
    Convenience function to perform OCR on a file.

    Usage:
        result = await perform_ocr("/path/to/exam.pdf")
        print(result.text)
    """
    engine = get_ocr_engine()
    return await engine.process_file(file_path)

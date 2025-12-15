"""
RyxHub OCR Module
Provides real OCR capabilities using Tesseract, with Claude Vision fallback
"""

from .engine import OCREngine, OCRResult
from .processors import process_pdf, process_image

__all__ = [
    "OCREngine",
    "OCRResult",
    "process_pdf",
    "process_image",
]

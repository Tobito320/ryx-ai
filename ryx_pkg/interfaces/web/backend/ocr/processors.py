"""
RyxHub OCR Processors
Helper functions for processing PDFs and images
"""

import os
import io
import tempfile
from pathlib import Path
from typing import Union, List, Optional, BinaryIO
import asyncio

from .engine import OCREngine, OCRResult, get_ocr_engine, compute_content_hash


async def process_pdf(
    file_data: Union[bytes, BinaryIO, str, Path],
    filename: Optional[str] = None,
) -> OCRResult:
    """
    Process a PDF file and extract text.

    Args:
        file_data: PDF content as bytes, file object, or path
        filename: Optional filename for logging

    Returns:
        OCRResult with extracted text
    """
    engine = get_ocr_engine()

    # If path, process directly
    if isinstance(file_data, (str, Path)):
        return await engine.process_file(file_data)

    # Write to temp file for processing
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        if isinstance(file_data, bytes):
            tmp.write(file_data)
        else:
            tmp.write(file_data.read())
        tmp_path = tmp.name

    try:
        result = await engine.process_file(tmp_path)
        return result
    finally:
        # Clean up temp file
        os.unlink(tmp_path)


async def process_image(
    file_data: Union[bytes, BinaryIO, str, Path],
    filename: Optional[str] = None,
) -> OCRResult:
    """
    Process an image file and extract text.

    Args:
        file_data: Image content as bytes, file object, or path
        filename: Optional filename for determining format

    Returns:
        OCRResult with extracted text
    """
    engine = get_ocr_engine()

    # If path, process directly
    if isinstance(file_data, (str, Path)):
        return await engine.process_file(file_data)

    # Determine suffix from filename
    suffix = ".png"
    if filename:
        ext = Path(filename).suffix.lower()
        if ext in [".jpg", ".jpeg", ".png", ".webp", ".tiff", ".bmp"]:
            suffix = ext

    # Write to temp file for processing
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        if isinstance(file_data, bytes):
            tmp.write(file_data)
        else:
            tmp.write(file_data.read())
        tmp_path = tmp.name

    try:
        result = await engine.process_file(tmp_path)
        return result
    finally:
        # Clean up temp file
        os.unlink(tmp_path)


async def process_upload(
    file_data: Union[bytes, BinaryIO],
    filename: str,
    content_type: str,
) -> dict:
    """
    Process an uploaded file (auto-detect PDF vs image).

    Args:
        file_data: File content
        filename: Original filename
        content_type: MIME type

    Returns:
        dict with:
            - ocr_result: OCRResult
            - content_hash: MD5 hash
            - file_type: "pdf" or "image"
    """
    # Determine file type
    is_pdf = (
        content_type == "application/pdf"
        or filename.lower().endswith(".pdf")
    )

    # Write to temp file
    suffix = ".pdf" if is_pdf else Path(filename).suffix or ".png"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        if isinstance(file_data, bytes):
            tmp.write(file_data)
        else:
            tmp.write(file_data.read())
        tmp_path = tmp.name

    try:
        # Compute hash for duplicate detection
        content_hash = compute_content_hash(tmp_path)

        # Process with OCR
        engine = get_ocr_engine()
        ocr_result = await engine.process_file(tmp_path)

        return {
            "ocr_result": ocr_result,
            "content_hash": content_hash,
            "file_type": "pdf" if is_pdf else "image",
            "temp_path": tmp_path,  # Caller should clean up
        }

    except Exception as e:
        # Clean up on error
        os.unlink(tmp_path)
        raise


def check_duplicate(content_hash: str, existing_hashes: List[str]) -> bool:
    """Check if content hash already exists"""
    return content_hash in existing_hashes


async def batch_process(
    files: List[tuple],  # [(file_data, filename, content_type), ...]
    max_concurrent: int = 3,
) -> List[dict]:
    """
    Process multiple files concurrently.

    Args:
        files: List of (file_data, filename, content_type) tuples
        max_concurrent: Maximum concurrent OCR operations

    Returns:
        List of process_upload results
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async def process_with_limit(file_data, filename, content_type):
        async with semaphore:
            return await process_upload(file_data, filename, content_type)

    tasks = [
        process_with_limit(file_data, filename, content_type)
        for file_data, filename, content_type in files
    ]

    return await asyncio.gather(*tasks, return_exceptions=True)

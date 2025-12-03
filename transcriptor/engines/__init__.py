"""OCR Engine implementations."""

from transcriptor.engines.base import OCREngine, OCRResult
from transcriptor.engines.tesseract import TesseractEngine
from transcriptor.engines.claude import ClaudeEngine

__all__ = ["OCREngine", "OCRResult", "TesseractEngine", "ClaudeEngine"]

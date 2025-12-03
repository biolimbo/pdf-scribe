"""
PDF OCR Transcriptor

A modular OCR tool supporting Tesseract and Claude Vision AI.
"""

from transcriptor.config import Config
from transcriptor.pipeline import Pipeline

__version__ = "1.0.0"
__all__ = ["Config", "Pipeline"]

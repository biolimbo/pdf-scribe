"""
Abstract base class for OCR engines.

This module defines the interface that all OCR engines must implement,
following the Dependency Inversion Principle. High-level modules (pipeline)
depend on this abstraction, not on concrete implementations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from PIL import Image


@dataclass
class OCRResult:
    """
    Result from an OCR operation.

    Attributes:
        page_num: The page number that was processed
        text: The extracted text (None if failed)
        cleaned_text: AI-cleaned text (None if cleanup not performed)
        rotation: Rotation angle applied (Tesseract only)
        error: Error message if operation failed
    """
    page_num: int
    text: Optional[str] = None
    cleaned_text: Optional[str] = None
    rotation: int = 0
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        """Check if OCR was successful."""
        return self.text is not None and self.error is None

    @property
    def final_text(self) -> Optional[str]:
        """Get the best available text (cleaned if available, else raw)."""
        return self.cleaned_text if self.cleaned_text else self.text


class OCREngine(ABC):
    """
    Abstract base class for OCR engines.

    Implementations must provide:
    - is_available(): Check if the engine's dependencies are installed
    - process_image(): Process a single image and return extracted text
    - name: Human-readable engine name

    Optional:
    - cleanup_text(): Post-process text to fix OCR errors
    - supports_cleanup: Whether the engine supports AI text cleanup
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable engine name for display."""
        pass

    @property
    def supports_cleanup(self) -> bool:
        """Whether this engine supports AI text cleanup."""
        return False

    @property
    def supports_rotation(self) -> bool:
        """Whether this engine supports auto-rotation detection."""
        return False

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the engine's dependencies are available.

        Returns:
            True if the engine can be used, False otherwise
        """
        pass

    @abstractmethod
    def process_image(
        self,
        image: Image.Image,
        lang: str = "eng",
        reflow: bool = False,
        **kwargs
    ) -> str:
        """
        Process a single image and extract text.

        Args:
            image: PIL Image to process
            lang: Language code (e.g., 'eng', 'spa')
            reflow: Whether to reflow text into paragraphs
            **kwargs: Engine-specific options

        Returns:
            Extracted text from the image

        Raises:
            OCRError: If processing fails
        """
        pass

    def cleanup_text(
        self,
        text: str,
        lang: str = "eng",
        **kwargs
    ) -> str:
        """
        Clean up OCR text to fix errors.

        Default implementation returns text unchanged.
        Override in engines that support cleanup.

        Args:
            text: Raw OCR text
            lang: Language code
            **kwargs: Engine-specific options

        Returns:
            Cleaned text
        """
        return text

    def validate(self) -> None:
        """
        Validate that the engine is properly configured.

        Raises:
            EngineNotAvailableError: If engine dependencies are missing
        """
        if not self.is_available():
            raise EngineNotAvailableError(
                f"{self.name} engine is not available. "
                f"Please install required dependencies."
            )


class OCRError(Exception):
    """Base exception for OCR-related errors."""
    pass


class EngineNotAvailableError(OCRError):
    """Raised when an OCR engine's dependencies are not installed."""
    pass

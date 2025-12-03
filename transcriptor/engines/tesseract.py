"""
Tesseract OCR engine implementation.

This module provides OCR using the free, open-source Tesseract engine.
Best for clean scans with good contrast.
"""

import re
from typing import List, Optional, Tuple

from PIL import Image

from transcriptor.engines.base import OCREngine, OCRError

# Optional import - gracefully handle missing dependency
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    pytesseract = None
    TESSERACT_AVAILABLE = False


class TesseractEngine(OCREngine):
    """
    Tesseract OCR engine.

    Uses pytesseract to interface with the Tesseract OCR engine.
    Supports multiple languages, page segmentation modes, and auto-rotation.
    """

    def __init__(
        self,
        psm: int = 3,
        oem: int = 3,
        auto_rotate: bool = False,
        rotate_confidence: float = 5.0
    ):
        """
        Initialize the Tesseract engine.

        Args:
            psm: Page Segmentation Mode (3=auto, 6=single block, etc.)
            oem: OCR Engine Mode (0=legacy, 1=LSTM, 3=auto)
            auto_rotate: Enable auto-rotation detection
            rotate_confidence: Minimum confidence to apply rotation
        """
        self.psm = psm
        self.oem = oem
        self.auto_rotate = auto_rotate
        self.rotate_confidence = rotate_confidence

    @property
    def name(self) -> str:
        return "Tesseract"

    @property
    def supports_rotation(self) -> bool:
        return True

    def is_available(self) -> bool:
        return TESSERACT_AVAILABLE

    def get_available_languages(self) -> List[str]:
        """Get list of available Tesseract languages."""
        if not self.is_available():
            return ["eng"]
        try:
            return pytesseract.get_languages()
        except Exception:
            return ["eng"]

    def validate_language(self, lang: str) -> str:
        """
        Validate and potentially fix a language specification.

        Args:
            lang: Language code(s), e.g., 'eng' or 'spa+eng'

        Returns:
            Valid language specification
        """
        available = self.get_available_languages()
        langs_to_check = lang.split("+")

        for l in langs_to_check:
            if l not in available:
                print(f"⚠️  WARNING: Language '{l}' not available in Tesseract")
                print(f"   Available: {', '.join(sorted(available))}")
                if "eng" in available:
                    print("   Falling back to 'eng'...")
                    return "eng"
                return available[0] if available else "eng"

        return lang

    def detect_rotation(
        self,
        image: Image.Image
    ) -> Tuple[Image.Image, int]:
        """
        Detect and correct page orientation using Tesseract OSD.

        Args:
            image: PIL Image to analyze

        Returns:
            Tuple of (potentially rotated image, rotation angle applied)
        """
        if not self.auto_rotate:
            return image, 0

        try:
            osd_output = pytesseract.image_to_osd(image)

            # Parse rotation angle
            rotate_match = re.search(r'Rotate:\s*(\d+)', osd_output)
            confidence_match = re.search(
                r'Orientation confidence:\s*([\d.]+)',
                osd_output
            )

            confidence = (
                float(confidence_match.group(1))
                if confidence_match else 0
            )

            if rotate_match:
                angle = int(rotate_match.group(1))
                if angle != 0 and confidence >= self.rotate_confidence:
                    image = image.rotate(-angle, expand=True)
                    return image, angle

            return image, 0

        except Exception:
            # OSD can fail on poor quality images
            return image, 0

    def process_image(
        self,
        image: Image.Image,
        lang: str = "eng",
        reflow: bool = False,
        **kwargs
    ) -> str:
        """
        Process an image with Tesseract OCR.

        Args:
            image: PIL Image to process
            lang: Tesseract language code
            reflow: Ignored (Tesseract doesn't support this)
            **kwargs: Additional Tesseract config options

        Returns:
            Extracted text

        Raises:
            OCRError: If Tesseract is not available
        """
        if not self.is_available():
            raise OCRError(
                "Tesseract not available. "
                "Install: pip install pytesseract && brew install tesseract"
            )

        # Build config string
        config = f"--psm {self.psm} --oem {self.oem}"

        # Add any additional config from kwargs
        if "config" in kwargs:
            config = f"{config} {kwargs['config']}"

        try:
            text = pytesseract.image_to_string(image, lang=lang, config=config)
            return text
        except Exception as e:
            raise OCRError(f"Tesseract processing failed: {e}")

    def process_with_rotation(
        self,
        image: Image.Image,
        lang: str = "eng",
        **kwargs
    ) -> Tuple[str, int]:
        """
        Process an image with optional auto-rotation.

        Args:
            image: PIL Image to process
            lang: Language code
            **kwargs: Additional options

        Returns:
            Tuple of (extracted text, rotation angle applied)
        """
        # Detect and apply rotation first
        image, rotation = self.detect_rotation(image)

        # Then OCR
        text = self.process_image(image, lang=lang, **kwargs)

        return text, rotation

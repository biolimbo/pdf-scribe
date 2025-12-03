"""
Claude Vision AI OCR engine implementation.

This module provides OCR using Anthropic's Claude Vision API.
Best for degraded documents, handwriting, and complex layouts.
"""

import base64
import io
from typing import Optional

from PIL import Image

from transcriptor.engines.base import OCREngine, OCRError
from transcriptor.config import LANGUAGE_NAMES, ClaudeModels

# Optional import - gracefully handle missing dependency
try:
    import anthropic
    CLAUDE_AVAILABLE = True
except ImportError:
    anthropic = None
    CLAUDE_AVAILABLE = False


class ClaudeEngine(OCREngine):
    """
    Claude Vision AI OCR engine.

    Uses Anthropic's Claude API for vision-based text extraction.
    Supports text reflow, multi-language OCR, and AI-powered cleanup.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        client: Optional["anthropic.Anthropic"] = None
    ):
        """
        Initialize the Claude engine.

        Args:
            model: Claude model to use (default from config)
            client: Pre-configured Anthropic client (creates one if not provided)
        """
        self.model = model or ClaudeModels.DEFAULT
        self._client = client

    @property
    def client(self) -> "anthropic.Anthropic":
        """Lazily initialize the Anthropic client."""
        if self._client is None:
            if not self.is_available():
                raise OCRError("Anthropic library not installed")
            self._client = anthropic.Anthropic()
        return self._client

    @property
    def name(self) -> str:
        return f"Claude Vision AI ({self.model})"

    @property
    def supports_cleanup(self) -> bool:
        return True

    def is_available(self) -> bool:
        return CLAUDE_AVAILABLE

    @staticmethod
    def image_to_base64(image: Image.Image) -> str:
        """Convert PIL Image to base64 string."""
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return base64.standard_b64encode(buffer.getvalue()).decode("utf-8")

    def _build_ocr_prompt(self, lang: str, reflow: bool) -> str:
        """
        Build the OCR prompt based on settings.

        Args:
            lang: Language code
            reflow: Whether to reflow text into paragraphs

        Returns:
            Prompt string for Claude
        """
        lang_name = LANGUAGE_NAMES.get(lang, lang)

        if reflow:
            return f"""Transcribe ALL the text from this scanned document image.

Instructions:
- This is a scanned document in {lang_name}
- Transcribe every word, number, and punctuation mark exactly as shown
- REFLOW the text into logical paragraphs - do NOT preserve the original line breaks
- Join lines that are part of the same sentence or paragraph into flowing text
- Start new paragraphs only where there is a logical break (new section, new topic, numbered clauses like "PRIMERO:", "SEGUNDO:", etc.)
- Preserve section headers and numbered items on their own lines
- If text is faded or unclear, make your best interpretation based on context
- Ignore any highlighter marks, stamps, or non-text elements
- Do NOT add any commentary, notes, or headers - only output the transcribed text
- Do NOT add titles like "TRANSCRIBED TEXT", "DOCUMENTO TRANSCRITO", or similar
- Do NOT translate - keep the original language
- Start directly with the document content

Output ONLY the transcribed text:"""
        else:
            return f"""Transcribe ALL the text from this scanned document image exactly as it appears.

Instructions:
- This is a scanned document in {lang_name}
- Transcribe every word, number, and punctuation mark exactly as shown
- Preserve the original paragraph structure
- If text is faded or unclear, make your best interpretation based on context
- Ignore any highlighter marks, stamps, or non-text elements
- Do NOT add any commentary, notes, or headers - only output the transcribed text
- Do NOT add titles like "TRANSCRIBED TEXT", "DOCUMENTO TRANSCRITO", or similar
- Do NOT translate - keep the original language
- Start directly with the document content

Output ONLY the transcribed text:"""

    def _build_cleanup_prompt(self, text: str, lang: str) -> str:
        """
        Build the cleanup prompt.

        Args:
            text: Raw OCR text to clean
            lang: Language code

        Returns:
            Cleanup prompt string
        """
        lang_name = LANGUAGE_NAMES.get(lang, lang)

        return f"""Clean up this OCR-transcribed text in {lang_name}. Fix obvious errors while preserving the EXACT meaning and structure.

Rules:
- Fix character recognition errors (e.g., "rn" that should be "m", "1" that should be "l")
- Fix broken words and sentences
- Fix punctuation and accents
- Preserve ALL original content - do not add, remove, or paraphrase anything
- Keep the same paragraph structure
- If unsure about a word, keep the original
- Do NOT translate or summarize
- Do NOT add any commentary

Original text:
{text}

Cleaned text:"""

    def process_image(
        self,
        image: Image.Image,
        lang: str = "eng",
        reflow: bool = False,
        **kwargs
    ) -> str:
        """
        Process an image with Claude Vision.

        Args:
            image: PIL Image to process
            lang: Language code for the document
            reflow: Whether to reflow text into paragraphs
            **kwargs: Additional options (e.g., max_tokens)

        Returns:
            Extracted text

        Raises:
            OCRError: If Claude API call fails
        """
        if not self.is_available():
            raise OCRError(
                "Anthropic library not installed. "
                "Run: pip install anthropic"
            )

        image_data = self.image_to_base64(image)
        prompt = self._build_ocr_prompt(lang, reflow)
        max_tokens = kwargs.get("max_tokens", 4096)

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
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
                                "text": prompt,
                            }
                        ],
                    }
                ],
            )
            return message.content[0].text
        except Exception as e:
            raise OCRError(f"Claude API call failed: {e}")

    def cleanup_text(
        self,
        text: str,
        lang: str = "eng",
        **kwargs
    ) -> str:
        """
        Clean up OCR text using Claude.

        Args:
            text: Raw OCR text
            lang: Language code
            **kwargs: Additional options (e.g., max_tokens, model)

        Returns:
            Cleaned text

        Raises:
            OCRError: If cleanup fails
        """
        if not self.is_available():
            raise OCRError("Anthropic library not installed")

        prompt = self._build_cleanup_prompt(text, lang)
        max_tokens = kwargs.get("max_tokens", 4096)
        model = kwargs.get("model", self.model)

        try:
            message = self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )
            return message.content[0].text
        except Exception as e:
            raise OCRError(f"Claude cleanup failed: {e}")

    def process_with_cleanup(
        self,
        image: Image.Image,
        lang: str = "eng",
        reflow: bool = False,
        cleanup_model: Optional[str] = None,
        **kwargs
    ) -> tuple[str, Optional[str]]:
        """
        Process an image and optionally clean up the result.

        This is the pipelined approach - OCR immediately followed by cleanup.

        Args:
            image: PIL Image to process
            lang: Language code
            reflow: Whether to reflow text
            cleanup_model: Model to use for cleanup (defaults to same as OCR)
            **kwargs: Additional options

        Returns:
            Tuple of (raw_text, cleaned_text)
        """
        # Step 1: OCR
        raw_text = self.process_image(image, lang=lang, reflow=reflow, **kwargs)

        # Step 2: Cleanup (if model provided)
        cleaned_text = None
        if cleanup_model and raw_text:
            cleaned_text = self.cleanup_text(
                raw_text,
                lang=lang,
                model=cleanup_model,
                **kwargs
            )

        return raw_text, cleaned_text

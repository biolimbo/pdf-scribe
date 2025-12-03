"""
Configuration and constants for the OCR transcriptor.

This module centralizes all configuration, making it easy to:
- Override settings via environment variables
- Add new preprocessing modes or engines
- Adjust tier-based concurrency limits
"""

import os
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Optional

# Load .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class Engine(StrEnum):
    """Supported OCR engines."""
    TESSERACT = "tesseract"
    CLAUDE = "claude"


class PreprocessMode(StrEnum):
    """Image preprocessing modes."""
    NONE = "none"
    GRAYSCALE = "grayscale"
    BINARIZE = "binarize"
    CONTRAST = "contrast"
    SHARPEN = "sharpen"
    DENOISE = "denoise"
    REMOVE_RED = "remove-red"
    REMOVE_BLUE = "remove-blue"
    SOFT = "soft"
    CLEAN = "clean"
    ALL = "all"


# Preprocessing descriptions for CLI help
PREPROCESS_DESCRIPTIONS = {
    PreprocessMode.NONE: "No preprocessing",
    PreprocessMode.GRAYSCALE: "Convert to grayscale",
    PreprocessMode.BINARIZE: "Convert to black/white (good for faded text)",
    PreprocessMode.CONTRAST: "Enhance contrast",
    PreprocessMode.SHARPEN: "Sharpen edges",
    PreprocessMode.DENOISE: "Remove noise/speckles",
    PreprocessMode.REMOVE_RED: "Remove red highlights/marks only",
    PreprocessMode.REMOVE_BLUE: "Remove blue highlights/marks only",
    PreprocessMode.SOFT: "Remove red + contrast + sharpen (NO binarization)",
    PreprocessMode.CLEAN: "Remove red + all enhancements including binarization",
    PreprocessMode.ALL: "Apply all preprocessing (no highlight removal)",
}


# Tesseract Page Segmentation Modes
PSM_MODES = {
    3: "Fully automatic page segmentation (default)",
    4: "Assume single column of variable sizes",
    6: "Assume single uniform block of text",
    11: "Sparse text - find as much text as possible",
    12: "Sparse text with OSD",
}


# Language code to full name mapping
LANGUAGE_NAMES = {
    "spa": "Spanish",
    "eng": "English",
    "fra": "French",
    "deu": "German",
    "por": "Portuguese",
    "ita": "Italian",
}


class ClaudeModels:
    """Claude model configuration."""
    DEFAULT = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5-20250929")
    CHEAPO = os.getenv("CLAUDE_CHEAPO_MODEL", "claude-haiku-4-5-20251001")
    EXPENSIVE = os.getenv("CLAUDE_EXPENSIVE_MODEL", "claude-opus-4-5-20251101")


class TierConfig:
    """
    API tier configuration for optimal concurrency.

    Anthropic API tiers and their rate limits:
    - Tier 1: 50 RPM
    - Tier 2: 1000 RPM
    - Tier 3: 2000 RPM
    - Tier 4: 4000 RPM
    """
    TIER = int(os.getenv("ANTHROPIC_TIER", "1"))

    # Aggressive worker counts (80% of RPM limit)
    WORKERS = {
        1: 40,
        2: 800,
        3: 1600,
        4: 3200,
    }

    @classmethod
    def get_workers(cls) -> int:
        """Get the optimal number of workers for the current tier."""
        return cls.WORKERS.get(cls.TIER, 40)


@dataclass
class Config:
    """
    Main configuration container.

    Encapsulates all settings for a transcription run, making it easy
    to pass around and modify settings without long parameter lists.
    """
    # Input/Output
    pdf_path: str = ""
    output_path: Optional[str] = None
    title: Optional[str] = None

    # Engine selection
    engine: Engine = Engine.TESSERACT

    # Claude-specific
    cheapo: bool = False
    expensive: bool = False
    cleanup: bool = False
    reflow: bool = False

    # Processing settings
    dpi: int = 150
    lang: str = "eng"
    workers: int = 1
    batch_size: int = 20

    # Page selection
    pages: Optional[str] = None
    first_n: Optional[int] = None

    # Preprocessing
    preprocess: PreprocessMode = PreprocessMode.NONE
    binarize_threshold: int = 140

    # Tesseract-specific
    psm: int = 3
    oem: int = 3
    auto_rotate: bool = False
    rotate_confidence: float = 5.0

    @property
    def claude_model(self) -> str:
        """Get the appropriate Claude model based on mode flags."""
        if self.expensive:
            return ClaudeModels.EXPENSIVE
        elif self.cheapo:
            return ClaudeModels.CHEAPO
        return ClaudeModels.DEFAULT

    @property
    def effective_workers(self) -> int:
        """Get effective worker count, using tier-based defaults for Claude."""
        if self.engine == Engine.CLAUDE and self.workers == 1:
            return TierConfig.get_workers()
        return self.workers

    @property
    def language_name(self) -> str:
        """Get full language name for prompts."""
        return LANGUAGE_NAMES.get(self.lang, self.lang)

    @property
    def mode_suffix(self) -> str:
        """Get mode suffix for display."""
        if self.expensive:
            return " [expensive mode]"
        elif self.cheapo:
            return " [cheapo mode]"
        return ""

    def apply_enhance_preset(self) -> None:
        """Apply the --enhance preset settings."""
        self.preprocess = PreprocessMode.ALL
        self.auto_rotate = True
        if self.dpi == 150:  # Only override if default
            self.dpi = 300

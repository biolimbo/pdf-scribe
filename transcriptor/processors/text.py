"""
Text processing module.

Provides utilities for text formatting and document assembly.
"""

from pathlib import Path
from typing import Dict, Optional


class TextProcessor:
    """
    Text processing and document assembly.

    Handles formatting OCR results into markdown documents
    with proper headers, page breaks, and metadata.
    """

    @staticmethod
    def build_header(
        title: str,
        source_file: str,
        engine_name: str,
        lang: str,
        dpi: int,
        preprocess: str,
        reflow: bool = False
    ) -> str:
        """
        Build the document header with metadata.

        Args:
            title: Document title
            source_file: Original PDF filename
            engine_name: OCR engine used
            lang: Language code
            dpi: DPI setting used
            preprocess: Preprocessing mode
            reflow: Whether text reflow was enabled

        Returns:
            Formatted markdown header
        """
        reflow_note = (
            "\n> - **Text reflow:** Enabled (paragraphs reformatted)"
            if reflow else ""
        )

        return f"""# {title}

---

> **NOTE:** This document was generated via OCR (Optical Character Recognition)
> from a scanned PDF. It may contain transcription errors.
> Refer to the original document for legal purposes.
>
> - **Source file:** {source_file}
> - **OCR Engine:** {engine_name}
> - **Language:** {lang}
> - **DPI:** {dpi}
> - **Preprocessing:** {preprocess}{reflow_note}

---

"""

    @staticmethod
    def format_page(page_num: int, text: str) -> str:
        """
        Format a single page's text for the document.

        Args:
            page_num: Page number
            text: Page text content

        Returns:
            Formatted page markdown
        """
        return f"\n---\n\n## Page {page_num}\n\n{text}\n"

    @staticmethod
    def merge_pages(
        header: str,
        pages: Dict[int, str]
    ) -> str:
        """
        Merge all pages into a single document.

        Args:
            header: Document header
            pages: Dict mapping page numbers to text

        Returns:
            Complete merged document
        """
        parts = [header]
        for page_num in sorted(pages.keys()):
            parts.append(TextProcessor.format_page(page_num, pages[page_num]))
        return "".join(parts)

    @staticmethod
    def save_page(
        folder: Path,
        page_num: int,
        text: str,
        suffix: str = ""
    ) -> Path:
        """
        Save a single page to a file.

        Args:
            folder: Output folder
            page_num: Page number
            text: Page text
            suffix: Optional suffix (e.g., "_clean")

        Returns:
            Path to the saved file
        """
        filename = f"page_{page_num:03d}{suffix}.md"
        filepath = folder / filename

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"## Page {page_num}\n\n{text}\n")

        return filepath

    @staticmethod
    def save_document(
        path: Path,
        content: str
    ) -> Path:
        """
        Save a complete document.

        Args:
            path: Output path
            content: Document content

        Returns:
            Path to the saved file
        """
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    @staticmethod
    def get_statistics(text: str) -> Dict[str, int]:
        """
        Calculate document statistics.

        Args:
            text: Document text

        Returns:
            Dict with character count, word count, etc.
        """
        return {
            "characters": len(text),
            "words": len(text.split()),
            "lines": text.count("\n") + 1,
        }

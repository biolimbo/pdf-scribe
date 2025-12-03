"""
PDF utilities module.

Provides utilities for PDF handling including page counting,
page selection parsing, and efficient image conversion.
"""

from pathlib import Path
from typing import List, Tuple, Iterator

from PIL import Image

try:
    from pdf2image import convert_from_path
    from pdf2image.pdf2image import pdfinfo_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False


class PDFError(Exception):
    """PDF-related errors."""
    pass


class PDFUtils:
    """
    PDF handling utilities.

    Provides efficient methods for working with PDF files,
    including smart page conversion that only converts needed pages.
    """

    @staticmethod
    def is_available() -> bool:
        """Check if pdf2image is available."""
        return PDF2IMAGE_AVAILABLE

    @staticmethod
    def get_page_count(pdf_path: Path) -> int:
        """
        Get the total number of pages in a PDF.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Number of pages

        Raises:
            PDFError: If page count cannot be determined
        """
        if not PDF2IMAGE_AVAILABLE:
            raise PDFError("pdf2image not installed")

        try:
            info = pdfinfo_from_path(str(pdf_path))
            return info["Pages"]
        except Exception as e:
            raise PDFError(f"Could not get page count: {e}")

    @staticmethod
    def parse_page_range(page_spec: str, total_pages: int) -> List[int]:
        """
        Parse a page specification into a list of page numbers.

        Supports formats:
        - Single page: "5"
        - Range: "1-5"
        - Multiple: "1,3,7"
        - Combined: "1-3,7,10-12"

        Args:
            page_spec: Page specification string
            total_pages: Total number of pages in the document

        Returns:
            Sorted list of unique page numbers
        """
        pages = set()

        for part in page_spec.split(','):
            part = part.strip()
            if '-' in part:
                # Range like "1-5"
                start, end = part.split('-', 1)
                start = int(start.strip())
                end = int(end.strip())
                for p in range(start, min(end + 1, total_pages + 1)):
                    if p >= 1:
                        pages.add(p)
            else:
                # Single page
                p = int(part)
                if 1 <= p <= total_pages:
                    pages.add(p)

        return sorted(pages)

    @staticmethod
    def is_contiguous(pages: List[int]) -> bool:
        """
        Check if a list of pages is contiguous.

        Args:
            pages: Sorted list of page numbers

        Returns:
            True if pages form a contiguous range
        """
        if not pages:
            return True
        return pages == list(range(min(pages), max(pages) + 1))

    @staticmethod
    def convert_pages(
        pdf_path: Path,
        pages: List[int],
        dpi: int = 150
    ) -> List[Tuple[int, Image.Image]]:
        """
        Convert specific PDF pages to images efficiently.

        Uses single conversion for contiguous ranges, individual
        conversions for non-contiguous pages.

        Args:
            pdf_path: Path to the PDF file
            pages: List of page numbers to convert
            dpi: Resolution for conversion

        Returns:
            List of (page_num, image) tuples
        """
        if not PDF2IMAGE_AVAILABLE:
            raise PDFError("pdf2image not installed")

        if not pages:
            return []

        result = []

        # Check if pages are contiguous
        if PDFUtils.is_contiguous(pages):
            # Single conversion call for efficiency
            images = convert_from_path(
                str(pdf_path),
                dpi=dpi,
                first_page=min(pages),
                last_page=max(pages)
            )
            result = list(zip(pages, images))
        else:
            # Convert each page individually
            for page_num in pages:
                images = convert_from_path(
                    str(pdf_path),
                    dpi=dpi,
                    first_page=page_num,
                    last_page=page_num
                )
                if images:
                    result.append((page_num, images[0]))

        return result

    @staticmethod
    def convert_pages_iter(
        pdf_path: Path,
        pages: List[int],
        dpi: int = 150
    ) -> Iterator[Tuple[int, Image.Image]]:
        """
        Convert PDF pages to images as a generator.

        Memory-efficient for large documents.

        Args:
            pdf_path: Path to the PDF file
            pages: List of page numbers to convert
            dpi: Resolution for conversion

        Yields:
            (page_num, image) tuples
        """
        if not PDF2IMAGE_AVAILABLE:
            raise PDFError("pdf2image not installed")

        for page_num in pages:
            images = convert_from_path(
                str(pdf_path),
                dpi=dpi,
                first_page=page_num,
                last_page=page_num
            )
            if images:
                yield (page_num, images[0])

    @staticmethod
    def convert_single_page(
        pdf_path: Path,
        page_num: int,
        dpi: int = 150
    ) -> Image.Image:
        """
        Convert a single PDF page to an image.

        Args:
            pdf_path: Path to the PDF file
            page_num: Page number to convert
            dpi: Resolution for conversion

        Returns:
            PIL Image

        Raises:
            PDFError: If conversion fails
        """
        if not PDF2IMAGE_AVAILABLE:
            raise PDFError("pdf2image not installed")

        try:
            images = convert_from_path(
                str(pdf_path),
                dpi=dpi,
                first_page=page_num,
                last_page=page_num
            )
            if images:
                return images[0]
            raise PDFError(f"No image returned for page {page_num}")
        except Exception as e:
            raise PDFError(f"Failed to convert page {page_num}: {e}")

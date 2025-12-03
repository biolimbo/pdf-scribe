"""
Command Line Interface module.

Provides the argument parser and CLI entry point for the OCR transcriptor.
Separates CLI concerns from the core processing logic.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

from transcriptor.config import (
    Config,
    Engine,
    PreprocessMode,
    PREPROCESS_DESCRIPTIONS,
    PSM_MODES,
)
from transcriptor.engines.tesseract import TesseractEngine
from transcriptor.pipeline import Pipeline


def get_cpu_count() -> int:
    """Get number of available CPUs for parallel processing."""
    try:
        count = os.cpu_count()
        return max(1, count - 1) if count and count > 1 else 1
    except Exception:
        return 1


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        description="Transcribe scanned PDF documents to text using OCR.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Document Selection:
  - Single file:  %(prog)s document.pdf
  - Batch mode:   %(prog)s  (processes all PDFs in input/ folder)

  Place PDFs in the input/ folder and run without arguments to process
  all files automatically. Results are saved to output/<document_name>/

Examples:
  # Batch process all PDFs in input/ folder
  %(prog)s --engine claude --lang spa

  # Basic usage with Tesseract (free, local)
  %(prog)s document.pdf

  # Use Claude Vision AI for best quality (requires API key)
  %(prog)s document.pdf --engine claude --lang spa

  # Claude with preprocessing for highlighted docs
  %(prog)s document.pdf --engine claude --preprocess remove-red

  # For poor quality scans with Tesseract (does everything)
  %(prog)s document.pdf --enhance --lang spa

  # Or manually specify Tesseract options
  %(prog)s document.pdf --dpi 300 --lang spa --preprocess all --rotate

  # Fast parallel processing with all enhancements
  %(prog)s document.pdf --enhance --lang spa --workers auto

  # Fix rotated pages
  %(prog)s document.pdf --rotate

  # Fine-tuned for specific document types
  %(prog)s document.pdf --psm 6 --preprocess binarize  # Single text block
  %(prog)s document.pdf --psm 4 --preprocess contrast  # Single column

  # Trial runs with specific pages (test settings before full run)
  %(prog)s document.pdf --first 3 --engine claude       # First 3 pages only
  %(prog)s document.pdf --pages 5 --engine claude       # Just page 5
  %(prog)s document.pdf --pages 1,5,10 --preprocess soft # Pages 1, 5, and 10
  %(prog)s document.pdf --pages 1-3,7,10-12             # Ranges and specific pages

OCR Engines:
  tesseract - Free, local OCR (default). Good for clean scans.
  claude    - Claude Vision AI. Best for degraded/typewritten documents.
              Requires: pip install anthropic python-dotenv
              Set ANTHROPIC_API_KEY in .env file or environment

Preprocessing options:
  none       - No preprocessing (fastest)
  grayscale  - Convert to grayscale
  binarize   - Black/white (good for faded text)
  contrast   - Enhance contrast
  sharpen    - Sharpen edges
  denoise    - Remove noise/speckles
  remove-red - Remove red highlights/marks
  clean      - Remove red + all enhancements (BEST for highlighted docs)
  all        - All enhancements without highlight removal

PSM (Page Segmentation Modes):
  3  - Fully automatic (default)
  4  - Single column of variable sizes
  6  - Single uniform block of text
  11 - Sparse text (find as much as possible)

Tips for poor quality scans:
  1. Use --enhance (shortcut for --dpi 300 --preprocess all --rotate)
  2. Use --lang spa for Spanish documents
  3. Use --workers auto to speed up processing
  4. Try --psm 6 if the page has a simple layout
        """
    )

    # Positional argument
    parser.add_argument(
        "pdf",
        nargs="?",
        help="Path to PDF file. If omitted, processes all PDFs in input/ folder"
    )

    # Engine selection
    parser.add_argument(
        "-e", "--engine",
        choices=["tesseract", "claude"],
        default="tesseract",
        help="OCR engine to use (default: tesseract). "
             "Use 'claude' for Claude Vision AI (requires ANTHROPIC_API_KEY)"
    )

    # Output options
    parser.add_argument(
        "-o", "--output",
        help="Output file path (default: same name with .md extension)"
    )

    parser.add_argument(
        "--title",
        help="Custom document title for the output header"
    )

    # Processing options
    parser.add_argument(
        "--dpi",
        type=int,
        default=150,
        help="DPI resolution for PDF conversion (default: 150). "
             "Use 300+ for poor quality scans"
    )

    parser.add_argument(
        "-l", "--lang",
        default="eng",
        help="Tesseract language code (default: eng). "
             "Use '+' for multiple: 'eng+spa'"
    )

    parser.add_argument(
        "-w", "--workers",
        default="1",
        help="Number of parallel workers. For Tesseract: 'auto' = CPU count. "
             "For Claude: default uses tier-based concurrency (set ANTHROPIC_TIER in .env). "
             "Tier 1=40, Tier 2=800, Tier 3=1600, Tier 4=3200 concurrent requests"
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=20,
        help="Pages per batch in sequential mode (default: 20)"
    )

    # Page selection
    parser.add_argument(
        "--pages",
        help="Specific pages to process. Examples: '1-5', '1,3,7', '5', '1-3,7,10-12'"
    )

    parser.add_argument(
        "--first",
        type=int,
        metavar="N",
        help="Only process first N pages (shortcut for --pages 1-N)"
    )

    # Claude-specific options
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Post-process with AI to fix OCR errors. Creates *_clean.md files alongside raw output. "
             "Requires Claude engine or ANTHROPIC_API_KEY"
    )

    parser.add_argument(
        "--reflow",
        action="store_true",
        help="Reflow text into logical paragraphs instead of preserving original line breaks. "
             "Claude will intelligently join lines that are part of the same sentence/paragraph. "
             "Only works with --engine claude"
    )

    parser.add_argument(
        "--cheapo",
        action="store_true",
        help="Use Haiku 3.5 instead of Sonnet 4.5 (faster and cheaper, but lower quality)"
    )

    parser.add_argument(
        "--expensive",
        action="store_true",
        help="Use Opus 4 instead of Sonnet 4.5 (slower and pricier, but highest quality)"
    )

    # Preprocessing options
    parser.add_argument(
        "-p", "--preprocess",
        choices=[m.value for m in PreprocessMode],
        default="none",
        help="Image preprocessing mode (default: none). "
             "Use 'all' for poor quality scans"
    )

    parser.add_argument(
        "--enhance",
        action="store_true",
        help="Shortcut for --preprocess all --dpi 300 --rotate"
    )

    # Tesseract-specific options
    parser.add_argument(
        "-r", "--rotate",
        action="store_true",
        help="Auto-detect and correct page orientation"
    )

    parser.add_argument(
        "--rotate-confidence",
        type=float,
        default=5.0,
        help="Minimum confidence (0-10+) to apply rotation (default: 5.0). "
             "Higher = more conservative, fewer false rotations"
    )

    parser.add_argument(
        "--psm",
        type=int,
        choices=[3, 4, 6, 11, 12],
        default=3,
        help="Tesseract Page Segmentation Mode (default: 3). "
             "Use 6 for single text blocks, 11 for sparse text"
    )

    parser.add_argument(
        "--oem",
        type=int,
        choices=[0, 1, 2, 3],
        default=3,
        help="Tesseract OCR Engine Mode (default: 3=auto). "
             "0=legacy, 1=LSTM, 2=both, 3=auto"
    )

    # Utility options
    parser.add_argument(
        "--list-langs",
        action="store_true",
        help="List available Tesseract languages and exit"
    )

    parser.add_argument(
        "--list-preprocess",
        action="store_true",
        help="List preprocessing options and exit"
    )

    return parser


def parse_workers(value: str) -> int:
    """Parse workers argument to integer."""
    if value.lower() == "auto":
        return get_cpu_count()

    try:
        workers = int(value)
        return max(1, workers)
    except ValueError:
        print(f"Error: Invalid workers value '{value}'. Use a number or 'auto'")
        sys.exit(1)


def args_to_config(args: argparse.Namespace) -> Config:
    """Convert parsed arguments to Config object."""
    config = Config(
        pdf_path=args.pdf,
        output_path=args.output,
        title=args.title,
        engine=Engine(args.engine),
        dpi=args.dpi,
        lang=args.lang,
        workers=parse_workers(args.workers),
        batch_size=args.batch_size,
        pages=args.pages,
        first_n=args.first,
        cleanup=args.cleanup,
        reflow=args.reflow,
        cheapo=args.cheapo,
        expensive=args.expensive,
        preprocess=PreprocessMode(args.preprocess),
        psm=args.psm,
        oem=args.oem,
        auto_rotate=args.rotate,
        rotate_confidence=args.rotate_confidence,
    )

    # Apply --enhance preset
    if args.enhance:
        config.apply_enhance_preset()

    return config


def list_languages() -> None:
    """List available Tesseract languages."""
    engine = TesseractEngine()
    if not engine.is_available():
        print("Tesseract is not installed.")
        sys.exit(1)

    langs = engine.get_available_languages()
    print("Available Tesseract languages:")
    for lang in sorted(langs):
        print(f"  {lang}")


def list_preprocess_options() -> None:
    """List preprocessing options."""
    print("Preprocessing options:")
    for mode, desc in PREPROCESS_DESCRIPTIONS.items():
        print(f"  {mode.value:12} - {desc}")


def main() -> None:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Handle utility commands
    if args.list_langs:
        list_languages()
        sys.exit(0)

    if args.list_preprocess:
        list_preprocess_options()
        sys.exit(0)

    # Determine PDF files to process
    pdf_files = []
    if args.pdf:
        pdf_files = [args.pdf]
    else:
        # Check input/ folder for PDFs
        input_dir = Path("input")
        if input_dir.exists():
            pdf_files = sorted([str(f) for f in input_dir.glob("*.pdf")])

        if not pdf_files:
            print("No PDF specified and no PDFs found in input/ folder.")
            print("Usage: python main.py document.pdf")
            print("   or: place PDFs in input/ folder and run without arguments")
            sys.exit(1)

    # Print header
    print("=" * 50)
    print("🔍 PDF OCR TRANSCRIPTOR")
    print("=" * 50)

    if len(pdf_files) > 1:
        print(f"📚 Batch processing {len(pdf_files)} PDFs from input/ folder")
        print("-" * 50)

    # Process each PDF
    results = []
    errors = []

    for pdf_path in pdf_files:
        args.pdf = pdf_path
        config = args_to_config(args)

        if len(pdf_files) > 1:
            print(f"\n📄 Processing: {Path(pdf_path).name}")
            print("-" * 50)

        try:
            pipeline = Pipeline(config)
            result = pipeline.run()
            results.append(result)
            print(f"\n✅ Transcription complete!")
            print(f"   File: {result}")
        except FileNotFoundError as e:
            print(f"\n❌ Error: {e}")
            errors.append((pdf_path, str(e)))
        except Exception as e:
            print(f"\n❌ Error: {e}")
            errors.append((pdf_path, str(e)))

    # Print batch summary
    if len(pdf_files) > 1:
        print("\n" + "=" * 50)
        print("📊 BATCH SUMMARY")
        print("=" * 50)
        print(f"   Successful: {len(results)}/{len(pdf_files)}")
        if errors:
            print(f"   Failed: {len(errors)}")
            for path, err in errors:
                print(f"      - {Path(path).name}: {err}")

    if errors and not results:
        sys.exit(1)


if __name__ == "__main__":
    main()

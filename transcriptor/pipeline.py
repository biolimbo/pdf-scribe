"""
Pipeline orchestrator module.

Coordinates the OCR processing pipeline, handling:
- Engine selection and initialization
- Parallel processing with thread/process pools
- Result aggregation and document assembly
- Progress reporting
"""

import os
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image

from transcriptor.config import Config, Engine, TierConfig
from transcriptor.engines.base import OCREngine, OCRResult
from transcriptor.engines.tesseract import TesseractEngine
from transcriptor.engines.claude import ClaudeEngine
from transcriptor.processors.image import ImageProcessor
from transcriptor.processors.text import TextProcessor
from transcriptor.utils.pdf import PDFUtils, PDFError


class Pipeline:
    """
    OCR processing pipeline orchestrator.

    Coordinates the entire OCR workflow from PDF to markdown output,
    handling engine selection, parallel processing, and result assembly.
    """

    def __init__(self, config: Config):
        """
        Initialize the pipeline with configuration.

        Args:
            config: Configuration object with all settings
        """
        self.config = config
        self.image_processor = ImageProcessor(config.binarize_threshold)
        self.text_processor = TextProcessor()
        self._engine: Optional[OCREngine] = None

    @property
    def engine(self) -> OCREngine:
        """Lazily initialize and return the OCR engine."""
        if self._engine is None:
            self._engine = self._create_engine()
        return self._engine

    def _create_engine(self) -> OCREngine:
        """Create the appropriate OCR engine based on config."""
        if self.config.engine == Engine.CLAUDE:
            return ClaudeEngine(model=self.config.claude_model)
        else:
            return TesseractEngine(
                psm=self.config.psm,
                oem=self.config.oem,
                auto_rotate=self.config.auto_rotate,
                rotate_confidence=self.config.rotate_confidence
            )

    def validate(self) -> None:
        """
        Validate that the pipeline can run with current config.

        Raises:
            Various exceptions if validation fails
        """
        # Check PDF exists
        pdf_path = Path(self.config.pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        # Check engine availability
        self.engine.validate()

        # Validate language for Tesseract
        if self.config.engine == Engine.TESSERACT:
            tesseract = self.engine
            if isinstance(tesseract, TesseractEngine):
                self.config.lang = tesseract.validate_language(self.config.lang)

    def run(self) -> Path:
        """
        Execute the complete OCR pipeline.

        Returns:
            Path to the output file
        """
        self.validate()

        pdf_path = Path(self.config.pdf_path)
        output_path = self._get_output_path(pdf_path)

        # Print header
        self._print_header(pdf_path)

        # Get page count and determine pages to process
        try:
            total_pages = PDFUtils.get_page_count(pdf_path)
        except PDFError:
            print("⚠️  Could not determine page count")
            total_pages = 999

        pages_to_process = self._get_pages_to_process(total_pages)
        self._print_config(total_pages, pages_to_process)

        # Start timing
        start_time = time.time()

        # Process based on engine type
        if self.config.engine == Engine.CLAUDE:
            results, cleaned_results = self._process_with_claude(
                pdf_path, pages_to_process
            )
        else:
            results, cleaned_results = self._process_with_tesseract(
                pdf_path, pages_to_process
            )

        # Calculate elapsed time
        elapsed_time = time.time() - start_time

        # Build and save documents
        output_path = self._save_documents(
            pdf_path, output_path, results, cleaned_results
        )

        # Print statistics
        self._print_statistics(results, output_path, elapsed_time)

        return output_path

    def _get_output_path(self, pdf_path: Path) -> Path:
        """Determine the output path, defaulting to output/<document>/ folder."""
        if self.config.output_path:
            return Path(self.config.output_path)

        # Default to output/<document_name>/ folder
        doc_name = pdf_path.stem
        output_dir = Path("output") / doc_name
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir / f"{doc_name}.md"

    def _get_pages_to_process(self, total_pages: int) -> List[int]:
        """Determine which pages to process."""
        # Handle --first shortcut
        page_spec = self.config.pages
        if self.config.first_n and not page_spec:
            page_spec = f"1-{self.config.first_n}"

        if page_spec:
            pages = PDFUtils.parse_page_range(page_spec, total_pages)
            valid_pages = [p for p in pages if 1 <= p <= total_pages]
            if not valid_pages:
                raise ValueError(
                    f"No valid pages in range. Document has {total_pages} pages."
                )
            return valid_pages

        return list(range(1, total_pages + 1))

    def _process_with_claude(
        self,
        pdf_path: Path,
        pages: List[int]
    ) -> Tuple[Dict[int, str], Dict[int, str]]:
        """
        Process pages using Claude Vision.

        Uses ThreadPoolExecutor for parallel API calls.
        """
        results = {}
        cleaned_results = {}

        max_workers = self.config.effective_workers
        do_cleanup = self.config.cleanup

        pipeline_mode = "OCR + cleanup" if do_cleanup else "OCR only"
        print(f"\n🤖 Processing with Claude ({self.config.claude_model})"
              f"{self.config.mode_suffix}...")
        print(f"   ⚡ Pipeline: {pipeline_mode} | Tier {TierConfig.TIER} | "
              f"{max_workers} concurrent requests")

        # Convert pages to images
        print(f"   📸 Converting PDF to images...")
        page_images = PDFUtils.convert_pages(pdf_path, pages, self.config.dpi)
        print(f"   ✓ Converted {len(page_images)} pages")

        # Preprocess images
        processed_images = []
        for page_num, image in page_images:
            image = self.image_processor.process(image, self.config.preprocess)
            processed_images.append((page_num, image))

        # Create output folder for streaming (pages subfolder)
        doc_folder = self._get_output_path(pdf_path).parent
        pages_folder = doc_folder / "pages"
        pages_folder.mkdir(parents=True, exist_ok=True)
        print(f"   📁 Streaming results to: {pages_folder}/")

        # Process with thread pool
        print(f"   🔄 Processing {len(processed_images)} pages...")

        claude_engine = self.engine
        if not isinstance(claude_engine, ClaudeEngine):
            raise RuntimeError("Expected Claude engine")

        cleanup_model = self.config.claude_model if do_cleanup else None

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for page_num, image in processed_images:
                future = executor.submit(
                    self._process_claude_page,
                    claude_engine,
                    image,
                    page_num,
                    cleanup_model
                )
                futures[future] = page_num

            for future in as_completed(futures):
                page_num = futures[future]
                try:
                    result = future.result()
                    if result.success:
                        results[result.page_num] = result.text

                        # Save raw page
                        self.text_processor.save_page(
                            pages_folder, result.page_num, result.text
                        )

                        status = "✓"
                        if result.cleaned_text:
                            cleaned_results[result.page_num] = result.cleaned_text
                            self.text_processor.save_page(
                                pages_folder, result.page_num,
                                result.cleaned_text, "_clean"
                            )
                            status = "✓ +cleaned"

                        print(f"   📝 Page {result.page_num}... {status}")
                    else:
                        print(f"   📝 Page {page_num}... ⚠️ (empty)")
                except Exception as e:
                    print(f"   📝 Page {page_num}... ❌ ({e})")

        return results, cleaned_results

    def _process_claude_page(
        self,
        engine: ClaudeEngine,
        image: Image.Image,
        page_num: int,
        cleanup_model: Optional[str]
    ) -> OCRResult:
        """Process a single page with Claude."""
        try:
            raw_text, cleaned_text = engine.process_with_cleanup(
                image,
                lang=self.config.lang,
                reflow=self.config.reflow,
                cleanup_model=cleanup_model
            )
            return OCRResult(
                page_num=page_num,
                text=raw_text,
                cleaned_text=cleaned_text
            )
        except Exception as e:
            return OCRResult(page_num=page_num, error=str(e))

    def _process_with_tesseract(
        self,
        pdf_path: Path,
        pages: List[int]
    ) -> Tuple[Dict[int, str], Dict[int, str]]:
        """
        Process pages using Tesseract.

        Uses ProcessPoolExecutor for parallel processing.
        """
        results = {}
        cleaned_results = {}
        workers = self.config.workers

        tesseract_engine = self.engine
        if not isinstance(tesseract_engine, TesseractEngine):
            raise RuntimeError("Expected Tesseract engine")

        if workers > 1 and len(pages) > 1:
            results = self._process_tesseract_parallel(
                pdf_path, pages, tesseract_engine, workers
            )
        else:
            results = self._process_tesseract_sequential(
                pdf_path, pages, tesseract_engine
            )

        # Run cleanup pass if enabled (uses Claude)
        if self.config.cleanup:
            cleaned_results = self._run_tesseract_cleanup(results)

        return results, cleaned_results

    def _process_tesseract_parallel(
        self,
        pdf_path: Path,
        pages: List[int],
        engine: TesseractEngine,
        workers: int
    ) -> Dict[int, str]:
        """Process pages in parallel with Tesseract."""
        print(f"\n🚀 Using parallel processing with {workers} workers...")

        results = {}

        # Prepare arguments for multiprocessing
        # Note: We pass primitive types that can be pickled
        page_args = [
            (
                str(pdf_path), page_num, self.config.dpi, self.config.lang,
                self.config.preprocess.value, engine.psm, engine.oem,
                engine.auto_rotate, engine.rotate_confidence
            )
            for page_num in pages
        ]

        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(_process_tesseract_page, args): args[1]
                for args in page_args
            }

            for future in as_completed(futures):
                page_num = futures[future]
                try:
                    result = future.result()
                    if result.success:
                        results[result.page_num] = result.text
                        rot_info = (f" (rotated {result.rotation}°)"
                                   if result.rotation else "")
                        print(f"   📝 Page {result.page_num}...{rot_info} ✓")
                    else:
                        print(f"   📝 Page {page_num}... ⚠️ (empty)")
                except Exception as e:
                    print(f"   📝 Page {page_num}... ❌ ({e})")

        return results

    def _process_tesseract_sequential(
        self,
        pdf_path: Path,
        pages: List[int],
        engine: TesseractEngine
    ) -> Dict[int, str]:
        """Process pages sequentially with Tesseract."""
        print(f"\n🔄 Processing {len(pages)} pages sequentially...")

        results = {}

        for page_num in pages:
            print(f"   📝 Page {page_num}...", end=" ", flush=True)

            try:
                # Convert single page
                image = PDFUtils.convert_single_page(
                    pdf_path, page_num, self.config.dpi
                )

                # Auto-rotate if enabled
                rotation = 0
                if engine.auto_rotate:
                    image, rotation = engine.detect_rotation(image)
                    if rotation:
                        print(f"(rotated {rotation}°) ", end="", flush=True)

                # Preprocess
                image = self.image_processor.process(
                    image, self.config.preprocess
                )

                # OCR
                text = engine.process_image(image, lang=self.config.lang)
                results[page_num] = text
                print("✓")

            except Exception as e:
                print(f"❌ ({e})")

        return results

    def _run_tesseract_cleanup(
        self,
        results: Dict[int, str]
    ) -> Dict[int, str]:
        """Run AI cleanup on Tesseract results."""
        try:
            claude_engine = ClaudeEngine(model=self.config.claude_model)
            claude_engine.validate()
        except Exception as e:
            print(f"\n⚠️  Cleanup skipped: {e}")
            return {}

        print(f"\n🧹 Running AI cleanup ({self.config.claude_model})"
              f"{self.config.mode_suffix}...")

        cleaned_results = {}
        max_workers = self.config.effective_workers

        print(f"   🔄 Cleaning {len(results)} pages with {max_workers} threads...")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for page_num, text in results.items():
                future = executor.submit(
                    claude_engine.cleanup_text,
                    text,
                    self.config.lang
                )
                futures[future] = page_num

            for future in as_completed(futures):
                page_num = futures[future]
                try:
                    cleaned_text = future.result()
                    cleaned_results[page_num] = cleaned_text
                    print(f"   🧹 Page {page_num}... ✓")
                except Exception as e:
                    print(f"   🧹 Page {page_num}... ❌ ({e})")

        return cleaned_results

    def _save_documents(
        self,
        pdf_path: Path,
        output_path: Path,
        results: Dict[int, str],
        cleaned_results: Dict[int, str]
    ) -> Path:
        """Save the final documents."""
        # Build header
        title = self.config.title or pdf_path.stem.replace("_", " ").replace("-", " ").title()
        header = self.text_processor.build_header(
            title=title,
            source_file=pdf_path.name,
            engine_name=self.engine.name,
            lang=self.config.lang,
            dpi=self.config.dpi,
            preprocess=self.config.preprocess.value,
            reflow=self.config.reflow
        )

        # Save main document
        print(f"\n   📦 Merging {len(results)} pages into final document...")
        main_doc = self.text_processor.merge_pages(header, results)
        self.text_processor.save_document(output_path, main_doc)

        # Save cleaned document if available
        if cleaned_results:
            print(f"   📦 Creating cleaned merged document...")
            clean_doc = self.text_processor.merge_pages(header, cleaned_results)
            clean_path = output_path.parent / f"{output_path.stem}_clean.md"
            self.text_processor.save_document(clean_path, clean_doc)
            print(f"   ✓ Cleaned document: {clean_path}")

        return output_path

    def _print_header(self, pdf_path: Path) -> None:
        """Print the startup header."""
        engine_display = "Claude Vision AI" if self.config.engine == Engine.CLAUDE else "Tesseract"
        print(f"🤖 Using engine: {engine_display}")
        print(f"🌐 Language: {self.config.lang}")
        print(f"📄 Analyzing PDF: {pdf_path.name}")

    def _print_config(self, total_pages: int, pages_to_process: List[int]) -> None:
        """Print configuration details."""
        if len(pages_to_process) < total_pages:
            print(f"📚 Total pages: {total_pages} "
                  f"(processing {len(pages_to_process)}: {pages_to_process})")
        else:
            print(f"📚 Total pages: {total_pages}")

        print(f"⚙️  Config: DPI={self.config.dpi}, Language={self.config.lang}, "
              f"Workers={self.config.workers}, Engine={self.config.engine.value}")

        if self.config.engine == Engine.TESSERACT:
            print(f"🔧 Preprocessing: {self.config.preprocess.value} | "
                  f"PSM: {self.config.psm} | OEM: {self.config.oem}")
            if self.config.auto_rotate:
                print("🔄 Auto-rotation: enabled")
        else:
            print(f"🔧 Preprocessing: {self.config.preprocess.value}")

        print("-" * 50)

    def _print_statistics(
        self,
        results: Dict[int, str],
        output_path: Path,
        elapsed_time: float
    ) -> None:
        """Print final statistics including timing."""
        full_text = "\n".join(results.values())
        stats = self.text_processor.get_statistics(full_text)

        # Calculate timing stats
        pages_count = len(results)
        per_page_time = elapsed_time / pages_count if pages_count > 0 else 0
        pages_per_minute = 60 / per_page_time if per_page_time > 0 else 0

        # Format elapsed time nicely
        if elapsed_time >= 60:
            minutes = int(elapsed_time // 60)
            seconds = elapsed_time % 60
            time_str = f"{minutes}m {seconds:.1f}s"
        else:
            time_str = f"{elapsed_time:.1f}s"

        print("\n" + "=" * 50)
        print("📊 STATISTICS")
        print("=" * 50)
        print(f"   Pages processed: {pages_count}")
        print(f"   Total time: {time_str}")
        print(f"   Rate: {per_page_time:.2f}s/page ({pages_per_minute:.1f} pages/min)")
        print(f"   Total characters: {stats['characters']:,}")
        print(f"   Approximate words: {stats['words']:,}")
        print(f"   Output file: {output_path}")
        print(f"   Size: {output_path.stat().st_size / 1024:.1f} KB")
        print("=" * 50)


# Module-level function for multiprocessing (must be picklable)
def _process_tesseract_page(args: tuple) -> OCRResult:
    """
    Process a single page with Tesseract.

    This function runs in a separate process and must be at module level
    to be picklable by multiprocessing.
    """
    (pdf_path, page_num, dpi, lang, preprocess,
     psm, oem, auto_rotate, rotate_confidence) = args

    try:
        from pdf2image import convert_from_path
        from transcriptor.engines.tesseract import TesseractEngine
        from transcriptor.processors.image import ImageProcessor
        from transcriptor.config import PreprocessMode

        # Convert page
        images = convert_from_path(
            pdf_path, dpi=dpi,
            first_page=page_num, last_page=page_num
        )

        if not images:
            return OCRResult(page_num=page_num, error="No image returned")

        image = images[0]
        rotation = 0

        # Create engine for this process
        engine = TesseractEngine(
            psm=psm, oem=oem,
            auto_rotate=auto_rotate,
            rotate_confidence=rotate_confidence
        )

        # Auto-rotate
        if auto_rotate:
            image, rotation = engine.detect_rotation(image)

        # Preprocess
        processor = ImageProcessor()
        image = processor.process(image, PreprocessMode(preprocess))

        # OCR
        text = engine.process_image(image, lang=lang)

        return OCRResult(page_num=page_num, text=text, rotation=rotation)

    except Exception as e:
        return OCRResult(page_num=page_num, error=str(e))

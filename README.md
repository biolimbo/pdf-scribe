# pdf-scribe

📄➡️✨ Feed it crusty scanned PDFs, get clean markdown. Tesseract when you're broke, Claude when you're bougie.

A powerful CLI tool for transcribing scanned PDF documents to markdown using OCR. Supports both Tesseract (free, local) and Claude Vision AI (superior quality for degraded documents).

## Features

- **Dual OCR Engines** - Tesseract for free local processing, Claude Vision for AI-powered accuracy
- **Batch Processing** - Drop PDFs in `input/` folder and process them all at once
- **Parallel Processing** - Multi-threaded/multi-process execution with tier-based concurrency
- **Image Preprocessing** - Binarize, denoise, sharpen, remove red highlights, and more
- **AI Text Cleanup** - Optional post-processing to fix OCR errors
- **Auto-Rotation** - Detects and corrects page orientation
- **Streaming Output** - Results saved page-by-page as processing happens
- **Flexible Page Selection** - Process specific pages, ranges, or just the first N pages

## Installation

### System Dependencies

Before installing pdf-scribe, you need two system dependencies:

| Dependency | Purpose | Required For |
|------------|---------|--------------|
| **Tesseract OCR** | Optical character recognition engine | `--engine tesseract` (default) |
| **Poppler** | PDF to image conversion | All PDF processing |

#### macOS (Homebrew)

```bash
# Install Tesseract and Poppler
brew install tesseract poppler

# Install ALL language packs (recommended)
brew install tesseract-lang

# Or install specific languages only
brew install tesseract-lang  # Includes all languages
```

#### Ubuntu/Debian

```bash
# Install Tesseract and Poppler
sudo apt-get update
sudo apt-get install tesseract-ocr poppler-utils

# Install ALL language packs
sudo apt-get install tesseract-ocr-all

# Or install specific languages
sudo apt-get install tesseract-ocr-spa  # Spanish
sudo apt-get install tesseract-ocr-fra  # French
sudo apt-get install tesseract-ocr-deu  # German
sudo apt-get install tesseract-ocr-por  # Portuguese
```

#### Windows

1. **Tesseract**: Download installer from [UB-Mannheim](https://github.com/UB-Mannheim/tesseract/wiki)
   - Run the installer
   - **Important**: Check "Add to PATH" during installation
   - Select additional languages in the installer

2. **Poppler**: Download from [poppler-windows](https://github.com/oschwartz10612/poppler-windows/releases)
   - Extract to `C:\Program Files\poppler`
   - Add `C:\Program Files\poppler\bin` to your PATH

#### Verify Installation

```bash
# Check Tesseract
tesseract --version
# Should show: tesseract 5.x.x

# Check available languages
tesseract --list-langs
# Should show: eng, spa, fra, etc.

# Check Poppler
pdftoppm -v
# Should show: pdftoppm version x.x.x
```

#### Common Language Codes

| Code | Language |
|------|----------|
| `eng` | English (default) |
| `spa` | Spanish |
| `fra` | French |
| `deu` | German |
| `por` | Portuguese |
| `ita` | Italian |
| `rus` | Russian |
| `chi_sim` | Chinese (Simplified) |
| `chi_tra` | Chinese (Traditional) |
| `jpn` | Japanese |
| `kor` | Korean |
| `ara` | Arabic |

Use multiple languages with `+`: `--lang eng+spa`

### Python Setup

**Requirements**: Python 3.10 or higher

```bash
# Clone the repository
git clone https://github.com/yourusername/pdf-scribe.git
cd pdf-scribe
```

#### Virtual Environment (Recommended)

Using a virtual environment keeps dependencies isolated and avoids conflicts with other projects.

**macOS/Linux:**
```bash
# Create virtual environment
python3 -m venv .venv

# Activate it (run this every time you open a new terminal)
source .venv/bin/activate

# Your prompt should now show (.venv)
```

**Windows (PowerShell):**
```powershell
# Create virtual environment
python -m venv .venv

# Activate it
.venv\Scripts\Activate.ps1

# If you get an execution policy error, run:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Windows (Command Prompt):**
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

#### Install Dependencies

```bash
# Make sure your venv is activated (you should see (.venv) in your prompt)

# Install core dependencies
pip install -r requirements.txt

# That's it! Claude Vision dependencies are included in requirements.txt
```

#### Deactivate Virtual Environment

When you're done:
```bash
deactivate
```

### API Key (for Claude Vision)

Only needed if using `--engine claude`:

```bash
cp .env.example .env
# Edit .env and add your Anthropic API key
```

Get your API key at: https://console.anthropic.com/

## Quick Start

### Single File

```bash
# Basic OCR with Tesseract
python main.py document.pdf

# Use Claude Vision for better quality
python main.py document.pdf --engine claude

# Spanish document with image enhancement
python main.py document.pdf --engine claude --lang spa --enhance
```

### Batch Processing

```bash
# Place PDFs in input/ folder, then:
python main.py --engine claude --lang spa

# All PDFs will be processed and saved to output/<document_name>/
```

## Usage

```
python main.py [pdf] [options]
```

### Document Selection

| Method | Command |
|--------|---------|
| Single file | `python main.py document.pdf` |
| Batch mode | `python main.py` (processes all PDFs in `input/`) |

### OCR Engines

| Engine | Flag | Description |
|--------|------|-------------|
| Tesseract | `--engine tesseract` | Free, local OCR (default) |
| Claude Vision | `--engine claude` | AI-powered, best for degraded docs |

### Common Options

| Option | Description |
|--------|-------------|
| `-e, --engine` | OCR engine: `tesseract` or `claude` |
| `-l, --lang` | Language code: `eng`, `spa`, `fra`, etc. |
| `-o, --output` | Custom output path |
| `--dpi` | Resolution for PDF conversion (default: 150) |
| `-w, --workers` | Parallel workers (`auto` for CPU count) |

### Image Preprocessing

| Mode | Flag | Description |
|------|------|-------------|
| None | `--preprocess none` | No preprocessing (fastest) |
| Grayscale | `--preprocess grayscale` | Convert to grayscale |
| Binarize | `--preprocess binarize` | Black/white (good for faded text) |
| Contrast | `--preprocess contrast` | Enhance contrast |
| Sharpen | `--preprocess sharpen` | Sharpen edges |
| Denoise | `--preprocess denoise` | Remove noise/speckles |
| Remove Red | `--preprocess remove-red` | Remove red highlights/marks |
| Clean | `--preprocess clean` | Remove red + all enhancements |
| All | `--preprocess all` | All enhancements (no red removal) |

### Enhancement Shortcut

```bash
# --enhance is equivalent to: --dpi 300 --preprocess all --rotate
python main.py document.pdf --enhance
```

### Page Selection

```bash
# First N pages only
python main.py document.pdf --first 5

# Specific pages
python main.py document.pdf --pages 1,3,7

# Page ranges
python main.py document.pdf --pages 1-5,10-15

# Mixed
python main.py document.pdf --pages 1-3,7,10-12
```

### Claude-Specific Options

| Option | Description |
|--------|-------------|
| `--cleanup` | Post-process with AI to fix OCR errors |
| `--reflow` | Intelligently join lines into paragraphs |
| `--cheapo` | Use Haiku 3.5 (faster, cheaper) |
| `--expensive` | Use Opus 4 (highest quality) |

### Tesseract-Specific Options

| Option | Description |
|--------|-------------|
| `--rotate` | Auto-detect and correct page orientation |
| `--rotate-confidence` | Minimum confidence for rotation (default: 5.0) |
| `--psm` | Page Segmentation Mode (3, 4, 6, 11, 12) |
| `--oem` | OCR Engine Mode (0-3) |

#### PSM Modes

| Mode | Description |
|------|-------------|
| 3 | Fully automatic (default) |
| 4 | Single column of variable sizes |
| 6 | Single uniform block of text |
| 11 | Sparse text (find as much as possible) |

## Output Structure

Each processed document gets its own folder:

```
output/
└── document_name/
    ├── document_name.md        # Full merged transcription
    ├── document_name_clean.md  # AI-cleaned version (if --cleanup)
    └── pages/
        ├── page_001.md         # Individual page
        ├── page_001_clean.md   # Cleaned page (if --cleanup)
        ├── page_002.md
        └── ...
```

## Examples

### Poor Quality Scans

```bash
# Kitchen sink approach - everything enabled
python main.py old_scan.pdf --enhance --lang spa --workers auto
```

### Highlighted Documents

```bash
# Remove red highlights before OCR
python main.py marked_up.pdf --preprocess clean --engine claude
```

### Quick Test Run

```bash
# Test settings on first 3 pages before full run
python main.py big_document.pdf --first 3 --engine claude
```

### Maximum Quality

```bash
# Opus model + cleanup + high DPI
python main.py important.pdf --engine claude --expensive --cleanup --dpi 300
```

### Budget Processing

```bash
# Haiku model for faster/cheaper processing
python main.py document.pdf --engine claude --cheapo
```

### Batch with Custom Settings

```bash
# Process all PDFs in input/ with Spanish + cleanup
python main.py --engine claude --lang spa --cleanup
```

## API Tier Configuration

For Claude Vision, set your API tier in `.env` for optimal concurrency:

```bash
# Check your tier at: https://console.anthropic.com/settings/limits
ANTHROPIC_TIER=2  # 1=50 RPM, 2=1000 RPM, 3=2000 RPM, 4=4000 RPM
```

## Utility Commands

```bash
# List available Tesseract languages
python main.py --list-langs

# List preprocessing options
python main.py --list-preprocess
```

## Dependencies

Core:
- `pdf2image` - PDF to image conversion
- `Pillow` - Image processing
- `pytesseract` - Tesseract OCR wrapper

For Claude Vision:
- `anthropic` - Anthropic API client
- `python-dotenv` - Environment variable management

## Tips

1. **Start with `--first 3`** to test settings before processing large documents
2. **Use `--enhance`** for poor quality scans (combines DPI boost, preprocessing, rotation)
3. **Use `--preprocess clean`** for documents with red highlights or marks
4. **Use `--workers auto`** to speed up processing with parallel execution
5. **Use `--cleanup`** for AI-powered post-processing to fix OCR errors
6. **Check `output/<doc>/pages/`** for individual page results if something looks wrong

## License

MIT License - see [LICENSE](LICENSE) for details.

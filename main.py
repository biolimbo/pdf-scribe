#!/usr/bin/env python3
"""
PDF OCR Transcriptor - Main Entry Point

Transcribes scanned PDF documents to text/markdown using OCR.
Supports Tesseract (free) or Claude Vision AI (better quality).

Usage:
    python main.py document.pdf
    python main.py document.pdf --engine claude --lang spa
    python main.py document.pdf --dpi 300 --lang spa --enhance
    python main.py document.pdf --workers auto --preprocess all --rotate

Or run as a module:
    python -m transcriptor document.pdf
"""

from transcriptor.cli import main

if __name__ == "__main__":
    main()

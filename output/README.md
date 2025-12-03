# Output Folder

OCR transcription results are saved here.

## Structure

Each processed document gets its own subfolder:

```
output/
└── document_name/
    ├── document_name.md        # Full merged transcription
    ├── document_name_clean.md  # AI-cleaned version (if --cleanup used)
    └── pages/
        ├── page_001.md         # Individual page transcription
        ├── page_001_clean.md   # Cleaned page (if --cleanup used)
        ├── page_002.md
        └── ...
```

## Files

- `*.md` - Main merged document with all pages
- `*_clean.md` - AI-cleaned version (requires `--cleanup` flag)
- `pages/` - Individual page transcriptions (useful for debugging)

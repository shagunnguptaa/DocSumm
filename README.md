# Document Summary Assistant

Minimal Flask app that accepts PDFs and images, extracts text (PDF text extraction or OCR for images / embedded PDF images), and produces smart summaries with length options and highlighted key points.

## Features
- Upload via drag-and-drop or file picker
- Accepts PDF and common image formats (PNG, JPG, BMP, TIFF)
- PDF text extraction with PyPDF2; OCR fallback on embedded images when available
- Image OCR with Tesseract via pytesseract
- Summary length options: short, medium, long
- Key points and keyword highlights

## Install

1) Python 3.10+

2) Create a virtual environment (recommended):
```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: . .venv/Scripts/Activate.ps1
```

3) Install dependencies:
```bash
pip install -r requirements.txt
```

4) Install Tesseract OCR (required for images and for OCR fallback):
- Windows: Download installer from `https://github.com/tesseract-ocr/tesseract` releases.
- After install, ensure `tesseract.exe` is on your PATH, or set path in `app.py`:
```python
pytesseract.pytesseract.tesseract_cmd = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
```

## Run
```bash
python app.py
```
Open `http://localhost:5000` in your browser.

## Notes
- PDF OCR without installing extra libraries is limited. This app attempts to extract embedded images from PDFs for OCR using PyPDF2, which covers many common PDFs. For scanned PDFs without extractable images, consider adding `pdf2image` and Poppler to rasterize pages.
- The summarizer is dependency-light (no heavy NLP libs) and uses frequency-based scoring with simple sentence splitting.

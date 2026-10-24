# Invoice OCR Digitization

A Python-based invoice digitization project using Tesseract OCR, Pytesseract, Pillow, and SQLite.

## Features
- Extract text from invoice images using OCR.
- Process multiple invoice images.
- Extract invoice fields such as invoice number, vendor, date, currency, subtotal, tax, and total.
- Validate required fields and check amount consistency.
- Store invoice records in SQLite.
- Generate a JSON report for invoices that require manual review.

## Project Files
- `main.py` — runs the invoice processing workflow.
- `invoice_processor.py` — OCR and invoice field extraction.
- `database.py` — SQLite database operations.
- `inspect_ocr.py` — helps inspect OCR output.
- `invoices/` — sample invoice images.
- `review_report.json` — generated review report.

## Requirements
- Python 3
- Tesseract OCR installed on your computer
- Python packages: `pytesseract`, `Pillow`

Install the Python packages:

```bash
python -m pip install pytesseract Pillow
```

## Configuration
Update the Tesseract executable path in `invoice_processor.py` if Tesseract is installed in a different location.

## Run
Open a terminal in the project directory and run:

```bash
python main.py
```

## Results and Limitations
The sample invoices are processed using OCR and checked for missing fields and amount mismatches. Some fields may not be recognized correctly, so invoices flagged for review require manual verification.

## Notes
This project was developed as a recruitment assessment using synthetic invoice images. OCR accuracy depends on image quality and text layout.


import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

import pytesseract
from PIL import Image, ImageOps, ImageEnhance


# Tesseract installation path
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


def read_image(image_path):
    """Run OCR on an invoice image and return raw text."""
    with Image.open(image_path) as image:
        image = ImageOps.grayscale(image)
        image = ImageEnhance.Contrast(image).enhance(1.5)

        text = pytesseract.image_to_string(
            image,
            config="--psm 6"
        )

    return text.strip()


def find_field(patterns, text):
    """Find the first matching field from OCR text."""
    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE | re.MULTILINE
        )
        if match:
            return match.group(1).strip()

    return None


def normalize_date(value):
    """Normalize supported invoice date formats to YYYY-MM-DD."""
    if not value:
        return None

    formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d-%m-%Y",
        "%d %b %Y",
        "%d %B %Y",
        "%b %d, %Y",
        "%B %d, %Y",
    ]

    for date_format in formats:
        try:
            return datetime.strptime(
                value.strip(), date_format
            ).date().isoformat()
        except ValueError:
            continue

    return None


def normalize_amount(value):
    """Convert a monetary amount to Decimal without binary floats."""
    if not value:
        return None

    cleaned = value.strip()
    cleaned = re.sub(r"(?i)\b(?:USD|INR|EUR|GBP|RS)\b", "", cleaned)
    cleaned = cleaned.replace("₹", "").replace("$", "")
    cleaned = cleaned.replace("€", "").replace("£", "")
    cleaned = cleaned.replace(",", "").strip()

    # Support amounts such as (125.00) as negative values.
    negative = cleaned.startswith("(") and cleaned.endswith(")")
    cleaned = cleaned.strip("()").strip()

    try:
        amount = Decimal(cleaned)
        return -amount if negative else amount
    except InvalidOperation:
        return None


def extract_invoice_fields(raw_text):
    """Extract invoice fields from OCR output."""
    invoice_number = find_field([
        r"Invoice\s*(?:Number|No\.?|#)\s*[:#-]?\s*([A-Z0-9][A-Z0-9/-]*)",
        r"Bill\s*(?:Number|No\.?)\s*[:#-]?\s*([A-Z0-9][A-Z0-9/-]*)",
    ], raw_text)

    vendor = find_field([
        r"Vendor\s*[:\-]\s*(.+)",
        r"Supplier\s*[:\-]\s*(.+)",
        r"Seller\s*[:\-]\s*(.+)",
    ], raw_text)

    date_text = find_field([
        r"Invoice\s*Date\s*[:\-]?\s*([A-Za-z0-9, /-]+)",
        r"Date\s*[:\-]\s*([A-Za-z0-9, /-]+)",
    ], raw_text)

    currency_match = re.search(
        r"\b(INR|USD|EUR|GBP|CAD|AUD)\b|[₹$€£]",
        raw_text,
        flags=re.IGNORECASE
    )

    currency = None
    if currency_match:
        symbol = currency_match.group(0).upper()
        currency = {
            "₹": "INR",
            "$": "USD",
            "€": "EUR",
            "£": "GBP",
        }.get(symbol, symbol)

    subtotal_text = find_field([
        r"Sub[\s-]*total\s*[:\-]?\s*(?:INR|USD|EUR|GBP)?\s*[₹$€£]?\s*([\d,]+(?:\.\d{1,2})?)",
        r"Net\s*Amount\s*[:\-]?\s*[₹$€£]?\s*([\d,]+(?:\.\d{1,2})?)",
    ], raw_text)

    tax_text = find_field([
        r"(?:Tax|GST|VAT)\s*(?:Amount)?\s*[:\-]?\s*(?:INR|USD|EUR|GBP)?\s*[₹$€£]?\s*([\d,]+(?:\.\d{1,2})?)",
    ], raw_text)

    total_text = find_field([
        r"Grand\s*Total\s*[:\-]?\s*(?:INR|USD|EUR|GBP)?\s*[₹$€£]?\s*([\d,]+(?:\.\d{1,2})?)",
        r"Total\s*(?:Amount|Due)?\s*[:\-]?\s*(?:INR|USD|EUR|GBP)?\s*[₹$€£]?\s*([\d,]+(?:\.\d{1,2})?)",
    ], raw_text)

    return {
        "invoice_number": invoice_number,
        "vendor": vendor,
        "invoice_date": normalize_date(date_text),
        "currency": currency,
        "subtotal": normalize_amount(subtotal_text),
        "tax": normalize_amount(tax_text),
        "total": normalize_amount(total_text),
    }


def validate_invoice(invoice):
    """Return validation errors; never silently guess missing values."""
    errors = []

    required_fields = [
        "invoice_number",
        "vendor",
        "invoice_date",
        "currency",
        "subtotal",
        "tax",
        "total",
    ]

    for field in required_fields:
        if invoice.get(field) is None or invoice.get(field) == "":
            errors.append(f"Missing or unreadable field: {field}")

    if invoice.get("invoice_date") is not None:
        try:
            datetime.strptime(invoice["invoice_date"], "%Y-%m-%d")
        except ValueError:
            errors.append("Invalid invoice date")

    for field in ("subtotal", "tax", "total"):
        value = invoice.get(field)
        if value is not None and value < 0:
            errors.append(f"Negative amount requires review: {field}")

    subtotal = invoice.get("subtotal")
    tax = invoice.get("tax")
    total = invoice.get("total")

    if subtotal is not None and tax is not None and total is not None:
        if subtotal + tax != total:
            errors.append(
                "Amount mismatch: subtotal + tax does not equal total"
            )

    return errors


def process_invoice(image_path):
    """Process one invoice image and preserve its raw OCR text."""
    result = {
        "source_filename": image_path.name,
        "raw_ocr_text": "",
        "status": "needs_review",
        "review_reasons": [],
        "invoice": {},
    }

    try:
        raw_text = read_image(image_path)
        result["raw_ocr_text"] = raw_text

        if not raw_text:
            result["review_reasons"].append(
                "OCR returned no readable text"
            )
            return result

        invoice = extract_invoice_fields(raw_text)
        errors = validate_invoice(invoice)

        result["invoice"] = invoice
        result["review_reasons"] = errors
        result["status"] = "valid" if not errors else "needs_review"

    except Exception as error:
        result["review_reasons"].append(
            f"Image processing failed: {type(error).__name__}: {error}"
        )

    return result




import json
from pathlib import Path
from decimal import Decimal

from invoice_processor import process_invoice
from database import (
    initialize_database,
    save_valid_invoice,
    save_source_scan,
    get_invoice_count,
)


BASE_DIR = Path(__file__).resolve().parent
INVOICE_DIR = BASE_DIR / "invoices"
REPORT_FILE = BASE_DIR / "review_report.json"


def json_safe(value):
    """Convert Decimal values into JSON-safe strings."""
    if isinstance(value, Decimal):
        return str(value)

    if isinstance(value, dict):
        return {
            key: json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [json_safe(item) for item in value]

    return value


def main():
    initialize_database()

    if not INVOICE_DIR.exists():
        print("ERROR: invoices folder not found:", INVOICE_DIR)
        return

    image_files = sorted(
        path for path in INVOICE_DIR.iterdir()
        if path.is_file()
        and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".tif", ".tiff"}
    )

    if not image_files:
        print("No invoice images found in:", INVOICE_DIR)
        return

    results = []

    for image_path in image_files:
        print("\nProcessing:", image_path.name)

        result = process_invoice(image_path)
        invoice_id = None

        if result["status"] == "valid":
            try:
                invoice_id = save_valid_invoice(result["invoice"])
                result["database_invoice_id"] = invoice_id
                print("Invoice validated and stored.")
            except Exception as error:
                result["status"] = "needs_review"
                result["review_reasons"].append(
                    f"Database save failed: {type(error).__name__}: {error}"
                )
                print("Database error; flagged for review.")
        else:
            print("Needs review:", "; ".join(result["review_reasons"]))

        try:
            save_source_scan(result, invoice_id)
        except Exception as error:
            result["review_reasons"].append(
                f"Source scan save failed: {type(error).__name__}: {error}"
            )
            result["status"] = "needs_review"
            print("Could not save source scan.")

        results.append(result)

    report = {
        "processed_files": len(results),
        "valid_invoices": sum(
            item["status"] == "valid" for item in results
        ),
        "needs_review": sum(
            item["status"] == "needs_review" for item in results
        ),
        "stored_invoice_count": get_invoice_count(),
        "results": results,
    }

    with REPORT_FILE.open("w", encoding="utf-8") as file:
        json.dump(
            json_safe(report),
            file,
            indent=4,
            ensure_ascii=False,
        )

    print("\n========== SUMMARY ==========")
    print("Images processed:", len(results))
    print("Valid invoices:", report["valid_invoices"])
    print("Needs review:", report["needs_review"])
    print("Distinct invoices in database:", report["stored_invoice_count"])
    print("JSON report saved to:", REPORT_FILE)


if __name__ == "__main__":
    main()

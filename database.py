
import sqlite3
from decimal import Decimal
from pathlib import Path


DATABASE_FILE = Path(__file__).resolve().parent / "invoices.db"


def connect_db():
    """Connect to the SQLite database."""
    connection = sqlite3.connect(DATABASE_FILE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database():
    """Create invoice and source-scan tables."""
    with connect_db() as connection:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number TEXT NOT NULL,
                vendor TEXT NOT NULL,
                invoice_date TEXT NOT NULL,
                currency TEXT NOT NULL,
                subtotal TEXT NOT NULL,
                tax TEXT NOT NULL,
                total TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(invoice_number, vendor)
            );

            CREATE TABLE IF NOT EXISTS source_scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_filename TEXT NOT NULL,
                raw_ocr_text TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL,
                review_reasons TEXT NOT NULL DEFAULT '',
                invoice_id INTEGER,
                processed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(invoice_id) REFERENCES invoices(id)
            );
        """)


def save_valid_invoice(invoice):
    """Insert a valid invoice once and return its database ID."""
    with connect_db() as connection:
        connection.execute("""
            INSERT OR IGNORE INTO invoices (
                invoice_number, vendor, invoice_date, currency,
                subtotal, tax, total
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            invoice["invoice_number"],
            invoice["vendor"],
            invoice["invoice_date"],
            invoice["currency"],
            str(Decimal(str(invoice["subtotal"]))),
            str(Decimal(str(invoice["tax"]))),
            str(Decimal(str(invoice["total"]))),
        ))

        row = connection.execute("""
            SELECT id FROM invoices
            WHERE invoice_number = ? AND vendor = ?
        """, (
            invoice["invoice_number"],
            invoice["vendor"],
        )).fetchone()

        return row["id"]


def save_source_scan(result, invoice_id=None):
    """Record every scan, including duplicates and items needing review."""
    reasons = "; ".join(result.get("review_reasons", []))

    with connect_db() as connection:
        connection.execute("""
            INSERT INTO source_scans (
                source_filename, raw_ocr_text, status,
                review_reasons, invoice_id
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            result["source_filename"],
            result.get("raw_ocr_text", ""),
            result["status"],
            reasons,
            invoice_id,
        ))


def get_invoice_count():
    """Return the number of distinct stored invoices."""
    with connect_db() as connection:
        row = connection.execute(
            "SELECT COUNT(*) AS total FROM invoices"
        ).fetchone()
        return row["total"]

"""
receipt_ocr.py — Tesseract OCR + receipt parser

Two public functions:
    extract_text_from_image(image_bytes) -> str
        Runs Tesseract on the image and returns raw text.

    parse_receipt(raw_text) -> dict
        Parses the raw OCR text into structured receipt data.

Installation:
    Mac:    brew install tesseract
    Ubuntu: sudo apt install tesseract-ocr
    Python: pip install pytesseract pillow

The parser uses heuristics rather than ML — it looks for:
    - Price patterns (£X.XX or X.XX at end of line)
    - Quantity patterns (2x, 2 x, qty:2)
    - Total/subtotal keywords
    - Date patterns
    - Store name (usually first non-empty line)
"""

import re
import io
from datetime import date
from decimal import Decimal, InvalidOperation


# ── OCR ───────────────────────────────────────────────────────────────────────

def extract_text_from_image(image_bytes: bytes) -> str:
    """
    Run Tesseract OCR on image bytes and return raw text.
    Raises ImportError if pytesseract/pillow not installed.
    Raises RuntimeError if Tesseract binary not found.
    """
    try:
        import pytesseract
        from PIL import Image, ImageFilter, ImageEnhance
    except ImportError:
        raise ImportError(
            "pytesseract and pillow are required. Run: pip install pytesseract pillow"
        )

    try:
        img = Image.open(io.BytesIO(image_bytes))

        # ── Pre-processing to improve OCR accuracy ──────────────────────
        # Convert to greyscale
        img = img.convert('L')

        # Increase contrast
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2.0)

        # Sharpen
        img = img.filter(ImageFilter.SHARPEN)

        # Scale up small images (Tesseract works better >= 300 DPI)
        w, h = img.size
        if max(w, h) < 1500:
            scale = 1500 / max(w, h)
            img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

        # Run Tesseract with receipt-optimised config
        config = '--psm 6 --oem 3'   # psm 6 = assume uniform block of text
        text = pytesseract.image_to_string(img, config=config)
        return text

    except Exception as e:
        if 'tesseract is not installed' in str(e).lower() or 'not found' in str(e).lower():
            raise RuntimeError(
                "Tesseract binary not found. Install it with: brew install tesseract"
            )
        raise


# ── Parser ────────────────────────────────────────────────────────────────────

# Price pattern: optional £/$ then digits, dot, 2 digits
_PRICE_RE  = re.compile(r'[£$€]?\s*(\d{1,6}[.,]\d{2})\s*$')
# Quantity patterns: "2x", "2 x", "qty 2", "2 @"
_QTY_RE    = re.compile(r'^(\d+(?:\.\d+)?)\s*[xX@]\s*|qty[:\s]+(\d+(?:\.\d+)?)\s*', re.I)
# Date patterns
_DATE_RES  = [
    re.compile(r'(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})'),
    re.compile(r'(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+(\d{2,4})', re.I),
]
# Lines to skip — totals, subtotals, VAT, change etc.
_SKIP_RE   = re.compile(
    r'^\s*(total|subtotal|sub total|balance|amount due|vat|tax|cash|change|card|'
    r'savings|points|discount|special|offer|member|club|thank|receipt|invoice|'
    r'tel|phone|www\.|http|visit|follow|twitter|facebook|instagram)\b',
    re.I
)
_TOTAL_RE  = re.compile(
    r'(total|amount\s+due|balance\s+due|grand\s+total)\s*[:\s]*[£$€]?\s*(\d+[.,]\d{2})',
    re.I
)

MONTH_MAP = {
    'jan':1,'feb':2,'mar':3,'apr':4,'may':5,'jun':6,
    'jul':7,'aug':8,'sep':9,'oct':10,'nov':11,'dec':12
}


def _parse_price(text: str) -> Decimal | None:
    """Extract a price from the end of a line."""
    m = _PRICE_RE.search(text)
    if not m:
        return None
    try:
        return Decimal(m.group(1).replace(',', '.'))
    except InvalidOperation:
        return None


def _parse_quantity(text: str) -> tuple[Decimal, str]:
    """
    Extract quantity from start of text.
    Returns (quantity, remaining_text).
    """
    m = _QTY_RE.match(text.strip())
    if m:
        qty_str = m.group(1) or m.group(2)
        try:
            qty = Decimal(qty_str)
            remaining = text[m.end():].strip()
            return qty, remaining
        except InvalidOperation:
            pass
    return Decimal('1'), text


def _parse_date(lines: list[str]) -> str:
    """Try to find a date in the receipt lines. Returns YYYY-MM-DD or today."""
    today = date.today()
    for line in lines:
        for pattern in _DATE_RES:
            m = pattern.search(line)
            if m:
                try:
                    groups = m.groups()
                    if len(groups) == 3:
                        if isinstance(groups[1], str) and groups[1].lower() in MONTH_MAP:
                            d = int(groups[0])
                            mo = MONTH_MAP[groups[1].lower()]
                            yr = int(groups[2])
                        else:
                            d, mo, yr = int(groups[0]), int(groups[1]), int(groups[2])
                        if yr < 100:
                            yr += 2000
                        if 1 <= mo <= 12 and 1 <= d <= 31:
                            return f"{yr}-{mo:02d}-{d:02d}"
                except (ValueError, IndexError):
                    continue
    return str(today)


def _clean_item_name(text: str) -> str:
    """Remove price from end of item name and clean it up."""
    # Remove trailing price
    text = _PRICE_RE.sub('', text).strip()
    # Remove leading/trailing punctuation
    text = re.sub(r'^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$', '', text)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.title()


def parse_receipt(raw_text: str) -> dict:
    """
    Parse raw OCR text from a receipt into structured data.

    Returns:
    {
        "merchant":  "Tesco",
        "date":      "2026-05-01",
        "currency":  "GBP",
        "items": [
            {
                "name":        "Semi-Skimmed Milk 2L",
                "quantity":    1,
                "unit_price":  1.80,
                "total_price": 1.80,
                "raw_text":    "SEMI SKIM MILK 2L      1.80"
            },
            ...
        ],
        "total":     42.50,
        "raw_text":  "..."
    }
    """
    lines = [l.strip() for l in raw_text.splitlines() if l.strip()]

    if not lines:
        return {
            'merchant': 'Unknown', 'date': str(date.today()),
            'currency': 'GBP', 'items': [], 'total': 0, 'raw_text': raw_text,
        }

    # ── Merchant name — first meaningful line ─────────────────────────────
    merchant = 'Unknown'
    for line in lines[:5]:
        # Skip lines that look like addresses or phone numbers
        if re.search(r'\d{5}|\+\d|tel:|www\.', line, re.I):
            continue
        if len(line) >= 3:
            merchant = line.title()
            break

    # ── Date ─────────────────────────────────────────────────────────────
    receipt_date = _parse_date(lines)

    # ── Currency ──────────────────────────────────────────────────────────
    currency = 'GBP'
    full_text = raw_text.lower()
    if '$' in raw_text and '£' not in raw_text:
        currency = 'USD'
    elif '€' in raw_text and '£' not in raw_text:
        currency = 'EUR'

    # ── Total ─────────────────────────────────────────────────────────────
    total = Decimal('0')
    for line in reversed(lines):
        m = _TOTAL_RE.search(line)
        if m:
            try:
                total = Decimal(m.group(2).replace(',', '.'))
                break
            except InvalidOperation:
                continue

    # ── Line items ────────────────────────────────────────────────────────
    items = []
    for line in lines:
        # Skip short lines, headers, totals, store info
        if len(line) < 4:
            continue
        if _SKIP_RE.match(line):
            continue
        # Must have a price at the end to be a line item
        price = _parse_price(line)
        if price is None or price <= 0:
            continue
        # Skip very large prices — likely totals missed by SKIP_RE
        if price > 500:
            continue

        qty, name_part = _parse_quantity(line)
        name = _clean_item_name(name_part)

        # Skip empty names or names that are just numbers
        if not name or re.match(r'^\d+$', name):
            continue

        unit_price = (price / qty).quantize(Decimal('0.01')) if qty > 0 else price

        items.append({
            'name':        name,
            'quantity':    float(qty),
            'unit_price':  float(unit_price),
            'total_price': float(price),
            'raw_text':    line,
        })

    # If we couldn't extract items but have a total, make one generic item
    if not items and total > 0:
        items.append({
            'name':        f'{merchant} purchase',
            'quantity':    1.0,
            'unit_price':  float(total),
            'total_price': float(total),
            'raw_text':    '',
        })

    # If total wasn't found, sum the items
    if total == 0 and items:
        total = Decimal(str(sum(i['total_price'] for i in items)))

    return {
        'merchant':  merchant,
        'date':      receipt_date,
        'currency':  currency,
        'items':     items,
        'total':     float(total),
        'raw_text':  raw_text,
    }
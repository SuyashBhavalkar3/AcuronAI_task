import re
import logging
from typing import List, Optional
from datetime import datetime, date

from app.schemas.invoice import ExtractedInvoice, ValidationError

logger = logging.getLogger(__name__)

GSTIN_PATTERN = re.compile(
    r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'
)
# PAN format: 5 letters, 4 digits, 1 letter (10 chars) — subset of GSTIN embedded chars
PAN_PATTERN = re.compile(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$')

# In-memory duplicate invoice tracker (reset on server restart)
_seen_invoice_numbers: set = set()


def validate_invoice(extracted: ExtractedInvoice, confidence_threshold: float = 0.6) -> List[ValidationError]:
    errors: List[ValidationError] = []

    # --- Mandatory field checks ---
    if not extracted.vendor_name:
        errors.append(ValidationError(field="vendor_name", message="Vendor name is missing", severity="error"))

    if not extracted.invoice_number:
        errors.append(ValidationError(field="invoice_number", message="Invoice number is missing", severity="error"))

    if not extracted.invoice_date:
        errors.append(ValidationError(field="invoice_date", message="Invoice date is missing", severity="error"))

    if extracted.total_amount is None:
        errors.append(ValidationError(field="total_amount", message="Invoice total amount is missing", severity="error"))

    # --- GSTIN format validation ---
    if extracted.vendor_gstin:
        gstin_clean = extracted.vendor_gstin.upper().strip()
        if not GSTIN_PATTERN.match(gstin_clean):
            # Check if it looks like a bare PAN (10 chars) rather than GSTIN (15 chars)
            if PAN_PATTERN.match(gstin_clean):
                errors.append(ValidationError(
                    field="vendor_gstin",
                    message=(
                        f"PAN number detected ({extracted.vendor_gstin}), not a full GSTIN. "
                        "GSTIN should be 15 characters (state code + PAN + entity suffix)."
                    ),
                    severity="warning"
                ))
            else:
                errors.append(ValidationError(
                    field="vendor_gstin",
                    message=f"Invalid GSTIN format: {extracted.vendor_gstin} (expected 15-char alphanumeric)",
                    severity="warning"
                ))
    else:
        errors.append(ValidationError(field="vendor_gstin", message="GSTIN not found in invoice", severity="warning"))

    # --- Date validation ---
    if extracted.invoice_date:
        try:
            parsed_date = _parse_date(extracted.invoice_date)
            if parsed_date and parsed_date > date.today():
                errors.append(ValidationError(
                    field="invoice_date",
                    message=f"Invoice date {extracted.invoice_date} is in the future",
                    severity="warning"
                ))
        except Exception:
            errors.append(ValidationError(
                field="invoice_date",
                message=f"Unable to parse invoice date: {extracted.invoice_date}",
                severity="warning"
            ))

    # --- GST calculation consistency ---
    if extracted.taxable_amount and extracted.gst_amount and extracted.total_amount:
        expected_total = extracted.taxable_amount + extracted.gst_amount
        # Use 1% of invoice total as tolerance (handles large invoices & rounding)
        tolerance = max(2.0, extracted.total_amount * 0.01)
        if abs(expected_total - extracted.total_amount) > tolerance:
            errors.append(ValidationError(
                field="total_amount",
                message=(
                    f"Invoice total inconsistency: taxable ({extracted.taxable_amount:,.2f}) + "
                    f"GST ({extracted.gst_amount:,.2f}) = {expected_total:,.2f}, "
                    f"but invoice total is {extracted.total_amount:,.2f}"
                ),
                severity="warning"
            ))

    # --- GST rate sanity check ---
    # gst_rate is now a string — could be "18" (single) or "18, 5" (mixed).
    # Parse and validate each individual rate.
    VALID_GST_RATES = {0, 5, 12, 18, 28}
    if extracted.gst_rate is not None:
        invalid_rates = []
        for part in extracted.gst_rate.split(","):
            part = part.strip().replace("%", "")
            if not part:
                continue
            try:
                rate_val = float(part)
                rate_int = int(rate_val) if rate_val.is_integer() else rate_val
                if rate_int not in VALID_GST_RATES:
                    invalid_rates.append(part)
            except ValueError:
                invalid_rates.append(part)  # couldn't parse — flag it

        if invalid_rates:
            errors.append(ValidationError(
                field="gst_rate",
                message=(
                    f"Unusual GST rate(s) detected: {', '.join(invalid_rates)}%. "
                    f"Standard rates are {VALID_GST_RATES}."
                ),
                severity="warning"
            ))

    # --- Duplicate invoice detection ---
    if extracted.invoice_number:
        if extracted.invoice_number in _seen_invoice_numbers:
            errors.append(ValidationError(
                field="invoice_number",
                message=f"Duplicate invoice number detected: {extracted.invoice_number}",
                severity="error"
            ))
        else:
            _seen_invoice_numbers.add(extracted.invoice_number)

    return errors


def _parse_date(date_str: str) -> Optional[date]:
    """Attempt to parse a date string in various formats."""
    formats = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%B %d, %Y", "%d %B %Y"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue
    return None


def reset_duplicate_tracker():
    """Clear the in-memory duplicate invoice set (e.g., per session)."""
    _seen_invoice_numbers.clear()

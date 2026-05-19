import logging
from datetime import date, datetime
from typing import Optional

from app.schemas.invoice import ExtractedInvoice, AccountingRow

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# GL Code Mapping (Vendor-name-based, extend as needed)
# ---------------------------------------------------------------------------
GL_CODE_MAP: dict[str, str] = {
    "default": "6000-VENDOR-EXP",
    "telecom": "6100-TELECOM",
    "rent": "6200-RENT",
    "software": "6300-SOFTWARE",
    "maintenance": "6400-MAINT",
    "consulting": "6500-CONSULT",
    "travel": "6600-TRAVEL",
    "utilities": "6700-UTIL",
    "insurance": "6800-INSUR",
}

# ---------------------------------------------------------------------------
# Vendor Code Mapping
# ---------------------------------------------------------------------------
VENDOR_CODE_MAP: dict[str, str] = {
    "default": "VND-MISC",
}

# ---------------------------------------------------------------------------
# TDS Applicability (by GL category)
# ---------------------------------------------------------------------------
TDS_APPLICABLE_CATEGORIES = {"consulting", "rent", "maintenance", "software"}

# ---------------------------------------------------------------------------
# Branch Code Mapping
# ---------------------------------------------------------------------------
DEFAULT_BRANCH_CODE = "HO"

# ---------------------------------------------------------------------------
# Journal Type Mapping
# ---------------------------------------------------------------------------
JOURNAL_TYPE_MAP: dict[str, str] = {
    "default": "AP",        # Accounts Payable
    "credit_note": "CN",
    "debit_note": "DN",
}


def _get_gl_code(vendor_name: Optional[str]) -> str:
    """Map vendor name to GL account code using keyword matching."""
    if not vendor_name:
        return GL_CODE_MAP["default"]
    vendor_lower = vendor_name.lower()
    for keyword, code in GL_CODE_MAP.items():
        if keyword != "default" and keyword in vendor_lower:
            return code
    return GL_CODE_MAP["default"]


def _get_vendor_code(vendor_name: Optional[str]) -> str:
    """Map vendor name to a short vendor code."""
    if not vendor_name:
        return VENDOR_CODE_MAP["default"]
    # Generate a code from the first 3 chars of vendor name
    clean = "".join(c for c in vendor_name if c.isalpha()).upper()
    return f"VND-{clean[:6]}" if clean else VENDOR_CODE_MAP["default"]


def _get_tds_applicability(gl_code: str) -> str:
    """Determine TDS applicability based on GL code category."""
    for category in TDS_APPLICABLE_CATEGORIES:
        if category.upper() in gl_code.upper():
            return "Y"
    return "N"


def _format_acc_period(invoice_date_str: Optional[str]) -> Optional[str]:
    """Convert invoice date to accounting period format MM/YYYY."""
    if not invoice_date_str:
        return None
    formats = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"]
    for fmt in formats:
        try:
            dt = datetime.strptime(invoice_date_str.strip(), fmt)
            return dt.strftime("%m/%Y")
        except ValueError:
            continue
    return None


def apply_rules(extracted: ExtractedInvoice) -> AccountingRow:
    """
    Apply business/accounting rules to map extracted invoice data
    into the standardized accounting row schema.
    """
    gl_code = _get_gl_code(extracted.vendor_name)
    vendor_code = _get_vendor_code(extracted.vendor_name)
    tds_flag = _get_tds_applicability(gl_code)
    acc_period = _format_acc_period(extracted.invoice_date)
    today_str = date.today().strftime("%Y-%m-%d")

    # Determine Dr/Cr (all vendor invoices are typically Cr for AP)
    dr_cr = "CR"
    
    # Period and Date of Entry (using today's date for entry context)
    acc_period = date.today().strftime("%m/%Y")
    trans_date = today_str

    # Reference: Vendor Code and Name
    reference = f"{vendor_code} - {extracted.vendor_name or 'Unknown'}"

    # Description: Nature of expenses
    description = f"Expenses for {extracted.vendor_name or 'Vendor'}"

    # TDS Code: TD01 if applicable
    tds_code = "TD01" if tds_flag == "Y" else None

    return AccountingRow(
        acc_period=acc_period,
        trans_date=trans_date,
        account_code=gl_code,
        curr_code="INR",
        trans_amount=extracted.total_amount,
        dr_cr=dr_cr,
        jrnal_type="Standard Expenses",
        jrnal_source="Not applicable",
        reference=reference,
        description=description,
        asset_code="",
        asset_indicator="",
        asset_item_qty="",
        due_date="",
        branch_analysis_code=DEFAULT_BRANCH_CODE,
        product_analysis_code="Not applicable",
        channel_analysis_code="Respective channel code",
        sub_channel_analysis_code="Not applicable",
        underwriting_year_analysis_code="Not applicable",
        employee_code_analysis_code="Not applicable",
        tds_applicability_analysis_code=tds_code,
        department_analysis_code="",
        sequence_code_analysis_code="Not applicable",
        vendor_code_analysis_code=vendor_code,
        invoice_date=extracted.invoice_date,
        from_date="Not applicable",
        to_date="Not applicable",
        addl_date_4="",
        addl_date_5="",
        cheque_neft_number=extracted.vendor_gstin,  # Mapped to Vendor GST number
        invoice_number=extracted.invoice_number,
        additional_remarks="NEFT",
        additional_remarks_2="Not applicable",
        credence_description="Not applicable",
        hsn_sac_no=extracted.hsn_sac,
        taxable_on_amount=extracted.taxable_amount,
        reverse_charge="Not applicable",
        reverse_charge_pct=0.0,
        item_details_sr_no="Not applicable",
        goods_service="Not applicable",
        gst_tax_rate=extracted.gst_rate,
        original_invoice_no_dr_cr="RS GST number", # Company GST Placeholder
        advance_challan_no=gl_code, # Mapped to GL Code
    )

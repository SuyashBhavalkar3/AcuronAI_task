import os
import re
import logging
from typing import Optional
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential

from app.config.settings import AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT, AZURE_DOCUMENT_INTELLIGENCE_KEY
from app.schemas.invoice import ExtractedInvoice

logger = logging.getLogger(__name__)


def get_di_client() -> DocumentIntelligenceClient:
    if not AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT or not AZURE_DOCUMENT_INTELLIGENCE_KEY:
        raise ValueError(
            "Azure Document Intelligence credentials are not configured. "
            "Please set AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT and AZURE_DOCUMENT_INTELLIGENCE_KEY in .env"
        )
    return DocumentIntelligenceClient(
        endpoint=AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT,
        credential=AzureKeyCredential(AZURE_DOCUMENT_INTELLIGENCE_KEY),
    )


def _safe_str(field) -> Optional[str]:
    """Safely extract string value from a v1.x DocumentField."""
    if field is None:
        return None
    try:
        # Prefer typed string value
        if hasattr(field, "value_string") and field.value_string is not None:
            return str(field.value_string)
        # Fallback to raw OCR content
        if hasattr(field, "content") and field.content is not None:
            return str(field.content)
        return None
    except Exception:
        return None


def _safe_float(field) -> Optional[float]:
    """Safely extract numeric value from a v1.x DocumentField."""
    if field is None:
        return None
    try:
        # Numeric field
        if hasattr(field, "value_number") and field.value_number is not None:
            return float(field.value_number)
        # Currency field (e.g. InvoiceTotal, SubTotal, TotalTax)
        if hasattr(field, "value_currency") and field.value_currency is not None:
            return float(field.value_currency.amount)
        # Fallback: try parsing content string
        if hasattr(field, "content") and field.content:
            cleaned = field.content.replace(",", "").replace("₹", "").strip()
            return float(cleaned)
        return None
    except Exception:
        return None


def _safe_date_str(field) -> Optional[str]:
    """Safely extract date string from a v1.x DocumentField."""
    if field is None:
        return None
    try:
        # Typed date value is a datetime.date object
        if hasattr(field, "value_date") and field.value_date is not None:
            return str(field.value_date)
        # Fallback to raw content string
        if hasattr(field, "content") and field.content is not None:
            return str(field.content)
        return None
    except Exception:
        return None


def extract_invoice_from_bytes(file_bytes: bytes, filename: str) -> ExtractedInvoice:
    """
    Sends a document to Azure Document Intelligence using the prebuilt-invoice model
    and returns a structured ExtractedInvoice.
    """
    client = get_di_client()
    logger.info(f"Sending {filename} to Azure Document Intelligence...")

    poller = client.begin_analyze_document(
        "prebuilt-invoice",
        body=file_bytes,
        content_type="application/octet-stream",
    )
    result = poller.result()

    if not result.documents:
        logger.warning(f"No invoice documents detected in {filename}")
        return ExtractedInvoice(raw_fields={})

    doc = result.documents[0]
    fields = doc.fields or {}

    # --- Robust GSTIN/PAN extraction ---
    vendor_gstin = None
    full_content = result.content or ""
    
    # 1. Look for 15-char GSTINs in the entire document
    gstin_pattern = r'\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}\b'
    all_gstins = re.findall(gstin_pattern, full_content)
    
    # 2. Get Azure's specific field hints
    azure_tax_id = _safe_str(fields.get("VendorTaxId"))
    
    # 3. Priority logic
    if all_gstins:
        # If we found full GSTINs in the text, prioritize them.
        # If Azure's VendorTaxId matches part of a GSTIN, use that specific GSTIN.
        if azure_tax_id:
            matching_gstin = next((g for g in all_gstins if azure_tax_id in g), None)
            if matching_gstin:
                vendor_gstin = matching_gstin
        
        if not vendor_gstin:
            # Otherwise take the first one found (usually in the header)
            vendor_gstin = all_gstins[0]
            
    if not vendor_gstin:
        # Fallback to Azure's field directly if no 15-char match found in text
        if azure_tax_id:
            vendor_gstin = azure_tax_id
        else:
            # Last resort: Look for 10-char PANs in full content
            pan_pattern = r'\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b'
            all_pans = re.findall(pan_pattern, full_content)
            if all_pans:
                vendor_gstin = all_pans[0]

    # --- Advanced Amount Extraction with Math Verification ---
    total = _safe_float(fields.get("InvoiceTotal"))
    taxable_amount = _safe_float(fields.get("SubTotal"))
    gst_amount = _safe_float(fields.get("TotalTax"))

    # AI is sometimes "chopping off" leading digits in Indian numbering (Lakhs/Crores).
    # We refactor this to be format-agnostic.
    def find_all_amounts(text):
        # Matches numbers with any comma placement (e.g., 10,93,877.00 or 1,093,877.00)
        # Sequence of digits and commas, followed by a period and 2-3 decimal digits.
        matches = re.findall(r'(?:\d[\d,]*\.\d{2,3})', text)
        
        amounts = []
        for m in matches:
            try:
                # Clean commas and convert to float
                val = float(m.replace(',', ''))
                # Ignore very small amounts or obvious noise
                if val > 0.01:
                    amounts.append(val)
            except ValueError:
                continue
        return sorted(list(set(amounts)), reverse=True)

    all_amounts = find_all_amounts(full_content)
    
    if len(all_amounts) >= 3:
        # Optimization: Look for a relationship where A + B = C (within 1.0 tolerance)
        found_triplet = False
        for i in range(len(all_amounts)): # C (Total)
            for j in range(i + 1, len(all_amounts)): # A or B
                for k in range(j + 1, len(all_amounts)): # B or A
                    # Check if all_amounts[j] + all_amounts[k] == all_amounts[i]
                    if abs((all_amounts[j] + all_amounts[k]) - all_amounts[i]) < 2.0:
                        # Triplet found: [Total, Taxable, GST]
                        total = all_amounts[i]
                        taxable_amount = all_amounts[j]
                        gst_amount = all_amounts[k]
                        found_triplet = True
                        break
                if found_triplet: break
            if found_triplet: break

    # Fallback: Specific label search for "Amount Due" if total still looks wrong
    if not total:
        due_match = re.search(r'TOTAL\s+AMOUNT\s+DUE.*?(\d{1,3}(?:,\d{3})*(?:\.\d{2}))', full_content, re.IGNORECASE | re.DOTALL)
        if due_match:
            total = float(due_match.group(1).replace(',', ''))

    # --- Line-item extraction (fallback + HSN/SAC pickup) ---
    hsn_sac = None
    items_field = fields.get("Items")
    if items_field is not None:
        item_list = getattr(items_field, "value_array", None) or []
        item_tax_sum = 0.0
        item_amt_sum = 0.0
        has_item_tax = False
        has_item_amt = False
        for item in item_list:
            item_fields = getattr(item, "value_object", None) or {}
            tax_val = _safe_float(item_fields.get("Tax"))
            if tax_val is not None:
                item_tax_sum += tax_val
                has_item_tax = True
            amt = _safe_float(item_fields.get("Amount"))
            if amt is not None:
                item_amt_sum += amt
                has_item_amt = True
            # Grab first HSN/SAC seen
            if hsn_sac is None:
                hsn_sac = _safe_str(item_fields.get("ProductCode"))

        # Only use item sums if top-level fields were missing
        if taxable_amount is None and has_item_amt:
            taxable_amount = round(item_amt_sum, 2)
        if gst_amount is None and has_item_tax:
            gst_amount = round(item_tax_sum, 2)

    # --- Derive missing values ---
    if taxable_amount is None and total is not None and gst_amount is not None:
        taxable_amount = round(total - gst_amount, 2)
    if gst_amount is None and total is not None and taxable_amount is not None:
        gst_amount = round(total - taxable_amount, 2)

    # --- GST rate (round to nearest standard rate if very close) ---
    gst_rate = None
    if taxable_amount and gst_amount and taxable_amount > 0:
        raw_rate = (gst_amount / taxable_amount) * 100
        # Snap to nearest standard GST rate if within 1% tolerance
        STANDARD_RATES = [0, 5, 12, 18, 28]
        nearest = min(STANDARD_RATES, key=lambda r: abs(r - raw_rate))
        gst_rate = nearest if abs(nearest - raw_rate) <= 1.0 else round(raw_rate, 2)

    # Build a safe raw_fields snapshot (string values only for JSON serialisation)
    raw_fields: dict = {}
    for k, v in fields.items():
        raw_fields[k] = _safe_str(v)

    return ExtractedInvoice(
        vendor_name=_safe_str(fields.get("VendorName")),
        vendor_gstin=vendor_gstin,
        invoice_number=_safe_str(fields.get("InvoiceId")),
        invoice_date=_safe_date_str(fields.get("InvoiceDate")),
        taxable_amount=taxable_amount,
        gst_amount=gst_amount,
        gst_rate=gst_rate,
        hsn_sac=hsn_sac,
        total_amount=total,
        raw_fields=raw_fields,
    )


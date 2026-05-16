import os
import re
import json
import logging
from typing import Optional
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from groq import Groq

from app.config.settings import AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT, AZURE_DOCUMENT_INTELLIGENCE_KEY, LLM_API_KEY
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


def extract_invoice_from_bytes(file_bytes: bytes, filename: str) -> ExtractedInvoice:
    """
    Sends a document to Azure Document Intelligence using the prebuilt-layout model
    and uses Groq LLM to extract structured fields into an ExtractedInvoice.
    """
    client = get_di_client()
    logger.info(f"Sending {filename} to Azure Document Intelligence (prebuilt-layout)...")

    # Use prebuilt-layout to get structured Markdown
    poller = client.begin_analyze_document(
        "prebuilt-layout",
        body=file_bytes,
        content_type="application/octet-stream",
        output_content_format="markdown",
    )
    result = poller.result()
    document_markdown = result.content or ""

    if not document_markdown:
        logger.warning(f"No content detected in {filename}")
        return ExtractedInvoice(raw_fields={})

    if not LLM_API_KEY:
        logger.error("LLM_API_KEY is not configured.")
        raise ValueError("LLM_API_KEY is not set in environment")

    logger.info(f"Extracting structured fields using Groq (model: openai/gpt-oss-120b)...")
    
    groq_client = Groq(api_key=LLM_API_KEY)
    
    system_prompt = '''You are an expert Indian accounting AI. You will be provided with the Markdown text of an invoice.
Your job is to extract the data into the exact JSON schema provided below.

Rules:
1. Total Amount MUST equal Taxable Amount + GST Amount.
2. GSTIN must be exactly 15 alphanumeric characters.
3. If a value is not found, return null. Do not guess.
4. Output MUST begin with the tag [ignoring loop detection] on its own line, followed by raw JSON only — no markdown, no backticks, no extra text.
5. CRITICAL - GST Rate: Indian invoices split GST into CGST and SGST (or IGST alone).
   - If you see CGST % and SGST %, the total gst_rate = CGST % + SGST % (e.g. 9% CGST + 9% SGST = 18% total).
   - If you see only IGST %, use that directly as gst_rate.
   - NEVER return just one component (e.g. 9) when both CGST and SGST are present.
   - Valid combined GST rates are: 0, 5, 12, 18, 28.
6. gst_amount is the TOTAL tax paid (CGST amount + SGST amount, or IGST amount).

JSON Schema to output:
{
    "vendor_name": "string or null",
    "vendor_gstin": "string or null",
    "invoice_number": "string or null",
    "invoice_date": "YYYY-MM-DD or null",
    "taxable_amount": number or null,
    "gst_amount": number or null,
    "gst_rate": number or null,
    "hsn_sac": "string or null",
    "total_amount": number or null
}'''

    try:
        completion = groq_client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Invoice Markdown:\n\n{document_markdown}"}
            ],
            temperature=0.0
        )
        
        response_content = completion.choices[0].message.content.strip()

        # --- Robust JSON extraction (3 layers) ---
        # Layer 0: Strip Groq loop-detection bypass tag (we asked the model to emit it)
        cleaned = response_content
        if cleaned.startswith("[ignoring loop detection]"):
            cleaned = cleaned[len("[ignoring loop detection]"):].strip()

        # Layer 1: Strip fenced code blocks (```json ... ``` or ``` ... ```)
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        # Layer 2: Try direct parse
        extracted_data = None
        try:
            extracted_data = json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Layer 3: Regex — find the first {...} JSON object even if prose surrounds it
        if extracted_data is None:
            json_match = re.search(r'\{[\s\S]*\}', cleaned)
            if json_match:
                try:
                    extracted_data = json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass

        if extracted_data is None:
            logger.error(f"All JSON parse attempts failed for {filename}. Raw LLM output: {response_content[:500]}")
            raise ValueError(
                f"LLM returned unparseable output for '{filename}'. "
                "The document may be a scan, image-only PDF, or in an unsupported format. "
                f"Raw response preview: {response_content[:200]}"
            )

        # --- Post-processing: detect and fix CGST+SGST split rate ---
        # If the LLM returned a rate that is exactly half of what the
        # math implies (taxable_amount / gst_amount ≈ rate*2), correct it.
        gst_rate = extracted_data.get("gst_rate")
        taxable_amount = extracted_data.get("taxable_amount")
        gst_amount = extracted_data.get("gst_amount")
        STANDARD_RATES = {0.0, 5.0, 12.0, 18.0, 28.0}

        if gst_rate is not None and taxable_amount and gst_amount and taxable_amount > 0:
            # Calculate effective GST rate from actual amounts
            effective_rate = round((gst_amount / taxable_amount) * 100, 2)
            doubled_rate = round(gst_rate * 2, 2)

            # If the extracted rate is NOT a standard rate, but doubling it IS standard,
            # and that doubled value matches the effective rate within 1%,
            # the LLM picked just one split component — correct it.
            if (
                gst_rate not in STANDARD_RATES
                and doubled_rate in STANDARD_RATES
                and abs(effective_rate - doubled_rate) <= 1.0
            ):
                logger.warning(
                    f"GST rate correction: LLM returned {gst_rate}% (single CGST/SGST component). "
                    f"Correcting to combined rate {doubled_rate}% based on amounts "
                    f"(taxable={taxable_amount}, gst={gst_amount})."
                )
                gst_rate = doubled_rate

        return ExtractedInvoice(
            vendor_name=extracted_data.get("vendor_name"),
            vendor_gstin=extracted_data.get("vendor_gstin"),
            invoice_number=extracted_data.get("invoice_number"),
            invoice_date=extracted_data.get("invoice_date"),
            taxable_amount=taxable_amount,
            gst_amount=gst_amount,
            gst_rate=gst_rate,
            hsn_sac=extracted_data.get("hsn_sac"),
            total_amount=extracted_data.get("total_amount"),
            raw_fields={"markdown_content": document_markdown, "raw_llm_response": response_content}
        )

    except Exception as e:
        logger.error(f"Extraction failed for '{filename}': {e}")
        raise



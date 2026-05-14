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
4. Output MUST be ONLY raw JSON without any markdown formatting, backticks, or text before/after.

JSON Schema to output:
{
    "vendor_name": "string or null",
    "vendor_gstin": "string or null",
    "invoice_number": "string or null",
    "invoice_date": "YYYY-MM-DD or null",
    "taxable_amount": float or null,
    "gst_amount": float or null,
    "gst_rate": float or null,
    "hsn_sac": "string or null",
    "total_amount": float or null
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
        
        # Clean up markdown code blocks if the model ignored the instruction
        if response_content.startswith("```json"):
            response_content = response_content[7:]
        if response_content.startswith("```"):
            response_content = response_content[3:]
        if response_content.endswith("```"):
            response_content = response_content[:-3]
        response_content = response_content.strip()

        extracted_data = json.loads(response_content)
        
        return ExtractedInvoice(
            vendor_name=extracted_data.get("vendor_name"),
            vendor_gstin=extracted_data.get("vendor_gstin"),
            invoice_number=extracted_data.get("invoice_number"),
            invoice_date=extracted_data.get("invoice_date"),
            taxable_amount=extracted_data.get("taxable_amount"),
            gst_amount=extracted_data.get("gst_amount"),
            gst_rate=extracted_data.get("gst_rate"),
            hsn_sac=extracted_data.get("hsn_sac"),
            total_amount=extracted_data.get("total_amount"),
            raw_fields={"markdown_content": document_markdown, "raw_llm_response": response_content}
        )

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM JSON: {e}")
        logger.error(f"Raw LLM output: {response_content}")
        return ExtractedInvoice(raw_fields={"error": "LLM returned invalid JSON", "markdown_content": document_markdown})
    except Exception as e:
        logger.error(f"Groq API error: {e}")
        return ExtractedInvoice(raw_fields={"error": str(e), "markdown_content": document_markdown})


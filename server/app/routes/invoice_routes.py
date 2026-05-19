import os
import time
import logging
from pathlib import Path
from typing import List

from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import Response

from app.config.settings import ALLOWED_EXTENSIONS, MAX_FILE_SIZE_MB
from app.schemas.invoice import InvoiceProcessingResult, ProcessInvoicesResponse
from app.services.azure_di_service import extract_invoice_from_bytes
from app.services.validation_service import validate_invoice, reset_duplicate_tracker
from app.services.rules_engine import apply_rules
from app.services.pdf_service import generate_pdf
from app.services.excel_service import generate_excel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/invoices", tags=["invoices"])

# Cooldown between invoices (seconds). Keeps cumulative token usage spread
# across Groq's 1-minute window and reduces 429 frequency in batches.
_INTER_INVOICE_COOLDOWN_S = 5


@router.post("/upload", response_model=ProcessInvoicesResponse)
async def upload_invoices(files: List[UploadFile] = File(...)):
    """
    Accept one or more invoice PDF/image uploads, process them through
    Azure Document Intelligence + Groq LLM sequentially, validate, apply
    rules, and return results.

    Rate-limit strategy:
      - Sequential processing: one Groq call at a time (no parallel load).
      - Inter-invoice cooldown: _INTER_INVOICE_COOLDOWN_S seconds between
        each successful extraction to spread token usage across the minute.
      - Groq call itself retries on 429 with exponential backoff (see
        azure_di_service._call_groq_with_retry).
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    reset_duplicate_tracker()
    results: List[InvoiceProcessingResult] = []

    for upload in files:
        filename = upload.filename or "unknown"
        ext = Path(filename).suffix.lower()

        # File type validation
        if ext not in ALLOWED_EXTENSIONS:
            results.append(InvoiceProcessingResult(
                filename=filename,
                status="error",
                error_message=f"File type '{ext}' is not supported. Allowed: {ALLOWED_EXTENSIONS}",
            ))
            continue

        # Read and size-check
        file_bytes = await upload.read()
        size_mb = len(file_bytes) / (1024 * 1024)
        if size_mb > MAX_FILE_SIZE_MB:
            results.append(InvoiceProcessingResult(
                filename=filename,
                status="error",
                error_message=f"File size {size_mb:.1f}MB exceeds limit of {MAX_FILE_SIZE_MB}MB.",
            ))
            continue

        try:
            # Step 1: Extract via Azure DI + Groq LLM
            extracted = extract_invoice_from_bytes(file_bytes, filename)

            # Step 2: Validate (includes duplicate detection)
            validation_errors = validate_invoice(extracted)

            # Step 3: Apply accounting rules engine
            accounting_row = apply_rules(extracted)

            has_errors = any(e.severity == "error" for e in validation_errors)
            has_warnings = any(e.severity == "warning" for e in validation_errors)
            status = "error" if has_errors else ("warning" if has_warnings else "success")

            results.append(InvoiceProcessingResult(
                filename=filename,
                status=status,
                extracted=extracted,
                accounting_row=accounting_row,
                validation_errors=validation_errors,
            ))

            # Cooldown: spread token usage across Groq's 1-min window
            if len(files) > 1:
                logger.info(
                    f"Inter-invoice cooldown: sleeping {_INTER_INVOICE_COOLDOWN_S}s "
                    "to stay within Groq rate limits..."
                )
                time.sleep(_INTER_INVOICE_COOLDOWN_S)

        except Exception as exc:
            logger.exception(f"Failed to process {filename}: {exc}")
            results.append(InvoiceProcessingResult(
                filename=filename,
                status="error",
                error_message=str(exc),
            ))

    success_count = sum(1 for r in results if r.status == "success")
    warning_count = sum(1 for r in results if r.status == "warning")
    error_count = sum(1 for r in results if r.status == "error")

    return ProcessInvoicesResponse(
        results=results,
        total=len(results),
        success_count=success_count,
        error_count=error_count,
        warning_count=warning_count,
    )


@router.post("/export-pdf")
async def export_pdf(results: List[InvoiceProcessingResult]):
    """
    Generate a styled PDF from existing processing results.
    Accepts JSON data, so no re-extraction is needed.
    """
    pdf_bytes = generate_pdf(results)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=invoice_report.pdf"},
    )


@router.post("/export-excel")
async def export_excel(results: List[InvoiceProcessingResult]):
    """
    Generate a styled Excel file from existing processing results.
    Accepts JSON data, so no re-extraction is needed.
    """
    excel_bytes = generate_excel(results)

    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=invoice_accounting.xlsx"},
    )


@router.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "service": "invoice-processor"}


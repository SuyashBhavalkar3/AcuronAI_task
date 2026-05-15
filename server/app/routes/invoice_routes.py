import asyncio
import os
import logging
from pathlib import Path
from typing import List

from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import Response

from app.config.settings import UPLOAD_DIR, OUTPUT_DIR, ALLOWED_EXTENSIONS, MAX_FILE_SIZE_MB
from app.schemas.invoice import InvoiceProcessingResult, ProcessInvoicesResponse, ValidationError
from app.services.azure_di_service import extract_invoice_from_bytes
from app.services.validation_service import validate_invoice, reset_duplicate_tracker
from app.services.rules_engine import apply_rules
from app.services.pdf_service import generate_pdf

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/invoices", tags=["invoices"])

# Ensure directories exist
Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)


@router.post("/upload", response_model=ProcessInvoicesResponse)
async def upload_invoices(files: List[UploadFile] = File(...)):
    """
    Accept one or more invoice PDF/image uploads, process them through
    Azure Document Intelligence, validate, apply rules, and return results.
    All invoices are processed concurrently to minimise latency.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    reset_duplicate_tracker()

    # ── Step 1: Read and validate all file bytes up-front (fast, sequential) ──
    pending: List[dict] = []   # files that pass basic checks, ready to process
    results: List[InvoiceProcessingResult] = []

    for upload in files:
        filename = upload.filename or "unknown"
        ext = Path(filename).suffix.lower()

        if ext not in ALLOWED_EXTENSIONS:
            results.append(InvoiceProcessingResult(
                filename=filename,
                status="error",
                error_message=f"File type '{ext}' is not supported. Allowed: {ALLOWED_EXTENSIONS}",
            ))
            continue

        file_bytes = await upload.read()
        size_mb = len(file_bytes) / (1024 * 1024)
        if size_mb > MAX_FILE_SIZE_MB:
            results.append(InvoiceProcessingResult(
                filename=filename,
                status="error",
                error_message=f"File size {size_mb:.1f}MB exceeds limit of {MAX_FILE_SIZE_MB}MB.",
            ))
            continue

        # Save to uploads directory
        save_path = Path(UPLOAD_DIR) / filename
        with open(save_path, "wb") as f:
            f.write(file_bytes)

        pending.append({"filename": filename, "file_bytes": file_bytes})

    # ── Step 2: Process all valid files CONCURRENTLY ──────────────────────────
    # Azure DI SDK and Groq are synchronous/blocking → run in thread pool so
    # they execute in parallel without blocking the event loop.
    async def process_one(filename: str, file_bytes: bytes) -> InvoiceProcessingResult:
        try:
            extracted = await asyncio.to_thread(extract_invoice_from_bytes, file_bytes, filename)
            # Validation (pure CPU, fast) and rules engine run in the same thread
            validation_errors = validate_invoice(extracted, skip_duplicate_check=True)
            accounting_row = apply_rules(extracted)
            has_errors = any(e.severity == "error" for e in validation_errors)
            has_warnings = any(e.severity == "warning" for e in validation_errors)
            status = "error" if has_errors else ("warning" if has_warnings else "success")
            return InvoiceProcessingResult(
                filename=filename,
                status=status,
                extracted=extracted,
                accounting_row=accounting_row,
                validation_errors=validation_errors,
            )
        except Exception as exc:
            logger.exception(f"Failed to process {filename}: {exc}")
            return InvoiceProcessingResult(
                filename=filename,
                status="error",
                error_message=str(exc),
            )

    if pending:
        parallel_results = await asyncio.gather(
            *[process_one(p["filename"], p["file_bytes"]) for p in pending]
        )
        results.extend(parallel_results)

    # ── Step 3: Duplicate detection (serial, after all results are in) ────────
    seen: set = set()
    for result in results:
        if result.extracted and result.extracted.invoice_number:
            inv_no = result.extracted.invoice_number
            if inv_no in seen:
                dup_error = ValidationError(
                    field="invoice_number",
                    message=f"Duplicate invoice number detected: {inv_no}",
                    severity="error",
                )
                result.validation_errors = (result.validation_errors or []) + [dup_error]
                result.status = "error"
            else:
                seen.add(inv_no)

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
async def export_pdf(files: List[UploadFile] = File(...)):
    """
    Process uploaded invoices and return a styled PDF file for download.
    """
    upload_response = await upload_invoices(files)
    pdf_bytes = generate_pdf(upload_response.results)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=invoice_report.pdf"},
    )


@router.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "service": "invoice-processor"}

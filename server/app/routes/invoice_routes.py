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

        # Read file bytes
        file_bytes = await upload.read()

        # File size validation
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

        try:
            # Step 1: Extract via Azure DI
            extracted = extract_invoice_from_bytes(file_bytes, filename)

            # Step 2: Validate
            validation_errors = validate_invoice(extracted)

            # Step 3: Apply rules engine
            accounting_row = apply_rules(extracted)

            # Determine status
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

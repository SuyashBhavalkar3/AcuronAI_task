import re
import json
import time
import random
import logging
from typing import Optional

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from groq import Groq
from groq import RateLimitError as GroqRateLimitError
from groq import APIStatusError as GroqAPIStatusError

from app.config.settings import (
    AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT,
    AZURE_DOCUMENT_INTELLIGENCE_KEY,
    LLM_API_KEY,
)
from app.schemas.invoice import ExtractedInvoice

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
GROQ_MODEL = "openai/gpt-oss-120b"

# Groq free tier: ~8,000 tokens/min.  Each char ≈ 0.25 tokens, so
# 12,000 chars ≈ 3,000 tokens — leaves headroom for system prompt + response.
MAX_MARKDOWN_CHARS = 12_000

# Retry configuration
_MAX_RETRIES = 4          # total attempts = 1 original + 4 retries
_BASE_BACKOFF_S = 15      # seconds for first retry (doubles each time)
_MAX_BACKOFF_S = 90       # cap: never wait longer than 90s per retry
_JITTER_S = 3             # ± random seconds added to avoid thundering herd

# If Groq's retry-after header exceeds this, the hourly/daily quota is
# exhausted — fail fast with a clear error instead of hanging the request.
_MAX_RETRY_AFTER_S = 90


# ---------------------------------------------------------------------------
# Azure DI client factory
# ---------------------------------------------------------------------------
def get_di_client() -> DocumentIntelligenceClient:
    if not AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT or not AZURE_DOCUMENT_INTELLIGENCE_KEY:
        raise ValueError(
            "Azure Document Intelligence credentials are not configured. "
            "Please set AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT and "
            "AZURE_DOCUMENT_INTELLIGENCE_KEY in .env"
        )
    return DocumentIntelligenceClient(
        endpoint=AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT,
        credential=AzureKeyCredential(AZURE_DOCUMENT_INTELLIGENCE_KEY),
    )


# ---------------------------------------------------------------------------
# Groq call with exponential backoff + retry-after header support
# ---------------------------------------------------------------------------
def _call_groq_with_retry(
    groq_client: Groq,
    system_prompt: str,
    user_content: str,
    filename: str,
) -> str:
    """
    Call the Groq chat-completions API with robust retry logic.

    Retry strategy:
      - Catches `groq.RateLimitError` (HTTP 429) specifically.
      - If retry-after header <= _MAX_RETRY_AFTER_S (90s): honours it and retries.
        This handles normal per-minute token limit bursts.
      - If retry-after header > _MAX_RETRY_AFTER_S: raises immediately with an
        actionable error — this means the hourly/daily quota is exhausted and
        waiting 7+ minutes would freeze the entire request unacceptably.
      - Falls back to exponential backoff (15s → 30s → 60s → 90s) with ±3s
        jitter when no retry-after header is present.
      - Non-rate-limit errors (auth, bad request, model error) are raised
        immediately without retrying.
      - Raises the final exception after _MAX_RETRIES failed attempts.
    """
    last_exc: Exception = RuntimeError("Groq call failed before any attempt.")

    for attempt in range(_MAX_RETRIES + 1):  # attempt 0 = first try
        try:
            completion = groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.0,
            )
            return completion.choices[0].message.content.strip()

        except GroqRateLimitError as exc:
            last_exc = exc
            if attempt >= _MAX_RETRIES:
                logger.error(
                    f"[{filename}] Groq rate limit hit. Exhausted all {_MAX_RETRIES} retries. Giving up."
                )
                raise

            # --- Determine wait time ---
            wait_s: float = _BASE_BACKOFF_S * (2 ** attempt)   # 15s, 30s, 60s, 90s
            wait_s = min(wait_s, _MAX_BACKOFF_S)                # cap at 90s

            # Parse the server's retry-after header if present
            retry_after_header: Optional[float] = None
            _resp = getattr(exc, "response", None)
            if _resp is not None:
                _hval = getattr(_resp, "headers", {}).get("retry-after")
                if _hval:
                    try:
                        retry_after_header = float(_hval)
                    except ValueError:
                        pass  # header wasn't a number — ignore

            if retry_after_header is not None:
                if retry_after_header > _MAX_RETRY_AFTER_S:
                    # Long retry-after = hourly/daily quota exhausted.
                    # Fail fast — don't freeze the request for 7+ minutes.
                    wait_mins = int(retry_after_header // 60)
                    wait_secs = int(retry_after_header % 60)
                    logger.error(
                        f"[{filename}] Groq quota exhausted. "
                        f"retry-after = {retry_after_header:.0f}s "
                        f"({wait_mins}m {wait_secs}s). "
                        "Failing fast — hourly/daily token limit hit. "
                        "Please wait before re-uploading this batch."
                    )
                    raise RuntimeError(
                        f"Groq API quota exhausted for '{filename}'. "
                        f"Server requested a {retry_after_header:.0f}s wait "
                        f"({wait_mins}m {wait_secs}s) — this invoice cannot be "
                        "processed right now. Please wait and retry this file separately."
                    ) from exc
                else:
                    # Short retry-after: honour it (per-minute burst limit)
                    wait_s = retry_after_header
                    logger.info(
                        f"[{filename}] Groq retry-after = {retry_after_header:.0f}s "
                        "(within limit). Honouring it."
                    )

            # Add jitter (only when using backoff, not server-provided wait)
            if retry_after_header is None:
                jitter = random.uniform(-_JITTER_S, _JITTER_S)
                wait_s = max(1.0, wait_s + jitter)

            logger.warning(
                f"[{filename}] Groq 429 rate limit (attempt {attempt + 1}/{_MAX_RETRIES + 1}). "
                f"Waiting {wait_s:.1f}s before retry..."
            )
            time.sleep(wait_s)

        except GroqAPIStatusError as exc:
            # Non-429 API errors (auth, bad request, model unavailable, etc.)
            # — don't retry, surface immediately
            logger.error(
                f"[{filename}] Groq API error (HTTP {exc.status_code}): {exc.message}. Not retrying."
            )
            raise

        except Exception as exc:
            # Unexpected error (network timeout, etc.) — do NOT retry
            logger.error(f"[{filename}] Unexpected error calling Groq: {exc}. Not retrying.")
            raise

    raise last_exc  # unreachable but satisfies type checker


# ---------------------------------------------------------------------------
# Main extraction function
# ---------------------------------------------------------------------------
def extract_invoice_from_bytes(file_bytes: bytes, filename: str) -> ExtractedInvoice:
    """
    Sends a document to Azure Document Intelligence using the prebuilt-layout model
    and uses Groq LLM to extract structured fields into an ExtractedInvoice.

    Rate-limit resilience:
      - Markdown is trimmed to MAX_MARKDOWN_CHARS before sending to Groq
        to keep token usage predictable and within the free-tier limit.
      - The Groq call uses exponential backoff + retry-after header support
        via _call_groq_with_retry().
    """
    client = get_di_client()
    logger.info(f"Sending {filename} to Azure Document Intelligence (prebuilt-layout)...")

    # --- Step 1: Get Markdown from Azure DI ---
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

    # --- Step 2: Trim Markdown (Head-Tail Truncation) ---
    # We take the start and the end of the document to ensure we get both
    # the invoice header (vendor, date, inv #) and the footer (totals, tax summary).
    original_len = len(document_markdown)
    if original_len > MAX_MARKDOWN_CHARS:
        half_budget = MAX_MARKDOWN_CHARS // 2
        head = document_markdown[:half_budget]
        tail = document_markdown[-half_budget:]
        document_markdown = f"{head}\n\n[... Truncated {original_len - MAX_MARKDOWN_CHARS} characters for length ...]\n\n{tail}"
        logger.warning(
            f"[{filename}] Markdown trimmed from {original_len} to {MAX_MARKDOWN_CHARS} chars "
            "(Head-Tail truncation) to stay within Groq token budget."
        )

    # --- Step 3: Build prompt ---
    system_prompt = (
        "You are an expert Indian accounting AI. You will be provided with the Markdown "
        "text of an invoice. Your job is to extract the data into the exact JSON schema "
        "provided below.\n\n"
        "Rules:\n"
        "1. GSTIN must be exactly 15 alphanumeric characters.\n"
        "2. If a value is genuinely not present, return null. Do not fabricate data.\n"
        "3. Output MUST begin with the tag [ignoring loop detection] on its own line, "
        "followed by raw JSON only — no markdown, no backticks, no extra text.\n"
        "\n"
        "4. total_amount (CRITICAL):\n"
        "   - This is the FINAL amount the buyer must pay. Look for labels like:\n"
        "     'Amount Chargeable', 'Grand Total', 'Invoice Total', 'Total Amount Due',\n"
        "     'Net Payable', 'Balance Due', or the largest bolded amount at the bottom.\n"
        "   - It includes taxable amount + ALL taxes + any round-off adjustments.\n"
        "   - NEVER leave total_amount null if any payable amount appears on the invoice.\n"
        "\n"
        "5. taxable_amount:\n"
        "   - Look for 'Taxable Value', 'Sub Total', 'Total Taxable Amount', or the\n"
        "     pre-tax sum. This is the base amount BEFORE ANY GST or Duties are applied.\n"
        "   - If the invoice includes non-GST taxes (like 'Electricity Duty' or 'Cess'),\n"
        "     the taxable_amount should be the amount before those as well.\n"
        "\n"
        "6. gst_amount (TOTAL GST tax only):\n"
        "   - Sum ONLY actual GST components (CGST, SGST, IGST, UTGST).\n"
        "   - DO NOT include 'Electricity Duty', 'Regulatory Asset Charges', or 'Cess'\n"
        "     in the gst_amount. Those should be considered part of the service cost\n"
        "     unless they are explicitly labeled as a GST component.\n"
        "   - For invoices with a SINGLE GST rate: gst_amount = CGST + SGST (or IGST).\n"
        "   - For invoices with MULTIPLE GST rates: Sum ALL unique GST rows.\n"
        "\n"
        "7. gst_rate (RETURN AS STRING):\n"
        "   - For single-rate invoices: add CGST% + SGST% and return as a string (e.g. \"18\").\n"
        "   - For MIXED-rate invoices (line items at different rates like 18%/5%/0%):\n"
        "     Return ONLY the unique combined rates as a comma-separated string.\n"
        "     e.g. items at 18% and 5% → \"18, 5\"\n"
        "     e.g. items at 18%, 5%, and 0% → \"18, 5, 0\"\n"
        "   - NEVER compute an average or weighted rate. Return the actual rates found.\n"
        "   - Valid combined rates per line item: 0, 5, 12, 18, 28.\n"
        "   - Return null only if no rates can be identified at all.\n"
        "\n"
        "8. hsn_sac:\n"
        "   - Return the first or most prominent HSN/SAC code from the line items.\n"
        "     If multiple distinct codes exist, return the first one.\n"
        "\n"
        "9. tax_breakdown (IMPORTANT for mixed-rate invoices):\n"
        "   - Provide an array of objects, one for each unique GST rate found.\n"
        "   - e.g. If 3000 is taxed at 18% and 2000 is at 5%:\n"
        "     [{\"rate\": 18, \"taxable_amount\": 3000, \"gst_amount\": 540},\n"
        "      {\"rate\": 5, \"taxable_amount\": 2000, \"gst_amount\": 100}]\n"
        "   - If it is a single-rate invoice, provide one entry in this list.\n"
        "\n"
        "JSON Schema to output:\n"
        "{\n"
        '    "vendor_name": "string or null",\n'
        '    "vendor_gstin": "string or null",\n'
        '    "invoice_number": "string or null",\n'
        '    "invoice_date": "YYYY-MM-DD or null",\n'
        '    "taxable_amount": number or null,\n'
        '    "gst_amount": number or null,\n'
        '    "gst_rate": "string (e.g. 18 or 18, 5) or null",\n'
        '    "hsn_sac": "string or null",\n'
        '    "total_amount": number or null,\n'
        '    "tax_breakdown": [\n'
        '        {"rate": number, "taxable_amount": number, "gst_amount": number}\n'
        '    ]\n'
        "}"
    )
    user_content = f"Invoice Markdown:\n\n{document_markdown}"

    # --- Step 4: Call Groq with retry ---
    logger.info(f"[{filename}] Calling Groq model '{GROQ_MODEL}' for structured extraction...")
    try:
        response_content = _call_groq_with_retry(
            groq_client=Groq(api_key=LLM_API_KEY),
            system_prompt=system_prompt,
            user_content=user_content,
            filename=filename,
        )
    except Exception as e:
        logger.error(f"[{filename}] Groq extraction failed after all retries: {e}")
        raise

    # --- Step 5: Robust JSON extraction (3 layers) ---
    # Layer 0: Strip Groq loop-detection bypass tag
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

    # Layer 2: Direct JSON parse
    extracted_data = None
    try:
        extracted_data = json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Layer 3: Regex fallback — find first {...} JSON object even if prose surrounds it
    if extracted_data is None:
        json_match = re.search(r'\{[\s\S]*\}', cleaned)
        if json_match:
            try:
                extracted_data = json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

    if extracted_data is None:
        logger.error(
            f"[{filename}] All JSON parse attempts failed. "
            f"Raw LLM output preview: {response_content[:500]}"
        )
        raise ValueError(
            f"LLM returned unparseable output for '{filename}'. "
            "The document may be a scan, image-only PDF, or in an unsupported format. "
            f"Raw response preview: {response_content[:200]}"
        )

    # --- Step 6: Post-processing math fallbacks ---
    # gst_rate is now a string (e.g. "18" or "18, 5").
    # Normalise whatever the LLM returned to a clean string.
    _gst_rate_raw = extracted_data.get("gst_rate")
    gst_rate: Optional[str]  # final string value
    taxable_amount = extracted_data.get("taxable_amount")
    gst_amount = extracted_data.get("gst_amount")
    total_amount = extracted_data.get("total_amount")
    tax_breakdown_raw = extracted_data.get("tax_breakdown") or []
    STANDARD_RATES = {0.0, 5.0, 12.0, 18.0, 28.0}

    # Normalise gst_rate: ensure clean comma-separated string with % signs
    if _gst_rate_raw is None:
        gst_rate = None
    else:
        # 1. Split and clean
        parts = [p.strip().replace("%", "") for p in str(_gst_rate_raw).split(",") if p.strip()]
        # 2. Convert to unique numbers for filtering
        unique_rates = []
        for p in parts:
            try:
                val = float(p)
                if val not in unique_rates:
                    unique_rates.append(val)
            except ValueError:
                continue

        # 3. Filter out 0 if other rates exist (as per user request)
        if len(unique_rates) > 1 and 0 in unique_rates:
            unique_rates = [r for r in unique_rates if r != 0]

        # 4. Format as clean numeric string (no % yet, to allow math fallbacks to work)
        clean_parts = []
        for r in sorted(unique_rates, reverse=True):
            r_str = str(int(r)) if r.is_integer() else f"{r:.2f}"
            clean_parts.append(r_str)

        gst_rate = ", ".join(clean_parts) if clean_parts else None

    # Determine if this is a mixed-rate invoice (multiple rates in the string)
    _is_mixed_rate = gst_rate is not None and "," in gst_rate

    # Fallback A: compute gst_amount from rate + taxable — only for single-rate invoices
    if gst_amount is None and gst_rate is not None and not _is_mixed_rate and taxable_amount:
        try:
            # Strip % just in case it's already there
            _rate_float = float(gst_rate.replace("%", "").strip())
            gst_amount = round(taxable_amount * _rate_float / 100, 2)
            logger.info(
                f"[{filename}] gst_amount derived from taxable × rate: "
                f"{taxable_amount} × {_rate_float}% = {gst_amount}"
            )
        except ValueError:
            pass  # rate string wasn't a plain number

    # Fallback B removed: for mixed-rate invoices the LLM now returns the actual
    # rates as a comma-separated string, so there is nothing to compute here.

    # Fallback C: compute total_amount if missing but taxable + gst are known
    if total_amount is None and taxable_amount is not None and gst_amount is not None:
        total_amount = round(taxable_amount + gst_amount, 2)
        logger.info(
            f"[{filename}] total_amount computed from taxable + gst: "
            f"{taxable_amount} + {gst_amount} = {total_amount}"
        )

    # --- Step 6b: Detect and fix CGST+SGST split rate (single-rate invoices only) ---
    # If the LLM returned just one CGST/SGST component instead of the combined rate
    # (e.g. "9" when it should be "18"), double it.
    if (
        gst_rate is not None
        and not _is_mixed_rate
        and taxable_amount
        and gst_amount
        and taxable_amount > 0
    ):
        try:
            # Strip % just in case
            _rate_float = float(gst_rate.replace("%", "").strip())
            effective_rate = round((gst_amount / taxable_amount) * 100, 2)
            doubled_rate = round(_rate_float * 2, 2)
            if (
                _rate_float not in STANDARD_RATES
                and doubled_rate in STANDARD_RATES
                and abs(effective_rate - doubled_rate) <= 1.0
            ):
                logger.warning(
                    f"[{filename}] GST rate correction: LLM returned {_rate_float}% "
                    f"(single CGST/SGST component). Correcting to combined rate {int(doubled_rate)}% "
                    f"(taxable={taxable_amount}, gst={gst_amount})."
                )
                gst_rate = str(int(doubled_rate)) if doubled_rate.is_integer() else str(doubled_rate)
        except ValueError:
            pass  # gst_rate wasn't a parseable float — skip correction

    # --- Step 7: Final Formatting for UI ---
    # Append % to each component of the gst_rate string (e.g. "18, 5" -> "18%, 5%")
    final_gst_rate = None
    if gst_rate:
        final_gst_rate = ", ".join(f"{p.strip()}%" for p in gst_rate.split(",") if p.strip())

    logger.info(
        f"[{filename}] Extraction complete — "
        f"taxable={taxable_amount}, gst={gst_amount}, "
        f"rate={final_gst_rate}, total={total_amount}"
    )
    return ExtractedInvoice(
        vendor_name=extracted_data.get("vendor_name"),
        vendor_gstin=extracted_data.get("vendor_gstin"),
        invoice_number=extracted_data.get("invoice_number"),
        invoice_date=extracted_data.get("invoice_date"),
        taxable_amount=taxable_amount,
        gst_amount=gst_amount,
        gst_rate=final_gst_rate,
        hsn_sac=extracted_data.get("hsn_sac"),
        total_amount=total_amount,
        tax_breakdown=tax_breakdown_raw,
        raw_fields={
            "markdown_content": document_markdown,
            "raw_llm_response": response_content,
        },
    )
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import date


class ValidationError(BaseModel):
    field: str
    message: str
    severity: str  # "error" | "warning"


class InvoiceField(BaseModel):
    value: Optional[Any] = None
    confidence: Optional[float] = None


class ExtractedInvoice(BaseModel):
    vendor_name: Optional[str] = None
    vendor_gstin: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    taxable_amount: Optional[float] = None
    gst_amount: Optional[float] = None
    gst_rate: Optional[float] = None
    hsn_sac: Optional[str] = None
    total_amount: Optional[float] = None
    raw_fields: Optional[dict] = None


class AccountingRow(BaseModel):
    acc_period: Optional[str] = None
    trans_date: Optional[str] = None
    account_code: Optional[str] = None
    curr_code: str = "INR"
    trans_amount: Optional[float] = None
    dr_cr: Optional[str] = None
    jrnal_type: Optional[str] = None
    jrnal_source: str = "Not applicable"
    reference: Optional[str] = None
    description: Optional[str] = None
    asset_code: Optional[str] = None
    asset_indicator: Optional[str] = None
    asset_item_qty: Optional[str] = None
    due_date: Optional[str] = None
    branch_analysis_code: Optional[str] = None
    product_analysis_code: Optional[str] = None
    channel_analysis_code: Optional[str] = None
    sub_channel_analysis_code: Optional[str] = None
    underwriting_year_analysis_code: Optional[str] = None
    employee_code_analysis_code: Optional[str] = None
    tds_applicability_analysis_code: Optional[str] = None
    department_analysis_code: Optional[str] = None
    sequence_code_analysis_code: Optional[str] = None
    vendor_code_analysis_code: Optional[str] = None
    invoice_date: Optional[str] = None
    from_date: Optional[str] = None
    to_date: Optional[str] = None
    addl_date_4: Optional[str] = None
    addl_date_5: Optional[str] = None
    cheque_neft_number: Optional[str] = None
    invoice_number: Optional[str] = None
    additional_remarks: Optional[str] = None
    additional_remarks_2: Optional[str] = None
    credence_description: Optional[str] = None
    hsn_sac_no: Optional[str] = None
    taxable_on_amount: Optional[float] = None
    reverse_charge: str = "N"
    reverse_charge_pct: float = 0.0
    item_details_sr_no: Optional[str] = None
    goods_service: Optional[str] = None
    gst_tax_rate: Optional[float] = None
    original_invoice_no_dr_cr: Optional[str] = None
    advance_challan_no: Optional[str] = None


class InvoiceProcessingResult(BaseModel):
    filename: str
    status: str  # "success" | "error" | "warning"
    extracted: Optional[ExtractedInvoice] = None
    accounting_row: Optional[AccountingRow] = None
    validation_errors: List[ValidationError] = []
    error_message: Optional[str] = None


class ProcessInvoicesResponse(BaseModel):
    results: List[InvoiceProcessingResult]
    total: int
    success_count: int
    error_count: int
    warning_count: int

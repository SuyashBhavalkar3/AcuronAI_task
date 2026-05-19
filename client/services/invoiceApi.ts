const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://acuronaitask-production.up.railway.app";

export interface ValidationError {
  field: string;
  message: string;
  severity: "error" | "warning";
}

export interface TaxRateBreakdown {
  rate: number;
  taxable_amount: number;
  gst_amount: number;
}

export interface ExtractedInvoice {
  vendor_name: string | null;
  vendor_gstin: string | null;
  invoice_number: string | null;
  invoice_date: string | null;
  taxable_amount: number | null;
  gst_amount: number | null;
  gst_rate: string | null;
  hsn_sac: string | null;
  total_amount: number | null;
  tax_breakdown?: TaxRateBreakdown[];
}

export interface AccountingRow {
  acc_period: string | null;
  trans_date: string | null;
  account_code: string | null;
  curr_code: string;
  trans_amount: number | null;
  dr_cr: string | null;
  jrnal_type: string | null;
  jrnal_source: string;
  reference: string | null;
  description: string | null;
  branch_analysis_code: string | null;
  tds_applicability_analysis_code: string | null;
  vendor_code_analysis_code: string | null;
  invoice_date: string | null;
  cheque_neft_number: string | null;
  invoice_number: string | null;
  hsn_sac_no: string | null;
  taxable_on_amount: number | null;
  reverse_charge: string;
  reverse_charge_pct: number;
  goods_service: string | null;
  gst_tax_rate: string | null;
  [key: string]: unknown;
}

export interface InvoiceProcessingResult {
  filename: string;
  status: "success" | "error" | "warning";
  extracted: ExtractedInvoice | null;
  accounting_row: AccountingRow | null;
  validation_errors: ValidationError[];
  error_message: string | null;
}

export interface ProcessInvoicesResponse {
  results: InvoiceProcessingResult[];
  total: number;
  success_count: number;
  error_count: number;
  warning_count: number;
}

export async function uploadInvoices(files: File[]): Promise<ProcessInvoicesResponse> {
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }

  const response = await fetch(`${API_BASE}/api/invoices/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Upload failed: ${response.status} - ${error}`);
  }

  return response.json();
}

export async function exportToPdf(results: InvoiceProcessingResult[]): Promise<Blob> {
  const response = await fetch(`${API_BASE}/api/invoices/export-pdf`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(results),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Export failed: ${response.status} - ${error}`);
  }

  return response.blob();
}

export async function exportToExcel(results: InvoiceProcessingResult[]): Promise<Blob> {
  const response = await fetch(`${API_BASE}/api/invoices/export-excel`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(results),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Export failed: ${response.status} - ${error}`);
  }

  return response.blob();
}

export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

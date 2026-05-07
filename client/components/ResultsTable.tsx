"use client";

import React, { useState } from "react";
import { ProcessInvoicesResponse } from "@/services/invoiceApi";
import { formatCurrency, formatDate } from "@/lib/formatters";
import { CheckCircle, XCircle, AlertTriangle, ChevronDown, ChevronUp } from "lucide-react";

interface ResultsTableProps {
  data: ProcessInvoicesResponse;
}

export default function ResultsTable({ data }: ResultsTableProps) {
  const [expandedRow, setExpandedRow] = useState<string | null>(null);

  const statusIcon = (status: string) => {
    if (status === "success") return <CheckCircle className="w-4 h-4 text-emerald-400" />;
    if (status === "error") return <XCircle className="w-4 h-4 text-red-400" />;
    return <AlertTriangle className="w-4 h-4 text-amber-400" />;
  };

  const statusBadge = (status: string) => {
    const base = "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold border";
    if (status === "success") return `${base} bg-emerald-500/15 text-emerald-400 border-emerald-500/30`;
    if (status === "error") return `${base} bg-red-500/15 text-red-400 border-red-500/30`;
    return `${base} bg-amber-500/15 text-amber-400 border-amber-500/30`;
  };

  return (
    <div className="space-y-4">
      {/* Summary Bar */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: "Processed", value: data.total, color: "text-slate-200", bg: "bg-slate-700/40" },
          { label: "Success", value: data.success_count, color: "text-emerald-400", bg: "bg-emerald-500/10" },
          { label: "Warnings", value: data.warning_count, color: "text-amber-400", bg: "bg-amber-500/10" },
        ].map((s) => (
          <div key={s.label} className={`${s.bg} rounded-xl p-3 text-center border border-slate-700/40`}>
            <div className={`text-2xl font-bold ${s.color}`}>{s.value}</div>
            <div className="text-xs text-slate-500 mt-0.5">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Table */}
      <div className="rounded-xl overflow-hidden border border-slate-700/50">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-800/80 border-b border-slate-700/50">
                {["File", "Status", "Vendor", "Invoice #", "Date", "Taxable Amt", "GST", "Total", "Validation"].map(
                  (h) => (
                    <th
                      key={h}
                      className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider whitespace-nowrap"
                    >
                      {h}
                    </th>
                  )
                )}
                <th className="px-4 py-3 w-8" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/30">
              {data.results.map((result) => {
                const isExpanded = expandedRow === result.filename;
                const e = result.extracted;
                const a = result.accounting_row;

                return (
                  <React.Fragment key={result.filename}>
                    <tr
                      className={`transition-colors hover:bg-slate-800/40 cursor-pointer
                        ${result.status === "error" ? "bg-red-500/5" : ""}
                        ${result.status === "warning" ? "bg-amber-500/5" : ""}
                      `}
                      onClick={() => setExpandedRow(isExpanded ? null : result.filename)}
                    >
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          {statusIcon(result.status)}
                          <span className="text-slate-200 font-medium max-w-[140px] truncate" title={result.filename}>
                            {result.filename}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className={statusBadge(result.status)}>{result.status}</span>
                      </td>
                      <td className="px-4 py-3 text-slate-300 max-w-[120px] truncate">
                        {e?.vendor_name || "—"}
                      </td>
                      <td className="px-4 py-3 text-slate-300 font-mono text-xs">
                        {e?.invoice_number || "—"}
                      </td>
                      <td className="px-4 py-3 text-slate-400 whitespace-nowrap">
                        {formatDate(e?.invoice_date || null)}
                      </td>
                      <td className="px-4 py-3 text-slate-300 font-mono text-xs text-right whitespace-nowrap">
                        {formatCurrency(e?.taxable_amount || null)}
                      </td>
                      <td className="px-4 py-3 text-slate-300 font-mono text-xs text-right whitespace-nowrap">
                        {formatCurrency(e?.gst_amount || null)}
                      </td>
                      <td className="px-4 py-3 text-slate-100 font-semibold font-mono text-xs text-right whitespace-nowrap">
                        {formatCurrency(e?.total_amount || null)}
                      </td>
                      <td className="px-4 py-3">
                        {result.validation_errors.length === 0 ? (
                          <span className="text-emerald-400 text-xs">Clean</span>
                        ) : (
                          <span className="text-amber-400 text-xs">
                            {result.validation_errors.length} issue{result.validation_errors.length > 1 ? "s" : ""}
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {isExpanded ? (
                          <ChevronUp className="w-4 h-4 text-slate-400" />
                        ) : (
                          <ChevronDown className="w-4 h-4 text-slate-400" />
                        )}
                      </td>
                    </tr>

                    {/* Expanded Detail Row */}
                    {isExpanded && (
                      <tr key={`${result.filename}-expanded`} className="bg-slate-900/60">
                        <td colSpan={10} className="px-6 py-5">
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            {/* Extracted Data */}
                            <div>
                              <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
                                Extracted Data
                              </h4>
                              <div className="space-y-2">
                                {[
                                  ["Vendor Name", e?.vendor_name],
                                  ["GSTIN", e?.vendor_gstin],
                                  ["Invoice Number", e?.invoice_number],
                                  ["Invoice Date", formatDate(e?.invoice_date || null)],
                                  ["HSN/SAC", e?.hsn_sac],
                                  ["GST Rate", e?.gst_rate != null ? `${e.gst_rate}%` : null],
                                  ["Taxable Amount", formatCurrency(e?.taxable_amount || null)],
                                  ["GST Amount", formatCurrency(e?.gst_amount || null)],
                                  ["Total Amount", formatCurrency(e?.total_amount || null)],
                                ].map(([label, value]) => (
                                  <div key={label as string} className="flex justify-between gap-4 text-sm">
                                    <span className="text-slate-500">{label}</span>
                                    <span className="text-slate-300 font-medium text-right">{value || "—"}</span>
                                  </div>
                                ))}
                              </div>
                            </div>

                            {/* Accounting Row */}
                            <div>
                              <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
                                Accounting Mapping
                              </h4>
                              <div className="space-y-2">
                                {[
                                  ["GL Account", a?.account_code],
                                  ["Acc Period", a?.acc_period],
                                  ["Dr/Cr", a?.dr_cr],
                                  ["Journal Type", a?.jrnal_type],
                                  ["Vendor Code", a?.vendor_code_analysis_code],
                                  ["Branch Code", a?.branch_analysis_code],
                                  ["TDS Applicable", a?.tds_applicability_analysis_code],
                                  ["Curr Code", a?.curr_code],
                                  ["Reverse Charge", a?.reverse_charge],
                                  ["Goods/Service", a?.goods_service],
                                ].map(([label, value]) => (
                                  <div key={label as string} className="flex justify-between gap-4 text-sm">
                                    <span className="text-slate-500">{label}</span>
                                    <span className="text-slate-300 font-medium font-mono text-xs text-right">
                                      {(value as string) || "—"}
                                    </span>
                                  </div>
                                ))}
                              </div>
                            </div>

                            {/* Validation Errors */}
                            {result.validation_errors.length > 0 && (
                              <div className="md:col-span-2">
                                <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
                                  Validation Issues
                                </h4>
                                <div className="space-y-2">
                                  {result.validation_errors.map((err, i) => (
                                    <div
                                      key={i}
                                      className={`flex items-start gap-2 p-3 rounded-lg text-sm
                                        ${err.severity === "error"
                                          ? "bg-red-500/10 border border-red-500/20 text-red-300"
                                          : "bg-amber-500/10 border border-amber-500/20 text-amber-300"
                                        }`}
                                    >
                                      {err.severity === "error" ? (
                                        <XCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                                      ) : (
                                        <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                                      )}
                                      <div>
                                        <span className="font-semibold capitalize">{err.field.replace(/_/g, " ")}: </span>
                                        {err.message}
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Error Message */}
                            {result.error_message && (
                              <div className="md:col-span-2 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
                                <p className="text-sm text-red-300">{result.error_message}</p>
                              </div>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

"use client";

import React, { useState } from "react";
import { ProcessInvoicesResponse } from "@/services/invoiceApi";
import { formatCurrency, formatDate } from "@/lib/formatters";
import { CheckCircle, XCircle, AlertTriangle, ChevronDown, ChevronUp, FileText } from "lucide-react";

interface ResultsTableProps {
  data: ProcessInvoicesResponse;
}

export default function ResultsTable({ data }: ResultsTableProps) {
  const [expandedRow, setExpandedRow] = useState<string | null>(null);

  const statusIcon = (status: string) => {
    if (status === "success") return <CheckCircle className="w-4 h-4 text-emerald-400 drop-shadow-[0_0_8px_rgba(52,211,153,0.5)]" />;
    if (status === "error") return <XCircle className="w-4 h-4 text-red-400 drop-shadow-[0_0_8px_rgba(248,113,113,0.5)]" />;
    return <AlertTriangle className="w-4 h-4 text-amber-400 drop-shadow-[0_0_8px_rgba(251,191,36,0.5)]" />;
  };

  const statusBadge = (status: string) => {
    const base = "inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest border transition-colors";
    if (status === "success") return `${base} bg-emerald-500/10 text-emerald-400 border-emerald-500/20 shadow-[0_0_10px_rgba(52,211,153,0.1)]`;
    if (status === "error") return `${base} bg-red-500/10 text-red-400 border-red-500/20 shadow-[0_0_10px_rgba(248,113,113,0.1)]`;
    return `${base} bg-amber-500/10 text-amber-400 border-amber-500/20 shadow-[0_0_10px_rgba(251,191,36,0.1)]`;
  };

  return (
    <div className="space-y-6 p-1">
      {/* Summary Bar */}
      <div className="grid grid-cols-3 gap-4 p-4 md:p-6 pb-0">
        {[
          { label: "Processed", value: data.total, color: "text-white", glow: "shadow-indigo-500/20", icon: <FileText className="w-4 h-4 text-indigo-400 mb-2 opacity-50"/> },
          { label: "Success", value: data.success_count, color: "text-emerald-400", glow: "shadow-emerald-500/20", icon: <CheckCircle className="w-4 h-4 text-emerald-400 mb-2 opacity-50"/> },
          { label: "Warnings", value: data.warning_count, color: "text-amber-400", glow: "shadow-amber-500/20", icon: <AlertTriangle className="w-4 h-4 text-amber-400 mb-2 opacity-50"/> },
        ].map((s) => (
          <div key={s.label} className={`relative overflow-hidden rounded-2xl bg-white/[0.03] border border-white/5 p-4 flex flex-col items-center justify-center transition-all hover:bg-white/[0.05]`}>
            {s.icon}
            <div className={`text-3xl md:text-4xl font-extrabold ${s.color} drop-shadow-md`}>{s.value}</div>
            <div className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.2em] mt-1">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Table */}
      <div className="overflow-x-auto px-4 md:px-6 pb-6">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="border-b border-white/10">
              {["File", "Status", "Vendor", "Invoice #", "Date", "Taxable", "GST", "Total", "Validation"].map(
                (h) => (
                  <th
                    key={h}
                    className="px-4 py-4 text-left text-[10px] font-bold text-slate-500 uppercase tracking-widest whitespace-nowrap"
                  >
                    {h}
                  </th>
                )
              )}
              <th className="px-4 py-4 w-8" />
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {data.results.map((result) => {
              const isExpanded = expandedRow === result.filename;
              const e = result.extracted;
              const a = result.accounting_row;

              return (
                <React.Fragment key={result.filename}>
                  <tr
                    className={`transition-colors hover:bg-white/[0.04] cursor-pointer group
                      ${isExpanded ? "bg-white/[0.02]" : ""}
                    `}
                    onClick={() => setExpandedRow(isExpanded ? null : result.filename)}
                  >
                    <td className="px-4 py-4">
                      <div className="flex items-center gap-3">
                        {statusIcon(result.status)}
                        <span className="text-slate-200 font-medium max-w-[140px] truncate group-hover:text-white transition-colors" title={result.filename}>
                          {result.filename}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      <span className={statusBadge(result.status)}>{result.status}</span>
                    </td>
                    <td className="px-4 py-4 text-slate-300 max-w-[120px] truncate font-medium">
                      {e?.vendor_name || "—"}
                    </td>
                    <td className="px-4 py-4 text-indigo-300 font-mono text-xs">
                      {e?.invoice_number || "—"}
                    </td>
                    <td className="px-4 py-4 text-slate-400 whitespace-nowrap text-xs">
                      {formatDate(e?.invoice_date || null)}
                    </td>
                    <td className="px-4 py-4 text-slate-300 font-mono text-xs text-right whitespace-nowrap">
                      {formatCurrency(e?.taxable_amount || null)}
                    </td>
                    <td className="px-4 py-4 text-slate-300 font-mono text-xs text-right whitespace-nowrap">
                      {formatCurrency(e?.gst_amount || null)}
                    </td>
                    <td className="px-4 py-4 text-emerald-400 font-bold font-mono text-xs text-right whitespace-nowrap">
                      {formatCurrency(e?.total_amount || null)}
                    </td>
                    <td className="px-4 py-4">
                      {result.validation_errors.length === 0 ? (
                        <span className="text-emerald-500 text-xs font-bold uppercase tracking-wider">Clean</span>
                      ) : (
                        <span className="text-amber-400 text-xs font-bold uppercase tracking-wider">
                          {result.validation_errors.length} issue{result.validation_errors.length > 1 ? "s" : ""}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-4">
                      <div className="w-8 h-8 rounded-full flex items-center justify-center bg-white/5 text-slate-400 group-hover:bg-white/10 group-hover:text-white transition-all">
                        {isExpanded ? (
                          <ChevronUp className="w-4 h-4" />
                        ) : (
                          <ChevronDown className="w-4 h-4" />
                        )}
                      </div>
                    </td>
                  </tr>

                  {/* Expanded Detail Row */}
                  {isExpanded && (
                    <tr key={`${result.filename}-expanded`} className="bg-black/20 border-b border-white/10 shadow-inner">
                      <td colSpan={10} className="px-6 py-8">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 relative">
                           {/* Decorative line */}
                           <div className="hidden md:block absolute left-1/2 top-0 bottom-0 w-px bg-gradient-to-b from-transparent via-white/10 to-transparent -translate-x-1/2" />
                           
                          {/* Extracted Data */}
                          <div className="space-y-4">
                            <h4 className="text-[10px] font-bold text-indigo-400 uppercase tracking-[0.2em] flex items-center gap-2">
                              <SparkleIcon /> Semantic Extraction
                            </h4>
                            <div className="space-y-3 bg-white/[0.02] p-4 rounded-2xl border border-white/5">
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
                                <div key={label as string} className="flex justify-between gap-4 text-sm items-center border-b border-white/5 pb-2 last:border-0 last:pb-0">
                                  <span className="text-slate-500 font-medium">{label}</span>
                                  <span className="text-slate-200 font-semibold text-right">{value || "—"}</span>
                                </div>
                              ))}
                            </div>
                          </div>

                          {/* Accounting Row */}
                          <div className="space-y-4">
                            <h4 className="text-[10px] font-bold text-cyan-400 uppercase tracking-[0.2em] flex items-center gap-2">
                              <CodeIcon /> System Mapping
                            </h4>
                            <div className="space-y-3 bg-white/[0.02] p-4 rounded-2xl border border-white/5">
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
                                <div key={label as string} className="flex justify-between gap-4 text-sm items-center border-b border-white/5 pb-2 last:border-0 last:pb-0">
                                  <span className="text-slate-500 font-medium">{label}</span>
                                  <span className="text-indigo-200 font-mono text-xs font-semibold px-2 py-0.5 bg-indigo-500/10 rounded border border-indigo-500/20 text-right">
                                    {(value as string) || "—"}
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>

                          {/* Validation Errors */}
                          {result.validation_errors.length > 0 && (
                            <div className="md:col-span-2 mt-4 animate-in fade-in slide-in-from-bottom-2">
                              <h4 className="text-[10px] font-bold text-amber-400 uppercase tracking-[0.2em] mb-3">
                                Pipeline Interventions
                              </h4>
                              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                {result.validation_errors.map((err, i) => (
                                  <div
                                    key={i}
                                    className={`flex items-start gap-3 p-4 rounded-xl text-sm border backdrop-blur-md
                                      ${err.severity === "error"
                                        ? "bg-red-500/10 border-red-500/20 text-red-200 shadow-[0_0_15px_rgba(248,113,113,0.1)]"
                                        : "bg-amber-500/10 border-amber-500/20 text-amber-200 shadow-[0_0_15px_rgba(251,191,36,0.1)]"
                                      }`}
                                  >
                                    {err.severity === "error" ? (
                                      <XCircle className="w-5 h-5 flex-shrink-0 text-red-400 drop-shadow-md" />
                                    ) : (
                                      <AlertTriangle className="w-5 h-5 flex-shrink-0 text-amber-400 drop-shadow-md" />
                                    )}
                                    <div>
                                      <span className="font-bold capitalize block text-white mb-0.5">{err.field.replace(/_/g, " ")}</span>
                                      <span className="opacity-90 leading-relaxed text-xs">{err.message}</span>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Error Message */}
                          {result.error_message && (
                            <div className="md:col-span-2 p-4 rounded-xl bg-red-500/10 border border-red-500/20 shadow-[0_0_20px_rgba(248,113,113,0.15)] mt-4">
                              <p className="text-sm font-medium text-red-300 flex items-center gap-2">
                                <XCircle className="w-4 h-4" /> {result.error_message}
                              </p>
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
  );
}

// Simple internal icon components to save importing more from lucide
function SparkleIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/></svg>
  );
}

function CodeIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
  );
}

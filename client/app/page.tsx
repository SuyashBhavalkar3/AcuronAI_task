"use client";

import { useState, useRef } from "react";
import { uploadInvoices, exportToExcel, exportToPdf, downloadBlob, ProcessInvoicesResponse } from "@/services/invoiceApi";
import UploadZone from "@/components/UploadZone";
import ResultsTable from "@/components/ResultsTable";
import { Download, FileSpreadsheet, Zap, Shield, BarChart3, FileText } from "lucide-react";
import { toast } from "sonner";

export default function Home() {
  const [results, setResults] = useState<ProcessInvoicesResponse | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isExportingExcel, setIsExportingExcel] = useState(false);
  const [isExportingPdf, setIsExportingPdf] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const resultsRef = useRef<HTMLDivElement>(null);

  const handleFilesSelected = async (files: File[]) => {
    setIsProcessing(true);
    setUploadedFiles(files);
    try {
      const response = await uploadInvoices(files);
      setResults(response);
      toast.success(`Processed ${response.total} invoice${response.total > 1 ? "s" : ""} successfully.`);
      setTimeout(() => {
        resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 100);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      toast.error(`Processing failed: ${msg}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleExportExcel = async () => {
    if (uploadedFiles.length === 0) return;
    setIsExportingExcel(true);
    try {
      const blob = await exportToExcel(uploadedFiles);
      downloadBlob(blob, `invoice_accounting_${new Date().toISOString().slice(0, 10)}.xlsx`);
      toast.success("Excel file downloaded successfully.");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      toast.error(`Export failed: ${msg}`);
    } finally {
      setIsExportingExcel(false);
    }
  };

  const handleExportPdf = async () => {
    if (uploadedFiles.length === 0) return;
    setIsExportingPdf(true);
    try {
      const blob = await exportToPdf(uploadedFiles);
      downloadBlob(blob, `invoice_report_${new Date().toISOString().slice(0, 10)}.pdf`);
      toast.success("PDF file downloaded successfully.");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      toast.error(`Export failed: ${msg}`);
    } finally {
      setIsExportingPdf(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0f1e] text-white">
      {/* Ambient background gradients */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-blue-600/10 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-indigo-600/8 rounded-full blur-3xl" />
        <div className="absolute top-1/2 left-0 w-64 h-64 bg-violet-600/6 rounded-full blur-3xl" />
      </div>

      {/* Header */}
      <header className="relative border-b border-slate-800/60 bg-slate-900/40 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-500/30">
              <FileSpreadsheet className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-base font-bold text-white tracking-tight">Acuron Invoice Intelligence</h1>
              <p className="text-xs text-slate-400">Powered by Azure Document Intelligence</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="flex items-center gap-1.5 text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-3 py-1.5 rounded-full">
              <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse" />
              API Live
            </span>
          </div>
        </div>
      </header>

      <main className="relative max-w-7xl mx-auto px-6 py-10 space-y-10">
        {/* Hero Section */}
        {!results && !isProcessing && (
          <section className="text-center space-y-4 py-6">
            <div className="inline-flex items-center gap-2 bg-blue-500/10 border border-blue-500/20 rounded-full px-4 py-1.5 text-sm text-blue-400">
              <Zap className="w-3.5 h-3.5" />
              AI-Powered Invoice Processing
            </div>
            <h2 className="text-4xl font-bold text-white leading-tight">
              Extract. Validate. Export.
              <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-indigo-400">
                In seconds.
              </span>
            </h2>
            <p className="text-slate-400 max-w-xl mx-auto text-base">
              Upload your vendor invoices and our AI pipeline extracts structured accounting data,
              applies GST rules, and maps to your GL codes automatically.
            </p>

            {/* Feature pills */}
            <div className="flex flex-wrap justify-center gap-3 pt-2">
              {[
                { icon: Shield, label: "GSTIN Validation" },
                { icon: BarChart3, label: "GST Calculation Check" },
                { icon: FileSpreadsheet, label: "Excel Export" },
                { icon: Zap, label: "Multi-Invoice Batch" },
              ].map(({ icon: Icon, label }) => (
                <div
                  key={label}
                  className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800/60 border border-slate-700/50 text-sm text-slate-300"
                >
                  <Icon className="w-4 h-4 text-blue-400" />
                  {label}
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Upload Section */}
        <section className="bg-slate-900/50 border border-slate-700/50 rounded-2xl p-6 backdrop-blur-sm shadow-xl">
          <div className="flex items-center justify-between mb-5">
            <h3 className="text-base font-semibold text-slate-100">Upload Invoices</h3>
            {results && (
              <button
                onClick={() => { setResults(null); setUploadedFiles([]); }}
                className="text-xs text-slate-400 hover:text-slate-200 transition-colors"
              >
                ← New batch
              </button>
            )}
          </div>
          <UploadZone onFilesSelected={handleFilesSelected} isProcessing={isProcessing} />
        </section>

        {/* Processing Loader */}
        {isProcessing && (
          <section className="bg-slate-900/50 border border-blue-500/20 rounded-2xl p-8 text-center backdrop-blur-sm">
            <div className="flex flex-col items-center gap-5">
              <div className="relative w-16 h-16">
                <div className="absolute inset-0 border-4 border-blue-500/20 rounded-full" />
                <div className="absolute inset-0 border-4 border-transparent border-t-blue-500 rounded-full animate-spin" />
                <div className="absolute inset-2 border-4 border-transparent border-t-indigo-400 rounded-full animate-spin animation-delay-150" style={{ animationDirection: "reverse", animationDuration: "0.8s" }} />
              </div>
              <div className="space-y-2">
                <p className="text-lg font-semibold text-slate-100">Processing your invoices</p>
                <p className="text-sm text-slate-400">
                  Azure AI is extracting data · Validating GSTIN · Applying accounting rules...
                </p>
              </div>
              <div className="w-64 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                <div className="h-full bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full animate-[shimmer_1.5s_ease-in-out_infinite]" style={{ width: "60%" }} />
              </div>
            </div>
          </section>
        )}

        {/* Results Section */}
        {results && !isProcessing && (
          <section ref={resultsRef} className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-semibold text-slate-100">Processing Results</h3>
            <div className="flex items-center gap-3">
              <button
                onClick={handleExportPdf}
                disabled={isExportingPdf || uploadedFiles.length === 0}
                className={`
                  flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold
                  transition-all duration-200
                  ${isExportingPdf
                    ? "bg-slate-700 text-slate-500 cursor-not-allowed"
                    : "bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500 text-white shadow-lg shadow-red-500/20 hover:shadow-red-500/30 hover:-translate-y-0.5"
                  }
                `}
              >
                {isExportingPdf ? (
                  <>
                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Exporting...
                  </>
                ) : (
                  <>
                    <FileText className="w-4 h-4" />
                    Download PDF
                  </>
                )}
              </button>

              <button
                onClick={handleExportExcel}
                disabled={isExportingExcel || uploadedFiles.length === 0}
                className={`
                  flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold
                  transition-all duration-200
                  ${isExportingExcel
                    ? "bg-slate-700 text-slate-500 cursor-not-allowed"
                    : "bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white shadow-lg shadow-emerald-500/20 hover:shadow-emerald-500/30 hover:-translate-y-0.5"
                  }
                `}
              >
                {isExportingExcel ? (
                  <>
                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Exporting...
                  </>
                ) : (
                  <>
                    <Download className="w-4 h-4" />
                    Download Excel
                  </>
                )}
              </button>
            </div>
            </div>

            <div className="bg-slate-900/50 border border-slate-700/50 rounded-2xl p-6 backdrop-blur-sm shadow-xl">
              <ResultsTable data={results} />
            </div>
          </section>
        )}
      </main>

      {/* Footer */}
      <footer className="relative border-t border-slate-800/60 mt-16 py-6">
        <div className="max-w-7xl mx-auto px-6 flex items-center justify-between text-xs text-slate-600">
          <span>Acuron Invoice Intelligence · MVP v1.0</span>
          <span>FastAPI + Azure Document Intelligence + Next.js</span>
        </div>
      </footer>
    </div>
  );
}

"use client";

import { useState, useRef } from "react";
import { uploadInvoices, exportToPdf, downloadBlob, ProcessInvoicesResponse } from "@/services/invoiceApi";
import UploadZone from "@/components/UploadZone";
import ResultsTable from "@/components/ResultsTable";
import { Download, FileSpreadsheet, Zap, Shield, BarChart3, FileText } from "lucide-react";
import { toast } from "sonner";

export default function Home() {
  const [results, setResults] = useState<ProcessInvoicesResponse | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
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
    <div className="min-h-screen bg-slate-50 text-slate-800 font-sans">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-slate-200 bg-white">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded bg-blue-600 flex items-center justify-center">
              <FileSpreadsheet className="w-4 h-4 text-white" />
            </div>
            <div>
              <h1 className="text-sm font-bold text-slate-900 tracking-tight">Acuron Ai Solutions Pvt Ltd</h1>
              <p className="text-[10px] text-slate-500 font-medium tracking-wide">info@acuronai.com | +91 9552033662 | acuronai.com</p>
            </div>
          </div>
          <div className="hidden md:flex items-center gap-4">
            <div className="flex items-center gap-2 px-3 py-1 rounded border border-slate-200 bg-slate-50">
              <span className="w-2 h-2 bg-emerald-500 rounded-full" />
              <span className="text-[10px] font-bold text-slate-600 uppercase tracking-wider">System Active</span>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-12 space-y-12">
        {/* Hero Section */}
        {!results && !isProcessing && (
          <section className="space-y-4 max-w-2xl">
            <h2 className="text-4xl font-extrabold text-slate-900 tracking-tight leading-tight">
              Professional Invoice Intelligence.
            </h2>
            <p className="text-lg text-slate-600 leading-relaxed font-medium">
              A clean pipeline for automated data extraction, GST validation, and accounting mapping.
            </p>
            <div className="flex flex-wrap gap-3 pt-2">
              {["GST Validation", "Math Verification", "PDF Reports"].map((tag) => (
                <span key={tag} className="px-3 py-1 rounded bg-slate-200 text-slate-700 text-[10px] font-bold uppercase tracking-wider">
                  {tag}
                </span>
              ))}
            </div>
          </section>
        )}

        {/* Upload Section */}
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-[0.2em] text-slate-400">Processing Console</h3>
            {results && (
              <button
                onClick={() => { setResults(null); setUploadedFiles([]); }}
                className="text-xs font-bold text-blue-600 hover:underline"
              >
                New batch
              </button>
            )}
          </div>
          
          <div className="bg-white border-2 border-slate-200 rounded-lg overflow-hidden">
            <UploadZone onFilesSelected={handleFilesSelected} isProcessing={isProcessing} />
            <div className="py-3 bg-slate-100 border-t border-slate-200 text-center">
              <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">
                Support: info@acuronai.com | +91 9552033662 | acuronai.com
              </p>
            </div>
          </div>
        </section>

        {/* Processing Loader */}
        {isProcessing && (
          <section className="py-20 flex flex-col items-center justify-center space-y-4">
            <div className="w-12 h-12 border-4 border-slate-200 border-t-blue-600 rounded-full animate-spin" />
            <div className="text-center">
              <p className="text-sm font-bold text-slate-900 uppercase tracking-widest">Analyzing Invoices</p>
              <p className="text-xs text-slate-500 font-medium mt-1">Verifying tax and accounting logic...</p>
            </div>
          </section>
        )}

        {/* Results Section */}
        {results && !isProcessing && (
          <section ref={resultsRef} className="space-y-6">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold uppercase tracking-[0.2em] text-slate-400">Extracted Results</h3>
              <button
                onClick={handleExportPdf}
                disabled={isExportingPdf || uploadedFiles.length === 0}
                className={`
                  px-8 py-3 rounded font-bold text-xs uppercase tracking-widest transition-all
                  ${isExportingPdf
                    ? "bg-slate-100 text-slate-400 cursor-not-allowed border border-slate-200"
                    : "bg-blue-600 text-white hover:bg-blue-700 active:scale-95"
                  }
                `}
              >
                {isExportingPdf ? "Exporting..." : "Download PDF"}
              </button>
            </div>

            <div className="bg-white border-2 border-slate-200 rounded-lg shadow-sm">
              <ResultsTable data={results} />
            </div>
          </section>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 mt-20 py-16 bg-white">
        <div className="max-w-6xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-8">
          <div className="space-y-2 text-center md:text-left">
            <p className="text-sm font-bold text-slate-900">Acuron Ai Solutions Pvt Ltd</p>
            <p className="text-[10px] text-slate-400 font-bold tracking-[0.2em] uppercase">Precision Intelligence Engine</p>
          </div>
          <div className="flex flex-wrap justify-center gap-8 text-[10px] font-bold uppercase tracking-widest text-slate-500">
            <a href="mailto:info@acuronai.com" className="hover:text-blue-600">info@acuronai.com</a>
            <span>+91 9552033662</span>
            <a href="https://acuronai.com" target="_blank" className="hover:text-blue-600">acuronai.com</a>
          </div>
        </div>
      </footer>
    </div>
  );
}

"use client";

import { useState, useRef } from "react";
import { uploadInvoices, exportToPdf, downloadBlob, ProcessInvoicesResponse } from "@/services/invoiceApi";
import UploadZone from "@/components/UploadZone";
import ResultsTable from "@/components/ResultsTable";
import { FileSpreadsheet, Sparkles } from "lucide-react";
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
    if (!results) return;
    setIsExportingPdf(true);
    try {
      const blob = await exportToPdf(results.results);
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
    <div className="min-h-screen bg-[#0a0f1e] text-slate-300 font-sans relative selection:bg-indigo-500/30">
      {/* Dynamic Background Effects */}
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[50%] rounded-full bg-indigo-600/20 blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[50%] rounded-full bg-cyan-600/10 blur-[120px] pointer-events-none" />
      <div className="absolute top-[40%] left-[60%] w-[30%] h-[30%] rounded-full bg-emerald-600/5 blur-[100px] pointer-events-none" />

      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-white/10 bg-[#0a0f1e]/70 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-cyan-500 flex items-center justify-center shadow-[0_0_20px_rgba(99,102,241,0.4)]">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-sm font-bold text-white tracking-tight">Acuron Ai Solutions Pvt Ltd</h1>
              <p className="text-[10px] text-indigo-300 font-medium tracking-wider">info@acuronai.com | +91 9552033662 | acuronai.com</p>
            </div>
          </div>
          <div className="hidden md:flex items-center gap-4">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full border border-white/10 bg-white/5 backdrop-blur-md">
              <span className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse shadow-[0_0_8px_rgba(52,211,153,0.8)]" />
              <span className="text-[10px] font-bold text-slate-300 uppercase tracking-widest">System Active</span>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-16 space-y-16 relative z-10">
        {/* Hero Section */}
        {!results && !isProcessing && (
          <section className="space-y-6 max-w-3xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs font-bold tracking-widest uppercase mb-2">
              <Sparkles className="w-3 h-3" />
              Next-Gen Extraction
            </div>
            <h2 className="text-5xl md:text-6xl font-extrabold tracking-tight leading-tight text-white">
              Professional{" "}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-cyan-400 to-emerald-400">
                Invoice Intelligence.
              </span>
            </h2>
            <p className="text-lg md:text-xl text-slate-400 leading-relaxed font-light">
              A deeply integrated, hybrid AI pipeline for automated data extraction, strict GST validation, and direct accounting mapping.
            </p>
            <div className="flex flex-wrap gap-3 pt-4">
              {["Semantic Analysis", "Math Verification", "Layout-Agnostic", "Export Ready"].map((tag) => (
                <span key={tag} className="px-4 py-1.5 rounded-full bg-white/5 border border-white/10 text-slate-300 text-[10px] font-bold uppercase tracking-widest hover:bg-white/10 transition-colors cursor-default">
                  {tag}
                </span>
              ))}
            </div>
          </section>
        )}

        {/* Upload Section */}
        <section className="space-y-6">
          <div className="flex items-center justify-between">
            <div className="flex flex-col md:flex-row md:items-center gap-2 md:gap-6">
              <h3 className="text-xs font-bold uppercase tracking-[0.2em] text-slate-500">Processing Console</h3>
              <span className="hidden md:inline text-white/20">•</span>
              <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">
                Support: info@acuronai.com | +91 9552033662 | acuronai.com
              </p>
            </div>
            {results && (
              <button
                onClick={() => { setResults(null); setUploadedFiles([]); }}
                className="text-xs font-bold text-indigo-400 hover:text-indigo-300 hover:underline underline-offset-4 transition-all"
              >
                Reset Engine
              </button>
            )}
          </div>
          
          <div className="bg-white/[0.02] backdrop-blur-xl border border-white/10 rounded-2xl overflow-hidden shadow-2xl relative group">
            <div className="absolute inset-0 bg-gradient-to-b from-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />
            <div className="p-1">
              <UploadZone onFilesSelected={handleFilesSelected} isProcessing={isProcessing} />
            </div>
          </div>
        </section>

        {/* Processing Loader */}
        {isProcessing && (
          <section className="py-24 flex flex-col items-center justify-center space-y-6">
            <div className="relative">
              <div className="w-16 h-16 border-4 border-white/5 border-t-indigo-500 rounded-full animate-spin" />
              <div className="absolute inset-0 w-16 h-16 border-4 border-transparent border-b-cyan-400 rounded-full animate-[spin_1.5s_linear_infinite_reverse]" />
            </div>
            <div className="text-center space-y-2">
              <p className="text-sm font-bold text-white uppercase tracking-widest bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-cyan-400 animate-pulse">
                Analyzing Invoices
              </p>
              <p className="text-xs text-slate-400 font-medium">Extracting semantic structure & applying accounting rules...</p>
            </div>
          </section>
        )}

        {/* Results Section */}
        {results && !isProcessing && (
          <section ref={resultsRef} className="space-y-6 animate-in fade-in slide-in-from-bottom-8 duration-700">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold uppercase tracking-[0.2em] text-slate-500">Extracted Results</h3>
              <div className="flex gap-3">
                <button
                  onClick={handleExportPdf}
                  disabled={isExportingPdf || uploadedFiles.length === 0}
                  className={`
                    px-6 py-2.5 rounded-lg font-bold text-xs uppercase tracking-widest transition-all duration-300 relative overflow-hidden group
                    ${isExportingPdf
                      ? "bg-white/5 text-slate-500 cursor-not-allowed border border-white/10"
                      : "bg-indigo-600/20 text-indigo-300 hover:text-white border border-indigo-500/30 hover:border-indigo-400/50 hover:bg-indigo-600/40 hover:shadow-[0_0_20px_rgba(79,70,229,0.3)] active:scale-95"
                    }
                  `}
                >
                  {!isExportingPdf && (
                    <span className="absolute inset-0 w-full h-full bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-[100%] group-hover:animate-[shimmer_1.5s_infinite]" />
                  )}
                  <span className="relative z-10">{isExportingPdf ? "Exporting..." : "Download Report"}</span>
                </button>
              </div>
            </div>

            <div className="bg-white/[0.02] backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl">
              <ResultsTable data={results} />
            </div>
          </section>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-white/5 mt-24 py-12 bg-black/20 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="space-y-1 text-center md:text-left">
            <p className="text-sm font-bold text-white">Acuron Ai Solutions Pvt Ltd</p>
            <p className="text-[10px] text-slate-500 font-bold tracking-[0.2em] uppercase">Precision Intelligence Engine</p>
          </div>
          <div className="flex flex-wrap justify-center gap-6 text-[10px] font-bold uppercase tracking-widest text-slate-500">
            <a href="mailto:info@acuronai.com" className="hover:text-indigo-400 transition-colors cursor-pointer">info@acuronai.com</a>
            <span>+91 9552033662</span>
            <a href="https://acuronai.com" target="_blank" className="hover:text-indigo-400 transition-colors cursor-pointer">acuronai.com</a>
          </div>
        </div>
      </footer>
    </div>
  );
}

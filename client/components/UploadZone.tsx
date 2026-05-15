"use client";

import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, FileText, X, AlertCircle } from "lucide-react";

interface UploadZoneProps {
  onFilesSelected: (files: File[]) => void;
  isProcessing: boolean;
}

export default function UploadZone({ onFilesSelected, isProcessing }: UploadZoneProps) {
  const [pendingFiles, setPendingFiles] = useState<File[]>([]);

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      const merged = [...pendingFiles, ...acceptedFiles].filter(
        (f, i, arr) => arr.findIndex((x) => x.name === f.name) === i
      );
      setPendingFiles(merged);
    },
    [pendingFiles]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "image/png": [".png"],
      "image/jpeg": [".jpg", ".jpeg"],
      "image/tiff": [".tiff"],
    },
    disabled: isProcessing,
    multiple: true,
  });

  const removeFile = (name: string) =>
    setPendingFiles((prev) => prev.filter((f) => f.name !== name));

  const handleProcess = () => {
    if (pendingFiles.length > 0) {
      onFilesSelected(pendingFiles);
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="space-y-6 p-6 md:p-8">
      {/* Drop Zone */}
      <div
        {...getRootProps()}
        className={`
          relative border-2 border-dashed rounded-3xl p-12 text-center cursor-pointer
          transition-all duration-500 ease-out overflow-hidden
          ${isDragActive
            ? "border-indigo-500/50 bg-indigo-500/10 scale-[1.02] shadow-[0_0_30px_rgba(99,102,241,0.2)]"
            : "border-white/10 bg-white/[0.02] hover:border-indigo-500/30 hover:bg-white/[0.04]"
          }
          ${isProcessing ? "opacity-50 cursor-not-allowed" : ""}
        `}
      >
        <input {...getInputProps()} />
        <div className="flex flex-col items-center gap-5 relative z-10">
          <div
            className={`
              w-20 h-20 rounded-2xl flex items-center justify-center
              transition-all duration-500 shadow-xl
              ${isDragActive 
                ? "bg-indigo-500/20 scale-110 shadow-indigo-500/20" 
                : "bg-white/5 border border-white/10 group-hover:scale-105"
              }
            `}
          >
            <Upload
              className={`w-10 h-10 transition-colors duration-500 ${isDragActive ? "text-indigo-400 animate-pulse" : "text-slate-400"}`}
            />
          </div>
          {isDragActive ? (
            <div className="space-y-1">
              <p className="text-xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-cyan-400">
                Release to Ignite Pipeline
              </p>
              <p className="text-sm text-indigo-300/70">Analyzing file formats...</p>
            </div>
          ) : (
            <div className="space-y-2">
              <p className="text-xl font-bold text-slate-200">
                Drag & Drop Invoice Data
              </p>
              <p className="text-sm text-slate-400">
                or <span className="text-indigo-400 hover:text-indigo-300 transition-colors cursor-pointer border-b border-indigo-400/30 hover:border-indigo-300 pb-0.5">browse your secure storage</span>
              </p>
              <div className="flex items-center justify-center gap-2 mt-4">
                {["PDF", "PNG", "JPG", "TIFF"].map(ext => (
                  <span key={ext} className="px-2 py-1 rounded bg-white/5 border border-white/10 text-[10px] font-bold text-slate-500 tracking-widest">{ext}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* File List */}
      {pendingFiles.length > 0 && (
        <div className="space-y-3 animate-in fade-in slide-in-from-top-4 duration-500">
          <div className="flex items-center justify-between px-2">
            <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">
              {pendingFiles.length} Document{pendingFiles.length > 1 ? "s" : ""} Queued
            </p>
          </div>
          <div className="space-y-2 max-h-64 overflow-y-auto pr-2 custom-scrollbar">
            {pendingFiles.map((file, idx) => (
              <div
                key={file.name}
                className="flex items-center gap-4 p-4 rounded-2xl bg-white/[0.03] border border-white/5 hover:border-white/10 hover:bg-white/[0.05] transition-all group animate-in fade-in slide-in-from-right-4"
                style={{ animationDelay: `${idx * 50}ms` }}
              >
                <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center flex-shrink-0">
                  <FileText className="w-5 h-5 text-indigo-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-slate-200 truncate">{file.name}</p>
                  <p className="text-xs text-slate-500 font-mono mt-0.5">{formatBytes(file.size)}</p>
                </div>
                {!isProcessing && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      removeFile(file.name);
                    }}
                    className="w-8 h-8 rounded-lg flex items-center justify-center text-slate-500 hover:text-red-400 hover:bg-red-500/10 transition-colors opacity-0 group-hover:opacity-100"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex gap-4 pt-2">
        <button
          onClick={handleProcess}
          disabled={pendingFiles.length === 0 || isProcessing}
          className={`
            flex-1 py-4 px-6 rounded-2xl font-bold text-sm tracking-wide uppercase
            transition-all duration-300 relative overflow-hidden group
            ${pendingFiles.length === 0 || isProcessing
              ? "bg-white/5 text-slate-500 cursor-not-allowed border border-white/5"
              : "bg-gradient-to-r from-indigo-600 to-cyan-600 text-white shadow-[0_0_20px_rgba(99,102,241,0.3)] hover:shadow-[0_0_30px_rgba(99,102,241,0.5)] hover:-translate-y-1"
            }
          `}
        >
          {isProcessing ? (
            <span className="flex items-center justify-center gap-3">
              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              Processing Pipeline...
            </span>
          ) : (
            <>
              {pendingFiles.length > 0 && (
                <span className="absolute inset-0 w-full h-full bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-[100%] group-hover:animate-[shimmer_1.5s_infinite]" />
              )}
              <span className="relative z-10">
                Extract Data ({pendingFiles.length})
              </span>
            </>
          )}
        </button>
        {pendingFiles.length > 0 && !isProcessing && (
          <button
            onClick={() => setPendingFiles([])}
            className="px-6 py-4 rounded-2xl text-xs font-bold uppercase tracking-widest text-slate-400 hover:text-red-400 hover:bg-red-500/10 border border-white/10 hover:border-red-500/30 transition-all duration-300"
          >
            Clear
          </button>
        )}
      </div>
    </div>
  );
}

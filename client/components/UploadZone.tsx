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
    <div className="space-y-4">
      {/* Drop Zone */}
      <div
        {...getRootProps()}
        className={`
          relative border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer
          transition-all duration-300 ease-in-out
          ${isDragActive
            ? "border-blue-400 bg-blue-500/10 scale-[1.01]"
            : "border-slate-600 bg-slate-800/40 hover:border-blue-500 hover:bg-slate-800/60"
          }
          ${isProcessing ? "opacity-50 cursor-not-allowed" : ""}
        `}
      >
        <input {...getInputProps()} />
        <div className="flex flex-col items-center gap-4">
          <div
            className={`
              w-16 h-16 rounded-2xl flex items-center justify-center
              transition-all duration-300
              ${isDragActive ? "bg-blue-500/30 scale-110" : "bg-slate-700/60"}
            `}
          >
            <Upload
              className={`w-8 h-8 transition-colors duration-300 ${isDragActive ? "text-blue-400" : "text-slate-400"}`}
            />
          </div>
          {isDragActive ? (
            <div>
              <p className="text-lg font-semibold text-blue-400">Drop your invoices here</p>
              <p className="text-sm text-blue-300/70">Release to add files</p>
            </div>
          ) : (
            <div>
              <p className="text-lg font-semibold text-slate-200">
                Drag & drop invoice files here
              </p>
              <p className="text-sm text-slate-400 mt-1">
                or <span className="text-blue-400 underline underline-offset-2">click to browse</span>
              </p>
              <p className="text-xs text-slate-500 mt-3">
                Supports PDF, PNG, JPG, JPEG, TIFF · Max 20MB per file
              </p>
            </div>
          )}
        </div>
      </div>

      {/* File List */}
      {pendingFiles.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">
            {pendingFiles.length} file{pendingFiles.length > 1 ? "s" : ""} selected
          </p>
          <div className="space-y-2 max-h-48 overflow-y-auto pr-1 custom-scrollbar">
            {pendingFiles.map((file) => (
              <div
                key={file.name}
                className="flex items-center gap-3 p-3 rounded-xl bg-slate-800/60 border border-slate-700/50 group"
              >
                <div className="w-8 h-8 rounded-lg bg-blue-500/20 flex items-center justify-center flex-shrink-0">
                  <FileText className="w-4 h-4 text-blue-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-200 truncate">{file.name}</p>
                  <p className="text-xs text-slate-500">{formatBytes(file.size)}</p>
                </div>
                {!isProcessing && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      removeFile(file.name);
                    }}
                    className="w-6 h-6 rounded-md flex items-center justify-center text-slate-500 hover:text-red-400 hover:bg-red-400/10 transition-colors opacity-0 group-hover:opacity-100"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex gap-3">
        <button
          onClick={handleProcess}
          disabled={pendingFiles.length === 0 || isProcessing}
          className={`
            flex-1 py-3 px-6 rounded-xl font-semibold text-sm
            transition-all duration-200
            ${pendingFiles.length === 0 || isProcessing
              ? "bg-slate-700 text-slate-500 cursor-not-allowed"
              : "bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white shadow-lg shadow-blue-500/20 hover:shadow-blue-500/40 hover:-translate-y-0.5 active:translate-y-0"
            }
          `}
        >
          {isProcessing ? (
            <span className="flex items-center justify-center gap-2">
              <span className="w-4 h-4 border-2 border-slate-400/30 border-t-slate-400 rounded-full animate-spin" />
              Processing...
            </span>
          ) : (
            `Process ${pendingFiles.length > 0 ? `${pendingFiles.length} ` : ""}Invoice${pendingFiles.length !== 1 ? "s" : ""}`
          )}
        </button>
        {pendingFiles.length > 0 && !isProcessing && (
          <button
            onClick={() => setPendingFiles([])}
            className="px-4 py-3 rounded-xl text-sm text-slate-400 hover:text-red-400 hover:bg-red-400/10 border border-slate-700 hover:border-red-400/30 transition-all duration-200"
          >
            Clear all
          </button>
        )}
      </div>
    </div>
  );
}

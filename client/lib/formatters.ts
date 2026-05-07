export type InvoiceStatus = "success" | "error" | "warning" | "idle";

export function formatCurrency(amount: number | null, currency = "INR"): string {
  if (amount === null || amount === undefined) return "—";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
  }).format(amount);
}

export function formatDate(dateStr: string | null): string {
  if (!dateStr) return "—";
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
  } catch {
    return dateStr;
  }
}

export function getStatusColor(status: InvoiceStatus) {
  switch (status) {
    case "success":
      return "bg-emerald-500/20 text-emerald-400 border-emerald-500/30";
    case "error":
      return "bg-red-500/20 text-red-400 border-red-500/30";
    case "warning":
      return "bg-amber-500/20 text-amber-400 border-amber-500/30";
    default:
      return "bg-slate-500/20 text-slate-400 border-slate-500/30";
  }
}

export function getStatusIcon(status: InvoiceStatus): string {
  switch (status) {
    case "success": return "✓";
    case "error": return "✗";
    case "warning": return "⚠";
    default: return "—";
  }
}

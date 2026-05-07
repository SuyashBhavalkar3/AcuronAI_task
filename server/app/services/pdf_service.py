import io
from typing import List
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from app.schemas.invoice import InvoiceProcessingResult

def generate_pdf(results: List[InvoiceProcessingResult]) -> bytes:
    """
    Generate a PDF document from processing results and return bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor("#1E3A5F"),
        alignment=1, # Center
        spaceAfter=20
    )
    
    elements = []
    
    # --- 1. Summary Table ---
    elements.append(Paragraph("Invoice Processing Summary", title_style))
    
    summary_header = ["File Name", "Status", "Vendor", "Total Amount"]
    summary_data = [summary_header]
    
    for res in results:
        e = res.extracted
        summary_data.append([
            res.filename,
            res.status.upper(),
            e.vendor_name if e and e.vendor_name else "—",
            f"{e.total_amount:,.2f}" if e and e.total_amount is not None else "—"
        ])
    
    summary_table = Table(summary_data, colWidths=[200, 80, 150, 100])
    summary_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E3A5F")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
    ])
    summary_table.setStyle(summary_style)
    elements.append(summary_table)
    elements.append(Spacer(1, 30))
    
    # --- 2. Detailed Breakdown per Invoice ---
    section_style = ParagraphStyle('SectionStyle', parent=styles['Heading2'], textColor=colors.HexColor("#1E3A5F"), spaceBefore=15)
    label_style = ParagraphStyle('LabelStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9)
    value_style = ParagraphStyle('ValueStyle', parent=styles['Normal'], fontSize=9)

    for res in results:
        elements.append(Paragraph(f"Details: {res.filename}", section_style))
        
        # Split into two columns: Extracted Data and Accounting Mapping
        e = res.extracted
        a = res.accounting_row
        
        extracted_info = [
            ["FIELD", "VALUE"],
            ["Vendor Name", e.vendor_name or "—"],
            ["GSTIN", e.vendor_gstin or "—"],
            ["Invoice #", e.invoice_number or "—"],
            ["Date", e.invoice_date or "—"],
            ["Taxable Amt", f"{e.taxable_amount:,.2f}" if e.taxable_amount else "—"],
            ["GST Amt", f"{e.gst_amount:,.2f}" if e.gst_amount else "—"],
            ["GST Rate", f"{e.gst_rate}%" if e.gst_rate is not None else "—"],
            ["HSN/SAC", e.hsn_sac or "—"],
            ["Total", f"{e.total_amount:,.2f}" if e.total_amount else "—"]
        ]
        
        mapping_info = [
            ["MAPPING", "VALUE"],
            ["GL Account", a.account_code or "—"],
            ["Acc Period", a.acc_period or "—"],
            ["Dr/Cr", a.dr_cr or "—"],
            ["Jrnal Type", a.jrnal_type or "—"],
            ["Reference", a.reference or "—"],
            ["TDS Code", a.tds_applicability_analysis_code or "—"],
            ["Branch", a.branch_analysis_code or "—"],
            ["GST Ref", a.cheque_neft_number or "—"],
            ["Remarks", a.additional_remarks or "—"]
        ]
        
        t_ext = Table(extracted_info, colWidths=[100, 150])
        t_map = Table(mapping_info, colWidths=[100, 150])
        
        detail_style = TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (1, 0), colors.lightgrey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ])
        t_ext.setStyle(detail_style)
        t_map.setStyle(detail_style)
        
        # Combine them side-by-side
        outer_table = Table([[t_ext, Spacer(20, 0), t_map]], colWidths=[260, 20, 260])
        elements.append(outer_table)
        
        # Validation Issues
        if res.validation_errors:
            elements.append(Paragraph("Validation Issues:", label_style))
            for err in res.validation_errors:
                color = "red" if err.severity == "error" else "orange"
                elements.append(Paragraph(f"• <font color='{color}'>[{err.field}] {err.message}</font>", value_style))
        
        elements.append(Spacer(1, 15))

    # Build PDF
    doc.build(elements)
    
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

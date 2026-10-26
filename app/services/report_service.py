import os
import json
from pathlib import Path
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from app.models.inspection import Inspection

def generate_inspection_pdf_report(inspection: Inspection, output_path: Path) -> str:
    """
    Generates an official pharmaceutical inspection and risk screening PDF report.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0f2b48')
    )
    
    subtitle_style = ParagraphStyle(
        'DocSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#556980')
    )

    heading2_style = ParagraphStyle(
        'SecHead',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#0f2b48'),
        spaceBefore=12,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#223344')
    )

    badge_risk_style = ParagraphStyle(
        'RiskBadge',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#b30000') if inspection.risk_level == 'high' else colors.HexColor('#008000')
    )

    disclaimer_style = ParagraphStyle(
        'Disclaimer',
        parent=styles['Italic'],
        fontName='Helvetica-Oblique',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#667788')
    )

    story = []

    # 1. Header Banner
    story.append(Paragraph("MediShield AI - Pharmaceutical Risk Screening Report", title_style))
    story.append(Paragraph("Visual Inspection, Reference Alignment, and Record Consistency Ledger", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0f2b48'), spaceBefore=8, spaceAfter=14))

    # 2. Key Metadata Table
    reason_codes_list = json.loads(inspection.reason_codes_json or "[]")
    meta_data = [
        [
            Paragraph("<b>Inspection Code:</b>", body_style),
            Paragraph(inspection.inspection_code, body_style),
            Paragraph("<b>Generated At:</b>", body_style),
            Paragraph(datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"), body_style)
        ],
        [
            Paragraph("<b>Model Provider:</b>", body_style),
            Paragraph(f"{inspection.model_provider} ({'DEMO' if inspection.is_demo else 'LIVE'})", body_style),
            Paragraph("<b>Processing Duration:</b>", body_style),
            Paragraph(f"{inspection.processing_time_ms or 0.0} ms", body_style)
        ],
        [
            Paragraph("<b>Product Link:</b>", body_style),
            Paragraph(inspection.product.name if inspection.product else "Unassigned / General Packaging", body_style),
            Paragraph("<b>Batch Number:</b>", body_style),
            Paragraph(inspection.batch.batch_number if inspection.batch else "Not Specified", body_style)
        ],
        [
            Paragraph("<b>Overall Risk Level:</b>", body_style),
            Paragraph(f"{inspection.risk_level.upper()} ({int(inspection.risk_score or 0)}/100)", badge_risk_style),
            Paragraph("<b>Inspection Status:</b>", body_style),
            Paragraph(inspection.status.replace('_', ' ').title(), body_style)
        ]
    ]

    t_meta = Table(meta_data, colWidths=[1.5*inch, 2.2*inch, 1.4*inch, 2.2*inch])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f4f7fa')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#d0d8e2')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 12))

    # 3. AI Screening & Explainability Section
    story.append(Paragraph("1. AI Visual Screening & Saliency Analysis", heading2_style))
    pred = inspection.prediction
    if pred:
        pred_data = [
            [Paragraph("<b>Predicted Class:</b>", body_style), Paragraph(pred.predicted_class or "N/A", body_style)],
            [Paragraph("<b>Model Confidence:</b>", body_style), Paragraph(f"{round((pred.confidence or 0)*100, 1)}%", body_style)],
            [Paragraph("<b>Model Notes:</b>", body_style), Paragraph(pred.explanation_note or "None", body_style)]
        ]
        t_pred = Table(pred_data, colWidths=[2.0*inch, 5.3*inch])
        t_pred.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#ffffff')),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(t_pred)
    else:
        story.append(Paragraph("No model prediction record associated with this inspection.", body_style))
    story.append(Spacer(1, 10))

    # 4. Genuine Reference Comparison
    story.append(Paragraph("2. Genuine Reference Packaging Comparison", heading2_style))
    if inspection.comparison_performed:
        comp_text = (
            f"Comparison completed against reference image ID #{inspection.reference_image_id or 'N/A'}. "
            f"Structural similarity index: <b>{int((inspection.comparison_score or 0)*100)}%</b>. "
            f"{inspection.comparison_notes or ''}"
        )
    else:
        comp_text = "No reference image was selected or comparison was skipped during this inspection."
    story.append(Paragraph(comp_text, body_style))
    story.append(Spacer(1, 10))

    # 5. OCR & Label Inspection
    story.append(Paragraph("3. OCR Label Inspection & Date Checks", heading2_style))
    ocr = inspection.ocr_result
    if ocr:
        ocr_data = [
            [Paragraph("<b>Extracted Product:</b>", body_style), Paragraph(ocr.detected_product_name or "Not found", body_style)],
            [Paragraph("<b>Extracted Manufacturer:</b>", body_style), Paragraph(ocr.detected_manufacturer or "Not found", body_style)],
            [Paragraph("<b>Extracted Batch / Lot:</b>", body_style), Paragraph(ocr.detected_batch_number or "Not found", body_style)],
            [Paragraph("<b>Extracted Expiry:</b>", body_style), Paragraph(f"{ocr.detected_expiry_date or 'N/A'} (Status: {ocr.expiry_status})", body_style)],
            [Paragraph("<b>Label Flags:</b>", body_style), Paragraph(", ".join(json.loads(ocr.label_flags_json or "[]")) or "None", body_style)]
        ]
        t_ocr = Table(ocr_data, colWidths=[2.0*inch, 5.3*inch])
        t_ocr.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#ffffff')),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(t_ocr)
    else:
        story.append(Paragraph("OCR extraction was not performed or failed.", body_style))
    story.append(Spacer(1, 10))

    # 6. Record Verification & Recall Status
    story.append(Paragraph("4. Database Record & Active Recall Verification", heading2_style))
    v = inspection.verification_result
    if v:
        story.append(Paragraph(v.summary_text, body_style))
    else:
        story.append(Paragraph("Database cross-referencing not recorded.", body_style))
    story.append(Spacer(1, 10))

    # 7. Reason Codes & Risk Assessment Summary
    story.append(Paragraph("5. Transparent Risk Synthesis", heading2_style))
    story.append(Paragraph(f"<b>Summary:</b> {inspection.risk_summary or 'No risk summary recorded.'}", body_style))
    story.append(Paragraph(f"<b>Triggered Reason Codes:</b> {', '.join(reason_codes_list) if reason_codes_list else 'None (Clean Baseline)'}", body_style))
    story.append(Spacer(1, 14))

    # 8. Mandatory Legal & Ethical Disclaimer
    story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor('#8899aa'), spaceBefore=8, spaceAfter=8))
    disclaimer_text = (
        "<b>STATUTORY NOTICE & LIMITATION OF LIABILITY:</b> "
        "MediShield AI is a software-based risk screening, optical character inspection, and investigative triage tool. "
        "This report DOES NOT constitute a certified pharmaceutical laboratory authentication, chemical assay, or official "
        "guarantee of drug safety, efficacy, or genuine origin. Positive screening flags warrant immediate escalation to "
        "authorized regulatory or brand protection personnel. Never rely on this report for clinical administration decisions."
    )
    story.append(Paragraph(disclaimer_text, disclaimer_style))

    doc.build(story)
    return str(output_path)


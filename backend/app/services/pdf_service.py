"""
Servizio generazione PDF per fatture.
Uses ReportLab per generare PDF professionali in formato A4.
"""
from io import BytesIO
from typing import Optional
from datetime import date
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, black, white, grey
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.platypus.flowables import HRFlowable

# Colori del brand FatturaMVP
PRIMARY_BLUE = HexColor("#1e40af")
LIGHT_BLUE = HexColor("#dbeafe")
ACCENT_BLUE = HexColor("#3b82f6")
TEXT_DARK = HexColor("#1f2937")
TEXT_GREY = HexColor("#6b7280")
BORDER_GREY = HexColor("#e5e7eb")
BG_LIGHT = HexColor("#f9fafb")


def generate_invoice_pdf(invoice_data: dict) -> bytes:
    """
    Genera un PDF professionale per la fattura.
    
    Args:
        invoice_data: dizionario con i dati della fattura
        
    Returns:
        bytes: contenuto PDF
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm,
        title=f"Fattura {invoice_data.get('invoice_number', '')}"
    )
    
    styles = _build_styles()
    elements = []
    
    # === HEADER ===
    elements.append(_build_header(invoice_data, styles))
    elements.append(Spacer(1, 8*mm))
    
    # === INFO FATTURA + CEDENTE/PRESTATORE ===
    elements.append(_build_info_section(invoice_data, styles))
    elements.append(Spacer(1, 8*mm))
    
    # === CESSIONARIO/COMMITTENTE ===
    elements.append(_build_cliente_section(invoice_data, styles))
    elements.append(Spacer(1, 8*mm))
    
    # === TABELLA BENI/SERVIZI ===
    elements.append(_build_items_table(invoice_data, styles))
    elements.append(Spacer(1, 6*mm))
    
    # === TOTALI ===
    elements.append(_build_totals_section(invoice_data, styles))
    elements.append(Spacer(1, 8*mm))
    
    # === DATI PAGAMENTO ===
    elements.append(_build_payment_section(invoice_data, styles))
    elements.append(Spacer(1, 6*mm))
    
    # === FOOTER ===
    elements.append(_build_footer(styles))
    
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def _build_styles() -> dict:
    """Costruisce stili personalizzati per il PDF."""
    base = getSampleStyleSheet()
    
    styles = {
        "title": ParagraphStyle(
            "InvoiceTitle",
            fontSize=24,
            fontName="Helvetica-Bold",
            textColor=PRIMARY_BLUE,
            alignment=TA_LEFT,
            spaceAfter=4*mm,
        ),
        "invoice_number": ParagraphStyle(
            "InvoiceNumber",
            fontSize=12,
            fontName="Helvetica-Bold",
            textColor=TEXT_DARK,
            alignment=TA_LEFT,
            spaceAfter=2*mm,
        ),
        "label": ParagraphStyle(
            "Label",
            fontSize=8,
            fontName="Helvetica-Bold",
            textColor=TEXT_GREY,
            alignment=TA_LEFT,
            spaceAfter=1*mm,
        ),
        "value": ParagraphStyle(
            "Value",
            fontSize=10,
            fontName="Helvetica",
            textColor=TEXT_DARK,
            alignment=TA_LEFT,
            spaceAfter=1*mm,
        ),
        "value_bold": ParagraphStyle(
            "ValueBold",
            fontSize=10,
            fontName="Helvetica-Bold",
            textColor=TEXT_DARK,
            alignment=TA_LEFT,
            spaceAfter=1*mm,
        ),
        "section_title": ParagraphStyle(
            "SectionTitle",
            fontSize=10,
            fontName="Helvetica-Bold",
            textColor=white,
            alignment=TA_LEFT,
            spaceAfter=2*mm,
        ),
        "table_header": ParagraphStyle(
            "TableHeader",
            fontSize=8,
            fontName="Helvetica-Bold",
            textColor=white,
            alignment=TA_CENTER,
        ),
        "table_cell": ParagraphStyle(
            "TableCell",
            fontSize=8,
            fontName="Helvetica",
            textColor=TEXT_DARK,
            alignment=TA_LEFT,
        ),
        "table_cell_right": ParagraphStyle(
            "TableCellRight",
            fontSize=8,
            fontName="Helvetica",
            textColor=TEXT_DARK,
            alignment=TA_RIGHT,
        ),
        "total_label": ParagraphStyle(
            "TotalLabel",
            fontSize=10,
            fontName="Helvetica-Bold",
            textColor=TEXT_DARK,
            alignment=TA_RIGHT,
        ),
        "total_value": ParagraphStyle(
            "TotalValue",
            fontSize=12,
            fontName="Helvetica-Bold",
            textColor=PRIMARY_BLUE,
            alignment=TA_RIGHT,
        ),
        "footer": ParagraphStyle(
            "Footer",
            fontSize=7,
            fontName="Helvetica",
            textColor=TEXT_GREY,
            alignment=TA_CENTER,
        ),
        "small": ParagraphStyle(
            "Small",
            fontSize=7,
            fontName="Helvetica",
            textColor=TEXT_GREY,
            alignment=TA_LEFT,
        ),
        "heading3": ParagraphStyle(
            "Heading3",
            fontSize=9,
            fontName="Helvetica-Bold",
            textColor=TEXT_DARK,
            alignment=TA_LEFT,
            spaceAfter=2*mm,
        ),
    }
    return styles


def _build_header(invoice_data: dict, styles: dict) -> Table:
    """Costruisce l'header della fattura con logo e numero."""
    # Logo placeholder + titolo
    logo_text = Paragraph(
        "<b>FATTURA</b>",
        ParagraphStyle(
            "LogoText",
            fontSize=28,
            fontName="Helvetica-Bold",
            textColor=PRIMARY_BLUE,
            alignment=TA_LEFT,
        )
    )
    
    invoice_num = invoice_data.get("invoice_number", "—")
    invoice_date = _format_date(invoice_data.get("invoice_date"))
    due_date = _format_date(invoice_data.get("due_date"))
    
    right_content = [
        Paragraph(f"<b>Fattura N.</b> {invoice_num}", styles["invoice_number"]),
        Paragraph(f"<b>Data:</b> {invoice_date}", styles["value"]),
        Paragraph(f"<b>Scadenza:</b> {due_date}", styles["value"]),
    ]
    
    header_data = [
        [logo_text, right_content]
    ]
    
    header_table = Table(header_data, colWidths=[100*mm, 70*mm])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BLUE),
        ("LEFTPADDING", (0, 0), (0, 0), 10*mm),
        ("RIGHTPADDING", (0, 0), (0, 0), 5*mm),
        ("LEFTPADDING", (1, 0), (1, 0), 10*mm),
        ("RIGHTPADDING", (1, 0), (1, 0), 10*mm),
        ("TOPPADDING", (0, 0), (-1, -1), 8*mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8*mm),
        ("ROUNDEDCORNERS", [5*mm], ),
    ]))
    
    return header_table


def _build_info_section(invoice_data: dict, styles: dict) -> Table:
    """Sezione info fattura + dati cedente/prestatore."""
    # Info fattura
    payment_days = invoice_data.get("payment_days", 30)
    payment_method = invoice_data.get("payment_method", "Bonifico bancario")
    
    status = invoice_data.get("status", "pending")
    status_map = {"paid": "PAGATA", "pending": "PENDING", "overdue": "SCADUTA", "cancelled": "CANCELLATA"}
    
    info_rows = [
        ["Stato", status_map.get(status, status.upper())],
        ["Pagamento", payment_method],
        ["Giorni pagamento", f"{payment_days} giorni"],
    ]
    
    info_table = Table(info_rows, colWidths=[35*mm, 50*mm])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TEXTCOLOR", (0, 0), (-1, -1), TEXT_DARK),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2*mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2*mm),
    ]))
    
    # Cedente/Prestatore
    supplier = invoice_data.get("supplier_name", "")
    supplier_vat = invoice_data.get("supplier_vat", "")
    supplier_address = invoice_data.get("supplier_address", "")
    supplier_phone = invoice_data.get("supplier_phone", "")
    supplier_email = invoice_data.get("supplier_email", "")
    supplier_pec = invoice_data.get("supplier_pec", "")
    supplier_sdi = invoice_data.get("supplier_sdi", "")
    supplier_cf = invoice_data.get("supplier_cf", "")
    
    # Header sezione Cedente
    cedente_header = Paragraph("CEDENTE / PRESTATORE", styles["section_title"])
    cedente_header_table = Table([[cedente_header]], colWidths=[85*mm])
    cedente_header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PRIMARY_BLUE),
        ("LEFTPADDING", (0, 0), (-1, -1), 5*mm),
        ("TOPPADDING", (0, 0), (-1, -1), 3*mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3*mm),
    ]))
    
    cedente_rows = []
    if supplier:
        cedente_rows.append([Paragraph(f"<b>{supplier}</b>", styles["value_bold"])])
    if supplier_vat:
        cedente_rows.append([Paragraph(f"P.IVA: {supplier_vat}", styles["small"])])
    if supplier_cf:
        cedente_rows.append([Paragraph(f"CF: {supplier_cf}", styles["small"])])
    if supplier_address:
        cedente_rows.append([Paragraph(supplier_address, styles["small"])])
    if supplier_phone:
        cedente_rows.append([Paragraph(f"Tel: {supplier_phone}", styles["small"])])
    if supplier_email:
        cedente_rows.append([Paragraph(f"Email: {supplier_email}", styles["small"])])
    if supplier_pec:
        cedente_rows.append([Paragraph(f"PEC: {supplier_pec}", styles["small"])])
    if supplier_sdi:
        cedente_rows.append([Paragraph(f"SDI: {supplier_sdi}", styles["small"])])
    
    cedente_table = Table(cedente_rows, colWidths=[85*mm])
    cedente_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BG_LIGHT),
        ("LEFTPADDING", (0, 0), (-1, -1), 5*mm),
        ("TOPPADDING", (0, 0), (-1, -1), 1*mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1*mm),
        ("LINEBELOW", (0, -1), (-1, -1), 0.5, BORDER_GREY),
    ]))
    
    main_table = Table(
        [[cedente_header_table], [cedente_table]],
        colWidths=[85*mm]
    )
    main_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    
    return KeepTogether([info_table, Spacer(1, 4*mm), main_table])


def _build_cliente_section(invoice_data: dict, styles: dict) -> Table:
    """Sezione dati cliente/cessionario."""
    customer = invoice_data.get("customer_name", "")
    customer_vat = invoice_data.get("customer_vat", "")
    customer_address = invoice_data.get("customer_address", "")
    customer_phone = invoice_data.get("customer_phone", "")
    customer_email = invoice_data.get("customer_email", "")
    customer_pec = invoice_data.get("customer_pec", "")
    customer_sdi = invoice_data.get("customer_sdi", "")
    customer_cf = invoice_data.get("customer_cf", "")
    
    header = Paragraph("CESSIONARIO / COMMITTENTE", styles["section_title"])
    header_table = Table([[header]], colWidths=[85*mm])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), ACCENT_BLUE),
        ("LEFTPADDING", (0, 0), (-1, -1), 5*mm),
        ("TOPPADDING", (0, 0), (-1, -1), 3*mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3*mm),
    ]))
    
    rows = []
    if customer:
        rows.append([Paragraph(f"<b>{customer}</b>", styles["value_bold"])])
    if customer_vat:
        rows.append([Paragraph(f"P.IVA: {customer_vat}", styles["small"])])
    if customer_cf:
        rows.append([Paragraph(f"CF: {customer_cf}", styles["small"])])
    if customer_address:
        rows.append([Paragraph(customer_address, styles["small"])])
    if customer_phone:
        rows.append([Paragraph(f"Tel: {customer_phone}", styles["small"])])
    if customer_email:
        rows.append([Paragraph(f"Email: {customer_email}", styles["small"])])
    if customer_pec:
        rows.append([Paragraph(f"PEC: {customer_pec}", styles["small"])])
    if customer_sdi:
        rows.append([Paragraph(f"SDI: {customer_sdi}", styles["small"])])
    
    content_table = Table(rows, colWidths=[85*mm])
    content_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BG_LIGHT),
        ("LEFTPADDING", (0, 0), (-1, -1), 5*mm),
        ("TOPPADDING", (0, 0), (-1, -1), 1*mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1*mm),
        ("LINEBELOW", (0, -1), (-1, -1), 0.5, BORDER_GREY),
    ]))
    
    return KeepTogether([header_table, content_table])


def _build_items_table(invoice_data: dict, styles: dict) -> Table:
    """Tabella beni/servizi della fattura."""
    header = Paragraph("BENI / SERVIZI", styles["section_title"])
    header_table = Table([[header]], colWidths=[170*mm])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PRIMARY_BLUE),
        ("LEFTPADDING", (0, 0), (-1, -1), 5*mm),
        ("TOPPADDING", (0, 0), (-1, -1), 3*mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3*mm),
    ]))
    
    # Table header
    table_header = [
        Paragraph("Descrizione", styles["table_header"]),
        Paragraph("Quantità", styles["table_header"]),
        Paragraph("Prezzo unitario", styles["table_header"]),
        Paragraph("Aliquota IVA", styles["table_header"]),
        Paragraph("Importo", styles["table_header"]),
    ]
    
    # Data rows - use description or default
    description = invoice_data.get("description", "Fornitura servizi / beni")
    amount = invoice_data.get("amount", 0)
    vat_rate = 22  # default IVA
    vat_amount = invoice_data.get("vat_amount", 0)
    total = invoice_data.get("total_amount", 0)
    
    # Split description into lines if long
    desc_lines = description.split("\n") if description else ["—"]
    
    rows = [table_header]
    for i, line in enumerate(desc_lines):
        qty = "1" if i == 0 else ""
        unit_price = f"€ {_format_currency(amount)}" if i == 0 else ""
        iva = f"{vat_rate}%" if i == 0 else ""
        row_importo = f"€ {_format_currency(amount)}" if i == 0 else ""
        
        rows.append([
            Paragraph(line, styles["table_cell"]),
            Paragraph(qty, styles["table_cell_right"]),
            Paragraph(unit_price, styles["table_cell_right"]),
            Paragraph(iva, styles["table_cell_right"]),
            Paragraph(row_importo, styles["table_cell_right"]),
        ])
    
    col_widths = [80*mm, 20*mm, 28*mm, 22*mm, 25*mm]
    items_table = Table(rows, colWidths=col_widths)
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3*mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3*mm),
        ("LEFTPADDING", (0, 0), (-1, -1), 3*mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3*mm),
        ("LINEBELOW", (0, 0), (-1, 0), 1, PRIMARY_BLUE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, BG_LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.3, BORDER_GREY),
    ]))
    
    return KeepTogether([header_table, items_table])


def _build_totals_section(invoice_data: dict, styles: dict) -> Table:
    """Sezione totali fattura."""
    amount = invoice_data.get("amount", 0)
    vat_amount = invoice_data.get("vat_amount", 0)
    total = invoice_data.get("total_amount", 0)
    
    rows = [
        [
            Paragraph("Imponibile:", styles["total_label"]),
            Paragraph(f"€ {_format_currency(amount)}", styles["total_label"]),
        ],
        [
            Paragraph("IVA (22%):", styles["total_label"]),
            Paragraph(f"€ {_format_currency(vat_amount)}", styles["total_label"]),
        ],
        [
            Paragraph("Totale fattura:", styles["total_label"]),
            Paragraph(f"€ {_format_currency(total)}", styles["total_value"]),
        ],
    ]
    
    totals_table = Table(rows, colWidths=[120*mm, 50*mm])
    totals_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2*mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2*mm),
        ("LINEABOVE", (0, 1), (-1, 1), 0.5, BORDER_GREY),
        ("LINEABOVE", (0, 2), (-1, 2), 1, PRIMARY_BLUE),
        ("BACKGROUND", (0, 2), (-1, 2), LIGHT_BLUE),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
    ]))
    
    return totals_table


def _build_payment_section(invoice_data: dict, styles: dict) -> Table:
    """Sezione dati pagamento con IBAN."""
    iban = invoice_data.get("supplier_iban", "")
    payment_method = invoice_data.get("payment_method", "Bonifico bancario")
    payment_days = invoice_data.get("payment_days", 30)
    
    header = Paragraph("DATI PAGAMENTO", styles["section_title"])
    header_table = Table([[header]], colWidths=[170*mm])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PRIMARY_BLUE),
        ("LEFTPADDING", (0, 0), (-1, -1), 5*mm),
        ("TOPPADDING", (0, 0), (-1, -1), 3*mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3*mm),
    ]))
    
    payment_rows = [
        ["Metodo di pagamento", payment_method],
        ["Giorni per il pagamento", f"{payment_days} giorni"],
    ]
    if iban:
        payment_rows.append(["IBAN", iban])
    
    content_rows = []
    for label, value in payment_rows:
        content_rows.append([
            Paragraph(label, styles["small"]),
            Paragraph(f"<b>{value}</b>", styles["value"]),
        ])
    
    content_table = Table(content_rows, colWidths=[50*mm, 120*mm])
    content_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BG_LIGHT),
        ("LEFTPADDING", (0, 0), (-1, -1), 5*mm),
        ("TOPPADDING", (0, 0), (-1, -1), 2*mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2*mm),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, -1), (-1, -1), 0.5, BORDER_GREY),
    ]))
    
    return KeepTogether([header_table, content_table])


def _build_footer(styles: dict) -> Table:
    """Footer della fattura."""
    footer_text = (
        "Fattura emessa da FatturaMVP — Il presente documento è stato generato elettronicamente. "
        "Ai sensi dell'art. 21 del D.P.R. 633/1972, la fattura elettronica è considerata originale "
        "se garantisce l'autenticità e l'integrità del contenuto."
    )
    
    footer = Paragraph(footer_text, styles["footer"])
    hr = HRFlowable(width="100%", thickness=0.5, color=BORDER_GREY, spaceAfter=3*mm)
    
    footer_table = Table([[footer]], colWidths=[170*mm])
    footer_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 3*mm),
    ]))
    
    return KeepTogether([hr, footer_table])


def _format_currency(value: float) -> str:
    """Formatta un valore in valuta italiana."""
    if value is None:
        return "0,00"
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _format_date(date_value) -> str:
    """Formatta una data in formato italiano."""
    if date_value is None:
        return "—"
    if isinstance(date_value, str):
        # Try to parse
        try:
            from datetime import datetime
            d = datetime.fromisoformat(date_value.replace("Z", "+00:00"))
            return d.strftime("%d/%m/%Y")
        except Exception:
            return date_value
    if isinstance(date_value, date):
        return date_value.strftime("%d/%m/%Y")
    return str(date_value)

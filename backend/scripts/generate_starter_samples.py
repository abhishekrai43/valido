"""Generate original starter PDF samples for Valido onboarding."""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "frontend" / "sample-docs"


def _build_doc(path: Path, story):
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
    )
    doc.build(story)


def _styles():
    styles = getSampleStyleSheet()
    styles["Title"].fontName = "Helvetica-Bold"
    styles["Heading2"].fontName = "Helvetica-Bold"
    styles["BodyText"].fontName = "Helvetica"
    return styles


def _kv_table(rows):
    table = Table(rows, colWidths=[55 * mm, 95 * mm])
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#d1d5db")),
            ]
        )
    )
    return table


def create_invoice_sample():
    styles = _styles()
    story = [
        Paragraph("NORTHWIND OFFICE SUPPLIES", styles["Title"]),
        Spacer(1, 6),
        Paragraph("INVOICE", styles["Heading2"]),
        Spacer(1, 10),
        _kv_table(
            [
                ["Invoice Number", "INV-2026-041"],
                ["Invoice Date", "April 20, 2026"],
                ["Due Date", "May 04, 2026"],
                ["Customer Name", "Bluewave Consulting"],
                ["Payment Terms", "Net 14"],
                ["Status", "Pending Payment"],
            ]
        ),
        Spacer(1, 14),
        Paragraph("Line Items", styles["Heading2"]),
        Spacer(1, 6),
        Table(
            [
                ["Description", "Qty", "Unit Price", "Amount"],
                ["Ergonomic Keyboard", "4", "$120.00", "$480.00"],
                ["Docking Station", "3", "$180.00", "$540.00"],
                ["Cable Kit", "8", "$20.00", "$160.00"],
            ],
            colWidths=[85 * mm, 20 * mm, 35 * mm, 35 * mm],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eff6ff")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                ]
            ),
        ),
        Spacer(1, 14),
        _kv_table(
            [
                ["Subtotal", "$1,180.00"],
                ["Tax", "$94.40"],
                ["Shipping", "$25.00"],
                ["Total Amount", "$1,299.40"],
                ["Balance Due", "$1,299.40"],
            ]
        ),
        Spacer(1, 10),
        Paragraph(
            "Notes: Please remit payment within 14 days. Thank you for your business.",
            styles["BodyText"],
        ),
    ]
    _build_doc(OUTPUT_DIR / "starter-invoice-demo.pdf", story)


def create_purchase_order_sample():
    styles = _styles()
    story = [
        Paragraph("VERTEX FACILITIES GROUP", styles["Title"]),
        Spacer(1, 6),
        Paragraph("PURCHASE ORDER", styles["Heading2"]),
        Spacer(1, 10),
        _kv_table(
            [
                ["PO Number", "PO-2026-118"],
                ["PO Date", "April 22, 2026"],
                ["Supplier", "Summit Industrial Parts"],
                ["Requested By", "Maya Chen"],
                ["Department", "Facilities"],
                ["Delivery Date", "May 01, 2026"],
                ["Approval Status", "Approved For Fulfillment"],
            ]
        ),
        Spacer(1, 14),
        Paragraph("Order Items", styles["Heading2"]),
        Spacer(1, 6),
        Table(
            [
                ["Part", "Qty", "Unit Cost", "Amount"],
                ["Air Filter Cartridge", "10", "$28.00", "$280.00"],
                ["Safety Sign Pack", "12", "$15.00", "$180.00"],
                ["Industrial Fastener Kit", "4", "$100.00", "$400.00"],
            ],
            colWidths=[90 * mm, 20 * mm, 32 * mm, 32 * mm],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ecfccb")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                ]
            ),
        ),
        Spacer(1, 14),
        _kv_table(
            [
                ["Subtotal", "$860.00"],
                ["Tax", "$68.80"],
                ["Total Amount", "$928.80"],
            ]
        ),
        Spacer(1, 10),
        Paragraph(
            "Instructions: Deliver to Dock C between 9:00 AM and 1:00 PM. Include PO Number on all packing slips.",
            styles["BodyText"],
        ),
    ]
    _build_doc(OUTPUT_DIR / "starter-purchase-order-demo.pdf", story)


def create_tax_form_sample():
    styles = _styles()
    story = [
        Paragraph("CEDAR VALLEY ANALYTICS", styles["Title"]),
        Spacer(1, 6),
        Paragraph("VENDOR TAX PROFILE", styles["Heading2"]),
        Spacer(1, 10),
        Paragraph(
            "Sample onboarding document inspired by common tax-registration fields used in vendor compliance workflows.",
            styles["BodyText"],
        ),
        Spacer(1, 10),
        _kv_table(
            [
                ["Business Name", "Cedar Valley Analytics LLC"],
                ["Federal Tax Classification", "LLC"],
                ["Tax ID (EIN)", "82-3456789"],
                ["Contact Email", "vendors@cedarvalley.example"],
                ["Business Address", "448 Market Street, Denver, CO 80202"],
                ["Certification Status", "Signed electronically"],
                ["Form Purpose", "Vendor setup and payment onboarding"],
            ]
        ),
        Spacer(1, 14),
        Paragraph("Certification", styles["Heading2"]),
        Spacer(1, 6),
        Paragraph(
            "I certify that the Tax ID shown on this form is correct and that the organization listed above is authorized to receive vendor payments.",
            styles["BodyText"],
        ),
        Spacer(1, 10),
        Paragraph("Authorized Signer: Jordan Blake", styles["BodyText"]),
        Paragraph("Date Signed: April 18, 2026", styles["BodyText"]),
    ]
    _build_doc(OUTPUT_DIR / "starter-vendor-tax-demo.pdf", story)


if __name__ == "__main__":
    create_invoice_sample()
    create_purchase_order_sample()
    create_tax_form_sample()
    print(f"Generated starter sample PDFs in {OUTPUT_DIR}")

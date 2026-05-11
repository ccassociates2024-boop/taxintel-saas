"""GST-compliant PDF invoice generation for SaaS subscription billing.

SAC code 998211 — "Legal and tax advisory services"
GST rate: 18 % (9 % CGST + 9 % SGST intra-state | 18 % IGST inter-state).

The supplier state is fixed as the platform's place_of_supply_state_code (default 07 — Delhi).
If the tenant's place_of_supply_state_code differs from the platform's, IGST applies.
"""
from __future__ import annotations

import io
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Platform details — update for production
_PLATFORM_NAME = "TaxIntel SaaS"
_PLATFORM_GSTIN = "07AAAAA0000A1Z5"   # placeholder — set real GSTIN
_PLATFORM_ADDRESS = "New Delhi, India"
_PLATFORM_STATE_CODE = "07"           # Delhi
_SAC_CODE = "998211"
_GST_RATE = Decimal("0.18")
_CURRENCY = "₹"


@dataclass
class LineItem:
    description: str
    quantity: int
    unit_price: Decimal
    sac_code: str = _SAC_CODE

    @property
    def amount(self) -> Decimal:
        return (self.unit_price * self.quantity).quantize(Decimal("0.01"), ROUND_HALF_UP)


@dataclass
class GSTBreakdown:
    subtotal: Decimal
    cgst: Decimal
    sgst: Decimal
    igst: Decimal
    total: Decimal
    is_intra_state: bool


def compute_gst(subtotal: Decimal, tenant_state_code: str) -> GSTBreakdown:
    is_intra = tenant_state_code == _PLATFORM_STATE_CODE
    half = (subtotal * Decimal("0.09")).quantize(Decimal("0.01"), ROUND_HALF_UP)
    if is_intra:
        return GSTBreakdown(
            subtotal=subtotal, cgst=half, sgst=half, igst=Decimal("0"),
            total=(subtotal + half + half), is_intra_state=True,
        )
    igst = (subtotal * _GST_RATE).quantize(Decimal("0.01"), ROUND_HALF_UP)
    return GSTBreakdown(
        subtotal=subtotal, cgst=Decimal("0"), sgst=Decimal("0"), igst=igst,
        total=(subtotal + igst), is_intra_state=False,
    )


def generate_invoice_pdf(
    invoice_number: str,
    invoice_date: date,
    due_date: date,
    tenant_legal_name: str,
    tenant_gstin: str | None,
    tenant_billing_email: str,
    tenant_state_code: str,
    line_items: list[LineItem],
    period_start: date | None = None,
    period_end: date | None = None,
) -> bytes:
    """Return a PDF as raw bytes — ready to upload to S3."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=15 * mm, bottomMargin=15 * mm,
    )

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=18, spaceAfter=2)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=11, spaceAfter=4)
    normal = styles["Normal"]
    small = ParagraphStyle("small", parent=normal, fontSize=8, textColor=colors.grey)

    subtotal = sum((item.amount for item in line_items), Decimal("0"))
    gst = compute_gst(subtotal, tenant_state_code)

    story = []

    # ── Header ─────────────────────────────────────────────────────────────
    header_data = [
        [
            Paragraph(f"<b>{_PLATFORM_NAME}</b>", h1),
            Paragraph(
                f"<b>TAX INVOICE</b><br/>"
                f"No: <b>{invoice_number}</b><br/>"
                f"Date: {invoice_date.strftime('%d %b %Y')}<br/>"
                f"Due: {due_date.strftime('%d %b %Y')}",
                styles["Normal"],
            ),
        ]
    ]
    header_table = Table(header_data, colWidths=[100 * mm, 75 * mm])
    header_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#4F46E5")))
    story.append(Spacer(1, 4 * mm))

    # ── Supplier / Buyer ───────────────────────────────────────────────────
    period_str = ""
    if period_start and period_end:
        period_str = f"<br/>Period: {period_start.strftime('%d %b %Y')} — {period_end.strftime('%d %b %Y')}"
    party_data = [
        [
            Paragraph(
                f"<b>From (Supplier)</b><br/>{_PLATFORM_NAME}<br/>"
                f"GSTIN: {_PLATFORM_GSTIN}<br/>{_PLATFORM_ADDRESS}<br/>"
                f"State Code: {_PLATFORM_STATE_CODE}",
                normal,
            ),
            Paragraph(
                f"<b>To (Recipient)</b><br/>{tenant_legal_name}<br/>"
                f"GSTIN: {tenant_gstin or 'N/A'}<br/>{tenant_billing_email}<br/>"
                f"State Code: {tenant_state_code}{period_str}",
                normal,
            ),
        ]
    ]
    party_table = Table(party_data, colWidths=[87 * mm, 88 * mm])
    party_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F9FAFB")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(party_table)
    story.append(Spacer(1, 6 * mm))

    # ── Line items ─────────────────────────────────────────────────────────
    story.append(Paragraph("<b>Services Rendered</b>", h2))
    col_headers = ["#", "Description", "SAC", "Qty", f"Rate ({_CURRENCY})", f"Amount ({_CURRENCY})"]
    rows = [col_headers]
    for i, item in enumerate(line_items, 1):
        rows.append([
            str(i),
            item.description,
            item.sac_code,
            str(item.quantity),
            f"{item.unit_price:,.2f}",
            f"{item.amount:,.2f}",
        ])

    items_table = Table(rows, colWidths=[8 * mm, 80 * mm, 18 * mm, 12 * mm, 25 * mm, 25 * mm])
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4F46E5")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F4F6")]),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D1D5DB")),
        ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 4 * mm))

    # ── GST Summary ────────────────────────────────────────────────────────
    tax_rows: list[list] = [
        ["Subtotal", f"{_CURRENCY} {gst.subtotal:,.2f}"],
    ]
    if gst.is_intra_state:
        tax_rows += [
            [f"CGST @ 9%", f"{_CURRENCY} {gst.cgst:,.2f}"],
            [f"SGST @ 9%", f"{_CURRENCY} {gst.sgst:,.2f}"],
        ]
    else:
        tax_rows.append([f"IGST @ 18%", f"{_CURRENCY} {gst.igst:,.2f}"])
    tax_rows.append(["", ""])
    tax_rows.append([f"<b>Total (INR)</b>", f"<b>{_CURRENCY} {gst.total:,.2f}</b>"])

    formatted_tax_rows = [[Paragraph(c, normal) for c in row] for row in tax_rows]
    tax_table = Table(formatted_tax_rows, colWidths=[130 * mm, 45 * mm], hAlign="RIGHT")
    tax_table.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("LINEABOVE", (0, -1), (-1, -1), 1, colors.HexColor("#4F46E5")),
        ("PADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(tax_table)
    story.append(Spacer(1, 8 * mm))

    # ── Footer ─────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#D1D5DB")))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(
        "This is a computer-generated invoice and does not require a physical signature. "
        "Payment terms: 15 days from invoice date. "
        f"Generated by {_PLATFORM_NAME} on {datetime.utcnow().strftime('%d %b %Y %H:%M UTC')}.",
        small,
    ))

    doc.build(story)
    return buf.getvalue()

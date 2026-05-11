from io import BytesIO
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from app.api.deps import get_current_tenant
from app.db.models import Tenant
from app.db.session import get_db
from app.repositories import ClientRepository

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/{client_id}/pdf")
def pdf_report(
    client_id: UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    client = ClientRepository(db).get_for_tenant(tenant.id, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    buffer = BytesIO()
    doc = canvas.Canvas(buffer, pagesize=A4)
    doc.setTitle("Tax Intelligence Report")
    doc.setFont("Helvetica-Bold", 16)
    doc.drawString(72, 780, "Tax Intelligence Report")
    doc.setFont("Helvetica", 11)
    doc.drawString(72, 748, f"Client: {client.full_name}")
    doc.drawString(72, 730, f"PAN: {client.pan}")
    doc.drawString(72, 700, "This MVP report summarizes uploaded tax data, computation, and AI recommendations.")
    doc.showPage()
    doc.save()
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=tax-report.pdf"},
    )


@router.get("/{client_id}/excel")
def excel_report(
    client_id: UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    client = ClientRepository(db).get_for_tenant(tenant.id, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Tax Summary"
    sheet.append(["Field", "Value"])
    sheet.append(["Client", client.full_name])
    sheet.append(["PAN", client.pan])
    sheet.append(["Residential Status", client.residential_status])
    sheet.append(["Summary", "Upload AIS, 26AS, computation, and recommendations for full export."])
    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=tax-summary.xlsx"},
    )

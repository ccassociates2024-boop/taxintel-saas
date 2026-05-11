"""Phase 1B — Razorpay subscription management + GST invoice endpoints."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_tenant
from app.core.config import settings
from app.core.webhooks import verify_razorpay
from app.core.webhooks import SignatureError
from app.db.models import Invoice, Subscription, Tenant
from app.db.session import get_db
from app.services.invoice import LineItem, generate_invoice_pdf
from app.schemas import TenantOut

log = structlog.get_logger(__name__)
router = APIRouter(tags=["billing"])

# ── Subscription plans ────────────────────────────────────────────────────────
PLANS = {
    "FREE":       {"name": "Free",       "amount": 0,    "max_clients": 5},
    "PRO":        {"name": "Pro",        "amount": 99900, "max_clients": 100},   # paise
    "ENTERPRISE": {"name": "Enterprise", "amount": 499900, "max_clients": 9999},
}


def _razorpay_client():
    """Lazily construct Razorpay client; raises 503 if keys missing."""
    if not settings.razorpay_key_id or not settings.razorpay_key_secret:
        raise HTTPException(status_code=503, detail="Razorpay not configured")
    import razorpay  # type: ignore[import]
    return razorpay.Client(
        auth=(settings.razorpay_key_id, settings.razorpay_key_secret)
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/billing/plans")
def list_plans():
    """Return available subscription plans."""
    return [
        {"plan": k, "name": v["name"], "amount_paise": v["amount"], "max_clients": v["max_clients"]}
        for k, v in PLANS.items()
    ]


@router.get("/billing/subscription")
def get_subscription(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """Return the current subscription for this tenant."""
    sub = db.scalar(select(Subscription).where(Subscription.tenant_id == tenant.id))
    if not sub:
        return {"plan": "FREE", "status": "active", "razorpay_subscription_id": None}
    return {
        "plan": sub.plan,
        "status": sub.status,
        "razorpay_subscription_id": sub.razorpay_subscription_id,
        "current_period_end": sub.current_period_end,
    }


@router.post("/billing/subscribe/{plan}")
def create_subscription(
    plan: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """Initiate a Razorpay subscription for the given plan."""
    plan = plan.upper()
    if plan not in PLANS or plan == "FREE":
        raise HTTPException(status_code=400, detail=f"Invalid plan. Choose: PRO, ENTERPRISE")

    plan_id_map = {"PRO": settings.razorpay_plan_pro, "ENTERPRISE": settings.razorpay_plan_enterprise}
    razorpay_plan_id = plan_id_map.get(plan)
    if not razorpay_plan_id:
        raise HTTPException(status_code=503, detail=f"Razorpay plan ID for {plan} not configured")

    client = _razorpay_client()
    sub_data = client.subscription.create({
        "plan_id": razorpay_plan_id,
        "total_count": 12,
        "quantity": 1,
        "customer_notify": 1,
        "notes": {"tenant_id": str(tenant.id), "tenant_name": tenant.trade_name},
    })

    # Upsert subscription record
    existing = db.scalar(select(Subscription).where(Subscription.tenant_id == tenant.id))
    if existing:
        existing.razorpay_subscription_id = sub_data["id"]
        existing.plan = plan
        existing.status = sub_data["status"]
        existing.updated_at = datetime.utcnow()
    else:
        db.add(Subscription(
            tenant_id=tenant.id,
            razorpay_subscription_id=sub_data["id"],
            plan=plan,
            status=sub_data["status"],
        ))
    db.commit()

    log.info("billing.subscription_created", tenant_id=str(tenant.id), plan=plan)
    return {
        "razorpay_subscription_id": sub_data["id"],
        "short_url": sub_data.get("short_url"),
        "plan": plan,
    }


@router.get("/billing/invoices")
def list_invoices(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """Return all invoices for this tenant."""
    invoices = db.scalars(
        select(Invoice).where(Invoice.tenant_id == tenant.id).order_by(Invoice.created_at.desc())
    ).all()
    return [
        {
            "id": str(inv.id),
            "invoice_number": inv.invoice_number,
            "amount_total": float(inv.amount_total),
            "status": inv.status,
            "created_at": inv.created_at.isoformat(),
        }
        for inv in invoices
    ]


@router.get("/billing/invoices/{invoice_id}/pdf")
def download_invoice_pdf(
    invoice_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """Stream the PDF for an invoice."""
    inv = db.scalar(
        select(Invoice).where(Invoice.id == invoice_id, Invoice.tenant_id == tenant.id)
    )
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Re-generate on the fly (or fetch from S3 if stored)
    items = [
        LineItem(
            description=li.get("description", "SaaS subscription"),
            quantity=li.get("quantity", 1),
            unit_price=Decimal(str(li.get("unit_price", inv.amount_subtotal))),
        )
        for li in (inv.line_items or [{"description": "SaaS subscription", "quantity": 1,
                                        "unit_price": str(inv.amount_subtotal)}])
    ]
    pdf_bytes = generate_invoice_pdf(
        invoice_number=inv.invoice_number,
        invoice_date=inv.created_at.date(),
        due_date=(inv.created_at + timedelta(days=15)).date(),
        tenant_legal_name=tenant.legal_name,
        tenant_gstin=tenant.gstin,
        tenant_billing_email=tenant.billing_email,
        tenant_state_code=tenant.place_of_supply_state_code,
        line_items=items,
        period_start=inv.period_start.date() if inv.period_start else None,
        period_end=inv.period_end.date() if inv.period_end else None,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={inv.invoice_number}.pdf"},
    )


# ── Razorpay Webhook ─────────────────────────────────────────────────────────

@router.post("/webhooks/razorpay")
async def razorpay_webhook(request: Request, db: Session = Depends(get_db)):
    body = await request.body()
    sig = request.headers.get("X-Razorpay-Signature", "")
    secret = settings.razorpay_webhook_secret or ""
    try:
        verify_razorpay(body, sig, secret)
    except SignatureError:
        log.warning("razorpay.webhook_bad_signature")
        raise HTTPException(status_code=400, detail="Bad signature")

    import json
    event = json.loads(body)
    event_type = event.get("event", "")
    log.info("razorpay.webhook", event=event_type)

    _handle_razorpay_event(db, event_type, event)
    return {"status": "ok"}


def _handle_razorpay_event(db: Session, event_type: str, event: dict) -> None:
    payload = event.get("payload", {})

    if event_type == "subscription.activated":
        sub_entity = payload.get("subscription", {}).get("entity", {})
        _upsert_subscription(db, sub_entity, "active")

    elif event_type in {"subscription.charged", "payment.captured"}:
        sub_entity = payload.get("subscription", {}).get("entity", {})
        payment = payload.get("payment", {}).get("entity", {})
        _upsert_subscription(db, sub_entity, "active")
        _create_invoice_from_payment(db, sub_entity, payment)

    elif event_type in {"subscription.cancelled", "subscription.expired"}:
        sub_entity = payload.get("subscription", {}).get("entity", {})
        _upsert_subscription(db, sub_entity, "cancelled")


def _upsert_subscription(db: Session, sub_entity: dict, status: str) -> None:
    rzp_id = sub_entity.get("id")
    if not rzp_id:
        return
    sub = db.scalar(select(Subscription).where(Subscription.razorpay_subscription_id == rzp_id))
    if not sub:
        return
    sub.status = status
    sub.updated_at = datetime.utcnow()
    if sub_entity.get("current_start"):
        sub.current_period_start = datetime.fromtimestamp(sub_entity["current_start"])
    if sub_entity.get("current_end"):
        sub.current_period_end = datetime.fromtimestamp(sub_entity["current_end"])
    db.commit()


def _create_invoice_from_payment(db: Session, sub_entity: dict, payment: dict) -> None:
    rzp_sub_id = sub_entity.get("id")
    if not rzp_sub_id:
        return
    sub = db.scalar(select(Subscription).where(Subscription.razorpay_subscription_id == rzp_sub_id))
    if not sub:
        return

    amount_paise = payment.get("amount", 0)
    subtotal = Decimal(str(amount_paise)) / 100

    # Sequential invoice number per tenant: YYYYMM-XXXX
    tenant_prefix = str(sub.tenant_id)[:8].upper()
    now = datetime.utcnow()
    seq = db.query(Invoice).filter(Invoice.tenant_id == sub.tenant_id).count() + 1
    invoice_number = f"INV-{now.strftime('%Y%m')}-{seq:04d}"

    db.add(Invoice(
        tenant_id=sub.tenant_id,
        invoice_number=invoice_number,
        amount_subtotal=subtotal,
        amount_total=subtotal,  # GST computed at PDF time
        status="paid",
        line_items=[{
            "description": f"{sub.plan} plan subscription",
            "quantity": 1,
            "unit_price": str(subtotal),
        }],
        razorpay_payment_id=payment.get("id"),
        period_start=datetime.fromtimestamp(sub_entity["current_start"]) if sub_entity.get("current_start") else None,
        period_end=datetime.fromtimestamp(sub_entity["current_end"]) if sub_entity.get("current_end") else None,
    ))
    db.commit()
    log.info("billing.invoice_created", invoice_number=invoice_number)

"""Billing API — subscriptions, M-Pesa, Paystack, webhooks, trial lifecycle."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import select

from app.core.dependencies import CurrentUser, DB, RequireSchoolAdmin
from app.core.subscriptions import Tier, TIERS
from app.core.trial_lifecycle import compute_subscription_state
from app.models.billing import SchoolSubscription
from app.schemas.billing import SubscriptionChangeRequest, MpesaPayRequest, PaystackPayRequest
from app.services.payments.billing_service import BillingService

router = APIRouter()


# ── Pricing / Tiers ──────────────────────────────────────────────

@router.get("/tiers")
async def list_tiers():
    """Public: list all pricing tiers with features."""
    return {
        "tiers": [
            {
                "name": t.value,
                "display": t.display,
                "price_monthly_kes": t.price_monthly_kes,
                "price_yearly_kes": t.price_yearly_kes,
                "max_students": t.max_students,
                "max_teachers": t.max_teachers,
                "max_campuses": t.max_campuses,
                "highlights": t.highlights,
                "features": sorted(t.features),
                "api_access": t.api_access,
                "priority_support": t.priority_support,
                "custom_branding": t.custom_branding,
                "dedicated_onboarding": t.dedicated_onboarding,
                "color": t.color,
            }
            for t in TIERS.values()
        ]
    }


# ── Subscription Management ──────────────────────────────────────

@router.get("/subscription")
async def my_subscription(db: DB, current_user: RequireSchoolAdmin):
    """Get current school's subscription and billing history.
    Includes trial state from the lifecycle engine.
    """
    svc = BillingService(db)
    billing = await svc.get_billing_history(current_user.school_id)

    # Enrich with trial lifecycle state
    sub = await db.scalar(
        select(SchoolSubscription).where(
            SchoolSubscription.school_id == current_user.school_id
        )
    )
    if sub:
        trial_state = compute_subscription_state(sub)
        billing["trial"] = {
            "days_left": trial_state.get("trial_days_left"),
            "effective_status": trial_state["effective_status"],
            "is_read_only": trial_state["is_read_only"],
            "message": trial_state["message"],
            "action_required": trial_state.get("action_required"),
        }
    else:
        billing["trial"] = {
            "days_left": None,
            "effective_status": "pending",
            "is_read_only": False,
            "message": "No subscription found. Register for a free trial.",
            "action_required": "register",
        }

    return billing


@router.get("/subscription/trial-status")
async def trial_status(db: DB, current_user: RequireSchoolAdmin):
    """Quick trial status check — used by the frontend banner and mobile apps."""
    sub = await db.scalar(
        select(SchoolSubscription).where(
            SchoolSubscription.school_id == current_user.school_id
        )
    )
    if not sub:
        return {
            "status": "pending_verification",
            "is_read_only": False,
            "message": "No active subscription.",
            "days_left": None,
        }

    state = compute_subscription_state(sub)
    return {
        "status": state["effective_status"],
        "is_read_only": state["is_read_only"],
        "message": state["message"],
        "days_left": state["trial_days_left"],
        "action_required": state.get("action_required"),
    }


@router.post("/subscription/change")
async def change_subscription(
    payload: SubscriptionChangeRequest,
    db: DB,
    current_user: RequireSchoolAdmin,
):
    """Upgrade or downgrade subscription tier."""
    svc = BillingService(db)
    result = await svc.change_tier(
        school_id=current_user.school_id,
        new_tier=Tier(payload.tier),
        billing_cycle=payload.billing_cycle,
        payment_method=payload.payment_method,
        mpesa_phone=payload.mpesa_phone,
        paystack_email=payload.paystack_email,
    )
    return result


@router.get("/subscription/check-feature")
async def check_feature(
    feature: str = Query(...),
    db: DB = None,
    current_user: RequireSchoolAdmin = None,
):
    """Check if current school can access a specific feature."""
    svc = BillingService(db)
    return await svc.check_feature_access(current_user.school_id, feature)


# ── M-Pesa ──────────────────────────────────────────────────────

@router.post("/mpesa/pay")
async def mpesa_pay(payload: MpesaPayRequest, db: DB, current_user: RequireSchoolAdmin):
    """Initiate M-Pesa STK Push payment for an invoice."""
    svc = BillingService(db)
    result = await svc.initiate_mpesa_payment(payload.invoice_id, payload.phone_number)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/mpesa/callback")
async def mpesa_callback(request: Request, db: DB):
    """Safaricom calls this endpoint after STK Push completes.
    NO authentication — this is a public webhook.
    """
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    svc = BillingService(db)
    result = await svc.confirm_mpesa_payment(data)

    # Always return success to Safaricom (they retry on non-200)
    return {"ResultCode": 0, "ResultDesc": "Accepted"}


@router.post("/mpesa/query")
async def mpesa_query(
    checkout_request_id: str = Query(...), db: DB = None,
    current_user: RequireSchoolAdmin = None,
):
    """Query M-Pesa STK Push status manually."""
    from app.services.payments.mpesa import MpesaGateway
    gw = MpesaGateway()
    result = await gw.query_status(checkout_request_id)
    return result


# ── Paystack ────────────────────────────────────────────────────

@router.post("/paystack/pay")
async def paystack_pay(payload: PaystackPayRequest, db: DB, current_user: RequireSchoolAdmin):
    """Initialize Paystack payment for an invoice."""
    svc = BillingService(db)
    result = await svc.initiate_paystack_payment(
        payload.invoice_id,
        payload.email or current_user.email,
        payload.callback_url or "",
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/paystack/verify")
async def paystack_verify(
    reference: str = Query(...), db: DB = None,
    current_user: RequireSchoolAdmin = None,
):
    """Verify a Paystack transaction after customer completes payment."""
    svc = BillingService(db)
    result = await svc.confirm_paystack_payment(reference)
    return result


@router.post("/paystack/webhook")
async def paystack_webhook(request: Request, db: DB):
    """Paystack calls this endpoint on charge.success and other events."""
    # Validate signature
    signature = request.headers.get("x-paystack-signature", "")
    body = await request.body()

    from app.services.payments.paystack import PaystackGateway
    if not PaystackGateway.validate_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        import json
        data = json.loads(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    parsed = PaystackGateway.parse_webhook(data)
    if not parsed:
        return {"status": "ignored"}

    # If charge.success → confirm payment
    if parsed["event"] == "charge.success":
        svc = BillingService(db)
        await svc.confirm_paystack_payment(parsed["reference"])

    return {"status": "received"}

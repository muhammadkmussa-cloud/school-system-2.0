"""School Management System — Billing & Subscription Service.

Orchestrates the full billing lifecycle:
    Tier selection → Invoice generation → Payment (M-Pesa / Paystack) → Activation
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from loguru import logger
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.subscriptions import Tier, get_tier_config, tier_has_feature, tier_allows_students
from app.models.billing import SchoolSubscription, Invoice, Payment
from app.models.school import School
from app.services.payments.mpesa import MpesaGateway
from app.services.payments.paystack import PaystackGateway


class BillingService:
    """Full billing lifecycle manager."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.mpesa = MpesaGateway()
        self.paystack = PaystackGateway()

    # ── Subscription Management ────────────────────────────────

    async def get_or_create_subscription(self, school_id: uuid.UUID) -> SchoolSubscription:
        """Get active subscription or create a free-tier default."""
        sub = await self.db.scalar(
            select(SchoolSubscription).where(
                SchoolSubscription.school_id == school_id,
                SchoolSubscription.status.in_(["active", "past_due", "trial"]),
            )
        )

        if sub:
            return sub

        # Create free-tier default
        tier = Tier.FREE
        now = datetime.now(timezone.utc)
        sub = SchoolSubscription(
            school_id=school_id,
            tier=tier.value,
            status="trial",
            billing_cycle="monthly",
            current_period_start=now,
            current_period_end=now + timedelta(days=14),  # 14-day trial
            trial_ends_at=now + timedelta(days=14),
        )
        self.db.add(sub)
        await self.db.flush()
        await self.db.refresh(sub)
        return sub

    async def change_tier(
        self,
        school_id: uuid.UUID,
        new_tier: Tier,
        billing_cycle: str = "monthly",
        payment_method: str | None = None,
        mpesa_phone: str | None = None,
        paystack_email: str | None = None,
    ) -> dict[str, Any]:
        """Upgrade/downgrade a school's subscription tier."""
        sub = await self.get_or_create_subscription(school_id)
        old_tier = sub.tier
        config = get_tier_config(new_tier)

        # If upgrading from free to paid → generate invoice
        if old_tier == Tier.FREE.value and new_tier != Tier.FREE:
            invoice = await self._create_invoice(sub, new_tier, billing_cycle)

            if payment_method:
                sub.payment_method = payment_method
            if mpesa_phone:
                sub.mpesa_phone = mpesa_phone
            if paystack_email:
                sub.paystack_email = paystack_email

            sub.tier = new_tier.value
            sub.billing_cycle = billing_cycle
            sub.status = "past_due"  # until payment confirmed
            await self.db.flush()

            return {
                "subscription_id": str(sub.id),
                "tier": new_tier.value,
                "status": "past_due",
                "invoice_id": str(invoice.id),
                "invoice_number": invoice.invoice_number,
                "amount_kes": invoice.amount_kes,
                "requires_payment": True,
            }

        # Free upgrade or same tier
        sub.tier = new_tier.value
        sub.billing_cycle = billing_cycle
        if payment_method:
            sub.payment_method = payment_method
        await self.db.flush()

        return {
            "subscription_id": str(sub.id),
            "tier": new_tier.value,
            "status": sub.status,
            "requires_payment": False,
        }

    # ── Invoice Generation ─────────────────────────────────────

    async def _create_invoice(
        self,
        sub: SchoolSubscription,
        tier: Tier,
        billing_cycle: str,
    ) -> Invoice:
        """Generate an invoice for subscription payment."""
        config = get_tier_config(tier)
        amount = config.price_monthly_kes if billing_cycle == "monthly" else config.price_yearly_kes

        now = datetime.now(timezone.utc)
        period_start = now
        if billing_cycle == "monthly":
            period_end = now + timedelta(days=30)
        else:
            period_end = now + timedelta(days=365)

        # Generate invoice number
        count = await self.db.scalar(select(func.count(Invoice.id))) or 0
        invoice_number = f"INV-{now.year}-{count + 1:05d}"

        invoice = Invoice(
            subscription_id=sub.id,
            school_id=sub.school_id,
            invoice_number=invoice_number,
            amount_kes=amount,
            status="pending",
            description=f"{config.display} Plan — {billing_cycle.capitalize()}",
            due_date=now + timedelta(days=7),
            period_start=period_start,
            period_end=period_end,
        )
        self.db.add(invoice)
        await self.db.flush()
        await self.db.refresh(invoice)

        logger.info(f"📄 Invoice {invoice_number}: KES {amount:.0f} for school {sub.school_id}")
        return invoice

    # ── Payment Initiation ─────────────────────────────────────

    async def initiate_mpesa_payment(
        self, invoice_id: uuid.UUID, phone_number: str
    ) -> dict[str, Any]:
        """Initiate M-Pesa STK Push for an invoice."""
        invoice = await self.db.scalar(select(Invoice).where(Invoice.id == invoice_id))
        if not invoice:
            return {"error": "Invoice not found"}

        # Create payment record
        payment = Payment(
            invoice_id=invoice.id,
            school_id=invoice.school_id,
            amount_kes=invoice.amount_kes,
            gateway="mpesa",
            mpesa_phone=phone_number,
            status="pending",
        )
        self.db.add(payment)
        await self.db.flush()

        # Initiate STK Push
        result = await self.mpesa.stk_push(
            phone_number=phone_number,
            amount=invoice.amount_kes,
            account_reference=invoice.invoice_number,
        )

        # Save gateway reference
        payment.gateway_reference = result.get("CheckoutRequestID")
        payment.gateway_response = result
        await self.db.flush()

        response_code = result.get("ResponseCode", "1")
        return {
            "payment_id": str(payment.id),
            "checkout_request_id": payment.gateway_reference,
            "merchant_request_id": result.get("MerchantRequestID"),
            "status": "initiated" if response_code == "0" else "failed",
            "message": result.get("CustomerMessage", result.get("ResponseDescription", "")),
        }

    async def initiate_paystack_payment(
        self, invoice_id: uuid.UUID, email: str, callback_url: str = ""
    ) -> dict[str, Any]:
        """Initialize Paystack payment for an invoice."""
        invoice = await self.db.scalar(select(Invoice).where(Invoice.id == invoice_id))
        if not invoice:
            return {"error": "Invoice not found"}

        # Create payment record
        payment = Payment(
            invoice_id=invoice.id,
            school_id=invoice.school_id,
            amount_kes=invoice.amount_kes,
            gateway="paystack",
            status="pending",
        )
        self.db.add(payment)
        await self.db.flush()

        # Initialize Paystack transaction
        result = await self.paystack.initialize_transaction(
            email=email,
            amount_kes=invoice.amount_kes,
            reference=invoice.invoice_number,
            callback_url=callback_url,
            metadata={"invoice_id": str(invoice.id), "payment_id": str(payment.id)},
        )

        if result.get("status"):
            tx_data = result["data"]
            payment.gateway_reference = tx_data.get("reference")
            payment.gateway_response = result
            await self.db.flush()

            return {
                "payment_id": str(payment.id),
                "reference": tx_data.get("reference"),
                "access_code": tx_data.get("access_code"),
                "authorization_url": tx_data.get("authorization_url"),
                "status": "initiated",
            }

        payment.status = "failed"
        payment.gateway_response = result
        await self.db.flush()

        return {
            "payment_id": str(payment.id),
            "status": "failed",
            "message": result.get("message", "Payment initialization failed"),
        }

    # ── Payment Confirmation ───────────────────────────────────

    async def confirm_mpesa_payment(self, callback_data: dict) -> dict[str, Any]:
        """Process M-Pesa callback and mark invoice as paid."""
        parsed = MpesaGateway.parse_callback(callback_data)
        if not parsed:
            return {"error": "Failed to parse M-Pesa callback"}

        checkout_id = parsed["checkout_request_id"]

        # Find payment record
        payment = await self.db.scalar(
            select(Payment).where(Payment.gateway_reference == checkout_id)
        )
        if not payment:
            logger.warning(f"M-Pesa callback: no payment found for {checkout_id}")
            return {"error": "Payment record not found"}

        if parsed["success"]:
            payment.status = "completed"
            payment.gateway_status = "completed"
            payment.mpesa_receipt = parsed.get("mpesa_receipt")

            # Mark invoice as paid
            await self._mark_invoice_paid(payment.invoice_id, payment.amount_kes)
        else:
            payment.status = "failed"
            payment.gateway_status = parsed.get("error", "Failed")

        payment.gateway_response = callback_data
        await self.db.flush()

        return {
            "payment_id": str(payment.id),
            "status": payment.status,
            "mpesa_receipt": payment.mpesa_receipt,
        }

    async def confirm_paystack_payment(self, reference: str) -> dict[str, Any]:
        """Verify Paystack transaction and mark invoice as paid."""
        result = await self.paystack.verify_transaction(reference)

        if not result.get("status"):
            return {"error": "Verification failed", "raw": result}

        tx_data = result["data"]
        tx_status = tx_data.get("status")

        # Find payment record
        payment = await self.db.scalar(
            select(Payment).where(Payment.gateway_reference == reference)
        )
        if not payment:
            return {"error": "Payment record not found"}

        if tx_status == "success":
            payment.status = "completed"
            payment.gateway_status = "success"
            payment.gateway_response = result

            # Save authorization for recurring billing
            auth = tx_data.get("authorization", {})
            if auth:
                payment.paystack_authorization_code = auth.get("authorization_code")
                payment.paystack_card_type = auth.get("card_type")
                payment.paystack_last4 = auth.get("last4")

                # Save to subscription for auto-renew
                sub = await self.db.scalar(
                    select(SchoolSubscription).where(
                        SchoolSubscription.id == payment.invoice.subscription_id
                    )
                )
                if sub:
                    sub.paystack_customer_code = tx_data.get("customer", {}).get("customer_code")
                    sub.paystack_email = tx_data.get("customer", {}).get("email")

            await self._mark_invoice_paid(payment.invoice_id, payment.amount_kes)
        else:
            payment.status = "failed"
            payment.gateway_status = tx_status
            payment.gateway_response = result

        await self.db.flush()

        return {
            "payment_id": str(payment.id),
            "status": payment.status,
            "reference": reference,
            "amount": tx_data.get("amount", 0) / 100.0,
        }

    async def _mark_invoice_paid(self, invoice_id: uuid.UUID, amount: float):
        """Mark an invoice as paid and activate subscription."""
        invoice = await self.db.scalar(select(Invoice).where(Invoice.id == invoice_id))
        if not invoice:
            return

        invoice.status = "paid"
        invoice.amount_paid_kes = amount
        invoice.paid_at = datetime.now(timezone.utc)

        # Activate subscription
        sub = await self.db.scalar(
            select(SchoolSubscription).where(SchoolSubscription.id == invoice.subscription_id)
        )
        if sub:
            now = datetime.now(timezone.utc)
            sub.status = "active"
            sub.current_period_start = invoice.period_start
            sub.current_period_end = invoice.period_end
            sub.trial_ends_at = None

        logger.info(f"✅ Invoice {invoice.invoice_number} marked PAID (KES {amount:.0f})")

    # ── Feature Checks ─────────────────────────────────────────

    async def check_feature_access(
        self, school_id: uuid.UUID, feature: str
    ) -> dict[str, Any]:
        """Check if a school can access a feature on their tier."""
        sub = await self.get_or_create_subscription(school_id)
        config = get_tier_config(sub.tier)

        allowed = tier_has_feature(sub.tier, feature)

        # Check extra features granted by admin
        if not allowed and sub.extra_features:
            allowed = feature in (sub.extra_features or [])

        return {
            "feature": feature,
            "allowed": allowed,
            "tier": sub.tier,
            "tier_display": config.display,
            "requires_upgrade": not allowed,
            "upgrade_to": None if allowed else self._minimum_tier_for_feature(feature),
        }

    def _minimum_tier_for_feature(self, feature: str) -> str | None:
        """Return the cheapest tier that includes a feature."""
        for tier in [Tier.STARTER, Tier.PROFESSIONAL, Tier.ENTERPRISE]:
            if tier_has_feature(tier, feature):
                return tier.value
        return Tier.ENTERPRISE.value

    async def get_billing_history(self, school_id: uuid.UUID) -> dict[str, Any]:
        """Return subscription + invoice + payment history."""
        sub = await self.db.scalar(
            select(SchoolSubscription).where(SchoolSubscription.school_id == school_id)
        )
        if not sub:
            return {"subscription": None, "invoices": [], "payments": []}

        invoices_raw = await self.db.scalars(
            select(Invoice).where(Invoice.subscription_id == sub.id)
        )
        invoices = list(invoices_raw)

        payments_raw = await self.db.scalars(
            select(Payment).where(Payment.school_id == school_id)
        )
        payments = list(payments_raw)

        config = get_tier_config(sub.tier)

        return {
            "subscription": {
                "id": str(sub.id),
                "tier": sub.tier,
                "tier_display": config.display,
                "status": sub.status,
                "billing_cycle": sub.billing_cycle,
                "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
                "payment_method": sub.payment_method,
                "auto_renew": sub.auto_renew,
                "trial_ends_at": sub.trial_ends_at.isoformat() if sub.trial_ends_at else None,
                "limits": {
                    "max_students": config.max_students,
                    "max_teachers": config.max_teachers,
                    "api_access": config.api_access,
                    "priority_support": config.priority_support,
                },
            },
            "invoices": [
                {
                    "id": str(inv.id),
                    "number": inv.invoice_number,
                    "amount_kes": inv.amount_kes,
                    "amount_paid_kes": inv.amount_paid_kes,
                    "status": inv.status,
                    "description": inv.description,
                    "due_date": inv.due_date.isoformat() if inv.due_date else None,
                    "paid_at": inv.paid_at.isoformat() if inv.paid_at else None,
                }
                for inv in invoices
            ],
            "payments": [
                {
                    "id": str(p.id),
                    "amount_kes": p.amount_kes,
                    "gateway": p.gateway,
                    "status": p.status,
                    "mpesa_receipt": p.mpesa_receipt,
                    "gateway_reference": p.gateway_reference,
                    "created_at": p.created_at.isoformat(),
                }
                for p in payments
            ],
        }

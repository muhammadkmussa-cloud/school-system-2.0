"""School Management System — Billing & Subscription models.

Tracks school subscriptions, invoices, and payment transactions.
Supports M-Pesa (Kenya), Paystack (card/bank), and manual billing.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime, Enum, Float, ForeignKey, Integer, String, Text, Boolean, func, JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class SchoolSubscription(Base, TimestampMixin):
    """A school's active subscription to a tier."""
    __tablename__ = "school_subscriptions"

    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False, unique=True,
    )
    tier: Mapped[str] = mapped_column(
        String(30), nullable=False, default="free"
    )  # "free" | "starter" | "professional" | "enterprise"

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )  # "active" | "past_due" | "cancelled" | "trial"

    billing_cycle: Mapped[str] = mapped_column(
        String(10), nullable=False, default="monthly"
    )  # "monthly" | "yearly"

    current_period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    current_period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Payment method
    payment_method: Mapped[str | None] = mapped_column(
        String(20)
    )  # "mpesa" | "paystack" | "manual"

    auto_renew: Mapped[bool] = mapped_column(Boolean, default=True)
    mpesa_phone: Mapped[str | None] = mapped_column(String(15))  # 2547XXXXXXXX
    paystack_email: Mapped[str | None] = mapped_column(String(255))
    paystack_customer_code: Mapped[str | None] = mapped_column(String(100))

    # Feature overrides (admin can grant extra features per school)
    extra_features: Mapped[list | None] = mapped_column(JSON, default=list)

    invoices = relationship("Invoice", back_populates="subscription", lazy="dynamic",
                            order_by="Invoice.created_at.desc()")


class Invoice(Base, TimestampMixin):
    """A single billing invoice."""
    __tablename__ = "invoices"

    subscription_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("school_subscriptions.id", ondelete="CASCADE"),
        nullable=False,
    )
    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True
    )

    invoice_number: Mapped[str] = mapped_column(
        String(30), unique=True, nullable=False
    )  # "INV-2026-00001"
    amount_kes: Mapped[float] = mapped_column(Float, nullable=False)
    amount_paid_kes: Mapped[float] = mapped_column(Float, default=0.0)

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # "pending" | "paid" | "overdue" | "cancelled" | "refunded"

    description: Mapped[str] = mapped_column(String(500))
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Period covered
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    subscription = relationship("SchoolSubscription", back_populates="invoices")
    payments = relationship("Payment", back_populates="invoice", lazy="dynamic",
                            order_by="Payment.created_at")


class Payment(Base, TimestampMixin):
    """A payment transaction (M-Pesa, Paystack, or manual)."""
    __tablename__ = "payments"

    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False
    )
    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True
    )

    amount_kes: Mapped[float] = mapped_column(Float, nullable=False)
    gateway: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "mpesa" | "paystack" | "manual"

    gateway_reference: Mapped[str | None] = mapped_column(
        String(100), index=True
    )  # M-Pesa CheckoutRequestID or Paystack reference

    gateway_status: Mapped[str | None] = mapped_column(String(50))
    gateway_response: Mapped[dict | None] = mapped_column(JSON)

    # M-Pesa specifics
    mpesa_phone: Mapped[str | None] = mapped_column(String(15))
    mpesa_receipt: Mapped[str | None] = mapped_column(String(30))  # M-Pesa confirmation code

    # Paystack specifics
    paystack_authorization_code: Mapped[str | None] = mapped_column(String(200))
    paystack_card_type: Mapped[str | None] = mapped_column(String(20))
    paystack_last4: Mapped[str | None] = mapped_column(String(4))

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # "pending" | "completed" | "failed" | "refunded"

    invoice = relationship("Invoice", back_populates="payments")

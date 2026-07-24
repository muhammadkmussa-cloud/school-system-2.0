"""Billing & payment schemas."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class SubscriptionChangeRequest(BaseModel):
    tier: str = Field(..., pattern=r"^(free|starter|growth|premium|enterprise)$")
    billing_cycle: str = Field(default="monthly", pattern=r"^(monthly|yearly)$")
    payment_method: str | None = None
    mpesa_phone: str | None = None
    paystack_email: str | None = None


class MpesaPayRequest(BaseModel):
    invoice_id: uuid.UUID
    phone_number: str = Field(..., pattern=r"^254\d{9}$")


class PaystackPayRequest(BaseModel):
    invoice_id: uuid.UUID
    email: str | None = None
    callback_url: str | None = None

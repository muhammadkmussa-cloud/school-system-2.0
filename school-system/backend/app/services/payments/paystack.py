"""School Management System — Paystack Payment Integration.

Supports card payments, mobile money, and bank transfers across Africa.
Uses Paystack's inline checkout (no redirect for web, popup for mobile).

Flow:
    1. Initialize transaction → get authorization_url
    2. Customer completes payment on Paystack's hosted page
    3. Paystack calls our webhook with result
    4. We verify via API + update invoice/payment status

Paystack API docs: https://paystack.com/docs/api/
"""

from __future__ import annotations

from typing import Any

import httpx
from loguru import logger

from app.core.config import settings


class PaystackGateway:
    """Paystack payments API client."""

    # ── Config ─────────────────────────────────────────────────

    @property
    def secret_key(self) -> str:
        return getattr(settings, "PAYSTACK_SECRET_KEY", "")

    @property
    def public_key(self) -> str:
        return getattr(settings, "PAYSTACK_PUBLIC_KEY", "")

    @property
    def base_url(self) -> str:
        return "https://api.paystack.co"

    @property
    def webhook_secret(self) -> str:
        return getattr(settings, "PAYSTACK_WEBHOOK_SECRET", "")

    # ── Helpers ────────────────────────────────────────────────

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }

    def _to_kobo(self, amount_kes: float) -> int:
        """Convert KES to kobo (Paystack uses the smallest currency unit).
        For KES, 1 KES = 100 kobo. For NGN, 1 NGN = 100 kobo.
        """
        return int(amount_kes * 100)

    def _from_kobo(self, kobo: int) -> float:
        return kobo / 100.0

    # ── Initialize Transaction ─────────────────────────────────

    async def initialize_transaction(
        self,
        email: str,
        amount_kes: float,
        reference: str,  # unique per transaction (invoice number)
        callback_url: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Initialize a Paystack transaction.

        Returns authorization_url that the customer uses to pay.
        For inline (modal), use the access_code with Paystack Popup JS.
        """
        payload: dict[str, Any] = {
            "email": email,
            "amount": self._to_kobo(amount_kes),
            "reference": reference,
            "currency": "KES",
            "channels": ["card", "bank", "ussd", "mobile_money"],
            "metadata": {
                **(metadata or {}),
                "platform": "School Management System",
            },
        }

        if callback_url:
            payload["callback_url"] = callback_url

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/transaction/initialize",
                json=payload,
                headers=self._headers(),
                timeout=15,
            )
            data = resp.json()

            if data.get("status"):
                logger.info(
                    f"💳 Paystack init: {email} KES {amount_kes:.0f} "
                    f"→ ref={reference}"
                )
            else:
                logger.warning(f"Paystack init failed: {data}")

            return data

    # ── Verify Transaction ─────────────────────────────────────

    async def verify_transaction(self, reference: str) -> dict[str, Any]:
        """Verify a Paystack transaction by reference.

        Returns full transaction data with status.
        Call this after customer returns from Paystack checkout.
        """
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/transaction/verify/{reference}",
                headers=self._headers(),
                timeout=15,
            )
            data = resp.json()

            if data.get("status"):
                tx_data = data.get("data", {})
                logger.info(
                    f"💳 Paystack verify: {reference} → "
                    f"{tx_data.get('status')} | {tx_data.get('gateway_response')}"
                )

            return data

    # ── Create Customer ────────────────────────────────────────

    async def create_customer(
        self, email: str, first_name: str = "", last_name: str = "", phone: str = ""
    ) -> dict[str, Any]:
        """Create a Paystack customer for recurring billing."""
        payload: dict[str, Any] = {"email": email}
        if first_name:
            payload["first_name"] = first_name
        if last_name:
            payload["last_name"] = last_name
        if phone:
            payload["phone"] = phone

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/customer",
                json=payload,
                headers=self._headers(),
                timeout=15,
            )
            return resp.json()

    # ── Charge Authorization (Recurring) ───────────────────────

    async def charge_authorization(
        self,
        authorization_code: str,
        email: str,
        amount_kes: float,
        reference: str,
    ) -> dict[str, Any]:
        """Charge a saved card via authorization code (recurring billing)."""
        payload = {
            "authorization_code": authorization_code,
            "email": email,
            "amount": self._to_kobo(amount_kes),
            "reference": reference,
            "currency": "KES",
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/transaction/charge_authorization",
                json=payload,
                headers=self._headers(),
                timeout=15,
            )
            return resp.json()

    # ── Webhook Handler ────────────────────────────────────────

    @staticmethod
    def parse_webhook(data: dict) -> dict[str, Any] | None:
        """Parse Paystack webhook payload.

        Event types: charge.success, transfer.success, etc.
        """
        try:
            event = data.get("event", "")
            tx_data = data.get("data", {})

            return {
                "event": event,
                "reference": tx_data.get("reference"),
                "amount": tx_data.get("amount", 0) / 100.0,  # convert from kobo
                "status": tx_data.get("status"),
                "gateway_response": tx_data.get("gateway_response"),
                "channel": tx_data.get("channel"),
                "currency": tx_data.get("currency"),
                "customer_email": tx_data.get("customer", {}).get("email"),
                "authorization": tx_data.get("authorization", {}),
                "paid_at": tx_data.get("paid_at"),
                "metadata": tx_data.get("metadata", {}),
                "raw": tx_data,
            }
        except Exception as e:
            logger.error(f"Paystack webhook parse failed: {e}")
            return None

    # ── Validate Webhook Signature ─────────────────────────────

    @staticmethod
    def validate_signature(body: bytes, signature: str) -> bool:
        """Verify Paystack webhook signature using HMAC SHA512."""
        import hashlib
        import hmac
        from app.core.config import settings

        secret = getattr(settings, "PAYSTACK_WEBHOOK_SECRET", "")
        if not secret:
            logger.warning("No PAYSTACK_WEBHOOK_SECRET configured — signature check skipped")
            return True  # In production, always validate

        computed = hmac.new(
            secret.encode("utf-8"), body, hashlib.sha512
        ).hexdigest()

        return hmac.compare_digest(computed, signature)

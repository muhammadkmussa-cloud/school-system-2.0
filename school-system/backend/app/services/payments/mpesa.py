"""School Management System — M-Pesa Daraja API Integration.

Implements Safaricom's M-Pesa Express (STK Push) for automated payments.
Supports both sandbox (testing) and production environments.

Flow:
    1. Initiate STK Push → customer gets USSD popup on phone
    2. Customer enters PIN → M-Pesa processes
    3. Safaricom calls our callback URL with result
    4. We verify + update invoice/payment status

M-Pesa API docs: https://developer.safaricom.co.ke/
"""

from __future__ import annotations

import base64
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
from loguru import logger

from app.core.config import settings


class MpesaGateway:
    """Safaricom Daraja API client for M-Pesa STK Push."""

    # ── Config (from env) ──────────────────────────────────────

    @property
    def consumer_key(self) -> str:
        return getattr(settings, "MPESA_CONSUMER_KEY", "")

    @property
    def consumer_secret(self) -> str:
        return getattr(settings, "MPESA_CONSUMER_SECRET", "")

    @property
    def passkey(self) -> str:
        return getattr(settings, "MPESA_PASSKEY", "")

    @property
    def shortcode(self) -> str:
        return getattr(settings, "MPESA_SHORTCODE", "174379")

    @property
    def environment(self) -> str:
        return getattr(settings, "MPESA_ENVIRONMENT", "sandbox")

    @property
    def callback_url(self) -> str:
        return getattr(
            settings, "MPESA_CALLBACK_URL",
            "https://api.example.com/api/v1/billing/mpesa/callback",
        )

    @property
    def base_url(self) -> str:
        if self.environment == "production":
            return "https://api.safaricom.co.ke"
        return "https://sandbox.safaricom.co.ke"

    # ── Auth ───────────────────────────────────────────────────

    async def _get_access_token(self) -> str:
        """Obtain OAuth2 access token from Safaricom."""
        auth = base64.b64encode(
            f"{self.consumer_key}:{self.consumer_secret}".encode()
        ).decode()

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials",
                headers={"Authorization": f"Basic {auth}"},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["access_token"]

    # ── STK Push ───────────────────────────────────────────────

    async def stk_push(
        self,
        phone_number: str,       # 2547XXXXXXXX
        amount: float,           # KES
        account_reference: str,  # invoice number
        transaction_desc: str = "School Management System Subscription",
    ) -> dict[str, Any]:
        """Initiate M-Pesa STK Push to customer's phone.

        Returns: {
            "MerchantRequestID": "...",
            "CheckoutRequestID": "...",
            "ResponseCode": "0",
            "CustomerMessage": "Success. Request accepted for processing"
        }
        """
        token = await self._get_access_token()

        # Format phone: ensure it starts with 254
        phone = phone_number.strip().replace("+", "")
        if phone.startswith("0"):
            phone = "254" + phone[1:]

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        password = base64.b64encode(
            f"{self.shortcode}{self.passkey}{timestamp}".encode()
        ).decode()

        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(amount),  # M-Pesa expects integer
            "PartyA": phone,
            "PartyB": self.shortcode,
            "PhoneNumber": phone,
            "CallBackURL": self.callback_url,
            "AccountReference": account_reference[:12],
            "TransactionDesc": transaction_desc[:13],
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/mpesa/stkpush/v1/processrequest",
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                timeout=30,
            )
            data = resp.json()

            logger.info(
                f"📱 M-Pesa STK Push: {phone} KES {amount:.0f} "
                f"→ {data.get('ResponseDescription', resp.status_code)}"
            )
            return data

    # ── Query Status ───────────────────────────────────────────

    async def query_status(self, checkout_request_id: str) -> dict[str, Any]:
        """Query the status of an STK Push transaction."""
        token = await self._get_access_token()

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        password = base64.b64encode(
            f"{self.shortcode}{self.passkey}{timestamp}".encode()
        ).decode()

        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "CheckoutRequestID": checkout_request_id,
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/mpesa/stkpushquery/v1/query",
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                timeout=15,
            )
            return resp.json()

    # ── Callback Handler ───────────────────────────────────────

    @staticmethod
    def parse_callback(data: dict) -> dict[str, Any] | None:
        """Parse Safaricom's callback payload into a clean result.

        Callback body structure:
        {
            "Body": {
                "stkCallback": {
                    "MerchantRequestID": "...",
                    "CheckoutRequestID": "...",
                    "ResultCode": 0,           # 0 = success
                    "ResultDesc": "Success",
                    "CallbackMetadata": {
                        "Item": [
                            {"Name": "Amount", "Value": 2500.0},
                            {"Name": "MpesaReceiptNumber", "Value": "SHF8XG7H3K"},
                            {"Name": "PhoneNumber", "Value": 254712345678},
                            {"Name": "TransactionDate", "Value": 20260712153000},
                        ]
                    }
                }
            }
        }
        """
        try:
            callback = data.get("Body", {}).get("stkCallback", {})
            result_code = callback.get("ResultCode")

            if result_code != 0:
                return {
                    "success": False,
                    "checkout_request_id": callback.get("CheckoutRequestID"),
                    "merchant_request_id": callback.get("MerchantRequestID"),
                    "error": callback.get("ResultDesc", "Unknown error"),
                }

            # Extract metadata
            items = callback.get("CallbackMetadata", {}).get("Item", [])
            meta = {item["Name"]: item.get("Value") for item in items}

            return {
                "success": True,
                "checkout_request_id": callback.get("CheckoutRequestID"),
                "merchant_request_id": callback.get("MerchantRequestID"),
                "amount": meta.get("Amount"),
                "mpesa_receipt": meta.get("MpesaReceiptNumber"),
                "phone": meta.get("PhoneNumber"),
                "transaction_date": meta.get("TransactionDate"),
            }
        except Exception as e:
            logger.error(f"M-Pesa callback parse failed: {e}")
            return None

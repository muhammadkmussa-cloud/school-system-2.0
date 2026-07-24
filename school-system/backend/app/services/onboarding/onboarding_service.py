"""School Management System — Paid Onboarding & Setup Service.

Schools can purchase a setup package where the School Management System team:
    - Imports existing student records
    - Creates teacher accounts
    - Sets up classes, streams, subjects
    - Configures grading schemes
    - Sets up the timetable
    - Trains staff (virtual or on-site)

Revenue model: fixed-fee packages, billable as one-time invoices.

This is a high-value service that ALSO increases customer success —
schools that get professional setup are far more likely to subscribe.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

from loguru import logger
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.billing import Invoice, SchoolSubscription


class OnboardingPackage(str, Enum):
    BASIC = "basic"            # CSV import only — KES 5,000
    STANDARD = "standard"      # Import + timetable setup — KES 15,000
    PREMIUM = "premium"        # Full setup + staff training — KES 35,000


@dataclass
class OnboardingPackageConfig:
    name: str
    display: str
    price_kes: int
    includes: list[str]
    turnaround_days: int  # estimated completion time


PACKAGES: dict[OnboardingPackage, OnboardingPackageConfig] = {
    OnboardingPackage.BASIC: OnboardingPackageConfig(
        name="basic",
        display="Basic Import",
        price_kes=5_000,
        includes=[
            "Student CSV import (up to 500 students)",
            "Teacher CSV import (up to 20 teachers)",
            "Class & stream creation",
            "Subject setup",
        ],
        turnaround_days=2,
    ),
    OnboardingPackage.STANDARD: OnboardingPackageConfig(
        name="standard",
        display="Standard Setup",
        price_kes=15_000,
        includes=[
            "Student CSV import (up to 2,000 students)",
            "Teacher CSV import (up to 50 teachers)",
            "Class, stream & subject setup",
            "Timetable creation (one master timetable)",
            "Grading scheme configuration",
            "Admin account training session (1 hour, virtual)",
        ],
        turnaround_days=5,
    ),
    OnboardingPackage.PREMIUM: OnboardingPackageConfig(
        name="premium",
        display="Premium Setup + Training",
        price_kes=35_000,
        includes=[
            "Student CSV import (unlimited students)",
            "Teacher CSV import (unlimited teachers)",
            "Full academic structure setup",
            "Master timetable creation",
            "Grading scheme + curriculum configuration",
            "Admin + teacher training (3 hours, virtual)",
            "On-site visit option (Mombasa/Nairobi — additional travel fee)",
            "30-day priority email support",
        ],
        turnaround_days=10,
    ),
}


class OnboardingRequestStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    AWAITING_DATA = "awaiting_data"  # waiting for school to send CSVs
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class OnboardingService:
    """Manages onboarding packages, requests, and billing."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def request_onboarding(
        self,
        school_id: uuid.UUID,
        package: OnboardingPackage,
        contact_name: str,
        contact_phone: str,
        contact_email: str,
        notes: str = "",
        preferred_date: str | None = None,
    ) -> dict[str, Any]:
        """School requests an onboarding package. Generates a one-time invoice."""

        config = PACKAGES[package]

        # Generate invoice number
        now = datetime.now(timezone.utc)
        count = await self.db.scalar(select(func.count(Invoice.id))) or 0
        invoice_number = f"ONB-{now.year}-{count + 1:05d}"

        # Get or create subscription
        sub = await self.db.scalar(
            select(SchoolSubscription).where(
                SchoolSubscription.school_id == school_id
            )
        )

        invoice = Invoice(
            subscription_id=sub.id if sub else uuid.uuid4(),
            school_id=school_id,
            invoice_number=invoice_number,
            amount_kes=config.price_kes,
            status="pending",
            description=f"Onboarding: {config.display} Package",
            due_date=now + timedelta(days=14),
            period_start=now,
            period_end=now + timedelta(days=30),
        )
        self.db.add(invoice)
        await self.db.flush()

        logger.info(
            f"🎓 Onboarding requested: {config.display} for school {school_id} "
            f"→ KES {config.price_kes:,}"
        )

        return {
            "request_id": str(invoice.id),
            "invoice_number": invoice_number,
            "package": config.display,
            "price_kes": config.price_kes,
            "includes": config.includes,
            "turnaround_days": config.turnaround_days,
            "status": "pending",
            "next_step": (
                "Complete payment via M-Pesa or Paystack on the Billing page. "
                "After payment, our team will contact you within 24 hours to begin setup."
            ),
        }

    async def list_packages(self) -> list[dict[str, Any]]:
        """List all available onboarding packages."""
        return [
            {
                "id": pkg.value,
                "name": config.display,
                "price_kes": config.price_kes,
                "includes": config.includes,
                "turnaround_days": config.turnaround_days,
            }
            for pkg, config in PACKAGES.items()
        ]

    async def get_onboarding_status(
        self, school_id: uuid.UUID
    ) -> dict[str, Any] | None:
        """Get the status of a school's onboarding request."""
        from app.models.billing import Invoice

        invoice = await self.db.scalar(
            select(Invoice).where(
                Invoice.school_id == school_id,
                Invoice.invoice_number.like("ONB-%"),
            ).order_by(Invoice.created_at.desc()).limit(1)
        )

        if not invoice:
            return None

        return {
            "invoice_number": invoice.invoice_number,
            "package": invoice.description,
            "price_kes": invoice.amount_kes,
            "status": invoice.status,
            "paid": invoice.status == "paid",
            "created_at": invoice.created_at.isoformat() if invoice.created_at else None,
        }

    # In a production system, a Django admin or internal dashboard would
    # manage the onboarding workflow (pending → in_progress → completed).
    # These status transitions are handled by School Management System staff, not the school.




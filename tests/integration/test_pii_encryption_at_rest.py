"""
BL-047 + BL-048: verify PII encryption at rest is transparent for ORM
read/write paths, and raw DB column values are encrypted Fernet tokens
(never plaintext).

Series 16.x Group B — encrypt PayoutRequest.requisites and
DocumentUpload.ocr_text via EncryptedString TypeDecorator (Fernet).
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.document_upload import DocumentUpload
from src.db.models.payout import PayoutRequest, PayoutStatus
from src.db.models.user import User

pytestmark = pytest.mark.asyncio


def _unique_int() -> int:
    return uuid.uuid4().int % 2_000_000_000


async def test_payout_request_requisites_encrypted_at_rest(
    db_session: AsyncSession,
) -> None:
    """ORM round-trip returns plaintext; raw SQL sees Fernet token."""
    plaintext = "Card 1234-5678-9012-3456, holder Иванов И.И., БИК 044525225"

    owner = User(
        telegram_id=_unique_int(),
        username=f"owner_{_unique_int()}",
        first_name="Owner",
        balance_rub=Decimal("0"),
        earned_rub=Decimal("0"),
    )
    db_session.add(owner)
    await db_session.flush()

    payout = PayoutRequest(
        owner_id=owner.id,
        gross_amount=Decimal("1000.00"),
        fee_amount=Decimal("15.00"),
        net_amount=Decimal("985.00"),
        status=PayoutStatus.pending,
        requisites=plaintext,
    )
    db_session.add(payout)
    await db_session.flush()
    payout_id = payout.id

    # ORM read path — transparent decrypt
    db_session.expire(payout)
    refreshed = await db_session.get(PayoutRequest, payout_id)
    assert refreshed is not None
    assert refreshed.requisites == plaintext

    # Raw SQL — must see encrypted Fernet token, never plaintext
    raw_row = await db_session.execute(
        text("SELECT requisites FROM payout_requests WHERE id = :id"),
        {"id": payout_id},
    )
    raw_value = raw_row.scalar_one()
    assert raw_value is not None
    assert raw_value != plaintext, "raw column must NOT contain plaintext"
    # Fernet tokens are URL-safe base64 starting with version byte 0x80 → 'gAAAAA' prefix
    assert raw_value.startswith("gAAAAA"), (
        f"raw value must be a Fernet token, got: {raw_value[:20]!r}"
    )


async def test_document_upload_ocr_text_encrypted_at_rest(
    db_session: AsyncSession,
) -> None:
    """ORM round-trip returns plaintext; raw SQL sees Fernet token. Tests
    a multi-line cyrillic passport-OCR-shaped payload."""
    plaintext = (
        "Серия 1234 №567890\n"
        "Выдан 01.01.2020 ОВД района Хамовники г. Москвы\n"
        "Код подразделения: 770-001\n"
        "ФИО: Иванов Иван Иванович\n"
        "Дата рождения: 15.06.1985\n"
        "Место рождения: г. Москва\n"
    ) * 5  # ~1.5 KB cyrillic — well under the 50 000 limit

    upload = DocumentUpload(
        user_id=_unique_int(),
        original_filename="passport.jpg",
        stored_path="/data/uploads/passport.jpg",
        file_type="jpg",
        file_size=204800,
        document_type="passport",
        ocr_text=plaintext,
    )
    db_session.add(upload)
    await db_session.flush()
    upload_id = upload.id

    db_session.expire(upload)
    refreshed = await db_session.get(DocumentUpload, upload_id)
    assert refreshed is not None
    assert refreshed.ocr_text == plaintext

    raw_row = await db_session.execute(
        text("SELECT ocr_text FROM document_uploads WHERE id = :id"),
        {"id": upload_id},
    )
    raw_value = raw_row.scalar_one()
    assert raw_value is not None
    assert raw_value != plaintext, "raw column must NOT contain plaintext"
    assert raw_value.startswith("gAAAAA"), (
        f"raw value must be a Fernet token, got: {raw_value[:20]!r}"
    )

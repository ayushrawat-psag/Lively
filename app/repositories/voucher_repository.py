from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.voucher import Voucher, VoucherRedemption


class VoucherRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_code(self, code: str) -> Voucher | None:
        stmt = select(Voucher).where(Voucher.code == code)
        return self.db.scalars(stmt).first()

    def count_redemptions(self, voucher_id: UUID) -> int:
        stmt = select(func.count()).select_from(VoucherRedemption).where(
            VoucherRedemption.voucher_id == voucher_id
        )
        return int(self.db.scalar(stmt) or 0)

    def count_user_redemptions(self, voucher_id: UUID, user_id: UUID) -> int:
        stmt = select(func.count()).select_from(VoucherRedemption).where(
            VoucherRedemption.voucher_id == voucher_id,
            VoucherRedemption.user_id == user_id,
        )
        return int(self.db.scalar(stmt) or 0)

    def create_redemption(self, *, voucher_id: UUID, user_id: UUID) -> VoucherRedemption:
        redemption = VoucherRedemption(
            voucher_id=voucher_id,
            user_id=user_id,
            redeemed_at=datetime.now(timezone.utc),
        )
        self.db.add(redemption)
        self.db.flush()
        return redemption

    def save(self) -> None:
        self.db.commit()

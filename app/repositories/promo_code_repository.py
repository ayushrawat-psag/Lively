from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.promo_code import PromoCode, PromoCodeRedemption


class PromoCodeRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_code(self, code: str) -> PromoCode | None:
        stmt = select(PromoCode).where(PromoCode.code == code)
        return self.db.scalars(stmt).first()

    def count_redemptions(self, promo_code_id: UUID) -> int:
        stmt = select(func.count()).select_from(PromoCodeRedemption).where(
            PromoCodeRedemption.promo_code_id == promo_code_id
        )
        return int(self.db.scalar(stmt) or 0)

    def count_user_redemptions(self, promo_code_id: UUID, user_id: UUID) -> int:
        stmt = select(func.count()).select_from(PromoCodeRedemption).where(
            PromoCodeRedemption.promo_code_id == promo_code_id,
            PromoCodeRedemption.user_id == user_id,
        )
        return int(self.db.scalar(stmt) or 0)

    def create_redemption(self, *, promo_code_id: UUID, user_id: UUID) -> PromoCodeRedemption:
        redemption = PromoCodeRedemption(
            promo_code_id=promo_code_id,
            user_id=user_id,
            redeemed_at=datetime.now(timezone.utc),
        )
        self.db.add(redemption)
        self.db.flush()
        return redemption

    def save(self) -> None:
        self.db.commit()

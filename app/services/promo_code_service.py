from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.promo_code import PromoCode, PromoCodeRedemption
from app.models.user import User
from app.repositories.promo_code_repository import PromoCodeRepository
from app.schemas.promo_codes import ValidatePromoCodeRequest, ValidatePromoCodeResponse

_INVALID_MESSAGE = "Invalid or expired promo code"


class PromoCodeService:
    def __init__(self, db: Session) -> None:
        self.repo = PromoCodeRepository(db)

    def validate(self, payload: ValidatePromoCodeRequest, user: User) -> ValidatePromoCodeResponse:
        code = payload.code.strip().upper()
        if not code:
            return ValidatePromoCodeResponse(
                success=True,
                valid=False,
                code=code,
                discountPercent=None,
                message=_INVALID_MESSAGE,
            )

        promo = self.repo.get_by_code(code)
        if not promo or not self._is_usable(promo, user.id):
            return ValidatePromoCodeResponse(
                success=True,
                valid=False,
                code=code,
                discountPercent=None,
                message=_INVALID_MESSAGE,
            )

        return ValidatePromoCodeResponse(
            success=True,
            valid=True,
            code=promo.code,
            discountPercent=promo.discount_percent,
            message="Promo code applied",
        )

    def record_redemption(self, *, user_id: UUID, promo_code_id: UUID) -> PromoCodeRedemption:
        """Record usage after subscription purchase is verified (call from future IAP verify)."""
        redemption = self.repo.create_redemption(promo_code_id=promo_code_id, user_id=user_id)
        self.repo.save()
        return redemption

    def _is_usable(self, promo: PromoCode, user_id: UUID) -> bool:
        now = datetime.now(timezone.utc)

        if not promo.is_active:
            return False
        if promo.starts_at is not None and promo.starts_at > now:
            return False
        if promo.expires_at is not None and promo.expires_at < now:
            return False
        if promo.max_redemptions is not None:
            if self.repo.count_redemptions(promo.id) >= promo.max_redemptions:
                return False
        if promo.max_redemptions_per_user is not None:
            if self.repo.count_user_redemptions(promo.id, user_id) >= promo.max_redemptions_per_user:
                return False
        return True

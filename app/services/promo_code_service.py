from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.enums import DiscountType
from app.models.user import User
from app.models.voucher import VoucherRedemption
from app.repositories.voucher_repository import VoucherRepository
from app.schemas.promo_codes import ValidatePromoCodeRequest, ValidatePromoCodeResponse

_INVALID_MESSAGE = "Invalid or expired promo code"


class PromoCodeService:
    def __init__(self, db: Session) -> None:
        self.repo = VoucherRepository(db)

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

        voucher = self.repo.get_by_code(code)
        if not voucher or not self._is_usable(voucher, user.id):
            return ValidatePromoCodeResponse(
                success=True,
                valid=False,
                code=code,
                discountPercent=None,
                message=_INVALID_MESSAGE,
            )

        discount_percent = None
        if voucher.discount_type == DiscountType.PERCENTAGE:
            discount_percent = int(voucher.discount_value)

        return ValidatePromoCodeResponse(
            success=True,
            valid=True,
            code=voucher.code,
            discountPercent=discount_percent,
            message="Promo code applied",
        )

    def record_redemption(self, *, user_id: UUID, voucher_id: UUID) -> VoucherRedemption:
        """Record usage after subscription purchase is verified (call from future IAP verify)."""
        redemption = self.repo.create_redemption(voucher_id=voucher_id, user_id=user_id)
        self.repo.save()
        return redemption

    def _is_usable(self, voucher, user_id: UUID) -> bool:
        now = datetime.now(timezone.utc)

        if not voucher.active:
            return False
        if voucher.valid_from is not None and voucher.valid_from > now:
            return False
        if voucher.valid_until is not None and voucher.valid_until < now:
            return False
        if voucher.max_redemptions is not None:
            if self.repo.count_redemptions(voucher.id) >= voucher.max_redemptions:
                return False
        if voucher.max_redemptions_per_user is not None:
            if self.repo.count_user_redemptions(voucher.id, user_id) >= voucher.max_redemptions_per_user:
                return False
        return True

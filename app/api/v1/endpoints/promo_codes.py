from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.promo_codes import ValidatePromoCodeRequest, ValidatePromoCodeResponse
from app.services.promo_code_service import PromoCodeService

router = APIRouter(prefix="/promo-code", tags=["promo-code"])


@router.post(
    "/validate",
    response_model=ValidatePromoCodeResponse,
    response_model_by_alias=True,
)
def validate_promo_code(
    payload: ValidatePromoCodeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ValidatePromoCodeResponse:
    return PromoCodeService(db).validate(payload, current_user)

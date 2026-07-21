from fastapi import APIRouter

from app.schemas.plans import PlansResponse
from app.services.plan_service import get_plans

router = APIRouter(prefix="/plans", tags=["plans"])


@router.get(
    "",
    response_model=PlansResponse,
    response_model_by_alias=True,
)
def list_plans() -> PlansResponse:
    return get_plans()

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.plans import PlansResponse
from app.services.plan_service import get_plans

router = APIRouter(prefix="/plans", tags=["plans"])


@router.get(
    "",
    response_model=PlansResponse,
    response_model_by_alias=True,
)
def list_plans(db: Session = Depends(get_db)) -> PlansResponse:
    return get_plans(db)

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import authorize_child_access, get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.whirlpool_island import (
    CompleteActivityRequest,
    CompleteActivityResponse,
    CompleteIslandRequest,
    CompleteIslandResponse,
    WhirlpoolIslandDetailsResponse,
)
from app.services.whirlpool_island_service import WhirlpoolIslandService

router = APIRouter(prefix="/children", tags=["whirlpool-island"])


def _parse_child_id(child_id: str) -> UUID:
    try:
        return UUID(child_id)
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "message": "Invalid child id"},
        ) from exc


@router.get(
    "/{child_id}/whirlpool-island",
    response_model=WhirlpoolIslandDetailsResponse,
    response_model_by_alias=True,
)
def get_whirlpool_island(
    child_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WhirlpoolIslandDetailsResponse:
    child = authorize_child_access(_parse_child_id(child_id), current_user, db)
    return WhirlpoolIslandService(db).get_details(child)


@router.post(
    "/{child_id}/whirlpool-island/activities/{activity_id}/complete",
    response_model=CompleteActivityResponse,
    response_model_by_alias=True,
)
def complete_whirlpool_activity(
    child_id: str,
    activity_id: str,
    payload: CompleteActivityRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompleteActivityResponse:
    child = authorize_child_access(_parse_child_id(child_id), current_user, db)
    return WhirlpoolIslandService(db).complete_activity(child, activity_id, payload)


@router.post(
    "/{child_id}/whirlpool-island/complete",
    response_model=CompleteIslandResponse,
    response_model_by_alias=True,
)
def complete_whirlpool_island(
    child_id: str,
    payload: CompleteIslandRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompleteIslandResponse:
    child = authorize_child_access(_parse_child_id(child_id), current_user, db)
    return WhirlpoolIslandService(db).complete_island(child, payload)

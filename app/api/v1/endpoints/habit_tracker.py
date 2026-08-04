from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import authorize_child_access, get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.habit_tracker import (
    CompleteHabitRequest,
    CompleteHabitResponse,
    HabitTrackerDetailsResponse,
)
from app.services.habit_tracker_service import HabitTrackerService

router = APIRouter(prefix="/children", tags=["habit-tracker"])


def _parse_child_id(child_id: str) -> UUID:
    try:
        return UUID(child_id)
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "message": "Invalid child id"},
        ) from exc


@router.get(
    "/{child_id}/habit-tracker",
    response_model=HabitTrackerDetailsResponse,
    response_model_by_alias=True,
)
def get_habit_tracker(
    child_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HabitTrackerDetailsResponse:
    child = authorize_child_access(_parse_child_id(child_id), current_user, db)
    return HabitTrackerService(db).get_details(child)


@router.post(
    "/{child_id}/habit-tracker/complete",
    response_model=CompleteHabitResponse,
    response_model_by_alias=True,
)
def complete_habit(
    child_id: str,
    payload: CompleteHabitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompleteHabitResponse:
    child = authorize_child_access(_parse_child_id(child_id), current_user, db)
    return HabitTrackerService(db).complete_habit(child, payload)

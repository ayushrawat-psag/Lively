from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import authorize_child_access, get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.fridge_inventory import (
    ConsumeFridgeRequest,
    ConsumeFridgeResponse,
    FridgeInventoryAllResponse,
    FridgeInventoryOneResponse,
)
from app.services.fridge_inventory_service import FridgeInventoryService

router = APIRouter(prefix="/children", tags=["fridge-inventory"])


def _parse_child_id(child_id: str) -> UUID:
    try:
        return UUID(child_id)
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "message": "Invalid child id"},
        ) from exc


@router.get(
    "/{child_id}/fridge-inventory",
    response_model=FridgeInventoryAllResponse,
    response_model_by_alias=True,
)
def get_fridge_inventory(
    child_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FridgeInventoryAllResponse:
    child = authorize_child_access(_parse_child_id(child_id), current_user, db)
    return FridgeInventoryService(db).get_all(child)


@router.get(
    "/{child_id}/fridge-inventory/habits/{habit_id}",
    response_model=FridgeInventoryOneResponse,
    response_model_by_alias=True,
)
def get_fridge_inventory_for_habit(
    child_id: str,
    habit_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FridgeInventoryOneResponse:
    child = authorize_child_access(_parse_child_id(child_id), current_user, db)
    return FridgeInventoryService(db).get_one(child, habit_id)


@router.patch(
    "/{child_id}/fridge-inventory/habits/{habit_id}/consume",
    response_model=ConsumeFridgeResponse,
    response_model_by_alias=True,
)
def consume_fridge_inventory(
    child_id: str,
    habit_id: str,
    payload: ConsumeFridgeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConsumeFridgeResponse:
    child = authorize_child_access(_parse_child_id(child_id), current_user, db)
    return FridgeInventoryService(db).consume(child, habit_id, payload)

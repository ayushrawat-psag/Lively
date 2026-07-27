from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import authorize_child_access, get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.children import (
    ChildAppStateUpdateResponse,
    ChildDetailResponse,
    ChildrenListResponse,
    ChildUpdateResponse,
    CreateChildRequest,
    CreateChildResponse,
    DeleteChildResponse,
    UpdateChildAppStateRequest,
    UpdateChildRequest,
)
from app.services.child_service import ChildService

router = APIRouter(prefix="/children", tags=["children"])


def _parse_child_id(child_id: str) -> UUID:
    try:
        return UUID(child_id)
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "message": "Invalid child id"},
        ) from exc


@router.post(
    "",
    response_model=CreateChildResponse,
    response_model_by_alias=True,
    status_code=201,
)
def create_child(
    payload: CreateChildRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CreateChildResponse:
    return ChildService(db).create(current_user, payload)


@router.get(
    "",
    response_model=ChildrenListResponse,
    response_model_by_alias=True,
)
def list_children(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChildrenListResponse:
    return ChildService(db).list_children(current_user)


@router.get(
    "/{child_id}",
    response_model=ChildDetailResponse,
    response_model_by_alias=True,
)
def get_child(
    child_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChildDetailResponse:
    return ChildService(db).get_child(current_user, _parse_child_id(child_id))


@router.patch(
    "/{child_id}",
    response_model=ChildUpdateResponse,
    response_model_by_alias=True,
)
def update_child(
    child_id: str,
    payload: UpdateChildRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChildUpdateResponse:
    return ChildService(db).update_child(current_user, _parse_child_id(child_id), payload)


@router.patch(
    "/{child_id}/app-state",
    response_model=ChildAppStateUpdateResponse,
    response_model_by_alias=True,
)
def update_child_app_state(
    child_id: str,
    payload: UpdateChildAppStateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChildAppStateUpdateResponse:
    parsed_child_id = _parse_child_id(child_id)
    child = authorize_child_access(parsed_child_id, current_user, db)
    return ChildService(db).update_app_state(child, payload)


@router.delete(
    "/{child_id}",
    response_model=DeleteChildResponse,
    response_model_by_alias=True,
)
def delete_child(
    child_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DeleteChildResponse:
    return ChildService(db).delete_child(current_user, _parse_child_id(child_id))

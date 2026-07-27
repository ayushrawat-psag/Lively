from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.enums import UserStatus, UserType
from app.models.user import User
from app.repositories.child_repository import ChildRepository
from app.repositories.family_repository import FamilyRepository
from app.schemas.children import (
    ChildAppStateUpdateResponse,
    ChildCreatedPublic,
    ChildDetailPublic,
    ChildDetailResponse,
    ChildProgress,
    ChildPublic,
    ChildrenListResponse,
    ChildUpdateResponse,
    CreateChildRequest,
    CreateChildResponse,
    DeleteChildResponse,
    UpdateChildAppStateRequest,
    UpdateChildRequest,
)
from app.services.plan_service import get_plans


def _split_name(name: str) -> tuple[str, str]:
    parts = name.strip().split(None, 1)
    if not parts:
        return "Child", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[1]


def _base_public(child: User) -> dict:
    return {
        "id": child.id,
        "name": child.display_name,
        "dateOfBirth": child.date_of_birth,
        "gender": child.gender or "",
        "devices": list(child.devices or []),
        "onBoarding": child.onboarding,
        "childAppTour": child.child_app_tour,
    }


def child_to_public(child: User) -> ChildPublic:
    return ChildPublic(**_base_public(child))


class ChildService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = ChildRepository(db)
        self.family_repo = FamilyRepository(db)

    def _max_children(self) -> int:
        return max(plan.max_children for plan in get_plans(self.db).plans)

    def create(self, parent: User, payload: CreateChildRequest) -> CreateChildResponse:
        active_count = self.repo.count_active_for_parent(parent.id)
        max_children = self._max_children()
        if active_count >= max_children:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "message": f"Maximum of {max_children} children allowed",
                },
            )

        family = self.family_repo.ensure_for_parent(parent.id)
        if parent.family_id is None:
            parent.family_id = family.id
            self.family_repo.flush()

        first_name, last_name = _split_name(payload.name)
        child = User(
            user_type=UserType.CHILD,
            first_name=first_name,
            last_name=last_name,
            date_of_birth=payload.date_of_birth,
            gender=payload.gender,
            devices=payload.devices,
            pin_hash=hash_password(payload.pin),
            onboarding=False,
            child_app_tour=False,
            is_child=True,
            family_id=family.id,
            status=UserStatus.ACTIVE,
        )
        self.repo.create(child)
        self.repo.save()
        self.repo.refresh(child)

        return CreateChildResponse(
            success=True,
            message="Child created successfully",
            child=ChildCreatedPublic(**_base_public(child), pin=payload.pin),
        )

    def list_children(self, parent: User) -> ChildrenListResponse:
        children = self.repo.list_active_for_parent(parent.id)
        if not children:
            return ChildrenListResponse(
                success=True,
                message="No children found",
                children=[],
            )
        return ChildrenListResponse(
            success=True,
            message="Children fetched successfully",
            children=[ChildPublic(**_base_public(c)) for c in children],
        )

    def get_child(self, parent: User, child_id: UUID) -> ChildDetailResponse:
        child = self.repo.get_active_for_parent(child_id=child_id, parent_user_id=parent.id)
        if not child:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"success": False, "message": "Child not found"},
            )
        return ChildDetailResponse(
            success=True,
            message="Child fetched successfully",
            child=ChildDetailPublic(
                **_base_public(child),
                progress=ChildProgress(completedActivities=0, currentLevel=None),
            ),
        )

    def update_child(
        self,
        parent: User,
        child_id: UUID,
        payload: UpdateChildRequest,
    ) -> ChildUpdateResponse:
        child = self.repo.get_active_for_parent(child_id=child_id, parent_user_id=parent.id)
        if not child:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"success": False, "message": "Child not found"},
            )

        data = payload.model_dump(exclude_unset=True)
        if "name" in data and data["name"] is not None:
            first_name, last_name = _split_name(data["name"])
            child.first_name = first_name
            child.last_name = last_name
        if "date_of_birth" in data and data["date_of_birth"] is not None:
            child.date_of_birth = data["date_of_birth"]
        if "gender" in data and data["gender"] is not None:
            child.gender = data["gender"]
        if "devices" in data and data["devices"] is not None:
            child.devices = data["devices"]
        if "pin" in data and data["pin"] is not None:
            child.pin_hash = hash_password(data["pin"])

        self.repo.save()
        self.repo.refresh(child)

        return ChildUpdateResponse(
            success=True,
            message="Child updated successfully",
            child=ChildPublic(**_base_public(child)),
        )

    def update_app_state(
        self,
        child: User,
        payload: UpdateChildAppStateRequest,
    ) -> ChildAppStateUpdateResponse:
        if payload.onboarding is not None:
            child.onboarding = payload.onboarding
        if payload.child_app_tour is not None:
            child.child_app_tour = payload.child_app_tour

        self.repo.save()
        self.repo.refresh(child)

        return ChildAppStateUpdateResponse(
            success=True,
            message="Child app state updated successfully",
            child=ChildPublic(**_base_public(child)),
        )

    def delete_child(self, parent: User, child_id: UUID) -> DeleteChildResponse:
        child = self.repo.get_active_for_parent(child_id=child_id, parent_user_id=parent.id)
        if not child:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"success": False, "message": "Child not found"},
            )

        self.repo.soft_delete(child)
        self.repo.save()

        return DeleteChildResponse(
            success=True,
            message="Child removed successfully",
            childId=child.id,
        )

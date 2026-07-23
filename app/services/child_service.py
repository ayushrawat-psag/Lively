from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.child import Child
from app.models.user import User
from app.repositories.child_repository import ChildRepository
from app.schemas.children import (
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
    UpdateChildRequest,
)
from app.services.plan_service import get_plans

MAX_CHILDREN = max(plan.max_children for plan in get_plans().plans)


def _base_public(child: Child) -> dict:
    return {
        "id": child.id,
        "name": child.name,
        "dateOfBirth": child.date_of_birth,
        "gender": child.gender,
        "devices": list(child.devices or []),
        "onBoarding": child.onboarding,
    }


def child_to_public(child: Child) -> ChildPublic:
    return ChildPublic(**_base_public(child))


class ChildService:
    def __init__(self, db: Session) -> None:
        self.repo = ChildRepository(db)

    def create(self, parent: User, payload: CreateChildRequest) -> CreateChildResponse:
        active_count = self.repo.count_active_for_parent(parent.id)
        if active_count >= MAX_CHILDREN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "message": f"Maximum of {MAX_CHILDREN} children allowed",
                },
            )

        child = Child(
            parent_user_id=parent.id,
            name=payload.name,
            date_of_birth=payload.date_of_birth,
            gender=payload.gender,
            devices=payload.devices,
            pin_hash=hash_password(payload.pin),
            onboarding=False,
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
            child.name = data["name"]
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

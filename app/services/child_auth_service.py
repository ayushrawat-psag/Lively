from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token, verify_password
from app.models.user import UserStatus
from app.repositories.auth_repository import AuthRepository
from app.repositories.child_repository import ChildRepository
from app.schemas.auth import user_to_public
from app.schemas.child_auth import (
    ChildLoginRequest,
    ChildLoginResponse,
    VerifyInviteCodeRequest,
    VerifyInviteCodeResponse,
)
from app.services.child_service import child_to_public


class ChildAuthService:
    def __init__(self, db: Session) -> None:
        self.auth_repo = AuthRepository(db)
        self.child_repo = ChildRepository(db)

    def verify_invite_code(self, payload: VerifyInviteCodeRequest) -> VerifyInviteCodeResponse:
        code = payload.invite_code.strip().upper()
        if not code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"success": False, "message": "Invite code is required"},
            )

        parent = self.auth_repo.get_user_by_invite_code(code)
        if not parent or not parent.email_verified or parent.status != UserStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"success": False, "message": "Invalid invite code"},
            )

        children = self.child_repo.list_active_for_parent(parent.id)

        return VerifyInviteCodeResponse(
            success=True,
            message="Invite code verified",
            requiresPin=True,
            user=user_to_public(parent),
            children=[child_to_public(child) for child in children],
            subscription=None,
        )

    def child_login(self, payload: ChildLoginRequest) -> ChildLoginResponse:
        if not payload.pin.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"success": False, "message": "PIN code is required"},
            )

        try:
            child_id = UUID(payload.child_id.strip())
        except (ValueError, TypeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"success": False, "message": "Invalid child id"},
            ) from exc

        child = self.child_repo.get_active_by_id(child_id)
        if not child:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"success": False, "message": "Child not found"},
            )

        if not child.pin_hash or not verify_password(payload.pin, child.pin_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"success": False, "message": "Invalid PIN code"},
            )

        token = create_access_token(
            subject=child.id,
            extra_claims={
                "actor": "child",
                "parentUserId": str(child.parent_user_id),
                "user_type": "Child",
            },
        )

        return ChildLoginResponse(
            success=True,
            message="Child login successful",
            token=token,
            child=child_to_public(child),
        )

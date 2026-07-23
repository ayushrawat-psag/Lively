from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.auth import SubscriptionPublic, UserPublic
from app.schemas.children import ChildPublic


class VerifyInviteCodeRequest(BaseModel):
    invite_code: str = Field(..., alias="inviteCode", min_length=1)

    model_config = {"populate_by_name": True}


class VerifyInviteCodeResponse(BaseModel):
    success: bool
    message: str
    requires_pin: bool = Field(..., alias="requiresPin")
    user: UserPublic
    children: list[ChildPublic]
    subscription: SubscriptionPublic | None = None

    model_config = {"populate_by_name": True}


class ChildLoginRequest(BaseModel):
    child_id: str = Field(..., alias="childId", min_length=1)
    pin: str = Field(..., min_length=1)

    model_config = {"populate_by_name": True}


class ChildLoginResponse(BaseModel):
    success: bool
    message: str
    token: str
    child: ChildPublic

    model_config = {"populate_by_name": True}

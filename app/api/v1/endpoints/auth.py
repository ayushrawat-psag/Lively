from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RegenerateInviteCodeResponse,
    ResendVerificationRequest,
    ResendVerificationResponse,
    SignupRequest,
    SignupResponse,
    VerifyEmailRequest,
    VerifyEmailResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/signup",
    response_model=SignupResponse,
    response_model_by_alias=True,
    status_code=201,
)
def signup(payload: SignupRequest, db: Session = Depends(get_db)) -> SignupResponse:
    return AuthService(db).signup(payload)


@router.post(
    "/login",
    response_model=LoginResponse,
    response_model_by_alias=True,
)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    return AuthService(db).login(payload)


@router.post(
    "/email/verify",
    response_model=VerifyEmailResponse,
    response_model_by_alias=True,
)
def verify_email(payload: VerifyEmailRequest, db: Session = Depends(get_db)) -> VerifyEmailResponse:
    return AuthService(db).verify_email(payload)


@router.post(
    "/email/resend",
    response_model=ResendVerificationResponse,
    response_model_by_alias=True,
)
def resend_verification(
    payload: ResendVerificationRequest,
    db: Session = Depends(get_db),
) -> ResendVerificationResponse:
    return AuthService(db).resend_verification(payload)


@router.post(
    "/invite-code/regenerate",
    response_model=RegenerateInviteCodeResponse,
    response_model_by_alias=True,
)
def regenerate_invite_code(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RegenerateInviteCodeResponse:
    return AuthService(db).regenerate_invite_code(current_user)

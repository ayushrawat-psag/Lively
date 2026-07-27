import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.invite_code import generate_invite_code
from app.core.security import create_access_token, hash_password, verify_password
from app.models.email_verification import EmailVerificationCode
from app.models.enums import AgeCohort, UserStatus, UserType
from app.models.user import User
from app.repositories.auth_repository import AuthRepository
from app.repositories.child_repository import ChildRepository
from app.schemas.auth import (
    ChildPublic,
    LoginRequest,
    LoginResponse,
    RegenerateInviteCodeResponse,
    ResendVerificationRequest,
    ResendVerificationResponse,
    SignupRequest,
    SignupResponse,
    VerifyEmailRequest,
    VerifyEmailResponse,
    split_full_name,
    user_to_public,
)
from app.services.email_service import EmailSendError, EmailService

logger = logging.getLogger(__name__)

_INVITE_CODE_MAX_ATTEMPTS = 5


class AuthService:
    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.repo = AuthRepository(db)
        self.settings = settings or get_settings()
        self.email_service = EmailService(self.settings)

    def signup(self, payload: SignupRequest) -> SignupResponse:
        email = payload.email.lower()
        existing = self.repo.get_user_by_email(email)
        if existing:
            if existing.email_verified:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "success": False,
                        "message": "Email already exists",
                        "emailExists": True,
                    },
                )
            return self._resume_unverified_signup(existing, payload)

        first_name, last_name = split_full_name(payload.name)
        if not first_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"success": False, "message": "Name is required"},
            )
        if not last_name:
            last_name = first_name

        user = User(
            user_type=UserType.PARENT if payload.guardian else UserType.GUARDIAN,
            first_name=first_name,
            last_name=last_name,
            email=email,
            password_hash=hash_password(payload.password),
            age_cohort=AgeCohort.ADULT,
            is_child=False,
            status=UserStatus.ACTIVE,
            email_verified=False,
            accepted_terms=payload.accepted_terms,
        )
        self.repo.create_user(user)
        return self._complete_signup(user)

    def _resume_unverified_signup(self, user: User, payload: SignupRequest) -> SignupResponse:
        first_name, last_name = split_full_name(payload.name)
        if not first_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"success": False, "message": "Name is required"},
            )
        if not last_name:
            last_name = first_name

        user.user_type = UserType.PARENT if payload.guardian else UserType.GUARDIAN
        user.first_name = first_name
        user.last_name = last_name
        user.password_hash = hash_password(payload.password)
        user.accepted_terms = payload.accepted_terms
        self.repo.flush()
        return self._complete_signup(user)

    def _complete_signup(self, user: User) -> SignupResponse:
        code = self._create_verification_code(user)
        self.repo.save()
        self.repo.refresh(user)

        email_sent = self._send_verification_email(user=user, code=code)
        if email_sent:
            message = "Signup successful. Verification email sent."
        else:
            message = (
                "Signup successful. Verification email could not be sent; use resend if needed."
            )

        return SignupResponse(
            success=True,
            message=message,
            emailExists=False,
            emailVerificationRequired=True,
            user=user_to_public(user),
            verificationCode=code if self.settings.include_verification_code_in_response else None,
        )

    def login(self, payload: LoginRequest) -> LoginResponse:
        email = payload.email.lower()
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"success": False, "message": "Email is required"},
            )
        if not payload.password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"success": False, "message": "Password is required"},
            )

        user = self.repo.get_user_by_email(email)
        if not user or not user.password_hash or not verify_password(payload.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"success": False, "message": "Invalid credentials"},
            )

        if not user.email_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "success": False,
                    "message": "Please verify your email before continuing",
                    "emailVerified": False,
                },
            )

        if not user.invite_code:
            self._assign_unique_invite_code(user)

        self.repo.update_last_login(user)
        self.repo.save()
        self.repo.refresh(user)

        token = self._create_access_token(user)

        return LoginResponse(
            success=True,
            message="Login successful",
            token=token,
            user=user_to_public(user),
            children=self._children_for_parent(user),
            subscription=None,
        )

    def verify_email(self, payload: VerifyEmailRequest) -> VerifyEmailResponse:
        email = payload.email.lower().strip()
        code = payload.code.strip()
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"success": False, "message": "Email is required"},
            )
        if not code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"success": False, "message": "Code is required"},
            )

        user = self.repo.get_user_by_email(email)
        if not user:
            # Same message as bad code to avoid confirming whether the email exists.
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"success": False, "message": "Invalid or expired verification code"},
            )

        verification = self.repo.get_active_code(user_id=user.id, code=code)
        if not verification:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"success": False, "message": "Invalid or expired verification code"},
            )

        self.repo.mark_code_used(verification)
        self.repo.mark_email_verified(user)
        self.repo.invalidate_active_codes(user.id)
        if not user.invite_code:
            self._assign_unique_invite_code(user)
        self.repo.update_last_login(user)
        self.repo.save()
        self.repo.refresh(user)

        token = self._create_access_token(user)

        return VerifyEmailResponse(
            success=True,
            message="Email verified successfully",
            code=code,
            token=token,
            user=user_to_public(user),
            children=[],
        )

    def regenerate_invite_code(self, user: User) -> RegenerateInviteCodeResponse:
        if not user.email_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"success": False, "message": "Please verify your email before continuing"},
            )

        self._assign_unique_invite_code(user, force=True)
        self.repo.save()
        self.repo.refresh(user)

        return RegenerateInviteCodeResponse(
            success=True,
            message="Invite code regenerated",
            inviteCode=user.invite_code or "",
        )

    def resend_verification(self, payload: ResendVerificationRequest) -> ResendVerificationResponse:
        email = payload.email.lower()
        user = self.repo.get_user_by_email(email)
        if not user:
            # Avoid email enumeration; still return success-style message for MVP contract.
            return ResendVerificationResponse(
                success=True,
                message="Verification email resent",
            )

        if user.email_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"success": False, "message": "Email is already verified"},
            )

        code = self._create_verification_code(user)
        self.repo.save()
        email_sent = self._send_verification_email(user=user, code=code)
        if email_sent:
            message = "Verification email resent"
        else:
            message = "Verification code updated. Email could not be sent; try again later."

        return ResendVerificationResponse(
            success=True,
            message=message,
            verificationCode=code if self.settings.include_verification_code_in_response else None,
        )

    def _send_verification_email(self, *, user: User, code: str) -> bool:
        if not self.email_service.is_configured:
            logger.info(
                "Campaign Monitor not configured — verification code for %s: %s",
                user.email,
                code,
            )
            return True
        try:
            self.email_service.send_verification_email(
                to_email=user.email or "",
                to_name=user.full_name,
                code=code,
            )
            return True
        except EmailSendError:
            logger.warning(
                "Failed to send verification email to %s; user can resend",
                user.email,
            )
            return False

    def _create_verification_code(self, user: User) -> str:
        self.repo.invalidate_active_codes(user.id)
        code = self._generate_code()
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=self.settings.verification_code_expire_minutes
        )
        verification = EmailVerificationCode(
            user=user,
            email=user.email or "",
            code=code,
            expires_at=expires_at,
            is_used=False,
        )
        self.repo.create_verification_code(verification)
        return code

    def _generate_code(self) -> str:
        length = self.settings.verification_code_length
        upper = 10**length
        return str(secrets.randbelow(upper)).zfill(length)

    def _assign_unique_invite_code(self, user: User, *, force: bool = False) -> None:
        if user.invite_code and not force:
            return

        for _ in range(_INVITE_CODE_MAX_ATTEMPTS):
            code = generate_invite_code()
            try:
                # Savepoint so a unique collision does not abort the outer transaction
                # (e.g. email verification already applied in the same request).
                with self.repo.db.begin_nested():
                    self.repo.set_invite_code(user, code)
                return
            except IntegrityError:
                continue

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"success": False, "message": "Failed to generate a unique invite code"},
        )

    def _children_for_parent(self, user: User) -> list[ChildPublic]:
        children = ChildRepository(self.repo.db).list_active_for_parent(user.id)
        return [self._child_to_public(child) for child in children]

    @staticmethod
    def _child_to_public(child: User) -> ChildPublic:
        name = child.display_name
        initial = name[0].upper() if name else ""
        return ChildPublic(id=child.id, name=name, initial=initial)

    def _create_access_token(self, user: User) -> str:
        return create_access_token(
            subject=user.id,
            extra_claims={"email": user.email, "user_type": user.user_type.value},
        )

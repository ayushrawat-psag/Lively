import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models.email_verification import EmailVerificationCode
from app.models.user import AgeCohort, User, UserStatus, UserType
from app.repositories.auth_repository import AuthRepository
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
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


class AuthService:
    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.repo = AuthRepository(db)
        self.settings = settings or get_settings()
        self.email_service = EmailService(self.settings)

    def signup(self, payload: SignupRequest) -> SignupResponse:
        email = payload.email.lower()
        existing = self.repo.get_user_by_email(email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "success": False,
                    "message": "Email already exists",
                    "emailExists": True,
                },
            )

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
        code = self._create_verification_code(user)
        self.repo.save()
        self.repo.refresh(user)

        self._send_verification_email(user=user, code=code)

        response = SignupResponse(
            success=True,
            message="Signup successful. Verification email sent.",
            emailExists=False,
            emailVerificationRequired=True,
            user=user_to_public(user),
            verificationCode=code if self.settings.include_verification_code_in_response else None,
        )
        return response

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

        self.repo.update_last_login(user)
        self.repo.save()

        token = create_access_token(
            subject=user.id,
            extra_claims={"email": user.email, "user_type": user.user_type.value},
        )

        return LoginResponse(
            success=True,
            message="Login successful",
            token=token,
            user=user_to_public(user),
            children=[],
        )

    def verify_email(self, payload: VerifyEmailRequest) -> VerifyEmailResponse:
        if not payload.code or not payload.code.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"success": False, "message": "Code is required"},
            )

        verification = self.repo.get_active_code(payload.code.strip())
        if not verification:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"success": False, "message": "Invalid or expired verification code"},
            )

        user = self.repo.get_user_by_id(verification.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"success": False, "message": "Invalid or expired verification code"},
            )

        self.repo.mark_code_used(verification)
        self.repo.mark_email_verified(user)
        self.repo.invalidate_active_codes(user.id)
        self.repo.save()
        self.repo.refresh(user)

        return VerifyEmailResponse(
            success=True,
            message="Email verified successfully",
            code=payload.code.strip(),
            user=user_to_public(user),
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
        self._send_verification_email(user=user, code=code)

        return ResendVerificationResponse(
            success=True,
            message="Verification email resent",
            verificationCode=code if self.settings.include_verification_code_in_response else None,
        )

    def _send_verification_email(self, *, user: User, code: str) -> None:
        if not self.email_service.is_configured:
            logger.info(
                "Brevo not configured — verification code for %s: %s",
                user.email,
                code,
            )
        try:
            self.email_service.send_verification_email(
                to_email=user.email or "",
                to_name=user.full_name,
                code=code,
            )
        except EmailSendError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "success": False,
                    "message": "Account created but failed to send verification email. Please try resend.",
                },
            ) from exc

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

from app.core.security import create_access_token, decode_access_token, hash_password, verify_password
from app.schemas.auth import split_full_name


def test_hash_and_verify_password() -> None:
    hashed = hash_password("Demo@123")
    assert hashed != "Demo@123"
    assert verify_password("Demo@123", hashed) is True
    assert verify_password("WrongPass", hashed) is False


def test_create_and_decode_access_token() -> None:
    token = create_access_token(subject="user-123", extra_claims={"email": "a@example.com"})
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "user-123"
    assert payload["email"] == "a@example.com"


def test_decode_invalid_token_returns_none() -> None:
    assert decode_access_token("not-a-real-token") is None


def test_split_full_name() -> None:
    assert split_full_name("John Doe") == ("John", "Doe")
    assert split_full_name("Madonna") == ("Madonna", "")
    assert split_full_name("  Ada   Lovelace  ") == ("Ada", "Lovelace")

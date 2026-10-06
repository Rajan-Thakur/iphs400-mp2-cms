"""Password hashing, signed sessions, and CSRF tokens.

Sessions are a signed cookie (itsdangerous): the cookie holds the user's id,
signed so it can't be forged or edited client-side, with no server-side
session store. CSRF uses the double-submit pattern with the same signer: a
random token is set as a signed cookie and echoed back in the form; a POST
is rejected unless the submitted value matches what the cookie's signature
verifies to.
"""
from __future__ import annotations

import hmac
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app import settings

SESSION_COOKIE = "session"
CSRF_COOKIE = "csrf_token_signed"
SESSION_MAX_AGE = 60 * 60 * 8  # 8 hours

_hasher = PasswordHasher()
_session_signer = URLSafeTimedSerializer(settings.SECRET_KEY, salt="session")
_csrf_signer = URLSafeTimedSerializer(settings.SECRET_KEY, salt="csrf")


def hash_password(raw: str) -> str:
    return _hasher.hash(raw)


def verify_password(raw: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, raw)
    except (VerifyMismatchError, VerificationError):
        return False


def sign_session(user_id: int) -> str:
    return _session_signer.dumps({"uid": user_id})


def read_session(token: str | None) -> int | None:
    if not token:
        return None
    try:
        data = _session_signer.loads(token, max_age=SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None
    return data.get("uid")


def new_csrf_pair() -> tuple[str, str]:
    """Return (raw_token_for_the_form, signed_token_for_the_cookie)."""
    raw = secrets.token_urlsafe(32)
    return raw, _csrf_signer.dumps(raw)


def verify_csrf(form_token: str | None, signed_cookie: str | None) -> bool:
    if not form_token or not signed_cookie:
        return False
    try:
        raw = _csrf_signer.loads(signed_cookie, max_age=SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return False
    return hmac.compare_digest(raw, form_token)


def read_or_mint_csrf(request) -> tuple[str, str | None]:
    """Reuse the request's existing valid CSRF cookie if it has one, so a
    second page load doesn't invalidate a token already embedded in a page
    the user still has open. Returns (raw_token_for_the_form,
    new_signed_cookie_value_or_None) — the caller only needs to call
    response.set_cookie(...) when the second element isn't None."""
    existing_signed = request.cookies.get(CSRF_COOKIE)
    if existing_signed:
        try:
            return _csrf_signer.loads(existing_signed, max_age=SESSION_MAX_AGE), None
        except (BadSignature, SignatureExpired):
            pass
    raw, signed = new_csrf_pair()
    return raw, signed

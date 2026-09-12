"""Staff password, session cookie, and login rate limiting (spec 10)."""
import secrets
import time
from collections import defaultdict

from fastapi import Depends, HTTPException, Request, Response, status
from itsdangerous import BadSignature, URLSafeTimedSerializer

from app.config import Settings, get_settings

SESSION_COOKIE = "nextable_session"
SESSION_VALUE = "host"
SESSION_MAX_AGE_SECONDS = 12 * 60 * 60


def _serializer(settings: Settings) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.session_secret, salt="nextable-session")


def password_matches(candidate: str, settings: Settings) -> bool:
    """Constant time, so a wrong password cannot be found one character at a time."""
    return secrets.compare_digest(candidate.encode(), settings.staff_password.encode())


def open_session(response: Response, settings: Settings) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        _serializer(settings).dumps(SESSION_VALUE),
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
        secure=False,  # The prototype runs over http; stage 4 turns this on.
        path="/",
    )


def close_session(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")


def has_valid_session(request: Request, settings: Settings) -> bool:
    raw = request.cookies.get(SESSION_COOKIE)
    if not raw:
        return False
    try:
        value = _serializer(settings).loads(raw, max_age=SESSION_MAX_AGE_SECONDS)
    except BadSignature:
        return False
    return value == SESSION_VALUE


def require_session(
    request: Request, settings: Settings = Depends(get_settings)
) -> None:
    """Every host route depends on this. The guest route never does."""
    if not has_valid_session(request, settings):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sign in to use the host console.",
        )


class LoginRateLimiter:
    """Blunt the guessing of a single shared password."""

    def __init__(self, limit: int, window_seconds: int) -> None:
        self._limit = limit
        self._window = window_seconds
        self._failures: dict[str, list[float]] = defaultdict(list)

    def _recent(self, caller: str, now: float) -> list[float]:
        fresh = [at for at in self._failures[caller] if now - at < self._window]
        self._failures[caller] = fresh
        return fresh

    def is_blocked(self, caller: str, now: float | None = None) -> bool:
        return len(self._recent(caller, now or time.time())) >= self._limit

    def record_failure(self, caller: str, now: float | None = None) -> None:
        self._failures[caller].append(now or time.time())

    def clear(self, caller: str) -> None:
        self._failures.pop(caller, None)

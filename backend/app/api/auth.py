"""Staff sign-in, spec 8.1."""
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.auth import close_session, open_session, password_matches, require_session
from app.config import Settings, get_settings
from app.schemas import LoginRequest, SessionResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _caller(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post("/login", status_code=status.HTTP_204_NO_CONTENT)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    settings: Settings = Depends(get_settings),
) -> None:
    limiter = request.app.state.login_limiter
    caller = _caller(request)

    if limiter.is_blocked(caller):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many sign-in attempts. Wait a few minutes and try again.",
        )

    if not password_matches(payload.password, settings):
        limiter.record_failure(caller)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="That password is not right.",
        )

    limiter.clear(caller)
    open_session(response, settings)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    close_session(response)


@router.get("/me", response_model=SessionResponse, dependencies=[Depends(require_session)])
def me() -> SessionResponse:
    return SessionResponse(signed_in=True)

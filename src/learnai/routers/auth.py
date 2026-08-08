"""Authentication endpoints: Google sign-in, refresh, logout, whoami, and a
dev-bypass login gated by ``settings.dev_auth_bypass``.

Tokens live only in ``HttpOnly``/``SameSite=Lax`` cookies (``Secure`` in
production) — never in a JSON response body, never in ``localStorage`` on
the client side. That's the fix for the old ``Home.js:19``, which read the
Cognito token straight out of ``localStorage``.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel

from learnai.config import Environment, Settings
from learnai.deps import (
    ACCESS_TOKEN_COOKIE,
    REFRESH_TOKEN_COOKIE,
    CurrentUser,
    SessionServiceDep,
    SettingsDep,
    UserRepoDep,
)
from learnai.errors import Forbidden, Unauthenticated
from learnai.services.auth.google_verifier import verify_google_id_token
from learnai.services.auth.session import IssuedTokens

router = APIRouter(prefix="/auth", tags=["auth"])


class GoogleLoginRequest(BaseModel):
    id_token: str


class UserOut(BaseModel):
    id: str
    email: str
    name: str
    picture: str | None


def _user_out(user: dict[str, Any]) -> UserOut:
    return UserOut(
        id=str(user["_id"]), email=user["email"], name=user["name"], picture=user.get("picture")
    )


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _set_session_cookies(response: Response, settings: Settings, tokens: IssuedTokens) -> None:
    secure = settings.environment is Environment.production
    response.set_cookie(
        ACCESS_TOKEN_COOKIE,
        tokens.access_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=settings.access_token_ttl_seconds,
        path="/",
    )
    # Scoped to /auth: the refresh token is only ever sent back to the
    # endpoints that need it (refresh, logout), not on every request.
    response.set_cookie(
        REFRESH_TOKEN_COOKIE,
        tokens.refresh_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=settings.refresh_token_ttl_seconds,
        path="/auth",
    )


def _clear_session_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_TOKEN_COOKIE, path="/")
    response.delete_cookie(REFRESH_TOKEN_COOKIE, path="/auth")


@router.post("/google", response_model=UserOut)
async def login_with_google(
    body: GoogleLoginRequest,
    request: Request,
    response: Response,
    settings: SettingsDep,
    user_repo: UserRepoDep,
    session_service: SessionServiceDep,
) -> UserOut:
    identity = await verify_google_id_token(body.id_token, client_id=settings.google_client_id)
    user = await user_repo.upsert_from_google(
        google_sub=identity.sub,
        email=identity.email,
        email_verified=True,
        name=identity.name,
        picture=identity.picture,
    )
    tokens = await session_service.start_session(
        user_id=user["_id"],
        user_agent=request.headers.get("user-agent"),
        ip=_client_ip(request),
    )
    _set_session_cookies(response, settings, tokens)
    return _user_out(user)


@router.post("/refresh", response_model=UserOut)
async def refresh(
    request: Request,
    response: Response,
    settings: SettingsDep,
    user_repo: UserRepoDep,
    session_service: SessionServiceDep,
) -> UserOut:
    refresh_token = request.cookies.get(REFRESH_TOKEN_COOKIE)
    if refresh_token is None:
        raise Unauthenticated("no refresh token presented")

    tokens = await session_service.rotate(
        refresh_token,
        user_agent=request.headers.get("user-agent"),
        ip=_client_ip(request),
    )
    claims = session_service.verify_access_token(tokens.access_token)
    user = await user_repo.find_by_id(claims.user_id)
    if user is None:
        raise Unauthenticated("user no longer exists")

    _set_session_cookies(response, settings, tokens)
    return _user_out(user)


@router.post("/logout", status_code=204)
async def logout(request: Request, response: Response, session_service: SessionServiceDep) -> None:
    refresh_token = request.cookies.get(REFRESH_TOKEN_COOKIE)
    if refresh_token is not None:
        await session_service.logout(refresh_token)
    _clear_session_cookies(response)


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> UserOut:
    return _user_out(user)


@router.post("/dev-login", response_model=UserOut)
async def dev_login(
    request: Request,
    response: Response,
    settings: SettingsDep,
    user_repo: UserRepoDep,
    session_service: SessionServiceDep,
) -> UserOut:
    """Runs the whole stack with zero cloud accounts. Refused (403) unless
    ``settings.dev_auth_bypass`` is on — and a production settings validator
    refuses to even start the process with that flag set (see config.py)."""
    if not settings.dev_auth_bypass:
        raise Forbidden("dev auth bypass is disabled")

    user = await user_repo.upsert_from_google(
        google_sub="dev-bypass",
        email="dev@localhost",
        email_verified=True,
        name="Dev User",
        picture=None,
    )
    tokens = await session_service.start_session(
        user_id=user["_id"], user_agent=request.headers.get("user-agent"), ip=_client_ip(request)
    )
    _set_session_cookies(response, settings, tokens)
    return _user_out(user)

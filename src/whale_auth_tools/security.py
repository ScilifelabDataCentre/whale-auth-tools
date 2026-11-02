"""Request authentication helpers."""

import secrets
from collections.abc import Callable
from typing import Annotated

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from whale_auth_tools.settings import Settings

bearer_scheme = HTTPBearer(auto_error=False)


def api_token_guard(settings: Settings) -> Callable:
    """Build a dependency that accepts an HTTP Bearer credential only."""

    async def require_api_token(
        credentials: Annotated[
            HTTPAuthorizationCredentials | None, Security(bearer_scheme)
        ],
    ) -> None:
        supplied_token = credentials.credentials if credentials else None
        if not supplied_token or not secrets.compare_digest(supplied_token, settings.api_token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="A valid API token is required.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    return require_api_token

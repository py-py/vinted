from __future__ import annotations

import os
import secrets
from typing import Annotated

from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from fastapi.security import HTTPBasic
from fastapi.security import HTTPBasicCredentials

_security = HTTPBasic()

CredentialsDep = Annotated[HTTPBasicCredentials, Depends(_security)]


def require_auth(credentials: CredentialsDep) -> str:
    """Gate every route behind HTTP Basic auth (ADMIN_USERNAME / ADMIN_PASSWORD).

    Fails closed: if credentials aren't configured the site is unreachable rather
    than wide open. Uses constant-time comparison to avoid leaking length/contents
    via timing.
    """
    admin_username = os.environ.get("ADMIN_USERNAME", "")
    admin_password = os.environ.get("ADMIN_PASSWORD", "")
    if not admin_username or not admin_password:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin auth not configured: set ADMIN_USERNAME and ADMIN_PASSWORD",
        )
    user_ok = secrets.compare_digest(
        credentials.username.encode("utf-8"), admin_username.encode("utf-8")
    )
    pass_ok = secrets.compare_digest(
        credentials.password.encode("utf-8"), admin_password.encode("utf-8")
    )
    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

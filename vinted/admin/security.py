"""HTTP Basic auth for every admin route."""

from __future__ import annotations

import os
import secrets

from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from fastapi.security import HTTPBasic
from fastapi.security import HTTPBasicCredentials

_security = HTTPBasic()


def require_auth(credentials: HTTPBasicCredentials = Depends(_security)) -> str:
    """Gate every route behind HTTP Basic auth (ADMIN_USERNAME / ADMIN_PASSWORD).

    Fails closed: if credentials aren't configured the site is unreachable rather
    than wide open. Uses constant-time comparison to avoid leaking length/contents
    via timing.
    """
    username = os.environ.get("ADMIN_USERNAME", "")
    password = os.environ.get("ADMIN_PASSWORD", "")
    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin auth not configured: set ADMIN_USERNAME and ADMIN_PASSWORD",
        )
    user_ok = secrets.compare_digest(
        credentials.username.encode("utf-8"), username.encode("utf-8")
    )
    pass_ok = secrets.compare_digest(
        credentials.password.encode("utf-8"), password.encode("utf-8")
    )
    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from jose import jwt, JWTError
import os

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
ALGORITHM = "HS256"


class TenantRBACMiddleware(BaseHTTPMiddleware):
    """Extract JWT from Authorization header (if present), decode it and attach payload
    to request.state.jwt_payload. This lets downstream dependencies use the token
    information without decoding multiple times.

    It does not enforce authentication by itself; endpoints may still require auth via
    dependencies.
    """

    async def dispatch(self, request: Request, call_next):
        auth = request.headers.get("authorization")
        if auth and auth.lower().startswith("bearer "):
            token = auth.split(None, 1)[1]
            try:
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                # attach minimal safe info
                request.state.jwt_payload = payload
            except JWTError:
                # invalid token; leave payload absent — auth deps will raise if required
                request.state.jwt_payload = None
        else:
            request.state.jwt_payload = None

        response = await call_next(request)
        return response

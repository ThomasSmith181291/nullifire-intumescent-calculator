"""Password gate for the public Hauser demonstration. No customer data should be uploaded."""
import os
import secrets
from fastapi import Request
from fastapi.responses import Response
from app.main import app

@app.middleware("http")
async def password_gate(request: Request, call_next):
    if request.url.path == "/api/health":
        return await call_next(request)
    expected = os.environ.get("HAUSER_DEMO_PASSWORD")
    if not expected:
        return Response("Demo password is not configured", status_code=503)
    authorization = request.headers.get("authorization", "")
    import base64
    try:
        scheme, encoded = authorization.split(" ", 1)
        decoded = base64.b64decode(encoded).decode("utf-8")
        username, password = decoded.split(":", 1)
    except (ValueError, UnicodeError, Exception):
        username, password, scheme = "", "", ""
    if scheme.lower() != "basic" or not secrets.compare_digest(username, "hauser") or not secrets.compare_digest(password, expected):
        return Response("Hauser demo sign-in required", status_code=401, headers={"WWW-Authenticate": 'Basic realm="Hauser prototype"'})
    return await call_next(request)

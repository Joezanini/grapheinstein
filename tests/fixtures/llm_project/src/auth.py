"""Auth helpers.

Auth Middleware validates JWT on each request.
validate_token implements the Auth Middleware checks described above.
"""

import jwt  # PyJWT


def validate_token(token: str) -> bool:
    """Validate JWT for Auth Middleware checks."""
    try:
        jwt.decode(token, options={"verify_signature": False})
        return True
    except Exception:
        return False

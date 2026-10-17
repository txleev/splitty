import hashlib
import secrets

# 8 random bytes = 64 bits. token_urlsafe(8) gives an 11-character URL-safe id.
SESSION_ID_BYTES = 8
TOKEN_BYTES = 32


def new_session_id() -> str:
    return secrets.token_urlsafe(SESSION_ID_BYTES)


def new_token() -> str:
    """Used for host tokens and guest member tokens."""
    return secrets.token_urlsafe(TOKEN_BYTES)


def hash_token(token: str) -> str:
    """Only the hash is stored, so a leaked database does not leak working tokens."""
    return hashlib.sha256(token.encode()).hexdigest()

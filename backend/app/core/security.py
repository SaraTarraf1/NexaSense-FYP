
import os
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv
from pwdlib import PasswordHash
from uuid import uuid4

load_dotenv()

# Password hashing using Argon2
password_hasher = PasswordHash.recommended()

# JWT configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def hash_password(password: str) -> str:
    """
    Hash a plain-text password before storing it
    in the PostgreSQL database.
    """
    return password_hasher.hash(password)


def verify_password(
    password: str,
    hashed_password: str
) -> bool:
    """
    Verify a password against its stored hash.
    """
    return password_hasher.verify(
        password,
        hashed_password
    )



def create_access_token(user_id: int) -> str:
    """
    Generate a signed JWT access token with a unique identifier.
    """
    if not SECRET_KEY:
        raise RuntimeError("JWT_SECRET_KEY is not configured")

    now = datetime.now(timezone.utc)
    expiration = now + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": str(user_id),
        "jti": str(uuid4()),
        "iat": now,
        "exp": expiration,
        "type": "access",
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )



def decode_access_token(token: str) -> dict:
    """
    Decode and validate a JWT access token.
    """
    if not SECRET_KEY:
        raise RuntimeError("JWT_SECRET_KEY is not configured")

    payload = jwt.decode(
        token,
        SECRET_KEY,
        algorithms=[ALGORITHM],
        options={"require": ["sub", "jti", "iat", "exp"]},
    )

    if payload.get("type") != "access":
        raise jwt.InvalidTokenError(
            "Invalid token type"
        )

    return payload

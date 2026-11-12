
from pwdlib import PasswordHash

# Configure secure password hashing using Argon2
password_hasher = PasswordHash.recommended()


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

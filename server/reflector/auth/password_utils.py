"""Password hashing utilities using PBKDF2-SHA256 (stdlib only)."""

import hashlib
import hmac
import os

PBKDF2_ITERATIONS = 100_000
SALT_LENGTH = 16  # bytes, hex-encoded to 32 chars


def hash_password(password: str) -> str:
    """Hash a password using PBKDF2-SHA256 with a random salt.

    Format: pbkdf2:sha256:<iterations>$<salt_hex>$<hash_hex>
    """
    salt = os.urandom(SALT_LENGTH).hex()
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    )
    return f"pbkdf2:sha256:{PBKDF2_ITERATIONS}${salt}${dk.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash using constant-time comparison."""
    try:
        header, salt, stored_hash = password_hash.split("$", 2)
        _, algo, iterations_str = header.split(":")
        iterations = int(iterations_str)

        dk = hashlib.pbkdf2_hmac(
            algo,
            password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations,
        )
        return hmac.compare_digest(dk.hex(), stored_hash)
    except (ValueError, AttributeError):
        return False

"""Tests for password hashing utilities."""

from reflector.auth.password_utils import hash_password, verify_password


def test_hash_and_verify():
    pw = "my-secret-password"
    h = hash_password(pw)
    assert verify_password(pw, h) is True


def test_wrong_password():
    h = hash_password("correct")
    assert verify_password("wrong", h) is False


def test_hash_format():
    h = hash_password("test")
    parts = h.split("$")
    assert len(parts) == 3
    assert parts[0] == "pbkdf2:sha256:100000"
    assert len(parts[1]) == 32  # 16 bytes hex = 32 chars
    assert len(parts[2]) == 64  # sha256 hex = 64 chars


def test_different_salts():
    h1 = hash_password("same")
    h2 = hash_password("same")
    assert h1 != h2  # different salts produce different hashes
    assert verify_password("same", h1) is True
    assert verify_password("same", h2) is True


def test_malformed_hash():
    assert verify_password("test", "garbage") is False
    assert verify_password("test", "") is False
    assert verify_password("test", "pbkdf2:sha256:100000$short") is False


def test_empty_password():
    h = hash_password("")
    assert verify_password("", h) is True
    assert verify_password("notempty", h) is False


def test_unicode_password():
    pw = "p\u00e4ssw\u00f6rd\U0001f512"
    h = hash_password(pw)
    assert verify_password(pw, h) is True
    assert verify_password("password", h) is False


def test_constant_time_comparison():
    """Verify that hmac.compare_digest is used (structural test)."""
    import inspect

    source = inspect.getsource(verify_password)
    assert "hmac.compare_digest" in source

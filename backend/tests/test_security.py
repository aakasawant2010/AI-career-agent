import pytest

from app.core.security import hash_password, verify_password


def test_hash_and_verify_roundtrip():
    h = hash_password("correct horse 1")
    assert verify_password("correct horse 1", h)
    assert not verify_password("wrong", h)


def test_hashes_are_salted():
    assert hash_password("same-password-1") != hash_password("same-password-1")


def test_overlong_password_rejected_not_truncated():
    with pytest.raises(ValueError):
        hash_password("a" * 73)


def test_verify_handles_garbage_hash():
    assert verify_password("x", "not-a-hash") is False

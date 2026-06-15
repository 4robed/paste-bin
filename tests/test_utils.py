import pytest
from datetime import datetime, timedelta
from utils import (
    make_short_code,
    expiry_from_option,
    hash_password,
    verify_password,
    make_unlock_cookie,
    verify_unlock_cookie,
    EXPIRY_OPTIONS,
    EXPIRY_LABELS,
    ALPHABET,
)


class TestMakeShortCode:
    def test_length(self):
        code = make_short_code()
        assert len(code) == 8

    def test_only_valid_chars(self):
        for _ in range(50):
            code = make_short_code()
            assert all(c in ALPHABET for c in code)

    def test_uniqueness(self):
        codes = {make_short_code() for _ in range(1000)}
        assert len(codes) == 1000


class TestExpiryFromOption:
    def test_never_returns_none(self):
        assert expiry_from_option("never") is None

    def test_unknown_key_returns_none(self):
        assert expiry_from_option("bogus") is None

    def test_1h_is_roughly_one_hour(self):
        before = datetime.utcnow()
        result = expiry_from_option("1h")
        after = datetime.utcnow()
        assert result is not None
        assert before + timedelta(hours=1) <= result <= after + timedelta(hours=1, seconds=1)

    def test_1d_is_roughly_one_day(self):
        before = datetime.utcnow()
        result = expiry_from_option("1d")
        assert result is not None
        assert result > before + timedelta(hours=23)
        assert result < before + timedelta(hours=25)

    def test_7d(self):
        result = expiry_from_option("7d")
        assert result is not None
        assert result > datetime.utcnow() + timedelta(days=6)

    def test_30d(self):
        result = expiry_from_option("30d")
        assert result is not None
        assert result > datetime.utcnow() + timedelta(days=29)

    def test_all_keys_covered(self):
        for key in EXPIRY_OPTIONS:
            result = expiry_from_option(key)
            if key == "never":
                assert result is None
            else:
                assert result is not None

    def test_labels_match_options(self):
        assert set(EXPIRY_LABELS.keys()) == set(EXPIRY_OPTIONS.keys())


class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        pw = "supersecret"
        assert hash_password(pw) != pw

    def test_verify_correct_password(self):
        pw = "correcthorsebatterystaple"
        hashed = hash_password(pw)
        assert verify_password(pw, hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("rightpassword")
        assert verify_password("wrongpassword", hashed) is False

    def test_different_hashes_same_input(self):
        pw = "same"
        h1 = hash_password(pw)
        h2 = hash_password(pw)
        assert h1 != h2  # bcrypt salts each hash

    def test_empty_string_password(self):
        hashed = hash_password("")
        assert verify_password("", hashed) is True
        assert verify_password("notempty", hashed) is False


class TestUnlockCookie:
    def test_valid_cookie_verifies(self):
        code = "AbCdEfGh"
        token = make_unlock_cookie(code)
        assert verify_unlock_cookie(token, code) is True

    def test_wrong_code_fails(self):
        token = make_unlock_cookie("AAAAAAAA")
        assert verify_unlock_cookie(token, "BBBBBBBB") is False

    def test_tampered_token_fails(self):
        token = make_unlock_cookie("AAAAAAAA")
        tampered = token[:-3] + "xxx"
        assert verify_unlock_cookie(tampered, "AAAAAAAA") is False

    def test_empty_token_fails(self):
        assert verify_unlock_cookie("", "AAAAAAAA") is False

    def test_expired_token_fails(self):
        code = "AAAAAAAA"
        token = make_unlock_cookie(code)
        assert verify_unlock_cookie(token, code, max_age=-1) is False

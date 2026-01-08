"""
Comprehensive test suite for security utilities and JWT functionality.

This module provides extensive test coverage for password hashing, JWT token
creation/validation, token expiration, security utility functions, and
security vulnerability prevention.

Test Categories:
- Password Hashing (bcrypt, argon2, validation)
- JWT Token Creation (access, refresh, custom claims)
- JWT Token Validation (signature, expiration, claims)
- Token Expiration (access, refresh, custom TTL)
- Security Utilities (sanitization, validation, encryption)
- Security Vulnerabilities (injection, timing attacks, token theft)
- Performance Tests (hashing speed, token generation)
- Edge Cases (malformed tokens, invalid inputs)
"""

import asyncio
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest
from jose import JWTError, jwt

# ============================================================================
# Test Fixtures and Utilities
# ============================================================================


@pytest.fixture
def jwt_secret_key() -> str:
    """
    Provide JWT secret key for testing.

    Returns:
        Secret key string for JWT operations
    """
    return "test_secret_key_for_jwt_operations_12345"


@pytest.fixture
def jwt_algorithm() -> str:
    """
    Provide JWT algorithm for testing.

    Returns:
        Algorithm name for JWT encoding/decoding
    """
    return "HS256"


@pytest.fixture
def valid_token_payload() -> dict[str, Any]:
    """
    Provide valid JWT token payload.

    Returns:
        Dictionary with valid token claims
    """
    return {
        "sub": "user@example.com",
        "user_id": "user_123",
        "role": "user",
        "type": "access",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }


@pytest.fixture
def expired_token_payload() -> dict[str, Any]:
    """
    Provide expired JWT token payload.

    Returns:
        Dictionary with expired token claims
    """
    return {
        "sub": "user@example.com",
        "user_id": "user_123",
        "role": "user",
        "type": "access",
        "iat": datetime.now(timezone.utc) - timedelta(hours=2),
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
    }


@pytest.fixture
def mock_datetime():
    """
    Mock datetime for consistent time-based testing.

    Returns:
        Mock datetime object with fixed time
    """
    fixed_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    with patch("src.services.security.datetime") as mock_dt:
        mock_dt.now.return_value = fixed_time
        mock_dt.utcnow.return_value = fixed_time
        yield mock_dt


@pytest.fixture
def sample_passwords() -> dict[str, str]:
    """
    Provide sample passwords for testing.

    Returns:
        Dictionary with various password types
    """
    return {
        "strong": "SecurePass123!@#",
        "weak": "password",
        "medium": "Password123",
        "special_chars": "P@ssw0rd!#$%",
        "unicode": "Pässwörd123!",
        "long": "VeryLongSecurePassword123!@#$%^&*()",
    }


# ============================================================================
# Password Hashing Tests
# ============================================================================


class TestPasswordHashing:
    """Test suite for password hashing functionality."""

    def test_hash_password_bcrypt_success(self, sample_passwords: dict[str, str]):
        """
        Test successful password hashing with bcrypt.

        Verifies that:
        - Password is hashed successfully
        - Hash is different from original password
        - Hash has correct bcrypt format
        - Hash length is appropriate
        """
        from src.services.security import hash_password

        password = sample_passwords["strong"]
        password_hash = hash_password(password)

        assert password_hash is not None
        assert password_hash != password
        assert password_hash.startswith("$2b$")
        assert len(password_hash) == 60

    def test_hash_password_different_salts(self, sample_passwords: dict[str, str]):
        """
        Test that same password produces different hashes due to salt.

        Verifies proper salt generation for security.
        """
        from src.services.security import hash_password

        password = sample_passwords["strong"]
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2
        assert hash1.startswith("$2b$")
        assert hash2.startswith("$2b$")

    def test_verify_password_correct(self, sample_passwords: dict[str, str]):
        """
        Test password verification with correct password.

        Verifies that correct password validates against hash.
        """
        from src.services.security import hash_password, verify_password

        password = sample_passwords["strong"]
        password_hash = hash_password(password)

        assert verify_password(password, password_hash) is True

    def test_verify_password_incorrect(self, sample_passwords: dict[str, str]):
        """
        Test password verification with incorrect password.

        Verifies that incorrect password fails validation.
        """
        from src.services.security import hash_password, verify_password

        password = sample_passwords["strong"]
        wrong_password = sample_passwords["weak"]
        password_hash = hash_password(password)

        assert verify_password(wrong_password, password_hash) is False

    def test_verify_password_empty_string(self, sample_passwords: dict[str, str]):
        """
        Test password verification with empty password.

        Verifies proper handling of empty password input.
        """
        from src.services.security import hash_password, verify_password

        password = sample_passwords["strong"]
        password_hash = hash_password(password)

        assert verify_password("", password_hash) is False

    def test_hash_password_unicode_support(self, sample_passwords: dict[str, str]):
        """
        Test password hashing with unicode characters.

        Verifies unicode password support.
        """
        from src.services.security import hash_password, verify_password

        password = sample_passwords["unicode"]
        password_hash = hash_password(password)

        assert verify_password(password, password_hash) is True

    def test_hash_password_special_characters(self, sample_passwords: dict[str, str]):
        """
        Test password hashing with special characters.

        Verifies special character handling in passwords.
        """
        from src.services.security import hash_password, verify_password

        password = sample_passwords["special_chars"]
        password_hash = hash_password(password)

        assert verify_password(password, password_hash) is True

    def test_hash_password_long_password(self, sample_passwords: dict[str, str]):
        """
        Test password hashing with very long password.

        Verifies handling of long passwords.
        """
        from src.services.security import hash_password, verify_password

        password = sample_passwords["long"]
        password_hash = hash_password(password)

        assert verify_password(password, password_hash) is True

    @pytest.mark.parametrize(
        "password",
        [
            "Short1!",
            "NoNumbers!",
            "nouppercase123!",
            "NOLOWERCASE123!",
            "NoSpecialChar123",
        ],
    )
    def test_password_strength_validation(self, password: str):
        """
        Test password strength validation rules.

        Args:
            password: Password to validate

        Verifies various password strength requirements.
        """
        from src.services.security import validate_password_strength

        result = validate_password_strength(password)

        # All these passwords should fail validation
        assert result is False

    def test_password_strength_valid(self):
        """
        Test password strength validation with valid passwords.

        Verifies that strong passwords pass validation.
        """
        from src.services.security import validate_password_strength

        valid_passwords = [
            "SecurePass123!",
            "MyP@ssw0rd",
            "C0mpl3x!Pass",
            "Str0ng#Password",
        ]

        for password in valid_passwords:
            assert validate_password_strength(password) is True

    def test_hash_password_timing_attack_resistance(
        self, sample_passwords: dict[str, str]
    ):
        """
        Test that password hashing is resistant to timing attacks.

        Verifies consistent hashing time regardless of password.
        """
        from src.services.security import hash_password

        password1 = sample_passwords["weak"]
        password2 = sample_passwords["strong"]

        start1 = time.time()
        hash_password(password1)
        time1 = time.time() - start1

        start2 = time.time()
        hash_password(password2)
        time2 = time.time() - start2

        # Times should be similar (within 50% variance)
        assert abs(time1 - time2) / max(time1, time2) < 0.5


# ============================================================================
# JWT Token Creation Tests
# ============================================================================


class TestJWTTokenCreation:
    """Test suite for JWT token creation functionality."""

    def test_create_access_token_success(
        self, jwt_secret_key: str, jwt_algorithm: str
    ):
        """
        Test successful access token creation.

        Verifies that:
        - Token is created successfully
        - Token has correct structure
        - Token contains required claims
        """
        from src.services.security import create_access_token

        user_data = {"sub": "user@example.com", "user_id": "user_123", "role": "user"}

        token = create_access_token(user_data, jwt_secret_key, jwt_algorithm)

        assert token is not None
        assert isinstance(token, str)
        assert len(token.split(".")) == 3

        # Decode and verify claims
        decoded = jwt.decode(token, jwt_secret_key, algorithms=[jwt_algorithm])
        assert decoded["sub"] == user_data["sub"]
        assert decoded["user_id"] == user_data["user_id"]
        assert decoded["role"] == user_data["role"]
        assert decoded["type"] == "access"
        assert "exp" in decoded
        assert "iat" in decoded

    def test_create_refresh_token_success(
        self, jwt_secret_key: str, jwt_algorithm: str
    ):
        """
        Test successful refresh token creation.

        Verifies refresh token has longer expiration than access token.
        """
        from src.services.security import create_refresh_token

        user_data = {"sub": "user@example.com", "user_id": "user_123"}

        token = create_refresh_token(user_data, jwt_secret_key, jwt_algorithm)

        assert token is not None
        decoded = jwt.decode(token, jwt_secret_key, algorithms=[jwt_algorithm])
        assert decoded["type"] == "refresh"
        assert "exp" in decoded

        # Refresh token should have longer expiration
        exp_time = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        time_diff = exp_time - now

        assert time_diff.days >= 7  # At least 7 days

    def test_create_token_with_custom_expiration(
        self, jwt_secret_key: str, jwt_algorithm: str
    ):
        """
        Test token creation with custom expiration time.

        Verifies custom TTL is respected.
        """
        from src.services.security import create_access_token

        user_data = {"sub": "user@example.com"}
        custom_ttl = timedelta(minutes=30)

        token = create_access_token(
            user_data, jwt_secret_key, jwt_algorithm, expires_delta=custom_ttl
        )

        decoded = jwt.decode(token, jwt_secret_key, algorithms=[jwt_algorithm])
        exp_time = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        time_diff = exp_time - now

        # Should be approximately 30 minutes (allow 1 minute variance)
        assert 29 <= time_diff.total_seconds() / 60 <= 31

    def test_create_token_with_additional_claims(
        self, jwt_secret_key: str, jwt_algorithm: str
    ):
        """
        Test token creation with additional custom claims.

        Verifies custom claims are included in token.
        """
        from src.services.security import create_access_token

        user_data = {
            "sub": "user@example.com",
            "user_id": "user_123",
            "role": "admin",
            "permissions": ["read", "write", "delete"],
            "tenant_id": "tenant_456",
        }

        token = create_access_token(user_data, jwt_secret_key, jwt_algorithm)

        decoded = jwt.decode(token, jwt_secret_key, algorithms=[jwt_algorithm])
        assert decoded["permissions"] == user_data["permissions"]
        assert decoded["tenant_id"] == user_data["tenant_id"]

    def test_create_token_empty_data(self, jwt_secret_key: str, jwt_algorithm: str):
        """
        Test token creation with empty user data.

        Verifies handling of minimal token data.
        """
        from src.services.security import create_access_token

        user_data = {}

        token = create_access_token(user_data, jwt_secret_key, jwt_algorithm)

        decoded = jwt.decode(token, jwt_secret_key, algorithms=[jwt_algorithm])
        assert "exp" in decoded
        assert "iat" in decoded
        assert decoded["type"] == "access"

    def test_create_token_unicode_data(self, jwt_secret_key: str, jwt_algorithm: str):
        """
        Test token creation with unicode characters in data.

        Verifies unicode support in token claims.
        """
        from src.services.security import create_access_token

        user_data = {"sub": "用户@example.com", "name": "José François"}

        token = create_access_token(user_data, jwt_secret_key, jwt_algorithm)

        decoded = jwt.decode(token, jwt_secret_key, algorithms=[jwt_algorithm])
        assert decoded["sub"] == user_data["sub"]
        assert decoded["name"] == user_data["name"]

    def test_create_token_different_algorithms(self, jwt_secret_key: str):
        """
        Test token creation with different algorithms.

        Verifies support for multiple JWT algorithms.
        """
        from src.services.security import create_access_token

        user_data = {"sub": "user@example.com"}
        algorithms = ["HS256", "HS384", "HS512"]

        for algorithm in algorithms:
            token = create_access_token(user_data, jwt_secret_key, algorithm)
            decoded = jwt.decode(token, jwt_secret_key, algorithms=[algorithm])
            assert decoded["sub"] == user_data["sub"]


# ============================================================================
# JWT Token Validation Tests
# ============================================================================


class TestJWTTokenValidation:
    """Test suite for JWT token validation functionality."""

    def test_decode_token_success(
        self, valid_token_payload: dict[str, Any], jwt_secret_key: str, jwt_algorithm: str
    ):
        """
        Test successful token decoding with valid token.

        Verifies token can be decoded and claims extracted.
        """
        from src.services.security import decode_token

        # Create token
        token = jwt.encode(valid_token_payload, jwt_secret_key, algorithm=jwt_algorithm)

        # Decode token
        decoded = decode_token(token, jwt_secret_key, jwt_algorithm)

        assert decoded is not None
        assert decoded["sub"] == valid_token_payload["sub"]
        assert decoded["user_id"] == valid_token_payload["user_id"]
        assert decoded["role"] == valid_token_payload["role"]

    def test_decode_token_expired(
        self, expired_token_payload: dict[str, Any], jwt_secret_key: str, jwt_algorithm: str
    ):
        """
        Test token decoding with expired token.

        Verifies expired tokens are rejected.
        """
        from src.services.security import decode_token

        # Create expired token
        token = jwt.encode(expired_token_payload, jwt_secret_key, algorithm=jwt_algorithm)

        # Should raise JWTError for expired token
        with pytest.raises(JWTError):
            decode_token(token, jwt_secret_key, jwt_algorithm)

    def test_decode_token_invalid_signature(
        self, valid_token_payload: dict[str, Any], jwt_secret_key: str, jwt_algorithm: str
    ):
        """
        Test token decoding with invalid signature.

        Verifies tokens with wrong signature are rejected.
        """
        from src.services.security import decode_token

        # Create token with different secret
        token = jwt.encode(
            valid_token_payload, "wrong_secret_key", algorithm=jwt_algorithm
        )

        # Should raise JWTError for invalid signature
        with pytest.raises(JWTError):
            decode_token(token, jwt_secret_key, jwt_algorithm)

    def test_decode_token_malformed(self, jwt_secret_key: str, jwt_algorithm: str):
        """
        Test token decoding with malformed token.

        Verifies malformed tokens are rejected.
        """
        from src.services.security import decode_token

        malformed_tokens = [
            "not.a.token",
            "invalid_token_format",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid",
            "",
            "...",
        ]

        for token in malformed_tokens:
            with pytest.raises(JWTError):
                decode_token(token, jwt_secret_key, jwt_algorithm)

    def test_decode_token_missing_claims(
        self, jwt_secret_key: str, jwt_algorithm: str
    ):
        """
        Test token decoding with missing required claims.

        Verifies tokens without required claims are handled properly.
        """
        from src.services.security import decode_token

        # Token without 'sub' claim
        payload = {"user_id": "user_123", "exp": datetime.now(timezone.utc) + timedelta(hours=1)}
        token = jwt.encode(payload, jwt_secret_key, algorithm=jwt_algorithm)

        decoded = decode_token(token, jwt_secret_key, jwt_algorithm)
        assert "sub" not in decoded
        assert decoded["user_id"] == "user_123"

    def test_validate_token_type_access(
        self, jwt_secret_key: str, jwt_algorithm: str
    ):
        """
        Test token type validation for access tokens.

        Verifies access token type is validated correctly.
        """
        from src.services.security import create_access_token, validate_token_type

        user_data = {"sub": "user@example.com"}
        token = create_access_token(user_data, jwt_secret_key, jwt_algorithm)

        assert validate_token_type(token, jwt_secret_key, jwt_algorithm, "access") is True

    def test_validate_token_type_refresh(
        self, jwt_secret_key: str, jwt_algorithm: str
    ):
        """
        Test token type validation for refresh tokens.

        Verifies refresh token type is validated correctly.
        """
        from src.services.security import create_refresh_token, validate_token_type

        user_data = {"sub": "user@example.com"}
        token = create_refresh_token(user_data, jwt_secret_key, jwt_algorithm)

        assert validate_token_type(token, jwt_secret_key, jwt_algorithm, "refresh") is True

    def test_validate_token_type_mismatch(
        self, jwt_secret_key: str, jwt_algorithm: str
    ):
        """
        Test token type validation with wrong type.

        Verifies token type mismatch is detected.
        """
        from src.services.security import create_access_token, validate_token_type

        user_data = {"sub": "user@example.com"}
        token = create_access_token(user_data, jwt_secret_key, jwt_algorithm)

        # Access token should not validate as refresh token
        assert validate_token_type(token, jwt_secret_key, jwt_algorithm, "refresh") is False

    def test_decode_token_with_leeway(
        self, jwt_secret_key: str, jwt_algorithm: str
    ):
        """
        Test token decoding with expiration leeway.

        Verifies leeway allows recently expired tokens.
        """
        from src.services.security import decode_token

        # Create token that expired 30 seconds ago
        payload = {
            "sub": "user@example.com",
            "exp": datetime.now(timezone.utc) - timedelta(seconds=30),
        }
        token = jwt.encode(payload, jwt_secret_key, algorithm=jwt_algorithm)

        # Should succeed with 60 second leeway
        decoded = decode_token(token, jwt_secret_key, jwt_algorithm, leeway=60)
        assert decoded["sub"] == "user@example.com"


# ============================================================================
# Token Expiration Tests
# ============================================================================


class TestTokenExpiration:
    """Test suite for token expiration functionality."""

    def test_access_token_default_expiration(
        self, jwt_secret_key: str, jwt_algorithm: str
    ):
        """
        Test access token has correct default expiration.

        Verifies default access token TTL is 1 hour.
        """
        from src.services.security import create_access_token

        user_data = {"sub": "user@example.com"}
        token = create_access_token(user_data, jwt_secret_key, jwt_algorithm)

        decoded = jwt.decode(token, jwt_secret_key, algorithms=[jwt_algorithm])
        exp_time = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        time_diff = exp_time - now

        # Should be approximately 1 hour (allow 1 minute variance)
        assert 59 <= time_diff.total_seconds() / 60 <= 61

    def test_refresh_token_default_expiration(
        self, jwt_secret_key: str, jwt_algorithm: str
    ):
        """
        Test refresh token has correct default expiration.

        Verifies default refresh token TTL is 7 days.
        """
        from src.services.security import create_refresh_token

        user_data = {"sub": "user@example.com"}
        token = create_refresh_token(user_data, jwt_secret_key, jwt_algorithm)

        decoded = jwt.decode(token, jwt_secret_key, algorithms=[jwt_algorithm])
        exp_time = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        time_diff = exp_time - now

        # Should be approximately 7 days
        assert 6.9 <= time_diff.days <= 7.1

    def test_token_expiration_check(self, jwt_secret_key: str, jwt_algorithm: str):
        """
        Test token expiration checking utility.

        Verifies utility correctly identifies expired tokens.
        """
        from src.services.security import is_token_expired

        # Create expired token
        expired_payload = {
            "sub": "user@example.com",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        expired_token = jwt.encode(
            expired_payload, jwt_secret_key, algorithm=jwt_algorithm
        )

        # Create valid token
        valid_payload = {
            "sub": "user@example.com",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        valid_token = jwt.encode(valid_payload, jwt_secret_key, algorithm=jwt_algorithm)

        assert is_token_expired(expired_token, jwt_secret_key, jwt_algorithm) is True
        assert is_token_expired(valid_token, jwt_secret_key, jwt_algorithm) is False

    def test_token_remaining_time(self, jwt_secret_key: str, jwt_algorithm: str):
        """
        Test calculation of remaining token validity time.

        Verifies utility correctly calculates time until expiration.
        """
        from src.services.security import get_token_remaining_time

        # Create token expiring in 30 minutes
        payload = {
            "sub": "user@example.com",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
        }
        token = jwt.encode(payload, jwt_secret_key, algorithm=jwt_algorithm)

        remaining = get_token_remaining_time(token, jwt_secret_key, jwt_algorithm)

        # Should be approximately 30 minutes (allow 1 minute variance)
        assert 29 <= remaining.total_seconds() / 60 <= 31

    def test_token_issued_at_time(self, jwt_secret_key: str, jwt_algorithm: str):
        """
        Test token issued at (iat) claim.

        Verifies iat claim is set correctly.
        """
        from src.services.security import create_access_token

        before_creation = datetime.now(timezone.utc)
        user_data = {"sub": "user@example.com"}
        token = create_access_token(user_data, jwt_secret_key, jwt_algorithm)
        after_creation = datetime.now(timezone.utc)

        decoded = jwt.decode(token, jwt_secret_key, algorithms=[jwt_algorithm])
        iat_time = datetime.fromtimestamp(decoded["iat"], tz=timezone.utc)

        assert before_creation <= iat_time <= after_creation


# ============================================================================
# Security Utilities Tests
# ============================================================================


class TestSecurityUtilities:
    """Test suite for security utility functions."""

    def test_sanitize_input_sql_injection(self):
        """
        Test input sanitization against SQL injection.

        Verifies SQL injection attempts are sanitized.
        """
        from src.services.security import sanitize_input

        malicious_inputs = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin'--",
            "' UNION SELECT * FROM users--",
        ]

        for malicious_input in malicious_inputs:
            sanitized = sanitize_input(malicious_input)
            assert "DROP" not in sanitized.upper()
            assert "UNION" not in sanitized.upper()
            assert "--" not in sanitized

    def test_sanitize_input_xss_prevention(self):
        """
        Test input sanitization against XSS attacks.

        Verifies XSS attempts are sanitized.
        """
        from src.services.security import sanitize_input

        xss_inputs = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<iframe src='malicious.com'></iframe>",
        ]

        for xss_input in xss_inputs:
            sanitized = sanitize_input(xss_input)
            assert "<script>" not in sanitized.lower()
            assert "javascript:" not in sanitized.lower()
            assert "<iframe>" not in sanitized.lower()

    def test_sanitize_input_preserves_valid_data(self):
        """
        Test that sanitization preserves valid input.

        Verifies legitimate input is not corrupted.
        """
        from src.services.security import sanitize_input

        valid_inputs = [
            "john.doe@example.com",
            "John Doe",
            "123 Main Street",
            "Valid text with spaces",
        ]

        for valid_input in valid_inputs:
            sanitized = sanitize_input(valid_input)
            assert sanitized == valid_input

    def test_validate_email_format(self):
        """
        Test email format validation.

        Verifies email validation utility works correctly.
        """
        from src.services.security import validate_email

        valid_emails = [
            "user@example.com",
            "john.doe@company.co.uk",
            "user+tag@example.com",
            "user123@test-domain.com",
        ]

        invalid_emails = [
            "invalid-email",
            "@example.com",
            "user@",
            "user@.com",
            "user space@example.com",
        ]

        for email in valid_emails:
            assert validate_email(email) is True

        for email in invalid_emails:
            assert validate_email(email) is False

    def test_generate_secure_random_string(self):
        """
        Test secure random string generation.

        Verifies random string generation is cryptographically secure.
        """
        from src.services.security import generate_secure_random_string

        # Generate multiple strings
        strings = [generate_secure_random_string(32) for _ in range(10)]

        # All should be unique
        assert len(set(strings)) == 10

        # All should have correct length
        for s in strings:
            assert len(s) == 32

        # Should contain alphanumeric characters
        for s in strings:
            assert s.isalnum()

    def test_constant_time_compare(self):
        """
        Test constant-time string comparison.

        Verifies timing attack resistant comparison.
        """
        from src.services.security import constant_time_compare

        string1 = "secret_value_123"
        string2 = "secret_value_123"
        string3 = "different_value"

        assert constant_time_compare(string1, string2) is True
        assert constant_time_compare(string1, string3) is False

    def test_constant_time_compare_timing(self):
        """
        Test that constant-time comparison has consistent timing.

        Verifies resistance to timing attacks.
        """
        from src.services.security import constant_time_compare

        string1 = "a" * 100
        string2 = "a" * 100
        string3 = "b" * 100

        # Time comparison with matching strings
        start1 = time.perf_counter()
        for _ in range(1000):
            constant_time_compare(string1, string2)
        time1 = time.perf_counter() - start1

        # Time comparison with non-matching strings
        start2 = time.perf_counter()
        for _ in range(1000):
            constant_time_compare(string1, string3)
        time2 = time.perf_counter() - start2

        # Times should be similar (within 20% variance)
        assert abs(time1 - time2) / max(time1, time2) < 0.2

    def test_encrypt_decrypt_data(self):
        """
        Test data encryption and decryption.

        Verifies symmetric encryption utilities work correctly.
        """
        from src.services.security import decrypt_data, encrypt_data

        original_data = "sensitive_information_12345"
        encryption_key = "encryption_key_32_bytes_long!!"

        # Encrypt data
        encrypted = encrypt_data(original_data, encryption_key)
        assert encrypted != original_data
        assert len(encrypted) > len(original_data)

        # Decrypt data
        decrypted = decrypt_data(encrypted, encryption_key)
        assert decrypted == original_data

    def test_encrypt_decrypt_unicode(self):
        """
        Test encryption/decryption with unicode data.

        Verifies unicode support in encryption.
        """
        from src.services.security import decrypt_data, encrypt_data

        original_data = "用户数据 José François"
        encryption_key = "encryption_key_32_bytes_long!!"

        encrypted = encrypt_data(original_data, encryption_key)
        decrypted = decrypt_data(encrypted, encryption_key)

        assert decrypted == original_data

    def test_hash_data_sha256(self):
        """
        Test SHA-256 hashing utility.

        Verifies data hashing for integrity checks.
        """
        from src.services.security import hash_data

        data = "data_to_hash"
        hash1 = hash_data(data)
        hash2 = hash_data(data)

        # Same data should produce same hash
        assert hash1 == hash2

        # Different data should produce different hash
        hash3 = hash_data("different_data")
        assert hash1 != hash3

        # Hash should be hex string of correct length (SHA-256 = 64 chars)
        assert len(hash1) == 64
        assert all(c in "0123456789abcdef" for c in hash1)


# ============================================================================
# Security Vulnerability Tests
# ============================================================================


class TestSecurityVulnerabilities:
    """Test suite for security vulnerability prevention."""

    def test_timing_attack_resistance_password_verify(
        self, sample_passwords: dict[str, str]
    ):
        """
        Test password verification is resistant to timing attacks.

        Verifies consistent timing regardless of password correctness.
        """
        from src.services.security import hash_password, verify_password

        password = sample_passwords["strong"]
        password_hash = hash_password(password)

        # Time correct password verification
        start1 = time.perf_counter()
        for _ in range(100):
            verify_password(password, password_hash)
        time1 = time.perf_counter() - start1

        # Time incorrect password verification
        start2 = time.perf_counter()
        for _ in range(100):
            verify_password("wrong_password", password_hash)
        time2 = time.perf_counter() - start2

        # Times should be similar (within 30% variance)
        # Bcrypt is designed to have consistent timing
        assert abs(time1 - time2) / max(time1, time2) < 0.3

    def test_jwt_algorithm_confusion_prevention(
        self, jwt_secret_key: str, jwt_algorithm: str
    ):
        """
        Test prevention of JWT algorithm confusion attacks.

        Verifies tokens with wrong algorithm are rejected.
        """
        from src.services.security import decode_token

        payload = {
            "sub": "user@example.com",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }

        # Create token with HS256
        token = jwt.encode(payload, jwt_secret_key, algorithm="HS256")

        # Try to decode with different algorithm
        with pytest.raises(JWTError):
            decode_token(token, jwt_secret_key, "HS512")

    def test_token_replay_attack_prevention(
        self, jwt_secret_key: str, jwt_algorithm: str
    ):
        """
        Test token replay attack prevention mechanisms.

        Verifies tokens include unique identifiers.
        """
        from src.services.security import create_access_token

        user_data = {"sub": "user@example.com"}

        # Create two tokens
        token1 = create_access_token(user_data, jwt_secret_key, jwt_algorithm)
        time.sleep(0.1)
        token2 = create_access_token(user_data, jwt_secret_key, jwt_algorithm)

        # Tokens should be different (due to iat claim)
        assert token1 != token2

        decoded1 = jwt.decode(token1, jwt_secret_key, algorithms=[jwt_algorithm])
        decoded2 = jwt.decode(token2, jwt_secret_key, algorithms=[jwt_algorithm])

        # iat should be different
        assert decoded1["iat"] != decoded2["iat"]

    def test_password_hash_collision_resistance(
        self, sample_passwords: dict[str, str]
    ):
        """
        Test password hash collision resistance.

        Verifies different passwords produce different hashes.
        """
        from src.services.security import hash_password

        passwords = list(sample_passwords.values())
        hashes = [hash_password(pwd) for pwd in passwords]

        # All hashes should be unique
        assert len(set(hashes)) == len(hashes)

    def test_jwt_none_algorithm_rejection(self, jwt_secret_key: str):
        """
        Test rejection of JWT 'none' algorithm.

        Verifies 'none' algorithm tokens are rejected.
        """
        from src.services.security import decode_token

        payload = {
            "sub": "user@example.com",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }

        # Create token with 'none' algorithm
        token = jwt.encode(payload, "", algorithm="none")

        # Should reject 'none' algorithm
        with pytest.raises(JWTError):
            decode_token(token, jwt_secret_key, "HS256")

    def test_token_signature_stripping_prevention(
        self, jwt_secret_key: str, jwt_algorithm: str
    ):
        """
        Test prevention of token signature stripping.

        Verifies tokens without signatures are rejected.
        """
        from src.services.security import decode_token

        payload = {
            "sub": "user@example.com",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }

        token = jwt.encode(payload, jwt_secret_key, algorithm=jwt_algorithm)

        # Strip signature (remove last part)
        parts = token.split(".")
        stripped_token = f"{parts[0]}.{parts[1]}."

        # Should reject token without signature
        with pytest.raises(JWTError):
            decode_token(stripped_token, jwt_secret_key, jwt_algorithm)

    def test_sql_injection_in_token_claims(
        self, jwt_secret_key: str, jwt_algorithm: str
    ):
        """
        Test handling of SQL injection attempts in token claims.

        Verifies malicious claims are handled safely.
        """
        from src.services.security import create_access_token, decode_token

        malicious_data = {
            "sub": "user@example.com'; DROP TABLE users; --",
            "user_id": "1' OR '1'='1",
        }

        token = create_access_token(malicious_data, jwt_secret_key, jwt_algorithm)
        decoded = decode_token(token, jwt_secret_key, jwt_algorithm)

        # Claims should be preserved as-is (sanitization happens at use)
        assert decoded["sub"] == malicious_data["sub"]
        assert decoded["user_id"] == malicious_data["user_id"]


# ============================================================================
# Performance Tests
# ============================================================================


class TestPerformance:
    """Test suite for performance validation."""

    def test_password_hashing_performance(self, sample_passwords: dict[str, str]):
        """
        Test password hashing performance.

        Verifies hashing completes within acceptable time.
        """
        from src.services.security import hash_password

        password = sample_passwords["strong"]

        start_time = time.perf_counter()
        hash_password(password)
        elapsed_time = time.perf_counter() - start_time

        # Bcrypt should take reasonable time (50ms to 1s)
        assert 0.05 < elapsed_time < 1.0

    def test_password_verification_performance(
        self, sample_passwords: dict[str, str]
    ):
        """
        Test password verification performance.

        Verifies verification completes within acceptable time.
        """
        from src.services.security import hash_password, verify_password

        password = sample_passwords["strong"]
        password_hash = hash_password(password)

        start_time = time.perf_counter()
        verify_password(password, password_hash)
        elapsed_time = time.perf_counter() - start_time

        # Verification should be fast (< 1 second)
        assert elapsed_time < 1.0

    def test_token_creation_performance(
        self, jwt_secret_key: str, jwt_algorithm: str
    ):
        """
        Test JWT token creation performance.

        Verifies token creation is fast.
        """
        from src.services.security import create_access_token

        user_data = {"sub": "user@example.com", "user_id": "user_123"}

        start_time = time.perf_counter()
        for _ in range(100):
            create_access_token(user_data, jwt_secret_key, jwt_algorithm)
        elapsed_time = time.perf_counter() - start_time

        # Should create 100 tokens in less than 1 second
        assert elapsed_time < 1.0

    def test_token_validation_performance(
        self, jwt_secret_key: str, jwt_algorithm: str
    ):
        """
        Test JWT token validation performance.

        Verifies token validation is fast.
        """
        from src.services.security import create_access_token, decode_token

        user_data = {"sub": "user@example.com"}
        token = create_access_token(user_data, jwt_secret_key, jwt_algorithm)

        start_time = time.perf_counter()
        for _ in range(100):
            decode_token(token, jwt_secret_key, jwt_algorithm)
        elapsed_time = time.perf_counter() - start_time

        # Should validate 100 tokens in less than 0.5 seconds
        assert elapsed_time < 0.5

    async def test_concurrent_token_creation(
        self, jwt_secret_key: str, jwt_algorithm: str
    ):
        """
        Test concurrent token creation performance.

        Verifies system handles concurrent token generation.
        """
        from src.services.security import create_access_token

        async def create_token(index: int):
            user_data = {"sub": f"user{index}@example.com"}
            return create_access_token(user_data, jwt_secret_key, jwt_algorithm)

        # Create 100 tokens concurrently
        start_time = time.perf_counter()
        tasks = [create_token(i) for i in range(100)]
        tokens = await asyncio.gather(*tasks)
        elapsed_time = time.perf_counter() - start_time

        assert len(tokens) == 100
        assert elapsed_time < 2.0  # Should complete in less than 2 seconds

    async def test_concurrent_password_hashing(
        self, sample_passwords: dict[str, str]
    ):
        """
        Test concurrent password hashing performance.

        Verifies system handles concurrent hashing operations.
        """
        from src.services.security import hash_password

        async def hash_async(password: str):
            return hash_password(password)

        password = sample_passwords["strong"]

        # Hash 20 passwords concurrently
        start_time = time.perf_counter()
        tasks = [hash_async(password) for _ in range(20)]
        hashes = await asyncio.gather(*tasks)
        elapsed_time = time.perf_counter() - start_time

        assert len(hashes) == 20
        assert elapsed_time < 5.0  # Should complete in less than 5 seconds


# ============================================================================
# Edge Cases and Error Handling Tests
# ============================================================================


class TestEdgeCases:
    """Test suite for edge cases and error handling."""

    def test_hash_empty_password(self):
        """
        Test hashing empty password.

        Verifies empty password handling.
        """
        from src.services.security import hash_password

        with pytest.raises(ValueError):
            hash_password("")

    def test_verify_password_empty_hash(self, sample_passwords: dict[str, str]):
        """
        Test password verification with empty hash.

        Verifies empty hash handling.
        """
        from src.services.security import verify_password

        password = sample_passwords["strong"]

        with pytest.raises(ValueError):
            verify_password(password, "")

    def test_create_token_none_data(self, jwt_secret_key: str, jwt_algorithm: str):
        """
        Test token creation with None data.

        Verifies None data handling.
        """
        from src.services.security import create_access_token

        with pytest.raises(ValueError):
            create_access_token(None, jwt_secret_key, jwt_algorithm)

    def test_decode_token_empty_string(
        self, jwt_secret_key: str, jwt_algorithm: str
    ):
        """
        Test token decoding with empty string.

        Verifies empty token handling.
        """
        from src.services.security import decode_token

        with pytest.raises(JWTError):
            decode_token("", jwt_secret_key, jwt_algorithm)

    def test_decode_token_none(self, jwt_secret_key: str, jwt_algorithm: str):
        """
        Test token decoding with None.

        Verifies None token handling.
        """
        from src.services.security import decode_token

        with pytest.raises((JWTError, TypeError)):
            decode_token(None, jwt_secret_key, jwt_algorithm)

    def test_token_with_very_long_claims(
        self, jwt_secret_key: str, jwt_algorithm: str
    ):
        """
        Test token creation with very long claim values.

        Verifies handling of large token payloads.
        """
        from src.services.security import create_access_token, decode_token

        user_data = {
            "sub": "user@example.com",
            "long_claim": "A" * 10000,  # 10KB of data
        }

        token = create_access_token(user_data, jwt_secret_key, jwt_algorithm)
        decoded = decode_token(token, jwt_secret_key, jwt_algorithm)

        assert decoded["long_claim"] == user_data["long_claim"]

    def test_token_with_nested_objects(
        self, jwt_secret_key: str, jwt_algorithm: str
    ):
        """
        Test token creation with nested object claims.

        Verifies complex claim structure support.
        """
        from src.services.security import create_access_token, decode_token

        user_data = {
            "sub": "user@example.com",
            "metadata": {
                "profile": {"name": "John Doe", "age": 30},
                "permissions": ["read", "write"],
            },
        }

        token = create_access_token(user_data, jwt_secret_key, jwt_algorithm)
        decoded = decode_token(token, jwt_secret_key, jwt_algorithm)

        assert decoded["metadata"]["profile"]["name"] == "John Doe"
        assert decoded["metadata"]["permissions"] == ["read", "write"]

    def test_sanitize_input_null_bytes(self):
        """
        Test input sanitization with null bytes.

        Verifies null byte handling.
        """
        from src.services.security import sanitize_input

        malicious_input = "user\x00admin"
        sanitized = sanitize_input(malicious_input)

        assert "\x00" not in sanitized

    def test_sanitize_input_control_characters(self):
        """
        Test input sanitization with control characters.

        Verifies control character handling.
        """
        from src.services.security import sanitize_input

        malicious_input = "user\r\n\t\x1b[31mtest"
        sanitized = sanitize_input(malicious_input)

        # Control characters should be removed or escaped
        assert "\x1b" not in sanitized

    def test_password_with_null_bytes(self):
        """
        Test password hashing with null bytes.

        Verifies null byte handling in passwords.
        """
        from src.services.security import hash_password

        password_with_null = "password\x00truncated"

        # Should either reject or handle null bytes safely
        try:
            password_hash = hash_password(password_with_null)
            assert password_hash is not None
        except ValueError:
            pass  # Acceptable to reject null bytes


# ============================================================================
# Integration Tests
# ============================================================================


class TestSecurityIntegration:
    """Integration tests for complete security workflows."""

    def test_complete_authentication_flow(
        self, jwt_secret_key: str, jwt_algorithm: str, sample_passwords: dict[str, str]
    ):
        """
        Test complete authentication flow from registration to token validation.

        Verifies entire security workflow works end-to-end.
        """
        from src.services.security import (
            create_access_token,
            decode_token,
            hash_password,
            verify_password,
        )

        # Step 1: Hash password during registration
        password = sample_passwords["strong"]
        password_hash = hash_password(password)

        # Step 2: Verify password during login
        assert verify_password(password, password_hash) is True

        # Step 3: Create access token after successful login
        user_data = {"sub": "user@example.com", "user_id": "user_123", "role": "user"}
        access_token = create_access_token(user_data, jwt_secret_key, jwt_algorithm)

        # Step 4: Validate token for protected resource access
        decoded = decode_token(access_token, jwt_secret_key, jwt_algorithm)
        assert decoded["sub"] == user_data["sub"]
        assert decoded["user_id"] == user_data["user_id"]

    def test_token_refresh_flow(self, jwt_secret_key: str, jwt_algorithm: str):
        """
        Test token refresh workflow.

        Verifies refresh token can be used to obtain new access token.
        """
        from src.services.security import (
            create_access_token,
            create_refresh_token,
            decode_token,
            validate_token_type,
        )

        user_data = {"sub": "user@example.com", "user_id": "user_123"}

        # Create initial tokens
        access_token = create_access_token(user_data, jwt_secret_key, jwt_algorithm)
        refresh_token = create_refresh_token(user_data, jwt_secret_key, jwt_algorithm)

        # Validate refresh token
        assert validate_token_type(refresh_token, jwt_secret_key, jwt_algorithm, "refresh")

        # Use refresh token to create new access token
        decoded_refresh = decode_token(refresh_token, jwt_secret_key, jwt_algorithm)
        new_user_data = {"sub": decoded_refresh["sub"], "user_id": decoded_refresh["user_id"]}
        new_access_token = create_access_token(
            new_user_data, jwt_secret_key, jwt_algorithm
        )

        # Verify new access token
        decoded_new = decode_token(new_access_token, jwt_secret_key, jwt_algorithm)
        assert decoded_new["sub"] == user_data["sub"]

    def test_password_change_flow(
        self, jwt_secret_key: str, jwt_algorithm: str, sample_passwords: dict[str, str]
    ):
        """
        Test password change workflow.

        Verifies password can be changed securely.
        """
        from src.services.security import hash_password, verify_password

        # Original password
        old_password = sample_passwords["strong"]
        old_hash = hash_password(old_password)

        # Verify old password
        assert verify_password(old_password, old_hash) is True

        # Change to new password
        new_password = sample_passwords["special_chars"]
        new_hash = hash_password(new_password)

        # Verify new password works
        assert verify_password(new_password, new_hash) is True

        # Verify old password no longer works with new hash
        assert verify_password(old_password, new_hash) is False

    def test_multi_factor_authentication_flow(
        self, jwt_secret_key: str, jwt_algorithm: str
    ):
        """
        Test multi-factor authentication token flow.

        Verifies MFA token generation and validation.
        """
        from src.services.security import create_access_token, decode_token

        # Create MFA token with short expiration
        mfa_data = {
            "sub": "user@example.com",
            "type": "mfa",
            "mfa_verified": False,
        }
        mfa_token = create_access_token(
            mfa_data, jwt_secret_key, jwt_algorithm, expires_delta=timedelta(minutes=5)
        )

        # Verify MFA token
        decoded = decode_token(mfa_token, jwt_secret_key, jwt_algorithm)
        assert decoded["type"] == "mfa"
        assert decoded["mfa_verified"] is False

        # After MFA verification, create full access token
        full_data = {
            "sub": "user@example.com",
            "user_id": "user_123",
            "role": "user",
            "mfa_verified": True,
        }
        access_token = create_access_token(full_data, jwt_secret_key, jwt_algorithm)

        decoded_access = decode_token(access_token, jwt_secret_key, jwt_algorithm)
        assert decoded_access["mfa_verified"] is True
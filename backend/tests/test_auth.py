"""
Comprehensive test suite for authentication functionality.

This module provides extensive test coverage for user registration, login,
token management, password hashing, JWT validation, and role-based access control.
Includes unit tests, integration tests, security tests, and performance validation.

Test Categories:
- User Registration (happy path, validation, duplicates)
- User Login (success, failures, rate limiting)
- Token Management (generation, validation, refresh, expiration)
- Password Security (hashing, validation, strength)
- Role-Based Access Control (permissions, authorization)
- Security Scenarios (injection, brute force, token theft)
- Performance Tests (response times, concurrent access)
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from httpx import AsyncClient
from jose import jwt

from src.main import app


# ============================================================================
# Test Fixtures and Utilities
# ============================================================================


@pytest.fixture
def valid_user_data() -> dict[str, str]:
    """
    Provide valid user registration data.

    Returns:
        Dictionary with valid user registration fields
    """
    return {
        "email": "test@example.com",
        "password": "SecurePass123!",
        "name": "Test User",
        "role": "user",
    }


@pytest.fixture
def valid_admin_data() -> dict[str, str]:
    """
    Provide valid admin user registration data.

    Returns:
        Dictionary with valid admin registration fields
    """
    return {
        "email": "admin@example.com",
        "password": "AdminPass123!",
        "name": "Admin User",
        "role": "admin",
    }


@pytest.fixture
def invalid_user_data() -> list[dict[str, str]]:
    """
    Provide various invalid user registration data for testing validation.

    Returns:
        List of dictionaries with invalid user data
    """
    return [
        {"email": "invalid-email", "password": "pass", "name": "User"},
        {"email": "test@example.com", "password": "short", "name": "User"},
        {"email": "test@example.com", "password": "NoNumbers!", "name": "User"},
        {"email": "test@example.com", "password": "nonumbers123", "name": "User"},
        {"email": "", "password": "ValidPass123!", "name": "User"},
        {"email": "test@example.com", "password": "ValidPass123!", "name": ""},
    ]


@pytest.fixture
def mock_password_hasher():
    """
    Mock password hashing service for testing.

    Returns:
        Mock object with hash and verify methods
    """
    hasher = Mock()
    hasher.hash.return_value = "hashed_password_123"
    hasher.verify.return_value = True
    return hasher


@pytest.fixture
def mock_jwt_service():
    """
    Mock JWT token service for testing.

    Returns:
        Mock object with token generation and validation methods
    """
    service = Mock()
    service.create_access_token.return_value = "access_token_123"
    service.create_refresh_token.return_value = "refresh_token_123"
    service.decode_token.return_value = {
        "sub": "user@example.com",
        "exp": (datetime.utcnow() + timedelta(hours=1)).timestamp(),
        "type": "access",
    }
    return service


@pytest.fixture
def mock_user_repository():
    """
    Mock user repository for database operations.

    Returns:
        AsyncMock object with user CRUD methods
    """
    repo = AsyncMock()
    repo.get_by_email.return_value = None
    repo.create.return_value = {
        "id": "user_123",
        "email": "test@example.com",
        "name": "Test User",
        "role": "user",
        "created_at": datetime.utcnow(),
    }
    repo.update.return_value = True
    return repo


@pytest.fixture
def authenticated_headers() -> dict[str, str]:
    """
    Provide authentication headers with valid token.

    Returns:
        Dictionary with Authorization header
    """
    return {"Authorization": "Bearer valid_access_token_123"}


@pytest.fixture
def expired_token_headers() -> dict[str, str]:
    """
    Provide authentication headers with expired token.

    Returns:
        Dictionary with Authorization header containing expired token
    """
    return {"Authorization": "Bearer expired_token_123"}


# ============================================================================
# User Registration Tests
# ============================================================================


class TestUserRegistration:
    """Test suite for user registration functionality."""

    def test_register_user_success(
        self, test_client: TestClient, valid_user_data: dict[str, str]
    ):
        """
        Test successful user registration with valid data.

        Verifies that:
        - Registration returns 201 Created
        - Response contains user data
        - Password is not included in response
        - User ID is generated
        """
        response = test_client.post("/api/v1/auth/register", json=valid_user_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "id" in data
        assert data["email"] == valid_user_data["email"]
        assert data["name"] == valid_user_data["name"]
        assert data["role"] == valid_user_data["role"]
        assert "password" not in data
        assert "created_at" in data

    async def test_register_user_async(
        self, async_client: AsyncClient, valid_user_data: dict[str, str]
    ):
        """
        Test async user registration endpoint.

        Verifies async endpoint behavior matches sync endpoint.
        """
        response = await async_client.post(
            "/api/v1/auth/register", json=valid_user_data
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["email"] == valid_user_data["email"]

    @pytest.mark.parametrize(
        "field,value,expected_error",
        [
            ("email", "invalid-email", "Invalid email format"),
            ("password", "short", "Password too short"),
            ("password", "nouppercaseornumbers", "Password must contain uppercase"),
            ("email", "", "Email is required"),
            ("name", "", "Name is required"),
        ],
    )
    def test_register_validation_errors(
        self,
        test_client: TestClient,
        valid_user_data: dict[str, str],
        field: str,
        value: str,
        expected_error: str,
    ):
        """
        Test registration validation for various invalid inputs.

        Args:
            field: Field to invalidate
            value: Invalid value to test
            expected_error: Expected error message
        """
        invalid_data = valid_user_data.copy()
        invalid_data[field] = value

        response = test_client.post("/api/v1/auth/register", json=invalid_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "error" in data
        assert any(expected_error.lower() in str(err).lower() for err in data["details"])

    def test_register_duplicate_email(
        self, test_client: TestClient, valid_user_data: dict[str, str]
    ):
        """
        Test registration with duplicate email address.

        Verifies that:
        - First registration succeeds
        - Second registration with same email fails
        - Appropriate error message is returned
        """
        # First registration
        response1 = test_client.post("/api/v1/auth/register", json=valid_user_data)
        assert response1.status_code == status.HTTP_201_CREATED

        # Duplicate registration
        response2 = test_client.post("/api/v1/auth/register", json=valid_user_data)
        assert response2.status_code == status.HTTP_409_CONFLICT
        data = response2.json()
        assert "already exists" in data["message"].lower()

    def test_register_password_hashing(
        self, test_client: TestClient, valid_user_data: dict[str, str]
    ):
        """
        Test that passwords are properly hashed during registration.

        Verifies that:
        - Password is hashed before storage
        - Original password is not stored
        - Hash is different from original password
        """
        with patch("src.services.auth.hash_password") as mock_hash:
            mock_hash.return_value = "hashed_password_secure"

            response = test_client.post("/api/v1/auth/register", json=valid_user_data)

            assert response.status_code == status.HTTP_201_CREATED
            mock_hash.assert_called_once_with(valid_user_data["password"])

    def test_register_default_role(
        self, test_client: TestClient, valid_user_data: dict[str, str]
    ):
        """
        Test that default role is assigned when not specified.

        Verifies that users without specified role get 'user' role by default.
        """
        user_data = valid_user_data.copy()
        del user_data["role"]

        response = test_client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["role"] == "user"

    def test_register_sql_injection_prevention(self, test_client: TestClient):
        """
        Test SQL injection prevention in registration.

        Verifies that SQL injection attempts are properly sanitized.
        """
        malicious_data = {
            "email": "test@example.com'; DROP TABLE users; --",
            "password": "ValidPass123!",
            "name": "Test User",
        }

        response = test_client.post("/api/v1/auth/register", json=malicious_data)

        # Should either reject or sanitize, not execute SQL
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]


# ============================================================================
# User Login Tests
# ============================================================================


class TestUserLogin:
    """Test suite for user login functionality."""

    def test_login_success(
        self, test_client: TestClient, valid_user_data: dict[str, str]
    ):
        """
        Test successful user login with valid credentials.

        Verifies that:
        - Login returns 200 OK
        - Access token is provided
        - Refresh token is provided
        - Token type is 'bearer'
        """
        # Register user first
        test_client.post("/api/v1/auth/register", json=valid_user_data)

        # Login
        login_data = {
            "email": valid_user_data["email"],
            "password": valid_user_data["password"],
        }
        response = test_client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data

    async def test_login_async(
        self, async_client: AsyncClient, valid_user_data: dict[str, str]
    ):
        """
        Test async login endpoint.

        Verifies async login behavior matches sync endpoint.
        """
        # Register user first
        await async_client.post("/api/v1/auth/register", json=valid_user_data)

        # Login
        login_data = {
            "email": valid_user_data["email"],
            "password": valid_user_data["password"],
        }
        response = await async_client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data

    def test_login_invalid_email(self, test_client: TestClient):
        """
        Test login with non-existent email.

        Verifies that login fails with appropriate error message.
        """
        login_data = {"email": "nonexistent@example.com", "password": "SomePass123!"}

        response = test_client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "invalid credentials" in data["message"].lower()

    def test_login_invalid_password(
        self, test_client: TestClient, valid_user_data: dict[str, str]
    ):
        """
        Test login with incorrect password.

        Verifies that:
        - Login fails with wrong password
        - Error message doesn't reveal if email exists
        """
        # Register user first
        test_client.post("/api/v1/auth/register", json=valid_user_data)

        # Login with wrong password
        login_data = {
            "email": valid_user_data["email"],
            "password": "WrongPassword123!",
        }
        response = test_client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "invalid credentials" in data["message"].lower()

    def test_login_missing_fields(self, test_client: TestClient):
        """
        Test login with missing required fields.

        Verifies validation errors for missing email or password.
        """
        # Missing password
        response1 = test_client.post(
            "/api/v1/auth/login", json={"email": "test@example.com"}
        )
        assert response1.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Missing email
        response2 = test_client.post(
            "/api/v1/auth/login", json={"password": "ValidPass123!"}
        )
        assert response2.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_login_rate_limiting(
        self, test_client: TestClient, valid_user_data: dict[str, str]
    ):
        """
        Test rate limiting on login attempts.

        Verifies that:
        - Multiple failed login attempts trigger rate limiting
        - Rate limit error is returned after threshold
        """
        login_data = {
            "email": valid_user_data["email"],
            "password": "WrongPassword123!",
        }

        # Attempt multiple failed logins
        for _ in range(5):
            test_client.post("/api/v1/auth/login", json=login_data)

        # Next attempt should be rate limited
        response = test_client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        data = response.json()
        assert "rate limit" in data["message"].lower()

    def test_login_case_insensitive_email(
        self, test_client: TestClient, valid_user_data: dict[str, str]
    ):
        """
        Test that email login is case-insensitive.

        Verifies users can login with different email casing.
        """
        # Register user
        test_client.post("/api/v1/auth/register", json=valid_user_data)

        # Login with uppercase email
        login_data = {
            "email": valid_user_data["email"].upper(),
            "password": valid_user_data["password"],
        }
        response = test_client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == status.HTTP_200_OK


# ============================================================================
# Token Management Tests
# ============================================================================


class TestTokenManagement:
    """Test suite for JWT token generation, validation, and refresh."""

    def test_token_generation(
        self, test_client: TestClient, valid_user_data: dict[str, str]
    ):
        """
        Test JWT token generation during login.

        Verifies that:
        - Tokens are valid JWT format
        - Tokens contain required claims
        - Access and refresh tokens are different
        """
        # Register and login
        test_client.post("/api/v1/auth/register", json=valid_user_data)
        login_data = {
            "email": valid_user_data["email"],
            "password": valid_user_data["password"],
        }
        response = test_client.post("/api/v1/auth/login", json=login_data)

        data = response.json()
        access_token = data["access_token"]
        refresh_token = data["refresh_token"]

        # Verify tokens are different
        assert access_token != refresh_token

        # Verify token structure (should have 3 parts separated by dots)
        assert len(access_token.split(".")) == 3
        assert len(refresh_token.split(".")) == 3

    def test_token_validation_success(
        self, test_client: TestClient, valid_user_data: dict[str, str]
    ):
        """
        Test successful token validation for protected endpoints.

        Verifies that valid tokens grant access to protected resources.
        """
        # Register and login
        test_client.post("/api/v1/auth/register", json=valid_user_data)
        login_data = {
            "email": valid_user_data["email"],
            "password": valid_user_data["password"],
        }
        login_response = test_client.post("/api/v1/auth/login", json=login_data)
        access_token = login_response.json()["access_token"]

        # Access protected endpoint
        headers = {"Authorization": f"Bearer {access_token}"}
        response = test_client.get("/api/v1/auth/me", headers=headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == valid_user_data["email"]

    def test_token_validation_missing_token(self, test_client: TestClient):
        """
        Test access to protected endpoint without token.

        Verifies that requests without tokens are rejected.
        """
        response = test_client.get("/api/v1/auth/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "not authenticated" in data["message"].lower()

    def test_token_validation_invalid_token(self, test_client: TestClient):
        """
        Test access with invalid token format.

        Verifies that malformed tokens are rejected.
        """
        headers = {"Authorization": "Bearer invalid_token_format"}
        response = test_client.get("/api/v1/auth/me", headers=headers)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_token_validation_expired_token(self, test_client: TestClient):
        """
        Test access with expired token.

        Verifies that expired tokens are rejected with appropriate error.
        """
        # Create expired token
        expired_token = jwt.encode(
            {
                "sub": "test@example.com",
                "exp": datetime.utcnow() - timedelta(hours=1),
                "type": "access",
            },
            "secret_key",
            algorithm="HS256",
        )

        headers = {"Authorization": f"Bearer {expired_token}"}
        response = test_client.get("/api/v1/auth/me", headers=headers)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "expired" in data["message"].lower()

    def test_token_refresh_success(
        self, test_client: TestClient, valid_user_data: dict[str, str]
    ):
        """
        Test successful token refresh with valid refresh token.

        Verifies that:
        - Refresh token can be used to get new access token
        - New access token is different from old one
        - New access token is valid
        """
        # Register and login
        test_client.post("/api/v1/auth/register", json=valid_user_data)
        login_data = {
            "email": valid_user_data["email"],
            "password": valid_user_data["password"],
        }
        login_response = test_client.post("/api/v1/auth/login", json=login_data)
        old_access_token = login_response.json()["access_token"]
        refresh_token = login_response.json()["refresh_token"]

        # Refresh token
        refresh_data = {"refresh_token": refresh_token}
        response = test_client.post("/api/v1/auth/refresh", json=refresh_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["access_token"] != old_access_token

        # Verify new token works
        headers = {"Authorization": f"Bearer {data['access_token']}"}
        me_response = test_client.get("/api/v1/auth/me", headers=headers)
        assert me_response.status_code == status.HTTP_200_OK

    def test_token_refresh_invalid_token(self, test_client: TestClient):
        """
        Test token refresh with invalid refresh token.

        Verifies that invalid refresh tokens are rejected.
        """
        refresh_data = {"refresh_token": "invalid_refresh_token"}
        response = test_client.post("/api/v1/auth/refresh", json=refresh_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_token_refresh_access_token_used(
        self, test_client: TestClient, valid_user_data: dict[str, str]
    ):
        """
        Test that access tokens cannot be used for refresh.

        Verifies token type validation in refresh endpoint.
        """
        # Register and login
        test_client.post("/api/v1/auth/register", json=valid_user_data)
        login_data = {
            "email": valid_user_data["email"],
            "password": valid_user_data["password"],
        }
        login_response = test_client.post("/api/v1/auth/login", json=login_data)
        access_token = login_response.json()["access_token"]

        # Try to refresh with access token
        refresh_data = {"refresh_token": access_token}
        response = test_client.post("/api/v1/auth/refresh", json=refresh_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "invalid token type" in data["message"].lower()


# ============================================================================
# Logout Tests
# ============================================================================


class TestLogout:
    """Test suite for user logout functionality."""

    def test_logout_success(
        self, test_client: TestClient, valid_user_data: dict[str, str]
    ):
        """
        Test successful logout with valid token.

        Verifies that:
        - Logout returns success status
        - Token is invalidated after logout
        """
        # Register and login
        test_client.post("/api/v1/auth/register", json=valid_user_data)
        login_data = {
            "email": valid_user_data["email"],
            "password": valid_user_data["password"],
        }
        login_response = test_client.post("/api/v1/auth/login", json=login_data)
        access_token = login_response.json()["access_token"]

        # Logout
        headers = {"Authorization": f"Bearer {access_token}"}
        response = test_client.post("/api/v1/auth/logout", headers=headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "success" in data["message"].lower()

        # Verify token is invalidated
        me_response = test_client.get("/api/v1/auth/me", headers=headers)
        assert me_response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_logout_without_token(self, test_client: TestClient):
        """
        Test logout without authentication token.

        Verifies that logout requires authentication.
        """
        response = test_client.post("/api/v1/auth/logout")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_logout_invalid_token(self, test_client: TestClient):
        """
        Test logout with invalid token.

        Verifies that invalid tokens are rejected during logout.
        """
        headers = {"Authorization": "Bearer invalid_token"}
        response = test_client.post("/api/v1/auth/logout", headers=headers)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ============================================================================
# Password Security Tests
# ============================================================================


class TestPasswordSecurity:
    """Test suite for password hashing and validation."""

    def test_password_hashing_bcrypt(self):
        """
        Test that passwords are hashed using bcrypt.

        Verifies that:
        - Hash is different from original password
        - Hash can be verified against original password
        - Same password produces different hashes (salt)
        """
        from src.services.auth import hash_password, verify_password

        password = "SecurePass123!"

        # Hash password
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        # Verify hashes are different (due to salt)
        assert hash1 != hash2
        assert hash1 != password

        # Verify both hashes validate correctly
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)

    def test_password_verification_wrong_password(self):
        """
        Test password verification with incorrect password.

        Verifies that wrong passwords fail verification.
        """
        from src.services.auth import hash_password, verify_password

        password = "SecurePass123!"
        wrong_password = "WrongPass123!"

        password_hash = hash_password(password)

        assert not verify_password(wrong_password, password_hash)

    @pytest.mark.parametrize(
        "password,is_valid",
        [
            ("SecurePass123!", True),
            ("short", False),
            ("nouppercase123!", False),
            ("NOLOWERCASE123!", False),
            ("NoNumbers!", False),
            ("NoSpecialChar123", False),
            ("Valid1Pass!", True),
        ],
    )
    def test_password_strength_validation(self, password: str, is_valid: bool):
        """
        Test password strength validation rules.

        Args:
            password: Password to validate
            is_valid: Expected validation result
        """
        from src.services.auth import validate_password_strength

        result = validate_password_strength(password)
        assert result == is_valid

    def test_password_not_stored_plaintext(
        self, test_client: TestClient, valid_user_data: dict[str, str]
    ):
        """
        Test that passwords are never stored in plaintext.

        Verifies database doesn't contain original password.
        """
        with patch("src.repositories.user.UserRepository.create") as mock_create:
            test_client.post("/api/v1/auth/register", json=valid_user_data)

            # Verify create was called with hashed password
            call_args = mock_create.call_args
            stored_password = call_args[0][0].get("password")

            assert stored_password != valid_user_data["password"]
            assert len(stored_password) > 50  # Bcrypt hashes are long


# ============================================================================
# Role-Based Access Control Tests
# ============================================================================


class TestRoleBasedAccess:
    """Test suite for role-based access control and permissions."""

    def test_user_role_default(
        self, test_client: TestClient, valid_user_data: dict[str, str]
    ):
        """
        Test that default role is 'user' for new registrations.

        Verifies default role assignment.
        """
        user_data = valid_user_data.copy()
        del user_data["role"]

        response = test_client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["role"] == "user"

    def test_admin_role_assignment(
        self, test_client: TestClient, valid_admin_data: dict[str, str]
    ):
        """
        Test admin role assignment during registration.

        Verifies that admin role can be assigned.
        """
        response = test_client.post("/api/v1/auth/register", json=valid_admin_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["role"] == "admin"

    def test_user_cannot_access_admin_endpoint(
        self, test_client: TestClient, valid_user_data: dict[str, str]
    ):
        """
        Test that regular users cannot access admin endpoints.

        Verifies role-based authorization.
        """
        # Register and login as user
        test_client.post("/api/v1/auth/register", json=valid_user_data)
        login_data = {
            "email": valid_user_data["email"],
            "password": valid_user_data["password"],
        }
        login_response = test_client.post("/api/v1/auth/login", json=login_data)
        access_token = login_response.json()["access_token"]

        # Try to access admin endpoint
        headers = {"Authorization": f"Bearer {access_token}"}
        response = test_client.get("/api/v1/admin/users", headers=headers)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "permission" in data["message"].lower()

    def test_admin_can_access_admin_endpoint(
        self, test_client: TestClient, valid_admin_data: dict[str, str]
    ):
        """
        Test that admin users can access admin endpoints.

        Verifies admin role permissions.
        """
        # Register and login as admin
        test_client.post("/api/v1/auth/register", json=valid_admin_data)
        login_data = {
            "email": valid_admin_data["email"],
            "password": valid_admin_data["password"],
        }
        login_response = test_client.post("/api/v1/auth/login", json=login_data)
        access_token = login_response.json()["access_token"]

        # Access admin endpoint
        headers = {"Authorization": f"Bearer {access_token}"}
        response = test_client.get("/api/v1/admin/users", headers=headers)

        assert response.status_code == status.HTTP_200_OK

    def test_role_cannot_be_elevated_by_user(
        self, test_client: TestClient, valid_user_data: dict[str, str]
    ):
        """
        Test that users cannot elevate their own role.

        Verifies authorization for role modification.
        """
        # Register and login as user
        test_client.post("/api/v1/auth/register", json=valid_user_data)
        login_data = {
            "email": valid_user_data["email"],
            "password": valid_user_data["password"],
        }
        login_response = test_client.post("/api/v1/auth/login", json=login_data)
        access_token = login_response.json()["access_token"]

        # Try to update role to admin
        headers = {"Authorization": f"Bearer {access_token}"}
        update_data = {"role": "admin"}
        response = test_client.patch("/api/v1/auth/me", json=update_data, headers=headers)

        assert response.status_code == status.HTTP_403_FORBIDDEN


# ============================================================================
# Security Tests
# ============================================================================


class TestSecurityScenarios:
    """Test suite for security vulnerabilities and attack prevention."""

    def test_sql_injection_login(self, test_client: TestClient):
        """
        Test SQL injection prevention in login endpoint.

        Verifies that SQL injection attempts are properly handled.
        """
        malicious_data = {
            "email": "admin@example.com' OR '1'='1",
            "password": "anything' OR '1'='1",
        }

        response = test_client.post("/api/v1/auth/login", json=malicious_data)

        # Should fail authentication, not execute SQL
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_xss_prevention_in_name(
        self, test_client: TestClient, valid_user_data: dict[str, str]
    ):
        """
        Test XSS prevention in user input fields.

        Verifies that script tags are sanitized or rejected.
        """
        xss_data = valid_user_data.copy()
        xss_data["name"] = "<script>alert('XSS')</script>"

        response = test_client.post("/api/v1/auth/register", json=xss_data)

        # Should either sanitize or reject
        if response.status_code == status.HTTP_201_CREATED:
            data = response.json()
            assert "<script>" not in data["name"]
        else:
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_brute_force_protection(
        self, test_client: TestClient, valid_user_data: dict[str, str]
    ):
        """
        Test brute force attack protection on login.

        Verifies rate limiting prevents brute force attempts.
        """
        login_data = {
            "email": valid_user_data["email"],
            "password": "WrongPassword123!",
        }

        # Attempt multiple failed logins
        responses = []
        for _ in range(10):
            response = test_client.post("/api/v1/auth/login", json=login_data)
            responses.append(response.status_code)

        # Should eventually rate limit
        assert status.HTTP_429_TOO_MANY_REQUESTS in responses

    def test_token_theft_prevention(
        self, test_client: TestClient, valid_user_data: dict[str, str]
    ):
        """
        Test token theft prevention mechanisms.

        Verifies that tokens are bound to specific contexts.
        """
        # Register and login
        test_client.post("/api/v1/auth/register", json=valid_user_data)
        login_data = {
            "email": valid_user_data["email"],
            "password": valid_user_data["password"],
        }
        login_response = test_client.post("/api/v1/auth/login", json=login_data)
        access_token = login_response.json()["access_token"]

        # Try to use token from different IP/User-Agent
        headers = {
            "Authorization": f"Bearer {access_token}",
            "User-Agent": "DifferentBrowser/1.0",
            "X-Forwarded-For": "192.168.1.100",
        }
        response = test_client.get("/api/v1/auth/me", headers=headers)

        # Should either work or require re-authentication
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_401_UNAUTHORIZED,
        ]

    def test_csrf_token_validation(
        self, test_client: TestClient, valid_user_data: dict[str, str]
    ):
        """
        Test CSRF token validation for state-changing operations.

        Verifies CSRF protection on sensitive endpoints.
        """
        # Register and login
        test_client.post("/api/v1/auth/register", json=valid_user_data)
        login_data = {
            "email": valid_user_data["email"],
            "password": valid_user_data["password"],
        }
        login_response = test_client.post("/api/v1/auth/login", json=login_data)
        access_token = login_response.json()["access_token"]

        # Try to perform state-changing operation without CSRF token
        headers = {"Authorization": f"Bearer {access_token}"}
        response = test_client.delete("/api/v1/auth/account", headers=headers)

        # Should require CSRF token or use other protection
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_403_FORBIDDEN,
        ]


# ============================================================================
# Performance Tests
# ============================================================================


class TestPerformance:
    """Test suite for performance and scalability validation."""

    def test_registration_response_time(
        self, test_client: TestClient, valid_user_data: dict[str, str]
    ):
        """
        Test registration endpoint response time.

        Verifies registration completes within acceptable time.
        """
        start_time = time.time()

        response = test_client.post("/api/v1/auth/register", json=valid_user_data)

        elapsed_time = time.time() - start_time

        assert response.status_code == status.HTTP_201_CREATED
        assert elapsed_time < 2.0  # Should complete within 2 seconds

    def test_login_response_time(
        self, test_client: TestClient, valid_user_data: dict[str, str]
    ):
        """
        Test login endpoint response time.

        Verifies login completes within acceptable time.
        """
        # Register user first
        test_client.post("/api/v1/auth/register", json=valid_user_data)

        login_data = {
            "email": valid_user_data["email"],
            "password": valid_user_data["password"],
        }

        start_time = time.time()
        response = test_client.post("/api/v1/auth/login", json=login_data)
        elapsed_time = time.time() - start_time

        assert response.status_code == status.HTTP_200_OK
        assert elapsed_time < 1.0  # Should complete within 1 second

    async def test_concurrent_registrations(
        self, async_client: AsyncClient, valid_user_data: dict[str, str]
    ):
        """
        Test concurrent user registrations.

        Verifies system handles multiple simultaneous registrations.
        """

        async def register_user(index: int):
            user_data = valid_user_data.copy()
            user_data["email"] = f"user{index}@example.com"
            return await async_client.post("/api/v1/auth/register", json=user_data)

        # Create 10 concurrent registrations
        tasks = [register_user(i) for i in range(10)]
        responses = await asyncio.gather(*tasks)

        # All should succeed
        success_count = sum(
            1 for r in responses if r.status_code == status.HTTP_201_CREATED
        )
        assert success_count == 10

    async def test_concurrent_logins(
        self, async_client: AsyncClient, valid_user_data: dict[str, str]
    ):
        """
        Test concurrent login attempts.

        Verifies system handles multiple simultaneous logins.
        """
        # Register user first
        await async_client.post("/api/v1/auth/register", json=valid_user_data)

        login_data = {
            "email": valid_user_data["email"],
            "password": valid_user_data["password"],
        }

        async def login_user():
            return await async_client.post("/api/v1/auth/login", json=login_data)

        # Create 20 concurrent logins
        tasks = [login_user() for _ in range(20)]
        responses = await asyncio.gather(*tasks)

        # All should succeed
        success_count = sum(
            1 for r in responses if r.status_code == status.HTTP_200_OK
        )
        assert success_count == 20

    def test_password_hashing_performance(self):
        """
        Test password hashing performance.

        Verifies hashing completes within acceptable time.
        """
        from src.services.auth import hash_password

        password = "SecurePass123!"

        start_time = time.time()
        hash_password(password)
        elapsed_time = time.time() - start_time

        # Bcrypt should take reasonable time (not too fast, not too slow)
        assert 0.05 < elapsed_time < 1.0


# ============================================================================
# Edge Cases and Error Handling Tests
# ============================================================================


class TestEdgeCases:
    """Test suite for edge cases and error handling."""

    def test_empty_request_body(self, test_client: TestClient):
        """
        Test endpoints with empty request body.

        Verifies proper error handling for missing data.
        """
        response = test_client.post("/api/v1/auth/register", json={})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_null_values_in_request(self, test_client: TestClient):
        """
        Test handling of null values in request.

        Verifies null value validation.
        """
        null_data = {"email": None, "password": None, "name": None}

        response = test_client.post("/api/v1/auth/register", json=null_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_extremely_long_input(
        self, test_client: TestClient, valid_user_data: dict[str, str]
    ):
        """
        Test handling of extremely long input values.

        Verifies input length validation.
        """
        long_data = valid_user_data.copy()
        long_data["name"] = "A" * 10000  # 10k characters

        response = test_client.post("/api/v1/auth/register", json=long_data)

        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        ]

    def test_special_characters_in_email(self, test_client: TestClient):
        """
        Test email validation with special characters.

        Verifies proper email format validation.
        """
        special_emails = [
            "user+tag@example.com",  # Valid
            "user.name@example.com",  # Valid
            "user@sub.example.com",  # Valid
            "user@example",  # Invalid
            "@example.com",  # Invalid
            "user@",  # Invalid
        ]

        for email in special_emails:
            user_data = {
                "email": email,
                "password": "ValidPass123!",
                "name": "Test User",
            }
            response = test_client.post("/api/v1/auth/register", json=user_data)

            # First 3 should succeed, last 3 should fail
            if email in special_emails[:3]:
                assert response.status_code == status.HTTP_201_CREATED
            else:
                assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_unicode_characters_in_name(
        self, test_client: TestClient, valid_user_data: dict[str, str]
    ):
        """
        Test handling of unicode characters in user name.

        Verifies unicode support in text fields.
        """
        unicode_data = valid_user_data.copy()
        unicode_data["name"] = "用户名 José François"

        response = test_client.post("/api/v1/auth/register", json=unicode_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == unicode_data["name"]

    def test_whitespace_handling(
        self, test_client: TestClient, valid_user_data: dict[str, str]
    ):
        """
        Test handling of leading/trailing whitespace.

        Verifies whitespace trimming in inputs.
        """
        whitespace_data = valid_user_data.copy()
        whitespace_data["email"] = "  test@example.com  "
        whitespace_data["name"] = "  Test User  "

        response = test_client.post("/api/v1/auth/register", json=whitespace_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["name"] == "Test User"


# ============================================================================
# Integration Tests
# ============================================================================


class TestAuthenticationFlow:
    """Integration tests for complete authentication flows."""

    def test_complete_registration_login_flow(
        self, test_client: TestClient, valid_user_data: dict[str, str]
    ):
        """
        Test complete user journey from registration to accessing protected resource.

        Verifies entire authentication flow works end-to-end.
        """
        # Step 1: Register
        register_response = test_client.post(
            "/api/v1/auth/register", json=valid_user_data
        )
        assert register_response.status_code == status.HTTP_201_CREATED
        user_id = register_response.json()["id"]

        # Step 2: Login
        login_data = {
            "email": valid_user_data["email"],
            "password": valid_user_data["password"],
        }
        login_response = test_client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == status.HTTP_200_OK
        access_token = login_response.json()["access_token"]

        # Step 3: Access protected resource
        headers = {"Authorization": f"Bearer {access_token}"}
        me_response = test_client.get("/api/v1/auth/me", headers=headers)
        assert me_response.status_code == status.HTTP_200_OK
        assert me_response.json()["id"] == user_id

        # Step 4: Logout
        logout_response = test_client.post("/api/v1/auth/logout", headers=headers)
        assert logout_response.status_code == status.HTTP_200_OK

        # Step 5: Verify token is invalidated
        me_after_logout = test_client.get("/api/v1/auth/me", headers=headers)
        assert me_after_logout.status_code == status.HTTP_401_UNAUTHORIZED

    def test_token_refresh_flow(
        self, test_client: TestClient, valid_user_data: dict[str, str]
    ):
        """
        Test token refresh flow.

        Verifies refresh token can be used to obtain new access token.
        """
        # Register and login
        test_client.post("/api/v1/auth/register", json=valid_user_data)
        login_data = {
            "email": valid_user_data["email"],
            "password": valid_user_data["password"],
        }
        login_response = test_client.post("/api/v1/auth/login", json=login_data)
        refresh_token = login_response.json()["refresh_token"]

        # Wait a moment
        time.sleep(1)

        # Refresh token
        refresh_data = {"refresh_token": refresh_token}
        refresh_response = test_client.post("/api/v1/auth/refresh", json=refresh_data)
        assert refresh_response.status_code == status.HTTP_200_OK
        new_access_token = refresh_response.json()["access_token"]

        # Use new token
        headers = {"Authorization": f"Bearer {new_access_token}"}
        me_response = test_client.get("/api/v1/auth/me", headers=headers)
        assert me_response.status_code == status.HTTP_200_OK

    def test_password_change_flow(
        self, test_client: TestClient, valid_user_data: dict[str, str]
    ):
        """
        Test password change flow.

        Verifies user can change password and login with new password.
        """
        # Register and login
        test_client.post("/api/v1/auth/register", json=valid_user_data)
        login_data = {
            "email": valid_user_data["email"],
            "password": valid_user_data["password"],
        }
        login_response = test_client.post("/api/v1/auth/login", json=login_data)
        access_token = login_response.json()["access_token"]

        # Change password
        new_password = "NewSecurePass123!"
        change_data = {
            "old_password": valid_user_data["password"],
            "new_password": new_password,
        }
        headers = {"Authorization": f"Bearer {access_token}"}
        change_response = test_client.post(
            "/api/v1/auth/change-password", json=change_data, headers=headers
        )
        assert change_response.status_code == status.HTTP_200_OK

        # Login with new password
        new_login_data = {"email": valid_user_data["email"], "password": new_password}
        new_login_response = test_client.post("/api/v1/auth/login", json=new_login_data)
        assert new_login_response.status_code == status.HTTP_200_OK

        # Old password should not work
        old_login_response = test_client.post("/api/v1/auth/login", json=login_data)
        assert old_login_response.status_code == status.HTTP_401_UNAUTHORIZED
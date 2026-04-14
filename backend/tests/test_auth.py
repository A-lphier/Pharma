"""
Tests for authentication endpoints.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user):
    """Test successful login."""
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpassword",
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, test_user):
    """Test login with wrong password."""
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "wrongpassword",
        },
    )
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    """Test login with nonexistent user."""
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "nonexistent",
            "password": "password",
        },
    )
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    """Test successful user registration."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "newpassword123",
            "full_name": "New User",
        },
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["username"] == "newuser"
    assert data["role"] == "user"
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_register_duplicate_username(client: AsyncClient, test_user):
    """Test registration with duplicate username."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "another@example.com",
            "username": "testuser",
            "password": "password123",
        },
    )
    
    assert response.status_code == 400
    assert "Username already registered" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, test_user):
    """Test registration with duplicate email."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "username": "anotheruser",
            "password": "password123",
        },
    )
    
    assert response.status_code == 400
    assert "Email already registered" in response.json()["detail"]


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, test_user):
    """Test token refresh."""
    # First login
    login_response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpassword",
        },
    )
    refresh_token = login_response.json()["refresh_token"]
    
    # Refresh token
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data

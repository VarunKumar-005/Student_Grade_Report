"""
test_auth.py — Integration tests for the /auth routes.

Uses the in-memory SQLite test database via conftest fixtures.
"""

import pytest
from fastapi.testclient import TestClient


class TestLogin:
    def test_login_success(self, client: TestClient, admin_user):
        resp = client.post(
            '/api/v1/auth/login',
            json={'email': 'admin@test.com', 'password': 'adminpass'},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert 'access_token' in data
        assert data['token_type'] == 'bearer'

    def test_login_wrong_password(self, client: TestClient, admin_user):
        resp = client.post(
            '/api/v1/auth/login',
            json={'email': 'admin@test.com', 'password': 'wrongpass'},
        )
        assert resp.status_code == 401

    def test_login_unknown_email(self, client: TestClient):
        resp = client.post(
            '/api/v1/auth/login',
            json={'email': 'nobody@test.com', 'password': 'pass'},
        )
        assert resp.status_code == 401

    def test_login_invalid_email_format(self, client: TestClient):
        resp = client.post(
            '/api/v1/auth/login',
            json={'email': 'not-an-email', 'password': 'pass'},
        )
        assert resp.status_code == 422  # Pydantic validation error


class TestGetMe:
    def test_get_me_authenticated(self, client: TestClient, admin_token: str, admin_user):
        resp = client.get(
            '/api/v1/auth/me',
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['email'] == 'admin@test.com'
        assert data['role'] == 'ADMIN'

    def test_get_me_unauthenticated(self, client: TestClient):
        resp = client.get('/api/v1/auth/me')
        assert resp.status_code == 403  # HTTPBearer returns 403 when no token

    def test_get_me_invalid_token(self, client: TestClient):
        resp = client.get(
            '/api/v1/auth/me',
            headers={'Authorization': 'Bearer invalid.token.here'},
        )
        assert resp.status_code == 401


class TestCreateUser:
    def test_admin_can_create_faculty(self, client: TestClient, admin_token: str):
        resp = client.post(
            '/api/v1/users/',
            json={
                'name': 'New Faculty',
                'email': 'newfaculty@test.com',
                'password': 'pass123',
                'role': 'FACULTY',
            },
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data['email'] == 'newfaculty@test.com'
        assert data['role'] == 'FACULTY'

    def test_duplicate_email_returns_409(self, client: TestClient, admin_token: str, admin_user):
        resp = client.post(
            '/api/v1/users/',
            json={
                'name': 'Dupe',
                'email': 'admin@test.com',  # already exists
                'password': 'pass',
                'role': 'FACULTY',
            },
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert resp.status_code == 409

    def test_faculty_cannot_create_user(self, client: TestClient, faculty_token: str):
        resp = client.post(
            '/api/v1/users/',
            json={
                'name': 'New User',
                'email': 'newuser@test.com',
                'password': 'pass',
                'role': 'FACULTY',
            },
            headers={'Authorization': f'Bearer {faculty_token}'},
        )
        assert resp.status_code == 403

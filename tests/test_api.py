"""API endpoint tests using TestClient with mocked auth.

These tests verify routing, request validation, and response shapes
without requiring a real database.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

_MOCK_PAYLOAD = {"sub": "test", "org_id": "test", "scopes": ["read", "write", "admin"]}


@pytest.fixture
def client():
    """TestClient with auth bypassed (full scopes)."""
    with patch("app.routers.cases.require_scope", return_value=_MOCK_PAYLOAD):
        with TestClient(app) as c:
            yield c


class TestHealthEndpoint:
    """Health check requires no auth and no DB."""

    def test_health_returns_ok(self):
        with TestClient(app) as c:
            resp = c.get("/health")
            assert resp.status_code == 200
            assert resp.json() == {"status": "ok"}


class TestCasesEndpointValidation:
    """Test that query parameter validation works on /api/cases."""

    def test_page_must_be_positive(self, client):
        with patch("app.routers.cases.get_db") as mock_get_db:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_get_db.return_value = mock_session

            resp = client.get("/api/cases?page=0")
            assert resp.status_code == 422  # validation error

    def test_page_size_max_100(self, client):
        with patch("app.routers.cases.get_db") as mock_get_db:
            mock_session = AsyncMock()
            mock_get_db.return_value = mock_session

            resp = client.get("/api/cases?page_size=200")
            assert resp.status_code == 422


class TestDeleteCaseEndpoint:
    """Test DELETE /api/cases/{case_id} routing."""

    def test_delete_nonexistent_case(self, client):
        """Deleting a non-existent case should 404."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        from app.models.database import get_db

        async def override_db():
            yield mock_session

        app.dependency_overrides[get_db] = override_db
        try:
            resp = client.delete("/api/cases/99999")
            assert resp.status_code == 404
        finally:
            app.dependency_overrides = {}


class TestScopeEnforcement:
    """Test that scope checks actually block unauthorized access."""

    def test_write_endpoint_rejects_read_only_user(self):
        """A user with only 'read' scope should get 403 on write endpoints."""
        read_only = {"sub": "viewer", "org_id": "test", "scopes": ["read"]}

        with patch("app.core.auth.get_current_user_payload", return_value=read_only):
            with TestClient(app) as c:
                resp = c.delete("/api/cases/1")
                assert resp.status_code == 403
                assert "write" in resp.json()["detail"]

    def test_read_endpoint_allows_read_only_user(self):
        """A user with 'read' scope should be able to access read endpoints."""
        read_only = {"sub": "viewer", "org_id": "test", "scopes": ["read"]}

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        from app.models.database import get_db

        async def override_db():
            yield mock_session

        app.dependency_overrides[get_db] = override_db
        try:
            with patch(
                "app.core.auth.get_current_user_payload", return_value=read_only
            ):
                with TestClient(app) as c:
                    resp = c.get("/api/cases/1")
                    # Should get 404 (case not found), NOT 401/403
                    assert resp.status_code == 404
        finally:
            app.dependency_overrides = {}

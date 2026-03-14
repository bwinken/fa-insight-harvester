"""Shared test fixtures.

For unit tests (data_cleaner, embedding), no fixtures needed — they're pure functions.
For API integration tests, fixtures here mock auth and DB dependencies.
"""

import pytest


@pytest.fixture
def dev_user_payload():
    """Standard dev user JWT payload."""
    return {"sub": "test-user", "org_id": "test-org"}

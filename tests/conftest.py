"""Session-scoped settings/auth/client fixtures, plus one fixture per
service client. Tests never import core.config / core.auth / core.http_client
directly -- they arrange via these fixtures instead.
"""
from __future__ import annotations

from typing import Iterator

import pytest

from api.payloads.users_payloads import build_user
from api.users_service import UsersService
from core.auth import TokenProvider
from core.config import Settings, load_settings
from core.http_client import ApiClient, ApiResponse
from core.recorder import RecorderProxy


@pytest.fixture(scope="session")
def settings(pytestconfig) -> Settings:
    return load_settings(pytestconfig)


@pytest.fixture(scope="session")
def token_provider(settings: Settings) -> TokenProvider:
    return TokenProvider(settings)


@pytest.fixture(scope="session")
def api_client(settings: Settings, token_provider: TokenProvider) -> ApiClient:
    # RecorderProxy forwards every request to whichever per-test Recorder
    # core.plugin has bound for the test currently running (see
    # core/recorder.py) -- ApiClient itself never knows about tests.
    return ApiClient(settings, token_provider, recorder=RecorderProxy())


@pytest.fixture
def users_service(api_client: ApiClient) -> UsersService:
    return UsersService(api_client)


@pytest.fixture
def cleanup_users(users_service: UsersService):
    """A test appends the id of any user it creates; they're deleted here
    after the test, regardless of pass/fail, so gorest.in doesn't
    accumulate test data across runs."""
    created_ids: list[int] = []
    yield created_ids
    for user_id in created_ids:
        users_service.delete_user(user_id)


@pytest.fixture
def created_user(users_service: UsersService) -> Iterator[ApiResponse]:
    """Arrange step for tests that need "a user that already exists" --
    creates one via the default payload builder and yields the raw create
    response, so the test does its own validation on it directly (assert_status,
    assert_field, assert_schema, ...). Deletes the user after the test
    regardless of pass/fail."""
    response = users_service.create_user(**build_user())

    yield response

    users_service.delete_user(response.json()["id"])

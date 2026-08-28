from api.payloads.users_payloads import build_user
from core.assertions import assert_field, assert_status
from core.auth import DEFAULT_ROLE, TokenProvider

EXPECTED_AUTH_ERROR = "Authentication failed. Please provide Authorization: Bearer <token> header."


def test_get_users_without_authorization_header(users_service):
    """TC-001: GET /public/v2/users with the Authorization header omitted."""
    response = users_service.list_users(headers={"Authorization": None})

    assert_status(response, 401)
    assert_field(response, "message", EXPECTED_AUTH_ERROR)

def test_get_users_with_empty_authorization_header(users_service):
    """TC-002: GET /public/v2/users with Authorization set to an empty string."""
    response = users_service.list_users(headers={"Authorization": ""})

    assert_status(response, 401)
    assert_field(response, "message", EXPECTED_AUTH_ERROR)

def test_get_users_with_malformed_authorization_scheme(users_service, token_provider: TokenProvider):
    """TC-003: GET /public/v2/users with Authorization not following the Bearer <token> scheme."""
    raw_token_response = users_service.list_users(
        headers={"Authorization": token_provider.get_token(DEFAULT_ROLE)}
    )
    assert_status(raw_token_response, 401)
    assert_field(raw_token_response, "message", EXPECTED_AUTH_ERROR)

    bearer_only_response = users_service.list_users(headers={"Authorization": "Bearer"})
    assert_status(bearer_only_response, 401)
    assert_field(bearer_only_response, "message", EXPECTED_AUTH_ERROR)

def test_create_user_without_authorization_header(users_service):
    """TC-004: POST /public/v2/users with the Authorization header omitted."""
    response = users_service.create_user(headers={"Authorization": None}, **build_user())

    assert_status(response, 401)
    assert_field(response, "message", EXPECTED_AUTH_ERROR)

def test_create_user_with_empty_authorization_header(users_service):
    """TC-005: POST /public/v2/users with Authorization set to an empty string."""
    response = users_service.create_user(headers={"Authorization": ""}, **build_user())

    assert_status(response, 401)
    assert_field(response, "message", EXPECTED_AUTH_ERROR)

def test_create_user_with_malformed_authorization_scheme(users_service, token_provider: TokenProvider):
    """TC-006: POST /public/v2/users with Authorization not following the Bearer <token> scheme."""
    raw_token_response = users_service.create_user(
        headers={"Authorization": token_provider.get_token(DEFAULT_ROLE)}, **build_user()
    )
    assert_status(raw_token_response, 401)
    assert_field(raw_token_response, "message", EXPECTED_AUTH_ERROR)

    bearer_only_response = users_service.create_user(headers={"Authorization": "Bearer"}, **build_user())
    assert_status(bearer_only_response, 401)
    assert_field(bearer_only_response, "message", EXPECTED_AUTH_ERROR)

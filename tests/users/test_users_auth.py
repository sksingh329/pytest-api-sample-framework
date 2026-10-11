from api.payloads.users_payloads import build_user
from core.assertions import assert_field, assert_status
from core.auth import DEFAULT_ROLE, TokenProvider

EXPECTED_AUTH_ERROR_MISSING_TOKEN = "Authentication failed. Please provide Authorization: Bearer <token> header."
EXPECTED_AUTH_ERROR_MALFORMED_TOKEN = "Authentication failed. Use Bearer token scheme."

def test_create_user_without_authorization_header(users_service):
    """TC-004: POST /public/v2/users with the Authorization header omitted."""
    response = users_service.create_user(headers={"Authorization": None}, **build_user())

    assert_status(response, 401)
    assert_field(response, "message", EXPECTED_AUTH_ERROR_MISSING_TOKEN)

def test_create_user_with_empty_authorization_header(users_service):
    """TC-005: POST /public/v2/users with Authorization set to an empty string."""
    response = users_service.create_user(headers={"Authorization": ""}, **build_user())

    assert_status(response, 401)
    assert_field(response, "message", EXPECTED_AUTH_ERROR_MISSING_TOKEN)

def test_create_user_with_malformed_authorization_scheme(users_service, token_provider: TokenProvider):
    """TC-006: POST /public/v2/users with Authorization not following the Bearer <token> scheme."""
    bearer_only_response = users_service.create_user(headers={"Authorization": "Bearer"}, **build_user())
    assert_status(bearer_only_response, 401)
    assert_field(bearer_only_response, "message", EXPECTED_AUTH_ERROR_MALFORMED_TOKEN)

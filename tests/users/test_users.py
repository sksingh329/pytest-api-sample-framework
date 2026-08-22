from api.payloads.users_payloads import build_user
from core.assertions import assert_field, assert_list, assert_response_time, assert_schema, assert_status


def test_list_users(users_service):
    response = users_service.list_users()

    assert_status(response, 200)
    assert_response_time(response, 2000)
    assert_list(response, "", unique_by="id")
    assert_schema(response, "users_list")

def test_create_user(created_user):
    assert_status(created_user, 201)
    assert_schema(created_user, "user")
    assert_field(created_user, "name", created_user.request_body["name"])
    assert_field(created_user, "email", created_user.request_body["email"])
    assert_field(created_user, "gender", created_user.request_body["gender"])
    assert_field(created_user, "status", created_user.request_body["status"])

def test_get_user(users_service, created_user):
    user_id = created_user.json()["id"]
    get_user_response = users_service.get_user(user_id=user_id)
    assert_status(get_user_response, 200)
    assert_schema(get_user_response, "user")
    assert_field(get_user_response, "id", user_id)
    assert_field(get_user_response, "name", created_user.request_body["name"])
    assert_field(get_user_response, "email", created_user.request_body["email"])
    assert_field(get_user_response, "gender", created_user.request_body["gender"])
    assert_field(get_user_response, "status", created_user.request_body["status"])

def test_replace_user(users_service, created_user):
    user_id = created_user.json()["id"]

    replacement = build_user(_seed=99)  # different values than created_user's, on purpose
    replace_response = users_service.update_user(user_id, **replacement)

    assert_status(replace_response, 200)
    assert_schema(replace_response, "user")
    assert_field(replace_response, "id", user_id)
    assert_field(replace_response, "name", replacement["name"])
    assert_field(replace_response, "email", replacement["email"])
    assert_field(replace_response, "gender", replacement["gender"])
    assert_field(replace_response, "status", replacement["status"])

"""UsersService: one method per gorest.in /users action, named for the
business action. Always returns ApiResponse, never a parsed dict.
"""
from __future__ import annotations

from api.base_service import BaseService
from api.constants import UsersEndpoints
from core.http_client import ApiResponse


class UsersService(BaseService):
    service_name = "users"

    def list_users(self, headers: dict | None = None, **params) -> ApiResponse:
        return self._get(UsersEndpoints.BASE, params=params, headers=headers)

    def get_user(self, user_id: int) -> ApiResponse:
        return self._get(UsersEndpoints.DETAIL.format(id=user_id))

    def create_user(self, headers: dict | None = None, **body) -> ApiResponse:
        return self._post(UsersEndpoints.BASE, json=body, headers=headers)

    def update_user(self, user_id: int, **body) -> ApiResponse:
        return self._put(UsersEndpoints.DETAIL.format(id=user_id), json=body)

    def delete_user(self, user_id: int) -> ApiResponse:
        return self._delete(UsersEndpoints.DETAIL.format(id=user_id))

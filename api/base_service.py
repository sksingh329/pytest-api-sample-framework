"""BaseService: thin get/post/put/delete helpers over an ApiClient, plus the
service name every request record is tagged with (for report grouping).
"""
from __future__ import annotations

from core.http_client import ApiClient, ApiResponse


class BaseService:
    service_name: str = "base"
    base_path: str = ""

    def __init__(self, client: ApiClient):
        self._client = client

    def _get(self, path: str = "", **kw) -> ApiResponse:
        return self._client.get(self.base_path + path, service=self.service_name, **kw)

    def _post(self, path: str = "", **kw) -> ApiResponse:
        return self._client.post(self.base_path + path, service=self.service_name, **kw)

    def _put(self, path: str = "", **kw) -> ApiResponse:
        return self._client.put(self.base_path + path, service=self.service_name, **kw)

    def _patch(self, path: str = "", **kw) -> ApiResponse:
        return self._client.patch(self.base_path + path, service=self.service_name, **kw)

    def _delete(self, path: str = "", **kw) -> ApiResponse:
        return self._client.delete(self.base_path + path, service=self.service_name, **kw)

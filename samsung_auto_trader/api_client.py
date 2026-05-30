import time
from typing import Any, Dict, Optional

import requests

from auth import AuthManager
from config import MAX_REQUEST_RETRIES, REQUEST_TIMEOUT_SECONDS
from logger import logger


class ApiResponse:
    def __init__(self, status_code: int, body: Dict[str, Any], raw: Optional[requests.Response] = None):
        self.status_code = status_code
        self.body = body
        self.raw = raw

    def is_success(self) -> bool:
        if self.status_code != 200:
            return False
        rt_cd = str(self.body.get("rt_cd", "0"))
        return rt_cd in ("0", "0000", "")


class ApiClient:
    def __init__(self, auth: AuthManager):
        self.auth = auth

    def get(self, path: str, params: Dict[str, Any], tr_id: str) -> ApiResponse:
        return self._request("GET", path, params=params, json_body=None, tr_id=tr_id)

    def post(self, path: str, json_body: Dict[str, Any], tr_id: str) -> ApiResponse:
        return self._request("POST", path, params=None, json_body=json_body, tr_id=tr_id)

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]],
        json_body: Optional[Dict[str, Any]],
        tr_id: str,
    ) -> ApiResponse:
        url = f"{self.auth.base_url}{path}"
        headers = self.auth.get_headers(tr_id)
        attempt = 0

        while attempt < MAX_REQUEST_RETRIES:
            attempt += 1
            try:
                response = requests.request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                    json=json_body,
                    timeout=REQUEST_TIMEOUT_SECONDS,
                )
                try:
                    body = response.json()
                except ValueError:
                    body = {}

                if response.status_code == 200:
                    return ApiResponse(response.status_code, body, raw=response)

                logger.warning(
                    "API request failed (attempt %s/%s): %s %s status=%s",
                    attempt,
                    MAX_REQUEST_RETRIES,
                    method,
                    url,
                    response.status_code,
                )
                if response.status_code < 500:
                    return ApiResponse(response.status_code, body, raw=response)

            except requests.RequestException as exc:
                logger.warning("API request exception (attempt %s/%s): %s", attempt, MAX_REQUEST_RETRIES, exc)

            time.sleep(2)

        logger.error("API request failed after %s attempts: %s %s", MAX_REQUEST_RETRIES, method, url)
        return ApiResponse(0, {}, raw=None)

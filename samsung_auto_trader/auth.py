import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

import requests

from config import (
    ACCOUNT_NUMBER,
    ACCOUNT_PRODUCT,
    API_BASE_URL,
    APPKEY,
    APPSECRET,
    REQUEST_TIMEOUT_SECONDS,
    TOKEN_CACHE_FILE,
    TOKEN_PATH,
)
from logger import logger


@dataclass
class TokenRecord:
    access_token: str
    issued_at: datetime
    expires_at: datetime
    environment: str


class AuthManager:
    def __init__(
        self,
        appkey: str,
        appsecret: str,
        base_url: str,
        account_number: str,
        account_product: str,
        cache_path: Path = TOKEN_CACHE_FILE,
    ):
        self.appkey = appkey
        self.appsecret = appsecret
        self.base_url = base_url
        self.account_number = account_number
        self.account_product = account_product
        self.cache_path = cache_path
        self._token_record: Optional[TokenRecord] = None

    @classmethod
    def from_env(cls) -> "AuthManager":
        return cls(
            appkey=APPKEY,
            appsecret=APPSECRET,
            base_url=API_BASE_URL,
            account_number=ACCOUNT_NUMBER,
            account_product=ACCOUNT_PRODUCT,
        )

    def get_token(self) -> str:
        if self._token_record and self._token_record.expires_at > datetime.now():
            logger.info("Reusing cached token")
            return self._token_record.access_token

        cache = self._read_cache()
        if cache:
            record = self._parse_cache(cache)
            if record and record.expires_at > datetime.now():
                logger.info("Reusing token from cache file")
                self._token_record = record
                return record.access_token

        logger.info("Requesting new token")
        return self._refresh_token()

    def get_headers(self, tr_id: str) -> Dict[str, str]:
        token = self.get_token()
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "authorization": f"Bearer {token}",
            "appkey": self.appkey,
            "appsecret": self.appsecret,
            "custtype": "P",
            "tr_id": tr_id,
            "tr_cont": "",
        }

    def _read_cache(self) -> Dict[str, Any]:
        if not self.cache_path.exists():
            return {}

        try:
            with self.cache_path.open("r", encoding="utf-8") as handle:
                return json.load(handle)
        except (OSError, ValueError) as exc:
            logger.warning("Unable to read token cache: %s", exc)
            return {}

    def _save_cache(self, data: Dict[str, Any]) -> None:
        try:
            with self.cache_path.open("w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2)
        except OSError as exc:
            logger.warning("Unable to write token cache: %s", exc)

    def _parse_cache(self, cache: Dict[str, Any]) -> Optional[TokenRecord]:
        access_token = cache.get("access_token")
        expires_at = cache.get("expires_at")
        environment = cache.get("environment")
        if not access_token or not expires_at or environment != "demo":
            return None

        try:
            expires_at_dt = datetime.fromisoformat(expires_at)
        except ValueError:
            return None

        issued_at = datetime.fromisoformat(cache.get("issued_at")) if cache.get("issued_at") else datetime.now()
        return TokenRecord(
            access_token=access_token,
            issued_at=issued_at,
            expires_at=expires_at_dt,
            environment=environment,
        )

    def _refresh_token(self) -> str:
        url = f"{self.base_url}{TOKEN_PATH}"
        body = {
            "grant_type": "client_credentials",
            "appkey": self.appkey,
            "appsecret": self.appsecret,
        }

        try:
            response = requests.post(url, json=body, timeout=REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.error("Token request failed: %s", exc)
            raise RuntimeError("Unable to fetch token") from exc

        try:
            data = response.json()
        except ValueError as exc:
            logger.error("Token response decode failed: %s", exc)
            raise RuntimeError("Unable to decode token response") from exc

        token = data.get("access_token") or data.get("accessToken")
        if not token:
            raise RuntimeError("Access token missing in token response")

        expires_in = data.get("expires_in")
        expires_at = (
            datetime.now() + timedelta(seconds=int(expires_in))
            if expires_in
            else datetime.now() + timedelta(hours=23, minutes=59)
        )

        self._token_record = TokenRecord(
            access_token=token,
            issued_at=datetime.now(),
            expires_at=expires_at,
            environment="demo",
        )

        self._save_cache(
            {
                "access_token": token,
                "issued_at": self._token_record.issued_at.isoformat(),
                "expires_at": self._token_record.expires_at.isoformat(),
                "environment": "demo",
                "account_number": self.account_number,
                "account_product": self.account_product,
            }
        )
        logger.info("Saved new token to cache")
        return token

import os
from datetime import time as dt_time
from pathlib import Path
from typing import Final

BASE_DIR: Final[Path] = Path(__file__).resolve().parent
TOKEN_CACHE_FILE: Final[Path] = BASE_DIR / "token_cache.json"

API_BASE_URL: Final[str] = "https://openapivts.koreainvestment.com:29443"
TOKEN_PATH: Final[str] = "/oauth2/tokenP"
QUOTE_PATH: Final[str] = "/uapi/domestic-stock/v1/quotations/inquire-asking-price-exp-ccn"
BALANCE_PATH: Final[str] = "/uapi/domestic-stock/v1/trading/inquire-balance"
ORDER_PATH: Final[str] = "/uapi/domestic-stock/v1/trading/order-cash"

TRADING_SYMBOL: Final[str] = "005930"
ORDER_QUANTITY: Final[int] = 1
PRICE_OFFSET: Final[int] = 1000
ORDER_DIVISION: Final[str] = "00"  # 지정가
SLL_TYPE: Final[str] = "01"  # 일반매도

TRADING_START: Final[dt_time] = dt_time(hour=9, minute=10)
TRADING_END: Final[dt_time] = dt_time(hour=15, minute=30)
POLL_INTERVAL_SECONDS: Final[int] = 300
ORDER_COOLDOWN_SECONDS: Final[int] = 900
REQUEST_TIMEOUT_SECONDS: Final[int] = 10
MAX_REQUEST_RETRIES: Final[int] = 2


def get_env_value(name: str, required: bool = False, default: str = "") -> str:
    value = os.getenv(name, default)
    if required and not value:
        raise EnvironmentError(f"Environment variable {name} is required")
    return value.strip()

APPKEY: Final[str] = get_env_value("GH_APPKEY", required=True)
APPSECRET: Final[str] = get_env_value("GH_APPSECRET", required=True)
ACCOUNT_NUMBER: Final[str] = get_env_value("GH_ACCOUNT", required=True)
ACCOUNT_PRODUCT: Final[str] = get_env_value("GH_ACNT_PRDT_CD", default="01")

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from api_client import ApiClient, ApiResponse
from config import QUOTE_PATH, TRADING_SYMBOL
from logger import logger


@dataclass
class PriceQuote:
    symbol: str
    bid_price: float
    ask_price: float
    last_price: float
    timestamp: str
    raw: Dict[str, Any]


class MarketDataClient:
    def __init__(self, client: ApiClient):
        self.client = client

    def get_current_quote(self, symbol: str = TRADING_SYMBOL) -> PriceQuote:
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": symbol,
        }

        response = self.client.get(QUOTE_PATH, params=params, tr_id="FHKST01010200")
        if not response.is_success():
            logger.error("Market quote request failed: %s", response.body)
            raise RuntimeError("Unable to fetch market quote")

        payload = self._extract_payload(response.body)
        bid_price = self._to_float(payload, ["bidp1", "bidp", "bid_price", "bid"])
        ask_price = self._to_float(payload, ["askp1", "askp", "ask_price", "ask"])
        last_price = self._to_float(payload, ["prpr", "stck_prpr", "last_price", "last"])
        timestamp = payload.get("ctm") or payload.get("time") or datetime.now().isoformat()

        effective_price = ask_price or bid_price or last_price
        if effective_price <= 0:
            logger.warning("Market quote returned an unexpected price: %s", payload)

        logger.info(
            "Current quote %s bid=%s ask=%s last=%s",
            symbol,
            bid_price,
            ask_price,
            last_price,
        )

        return PriceQuote(
            symbol=symbol,
            bid_price=bid_price,
            ask_price=ask_price,
            last_price=effective_price,
            timestamp=timestamp,
            raw=payload,
        )

    def _extract_payload(self, body: Dict[str, Any]) -> Dict[str, Any]:
        for key in ("output1", "output", "output2"):
            data = body.get(key)
            if data:
                if isinstance(data, list):
                    return data[0] if data else {}
                if isinstance(data, dict):
                    return data
        return body if isinstance(body, dict) else {}

    def _to_float(self, payload: Dict[str, Any], keys: List[str]) -> float:
        for key in keys:
            value = payload.get(key)
            if value is None:
                continue
            try:
                return float(value)
            except (ValueError, TypeError):
                continue
        return 0.0

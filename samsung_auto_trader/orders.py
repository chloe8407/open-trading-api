from dataclasses import dataclass
from typing import Any, Dict, Optional

from api_client import ApiClient
from config import ACCOUNT_NUMBER, ACCOUNT_PRODUCT, ORDER_PATH, ORDER_DIVISION, SLL_TYPE
from logger import logger


@dataclass
class OrderResult:
    success: bool
    order_id: Optional[str]
    execution_message: str
    raw: Dict[str, Any]


class OrderClient:
    def __init__(self, client: ApiClient):
        self.client = client

    def place_buy_order(self, symbol: str, quantity: int, price: int) -> OrderResult:
        return self._send_order(symbol, quantity, price, order_side="buy")

    def place_sell_order(self, symbol: str, quantity: int, price: int) -> OrderResult:
        return self._send_order(symbol, quantity, price, order_side="sell")

    def _send_order(self, symbol: str, quantity: int, price: int, order_side: str) -> OrderResult:
        if quantity <= 0 or price <= 0:
            message = "Order quantity and price must be positive"
            logger.error(message)
            return OrderResult(success=False, order_id=None, execution_message=message, raw={})

        tr_id = "VTTC0802U" if order_side == "buy" else "VTTC0801U"
        payload: Dict[str, Any] = {
            "CANO": ACCOUNT_NUMBER,
            "ACNT_PRDT_CD": ACCOUNT_PRODUCT,
            "PDNO": symbol,
            "ORD_DVSN": ORDER_DIVISION,
            "ORD_QTY": str(quantity),
            "ORD_UNPR": str(price),
        }

        if order_side == "sell":
            payload["SLL_TYPE"] = SLL_TYPE

        logger.info(
            "Submitting %s order %s %s @ %s",
            order_side,
            quantity,
            symbol,
            price,
        )

        response = self.client.post(ORDER_PATH, json_body=payload, tr_id=tr_id)
        success = response.is_success()
        body = response.body
        details = self._extract_output(body)

        order_id = details.get("ordno") or details.get("orgn_ordno") or details.get("order_no")
        msg1 = details.get("msg1") or details.get("message") or body.get("msg1") or ""

        if not success:
            logger.error("Order request failed: %s", body)

        return OrderResult(
            success=success,
            order_id=order_id,
            execution_message=msg1,
            raw=body,
        )

    def _extract_output(self, body: Dict[str, Any]) -> Dict[str, Any]:
        for key in ("output", "output1", "output2"):
            value = body.get(key)
            if isinstance(value, dict):
                return value
            if isinstance(value, list) and value:
                return value[0]
        return body

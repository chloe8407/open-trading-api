from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from api_client import ApiClient
from config import ACCOUNT_NUMBER, ACCOUNT_PRODUCT, BALANCE_PATH
from logger import logger


@dataclass
class Holding:
    symbol: str
    quantity: int
    average_price: float
    current_price: float
    raw: Dict[str, Any]


@dataclass
class AccountSnapshot:
    available_cash: float
    holdings: List[Holding]

    @property
    def total_shares(self) -> int:
        return sum(h.quantity for h in self.holdings)

    def holding_for_symbol(self, symbol: str) -> Optional[Holding]:
        for holding in self.holdings:
            if holding.symbol == symbol:
                return holding
        return None


class AccountClient:
    def __init__(self, client: ApiClient):
        self.client = client

    def get_balance_snapshot(self, symbol: str) -> AccountSnapshot:
        params = {
            "CANO": ACCOUNT_NUMBER,
            "ACNT_PRDT_CD": ACCOUNT_PRODUCT,
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",
            "INQR_DVSN": "00",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "00",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        }

        response = self.client.get(BALANCE_PATH, params=params, tr_id="VTTC8434R")
        if not response.is_success():
            logger.error("Balance request failed: %s", response.body)
            raise RuntimeError("Unable to fetch account balance")

        body = response.body
        summary = self._normalize_section(body, ["output2", "output"])
        holdings_data = self._normalize_section(body, ["output1"])

        holdings = self._parse_holdings(holdings_data, symbol)
        available_cash = self._parse_available_cash(summary)

        logger.info(
            "Balance snapshot for %s available_cash=%s holdings=%s",
            symbol,
            available_cash,
            [h.quantity for h in holdings],
        )

        return AccountSnapshot(available_cash=available_cash, holdings=holdings)

    def _normalize_section(self, body: Dict[str, Any], keys: List[str]) -> Any:
        for key in keys:
            section = body.get(key)
            if section is not None:
                return section
        return {}

    def _parse_holdings(self, holdings_data: Any, symbol: str) -> List[Holding]:
        listings = []
        if isinstance(holdings_data, dict):
            holdings_data = [holdings_data]

        if not isinstance(holdings_data, list):
            return listings

        for item in holdings_data:
            if not isinstance(item, dict):
                continue
            symbol_code = item.get("pdno") or item.get("pd_no") or item.get("isu_cd") or ""
            if symbol_code != symbol:
                continue
            quantity = self._to_int(item.get("hldg_qty") or item.get("hold_qty") or item.get("pchs_qty") or item.get("ord_qty") or 0)
            average_price = self._to_float(item.get("pchs_avg_pric") or item.get("avrg_pric") or item.get("prpr") or item.get("ord_prc") or 0)
            current_price = self._to_float(item.get("prpr") or item.get("last_price") or 0)
            listings.append(
                Holding(
                    symbol=symbol_code,
                    quantity=quantity,
                    average_price=average_price,
                    current_price=current_price,
                    raw=item,
                )
            )
        return listings

    def _parse_available_cash(self, summary: Any) -> float:
        if not isinstance(summary, dict):
            return 0.0
        keys = [
            "ord_psbl_cash",
            "dnca_tot_amt",
            "nxdy_excc_amt",
            "prvs_rcdl_excc_amt",
        ]
        for key in keys:
            value = summary.get(key)
            if value is not None:
                return self._to_float(value)
        return 0.0

    def _to_int(self, value: Any) -> int:
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return 0

    def _to_float(self, value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

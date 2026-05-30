from datetime import datetime, timedelta
from time import sleep
from typing import Optional
from zoneinfo import ZoneInfo

from account import AccountClient, AccountSnapshot
from api_client import ApiClient
from config import (
    ORDER_COOLDOWN_SECONDS,
    ORDER_QUANTITY,
    PRICE_OFFSET,
    POLL_INTERVAL_SECONDS,
    TRADING_END,
    TRADING_START,
    TRADING_SYMBOL,
)
from logger import logger
from market_data import MarketDataClient, PriceQuote
from orders import OrderClient

KST = ZoneInfo("Asia/Seoul")


class AutoTrader:
    def __init__(self, client: ApiClient):
        self.client = client
        self.market_data = MarketDataClient(client)
        self.account = AccountClient(client)
        self.orders = OrderClient(client)
        self.last_order_time: Optional[datetime] = None

    def run(self) -> None:
        logger.info("Auto trader started")
        while True:
            now = datetime.now(KST)
            if now >= self._end_time(now):
                logger.info("Trading window closed at %s", TRADING_END)
                break

            if now < self._start_time(now):
                wait_seconds = (self._start_time(now) - now).total_seconds()
                logger.info("Trading window has not opened yet, waiting %.0f seconds", wait_seconds)
                sleep(min(wait_seconds, 60))
                continue

            try:
                self._execute_cycle(now)
            except Exception as exc:
                logger.error("Trading cycle failed: %s", exc)

            if datetime.now(KST) >= self._end_time(now):
                logger.info("Trading window closed during execution")
                break

            logger.info("Sleeping for %s seconds before next cycle", POLL_INTERVAL_SECONDS)
            sleep(POLL_INTERVAL_SECONDS)

        logger.info("Auto trader stopped")

    def _execute_cycle(self, now: datetime) -> None:
        quote = self.market_data.get_current_quote(TRADING_SYMBOL)
        snapshot_before = self.account.get_balance_snapshot(TRADING_SYMBOL)

        if self._should_place_orders(now):
            self._place_order_cycle(quote, snapshot_before)
        else:
            logger.info("Order cooldown active, skipping new orders")

        snapshot_after = self.account.get_balance_snapshot(TRADING_SYMBOL)
        self._log_execution(snapshot_before, snapshot_after)

    def _place_order_cycle(self, quote: PriceQuote, snapshot: AccountSnapshot) -> None:
        buy_price = max(1, int(quote.last_price - PRICE_OFFSET))
        sell_price = int(quote.last_price + PRICE_OFFSET)

        buy_result = self.orders.place_buy_order(TRADING_SYMBOL, ORDER_QUANTITY, buy_price)
        logger.info("Buy order result success=%s order_id=%s message=%s", buy_result.success, buy_result.order_id, buy_result.execution_message)

        sell_result = None
        holding = snapshot.holding_for_symbol(TRADING_SYMBOL)
        if holding and holding.quantity >= ORDER_QUANTITY:
            sell_result = self.orders.place_sell_order(TRADING_SYMBOL, ORDER_QUANTITY, sell_price)
            logger.info("Sell order result success=%s order_id=%s message=%s", sell_result.success, sell_result.order_id, sell_result.execution_message)
        else:
            logger.info(
                "Skipping sell order because holding is insufficient (%s shares available)",
                holding.quantity if holding else 0,
            )

        self.last_order_time = datetime.now(KST)

    def _should_place_orders(self, now: datetime) -> bool:
        if self.last_order_time is None:
            return True
        cooldown_end = self.last_order_time + timedelta(seconds=ORDER_COOLDOWN_SECONDS)
        return now >= cooldown_end

    def _log_execution(self, before: AccountSnapshot, after: AccountSnapshot) -> None:
        before_qty = before.holding_for_symbol(TRADING_SYMBOL).quantity if before.holding_for_symbol(TRADING_SYMBOL) else 0
        after_qty = after.holding_for_symbol(TRADING_SYMBOL).quantity if after.holding_for_symbol(TRADING_SYMBOL) else 0
        logger.info(
            "Holdings before=%s after=%s available_cash before=%s after=%s",
            before_qty,
            after_qty,
            before.available_cash,
            after.available_cash,
        )

        if after_qty != before_qty or after.available_cash != before.available_cash:
            logger.info("Execution appears to have occurred or account was updated")
        else:
            logger.info("No balance or holding change detected after orders")

    def _start_time(self, now: datetime) -> datetime:
        return datetime.combine(now.date(), TRADING_START, tzinfo=KST)

    def _end_time(self, now: datetime) -> datetime:
        return datetime.combine(now.date(), TRADING_END, tzinfo=KST)

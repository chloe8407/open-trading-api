from auth import AuthManager
from api_client import ApiClient
from logger import configure_logger, logger
from trader import AutoTrader


def main() -> None:
    configure_logger()
    logger.info("Starting Samsung Auto Trader")

    auth = AuthManager.from_env()
    client = ApiClient(auth)
    trader = AutoTrader(client)
    trader.run()


if __name__ == "__main__":
    main()

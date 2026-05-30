# Samsung Auto Trader

A simple mock trading system for Samsung Electronics (`005930`) using the Korea Investment & Securities Open API.

## What this project does

- Authenticates to the KIS mock trading API using environment variables
- Caches the bearer token for same-day reuse
- Polls the current market price for `005930`
- Checks balance and holdings before order submission
- Places a limit buy order at `current_price - 1000`
- Places a limit sell order at `current_price + 1000` when holdings exist
- Verifies execution by refreshing holdings/balance after orders
- Runs only during the trading window: `09:10` to `15:30`

## Folder structure

- `main.py` - entry point
- `config.py` - environment and runtime settings
- `auth.py` - token manager and token cache
- `api_client.py` - HTTP wrapper for KIS REST API calls
- `market_data.py` - price quote retrieval
- `account.py` - balance and holdings snapshot
- `orders.py` - buy/sell order submission
- `trader.py` - trading loop and business logic
- `logger.py` - logger configuration
- `token_cache.json` - local token cache file

## Environment variables

Set the following before running:

- `GH_ACCOUNT` - mock trading account number
- `GH_APPKEY` - mock trading API app key
- `GH_APPSECRET` - mock trading API app secret
- `GH_ACNT_PRDT_CD` - optional account product code (default: `01`)

Example:

```bash
export GH_ACCOUNT="12345678"
export GH_APPKEY="your_appkey"
export GH_APPSECRET="your_appsecret"
export GH_ACNT_PRDT_CD="01"
```

## Install

```bash
cd samsung_auto_trader
python -m pip install -r requirements.txt
```

## Run

```bash
python main.py
```

The system will wait until `09:10` local time before trading and stop automatically after `15:30`.

## Notes

- This is a polling-only, mock trading implementation.
- It avoids unnecessary token refresh and uses conservative polling.
- The sell order is only submitted if the account already holds enough shares.

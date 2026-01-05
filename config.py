import os

TRADING_ENV = os.getenv("TRADING_ENV", "demo")
TRADING_ENABLED = os.getenv("TRADING_ENABLED", "false").lower() == "true"

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")

BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY", "")
BINANCE_BASE_URL = os.getenv("BINANCE_BASE_URL") or "https://demo-fapi.binance.com"

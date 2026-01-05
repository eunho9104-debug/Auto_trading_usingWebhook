import requests

# Live or Demo setup
import os

ENV = os.getenv("TRADING_ENV", "demo").lower()

if ENV == "live":
    API_KEY = os.getenv("BINANCE_API_KEY")
    SECRET = os.getenv("BINANCE_SECRET_KEY")
    BASE_URL = "https://fapi.binance.com"
else:
    API_KEY = os.getenv("BINANCE_DEMO_API_KEY")
    SECRET = os.getenv("BINANCE_DEMO_SECRET_KEY")
    BASE_URL = os.getenv("BINANCE_DEMO_BASE_URL", "https://demo-fapi.binance.com")



def execute_trade(data):
    strategy = data.get("strategy")
    side = data.get("side")
    quantity = float(data.get("quantity"))
    symbol = data.get("symbol")

    # 예시: 바이낸스 API 호출
    print(f"🚀 Executing {side} for {symbol} using {strategy}, quantity: {quantity}")

    # 여기에 실제 거래소 API 연동 로직 추가
    # 예: binance_client.order_market_buy(symbol=symbol, quantity=quantity)

    return {
        "strategy": strategy,
        "side": side,
        "symbol": symbol,
        "quantity": quantity,
        "status": "executed"
    }
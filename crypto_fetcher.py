from dotenv import load_dotenv
import os

load_dotenv()
print(os.getenv("BINANCE_API_KEY"))

api_key = os.getenv('BINANCE_API_KEY')
api_secret = os.getenv('BINANCE_SECRET_KEY')

import requests
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.binance.com/api/v3/klines"
SYMBOLS = [
    "ETHUSDT", "ETCUSDT", "LTCUSDT", "XRPUSDT", "DOGEUSDT",
    "MOVEUSDT", "SOLUSDT",
    "PUMPUSDT", "BNBUSDT", "AVNTUSDT" ]
 # 원하는 코인 리스트
INTERVALS = ["1h", "30m", "15m", "5m", "3m"]  # 시간봉 리스트

def fetch_ohlcv(symbol, interval, limit=500):
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }
    response = requests.get(BASE_URL, params=params)
    response.raise_for_status()
    data = response.json()

    df = pd.DataFrame(data, columns=[
        "timestamp", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "number_of_trades",
        "taker_buy_base_volume", "taker_buy_quote_volume", "ignore"
    ])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    return df[["open", "high", "low", "close", "volume"]]

def save_to_csv(df, symbol, interval):
    os.makedirs("data", exist_ok=True)
    filename = f"data/{symbol}_{interval}.csv"
    df.to_csv(filename)
    print(f"✅ 저장 완료: {filename}")

if __name__ == "__main__":
    for symbol in SYMBOLS:
        for interval in INTERVALS:
            try:
                df = fetch_ohlcv(symbol, interval)
                save_to_csv(df, symbol, interval)
            except Exception as e:
                print(f"⚠️ {symbol} {interval} 오류 발생: {e}")
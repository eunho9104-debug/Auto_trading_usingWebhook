import os
import time
import hmac
import hashlib
import urllib.parse
import requests
from decimal import Decimal, ROUND_DOWN
from dotenv import load_dotenv
load_dotenv()

# =========================
# 0) ENV (환경변수)
# =========================
TRADING_ENV = os.getenv("TRADING_ENV", "demo").lower()

if TRADING_ENV == "live":
    API_KEY = os.getenv("BINANCE_API_KEY")
    API_SECRET = os.getenv("BINANCE_SECRET_KEY")
    BASE_URL = "https://fapi.binance.com"
else:
    API_KEY = os.getenv("BINANCE_DEMO_API_KEY")
    API_SECRET = os.getenv("BINANCE_DEMO_SECRET_KEY")
    BASE_URL = os.getenv("BINANCE_DEMO_BASE_URL", "https://demo-fapi.binance.com")

# 안전장치: 심볼 고정
ALLOWED_SYMBOL = os.getenv("ALLOWED_SYMBOL", "ETHUSDT").upper()

# 기본 주문 규모(테스트용): quantity가 payload에 없으면 notional로 계산
DEFAULT_NOTIONAL_USDT = float(os.getenv("DEFAULT_NOTIONAL_USDT", "20"))  # 20 USDT
LEVERAGE = int(os.getenv("LEVERAGE", "3"))  # 테스트는 낮게 추천
MARGIN_TYPE = os.getenv("MARGIN_TYPE", "ISOLATED").upper()  # ISOLATED or CROSSED

# 지정가 사다리 설정: 1→2→3틱, 각 단계 대기 후 미체결이면 취소
LADDER_TICKS = [1, 2, 3]
WAIT_PER_ATTEMPT_SEC = float(os.getenv("WAIT_PER_ATTEMPT_SEC", "2.0"))

SESSION = requests.Session()
SESSION.headers.update({"X-MBX-APIKEY": API_KEY or ""})

# 캐시(심볼별 tick/step)
_symbol_filters_cache = {}


# =========================
# 1) 유틸: 서명(HMAC) & 요청
# =========================
def _sign(params: dict) -> str:
    """HMAC(Hash-based Message Authentication Code, 해시 기반 메시지 인증 코드) 서명 생성"""
    query = urllib.parse.urlencode(params, doseq=True)
    signature = hmac.new(API_SECRET.encode("utf-8"), query.encode("utf-8"), hashlib.sha256).hexdigest()
    return signature

def _signed_request(method: str, path: str, params: dict):
    if not API_KEY or not API_SECRET:
        raise RuntimeError("API_KEY/API_SECRET 환경변수가 비어 있습니다. (.env 확인)")

    params = dict(params)
    params["timestamp"] = int(time.time() * 1000)
    params["recvWindow"] = 5000
    params["signature"] = _sign(params)

    url = f"{BASE_URL}{path}"
    if method.upper() == "GET":
        r = SESSION.get(url, params=params, timeout=10)
    elif method.upper() == "POST":
        r = SESSION.post(url, params=params, timeout=10)
    elif method.upper() == "DELETE":
        r = SESSION.delete(url, params=params, timeout=10)
    else:
        raise ValueError("Unsupported method")

    # 바이낸스는 에러 시 JSON으로 msg/code 내려줌
    if r.status_code >= 400:
        try:
            err = r.json()
        except Exception:
            err = {"raw": r.text}
        raise RuntimeError(f"Binance API error {r.status_code}: {err}")

    return r.json()

def _public_get(path: str, params: dict = None):
    url = f"{BASE_URL}{path}"
    r = SESSION.get(url, params=params or {}, timeout=10)
    if r.status_code >= 400:
        raise RuntimeError(f"Public API error {r.status_code}: {r.text}")
    return r.json()


# =========================
# 2) 심볼 필터(틱/스텝) 조회 & 라운딩
# =========================
def _get_symbol_filters(symbol: str):
    symbol = symbol.upper()
    if symbol in _symbol_filters_cache:
        return _symbol_filters_cache[symbol]

    info = _public_get("/fapi/v1/exchangeInfo")
    s = next(x for x in info["symbols"] if x["symbol"] == symbol)

    tick_size = None
    step_size = None
    min_qty = None

    for f in s["filters"]:
        if f["filterType"] == "PRICE_FILTER":
            tick_size = Decimal(f["tickSize"])
        if f["filterType"] == "LOT_SIZE":
            step_size = Decimal(f["stepSize"])
            min_qty = Decimal(f["minQty"])

    if tick_size is None or step_size is None:
        raise RuntimeError("tickSize/stepSize를 exchangeInfo에서 찾지 못했습니다.")

    _symbol_filters_cache[symbol] = {
        "tick": tick_size,
        "step": step_size,
        "min_qty": min_qty or Decimal("0")
    }
    return _symbol_filters_cache[symbol]

def _floor_to_step(value: Decimal, step: Decimal) -> Decimal:
    return (value / step).to_integral_value(rounding=ROUND_DOWN) * step

def _round_price_to_tick(price: Decimal, tick: Decimal) -> Decimal:
    return (price / tick).to_integral_value(rounding=ROUND_DOWN) * tick


# =========================
# 3) 계정/포지션 관련
# =========================
def _ensure_leverage_and_margin(symbol: str):
    """레버리지/마진 타입을 미리 맞춰둠(에러나면 무시하지 말고 확인)"""
    symbol = symbol.upper()
    try:
        _signed_request("POST", "/fapi/v1/marginType", {"symbol": symbol, "marginType": MARGIN_TYPE})
    except RuntimeError as e:
        # 이미 설정되어 있으면 에러가 날 수 있음 -> 그 경우는 무시 가능
        if "No need to change margin type" not in str(e):
            raise
    _signed_request("POST", "/fapi/v1/leverage", {"symbol": symbol, "leverage": LEVERAGE})

def _get_position_amt(symbol: str) -> Decimal:
    """현재 포지션 수량(양수=롱, 음수=숏, 0=없음)"""
    symbol = symbol.upper()
    positions = _signed_request("GET", "/fapi/v2/positionRisk", {})
    p = next(x for x in positions if x["symbol"] == symbol)
    return Decimal(p["positionAmt"])


# =========================
# 4) 주문 관련(지정가 사다리 + 시장가 전환)
# =========================
def _place_limit_order(symbol: str, side: str, qty: Decimal, price: Decimal, reduce_only: bool, client_id: str = None):
    params = {
        "symbol": symbol,
        "side": side.upper(),             # BUY / SELL
        "type": "LIMIT",
        "timeInForce": "GTC",
        "quantity": str(qty),
        "price": str(price),
        "reduceOnly": "true" if reduce_only else "false",
        "newOrderRespType": "RESULT",
    }
    if client_id:
        params["newClientOrderId"] = client_id[:36]  # 너무 길면 잘림

    return _signed_request("POST", "/fapi/v1/order", params)

def _place_market_order(symbol: str, side: str, qty: Decimal, reduce_only: bool, client_id: str = None):
    params = {
        "symbol": symbol,
        "side": side.upper(),
        "type": "MARKET",
        "quantity": str(qty),
        "reduceOnly": "true" if reduce_only else "false",
        "newOrderRespType": "RESULT",
    }
    if client_id:
        params["newClientOrderId"] = client_id[:36]

    return _signed_request("POST", "/fapi/v1/order", params)

def _get_order(symbol: str, order_id: int):
    return _signed_request("GET", "/fapi/v1/order", {"symbol": symbol, "orderId": order_id})

def _cancel_order(symbol: str, order_id: int):
    return _signed_request("DELETE", "/fapi/v1/order", {"symbol": symbol, "orderId": order_id})

def _get_mark_price(symbol: str) -> Decimal:
    data = _public_get("/fapi/v1/ticker/price", {"symbol": symbol})
    return Decimal(data["price"])


# =========================
# 5) 메인: execute_trade
# =========================
def execute_trade(data: dict):
    """
    기대 payload 예시(진입):
    {
      "symbol": "ETHUSDT",
      "side": "buy",
      "quantity": "0.05",
      "price_ref": "현재가근처값",   # 선택
      "client_id": "abc123",       # 선택
      "intent": "entry"            # 선택
    }

    청산 payload는 아래 중 하나로 표시(둘 중 하나만 있어도 됨):
      - "intent": "exit"
      - "reduce_only": true
    """
    symbol = (data.get("symbol") or ALLOWED_SYMBOL).upper()
    if symbol != ALLOWED_SYMBOL:
        raise RuntimeError(f"허용되지 않은 symbol입니다: {symbol} (허용: {ALLOWED_SYMBOL})")

    # 진입/청산 의도
    intent = (data.get("intent") or "entry").lower()
    reduce_only = bool(data.get("reduce_only")) or intent == "exit"

    # side 결정
    side = (data.get("side") or "").lower()
    if side not in ("buy", "sell", ""):
        raise RuntimeError("side는 buy/sell 이어야 합니다.")

    # 거래 시작 전 레버리지/마진 타입 정렬
    _ensure_leverage_and_margin(symbol)

    filters = _get_symbol_filters(symbol)
    tick = filters["tick"]
    step = filters["step"]
    min_qty = filters["min_qty"]

    # 기준 가격
    if data.get("price_ref"):
        price_ref = Decimal(str(data["price_ref"]))
    else:
        price_ref = _get_mark_price(symbol)

    # 청산이면: 현재 포지션을 조회해서 수량/방향 자동 결정(선생님이 원하는 “그 포지션 그대로 나오기”)
    if reduce_only:
        pos_amt = _get_position_amt(symbol)
        if pos_amt == 0:
            return {"status": "ignored", "reason": "no position to reduce", "symbol": symbol}

        qty = abs(pos_amt)
        # stepSize에 맞춰 버림
        qty = _floor_to_step(qty, step)
        if qty <= 0:
            return {"status": "ignored", "reason": "qty too small after step rounding", "symbol": symbol}

        # 포지션 방향에 따라 청산 side 자동
        # 롱(+): SELL로 줄임 / 숏(-): BUY로 줄임
        side_effective = "SELL" if pos_amt > 0 else "BUY"

    else:
        # 진입이면: payload quantity가 있으면 그걸 사용, 없으면 notional로 계산
        if data.get("quantity"):
            qty = Decimal(str(data["quantity"]))
        else:
            # notional / price_ref = 수량
            qty = Decimal(str(DEFAULT_NOTIONAL_USDT)) / price_ref

        # stepSize에 맞춰 버림
        qty = _floor_to_step(qty, step)
        if qty < min_qty:
            raise RuntimeError(f"수량이 최소 주문 수량(minQty)보다 작습니다: qty={qty}, minQty={min_qty}")

        # side는 payload에서 필수(진입은 buy/sell 명확해야 함)
        if side == "":
            raise RuntimeError("진입(entry) 주문에는 side(buy/sell)가 필요합니다.")
        side_effective = side.upper()

    # client_id(중복 방지용) - 있으면 주문에 넣음
    client_id = data.get("client_id") or data.get("order_id") or None

    # 공격적 지정가 사다리: 1→2→3틱, 미체결이면 취소 후 다음 단계, 마지막은 시장가 전환
    last_order = None
    for n in LADDER_TICKS:
        if side_effective == "BUY":
            target_price = price_ref + (Decimal(n) * tick)
        else:
            target_price = price_ref - (Decimal(n) * tick)

        target_price = _round_price_to_tick(target_price, tick)

        # LIMIT 주문
        resp = _place_limit_order(
            symbol=symbol,
            side=side_effective,
            qty=qty,
            price=target_price,
            reduce_only=reduce_only,
            client_id=client_id
        )
        last_order = resp
        order_id = int(resp["orderId"])

        time.sleep(WAIT_PER_ATTEMPT_SEC)

        # 체결 확인
        o = _get_order(symbol, order_id)
        status = o.get("status")
        if status == "FILLED":
            return {
                "status": "filled_limit",
                "symbol": symbol,
                "side": side_effective,
                "reduce_only": reduce_only,
                "qty": str(qty),
                "price": str(target_price),
                "order": o
            }

        # 미체결/부분체결이면 취소하고 다음 단계
        try:
            _cancel_order(symbol, order_id)
        except Exception:
            pass  # 취소 실패는 다음 로직에서 다시 확인 가능

    # 3틱도 안 되면 시장가 전환(A)
    mr = _place_market_order(
        symbol=symbol,
        side=side_effective,
        qty=qty,
        reduce_only=reduce_only,
        client_id=client_id
    )
    return {
        "status": "filled_market_fallback",
        "symbol": symbol,
        "side": side_effective,
        "reduce_only": reduce_only,
        "qty": str(qty),
        "order": mr
    }


if __name__ == "__main__":
    print("=== trader.py started ===")
    print("TRADING_ENV =", TRADING_ENV)
    print("BASE_URL =", BASE_URL)
    print("API loaded? =", bool(API_KEY), bool(API_SECRET))
print("DEMO key exists?", bool(os.getenv("BINANCE_DEMO_API_KEY")), bool(os.getenv("BINANCE_DEMO_SECRET_KEY")))
print("LIVE key exists?", bool(os.getenv("BINANCE_API_KEY")), bool(os.getenv("BINANCE_SECRET_KEY")))

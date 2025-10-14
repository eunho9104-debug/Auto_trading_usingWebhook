"# Auto_trading_usingWebhook" 

# 📈 Auto Trading using Webhook

자동매매 전략을 트레이딩뷰 + 파이썬으로 구현한 프로젝트입니다.  
전략은 트레이딩뷰에서 설계하고, 웹훅을 통해 파이썬 서버로 신호를 전달하여 거래소 API로 주문을 실행합니다.

---

## 🚀 프로젝트 구성

암호화폐 전략 분석 및 자동매매/ ├── fetcher/         # 데이터 수집 모듈 ├── strategy/        # 전략 로직 (예: HA Signal3) ├── visualizer/      # 시각화 및 분석 도구 ├── config.py        # 환경 설정 ├── main.py          # 실행 진입



## ⚙️ 사용 기술

- TradingView (Pine Script)
- Python 3.10+
- Flask (Webhook 서버)
- Binance API
- Matplotlib / Seaborn

---

## 📡 자동매매 흐름

1. 트레이딩뷰에서 전략 조건 만족 시 alert 발생
2. 웹훅으로 Flask 서버에 JSON 신호 전송
3. 파이썬에서 거래소 API로 주문 실행

---

## 📊 전략 예시: HA Signal3

- Heikin-Ashi 캔들 반전
- EMA 크로스 + 추세 필터
- 캔들 강도 조건 + 재진입 로직
- ATR 기반 손절 설정

---

## 🧪 실행 방법

```bash
git clone https://github.com/eunho9104-debug/Auto_trading_usingWebhook.git
cd Auto_trading_usingWebhook
pip install -r requirements.txt
python main.py

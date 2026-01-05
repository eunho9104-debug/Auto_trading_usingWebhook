from flask import Flask, request, jsonify
from trader import execute_trade


#읽히는지 확인용 + 에러확인용

from dotenv import load_dotenv
import traceback
load_dotenv()


import os

from dotenv import load_dotenv
load_dotenv()

print("TRADING_ENV =", os.getenv("TRADING_ENV"))
print("TRADING_ENABLED =", os.getenv("TRADING_ENABLED"))
print("BINANCE_BASE_URL =", os.getenv("BINANCE_BASE_URL"))
print("WEBHOOK_SECRET exists? =", bool(os.getenv("WEBHOOK_SECRET")))



app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json(silent=True) or {}
    print("📩 Webhook received:", data)

    try:
        result = execute_trade(data)
        return jsonify({'status': 'success', 'detail': result})
    except Exception as e:
        print("❌ ERROR:", str(e))
        print(traceback.format_exc())
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000)
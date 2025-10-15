from flask import Flask, request, jsonify
from trader import execute_trade

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    print("📩 Webhook received:", data)

    try:
        result = execute_trade(data)
        return jsonify({'status': 'success', 'detail': result})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000)
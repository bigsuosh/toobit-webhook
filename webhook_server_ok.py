from flask import Flask, request, jsonify
import hmac
import hashlib
import requests
import time
import os
from dotenv import load_dotenv

# بارگذاری API Keyها از فایل .env
load_dotenv()
api_key = os.getenv("API_KEY")
secret_key = os.getenv("SECRET_KEY")
telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

app = Flask(__name__)

# تابع ساخت signature برای Toobit
def sign_params(params, secret_key):
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    signature = hmac.new(secret_key.encode(), query_string.encode(), hashlib.sha256).hexdigest()
    return signature

# تابع ارسال پیام تلگرام
def send_telegram_message(message):
    try:
        url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
        payload = {
            "chat_id": telegram_chat_id,
            "text": message
        }
        requests.post(url, json=payload)
    except Exception as e:
        print("❌ خطا در ارسال پیام تلگرام:", e)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()

    try:
        signal = data.get("signal")  # "buy" یا "sell"
        qty = data.get("qty")        # مقدار کوین
        price = data.get("price")    # قیمت سفارش

        if not all([signal, qty, price]):
            return jsonify({"error": "اطلاعات ناقص"}), 400

        # آماده‌سازی پارامتر سفارش
        timestamp = str(int(time.time() * 1000))
        order_params = {
            "symbol": "BTCUSDT",
            "side": "BUY" if signal.lower() == "buy" else "SELL",
            "type": "LIMIT",
            "timeInForce": "GTC",
            "quantity": str(qty),
            "price": str(price),
            "timestamp": timestamp
        }

        order_params["signature"] = sign_params(order_params, secret_key)

        headers = {
            "X-BB-APIKEY": api_key
        }

        order_url = "https://api.toobit.com/api/v1/spot/order"
        response = requests.post(order_url, headers=headers, data=order_params)
        result = response.json()

        # ارسال پیام تلگرام
        msg = f"📥 سفارش {'خرید' if signal == 'buy' else 'فروش'} ثبت شد\n\n📌 جفت ارز: BTCUSDT\n🔢 مقدار: {qty}\n💵 قیمت: {price}\n📝 وضعیت: {result.get('status', '---')}"
        send_telegram_message(msg)

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5005)

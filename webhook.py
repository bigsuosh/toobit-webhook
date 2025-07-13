from flask import Flask, request, jsonify
import hmac
import hashlib
import requests
import time
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
api_key = os.getenv("API_KEY")
secret_key = os.getenv("SECRET_KEY")
telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

# Check if environment variables are loaded
if not all([api_key, secret_key, telegram_token, telegram_chat_id]):
    print("❌ Error: Missing environment variables in .env file")
    exit()

app = Flask(__name__)

# Function to create signature for Toobit
def sign_params(params, secret_key):
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    signature = hmac.new(secret_key.encode(), query_string.encode(), hashlib.sha256).hexdigest()
    return signature

# Function to send Telegram message
def send_telegram_message(message):
    try:
        url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
        payload = {
            "chat_id": telegram_chat_id,
            "text": message,
            "parse_mode": "Markdown"  # For better formatting
        }
        # Disable proxy explicitly
        proxies = {
            "http": None,
            "https": None
        }
        response = requests.post(url, json=payload, timeout=10, proxies=proxies)
        result = response.json()
        if result.get("ok"):
            print("✅ Telegram message sent successfully:", result)
            return True
        else:
            print("❌ Error sending Telegram message:", result)
            return False
    except requests.exceptions.RequestException as e:
        print("❌ Network error in sending Telegram message:", str(e))
        return False
    except Exception as e:
        print("❌ Unexpected error in sending Telegram message:", str(e))
        return False

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()

    try:
        signal = data.get("signal")  # "buy" or "sell"
        qty = data.get("qty")        # Quantity of coin
        price = data.get("price")    # Order price

        if not all([signal, qty, price]):
            error_msg = "❌ اطلاعات ناقص: signal، qty یا price ارائه نشده است"
            send_telegram_message(error_msg)
            return jsonify({"error": "اطلاعات ناقص"}), 400

        # Validate signal
        if signal.lower() not in ["buy", "sell"]:
            error_msg = f"❌ سیگنال نامعتبر: {signal}"
            send_telegram_message(error_msg)
            return jsonify({"error": "سیگنال باید buy یا sell باشد"}), 400

        # Prepare order parameters
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

        # Prepare Telegram message
        status = result.get('status', 'نامشخص')
        order_id = result.get('orderId', 'نامشخص')
        msg = (
            f"📊 *سفارش {'خرید' if signal.lower() == 'buy' else 'فروش'} ثبت شد*\n\n"
            f"📌 *جفت ارز*: BTCUSDT\n"
            f"🔢 *مقدار*: {qty}\n"
            f"💵 *قیمت*: {price}\n"
            f"📝 *وضعیت*: {status}\n"
            f"🆔 *شناسه سفارش*: {order_id}"
        )
        send_telegram_message(msg)

        return jsonify(result), 200

    except Exception as e:
        error_msg = f"❌ خطا در پردازش وب‌هوک: {str(e)}"
        send_telegram_message(error_msg)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5005)
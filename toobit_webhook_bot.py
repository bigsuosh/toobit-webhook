from flask import Flask, request, jsonify
import hmac
import hashlib
import requests
import time
import os
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime

# بارگذاری متغیرهای محیطی از فایل .env
load_dotenv()
api_key = os.getenv("API_KEY")
secret_key = os.getenv("SECRET_KEY")
telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

# بررسی وجود متغیرهای محیطی
if not all([api_key, secret_key, telegram_token, telegram_chat_id]):
    print("❌ خطا: برخی از متغیرهای محیطی (API_KEY, SECRET_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID) در فایل .env یافت نشد")
    exit()

app = Flask(__name__)

# فایل لاگ سفارشات و خطاها
ORDER_LOG_FILE = "order_logs.xlsx"
ERROR_LOG_FILE = "error_logs.txt"

# ساخت امضا برای Toobit
def sign_params(params, secret_key):
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    signature = hmac.new(secret_key.encode(), query_string.encode(), hashlib.sha256).hexdigest()
    return signature

# ارسال پیام تلگرام
def send_telegram_message(message):
    try:
        url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
        payload = {
            "chat_id": telegram_chat_id,
            "text": message
        }
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code != 200:
            print(f"❌ خطا در ارسال پیام تلگرام: {r.text}")
    except Exception as e:
        print("❌ خطا در ارسال پیام تلگرام:", e)

# ذخیره لاگ سفارشات در فایل اکسل
def log_order(data):
    try:
        df_new = pd.DataFrame([data])
        if os.path.exists(ORDER_LOG_FILE):
            df_old = pd.read_excel(ORDER_LOG_FILE)
            df = pd.concat([df_old, df_new], ignore_index=True)
        else:
            df = df_new
        df.to_excel(ORDER_LOG_FILE, index=False)
    except Exception as e:
        log_error(f"خطا در ذخیره لاگ سفارش: {e}")

# ذخیره خطاها در فایل متنی
def log_error(msg):
    with open(ERROR_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {msg}\n")

# گرفتن موجودی حساب USDT از Toobit
def get_usdt_balance():
    try:
        url = "https://api.toobit.com/api/v1/account"
        timestamp = str(int(time.time() * 1000))
        params = {
            "timestamp": timestamp
        }
        params["signature"] = sign_params(params, secret_key)
        headers = {"X-BB-APIKEY": api_key}
        r = requests.get(url, headers=headers, params=params, timeout=10)
        if r.status_code != 200:
            log_error(f"خطا در دریافت موجودی: {r.status_code} - {r.text}")
            return None
        data = r.json()
        for bal in data.get("balances", []):
            if bal.get("asset") == "USDT":
                return float(bal.get("free", "0"))
        return 0.0
    except Exception as e:
        log_error(f"خطا در دریافت موجودی: {e}")
        return None

# ارسال سفارش به Toobit با تلاش مجدد
def place_order(order_params, max_retries=3, retry_delay=2):
    for attempt in range(max_retries):
        try:
            headers = {"X-BB-APIKEY": api_key}
            response = requests.post(
                "https://api.toobit.com/api/v1/spot/order",
                headers=headers,
                data=order_params,
                timeout=10,
                verify=True
            )
            result = response.json()
            return result
        except requests.exceptions.RequestException as e:
            log_error(f"خطا در ارسال سفارش (تلاش {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                return {"error": f"خطا در ارسال سفارش پس از {max_retries} تلاش"}

# تجزیه متن ورودی وب‌هوک
def parse_text_input(text):
    data = {}
    lines = text.strip().split('\n')
    signal_line = lines[0].strip()
    if 'LONG Signal' in signal_line:
        data['signal'] = 'LONG'
    elif 'SELL Signal' in signal_line:
        data['signal'] = 'SELL'
    else:
        return None  # سیگنال نامعتبر

    for line in lines[1:]:
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip().replace('$', '')  # حذف $ از قیمت
            if key == 'Symbol':
                data['symbol'] = value
            elif key == 'Buy Qty':
                data['buy_qty'] = value
            elif key == 'Close Qty':
                data['close_qty'] = value
            elif key == 'Price':
                data['price'] = value
            elif key == 'Equity':
                data['equity'] = value
            elif key == 'Available Cash':
                data['available_cash'] = value
            elif key == 'Unsold Value':
                data['unsold_value'] = value
    return data

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.content_type not in ['application/json', 'text/plain']:
        return jsonify({"error": "نوع محتوا باید application/json یا text/plain باشد"}), 415
    try:
        if request.content_type == 'application/json':
            data = request.get_json(silent=True)
            if not data:
                return jsonify({"error": "بدنه JSON نامعتبر است"}), 400
        else:
            text = request.get_data(as_text=True)
            data = parse_text_input(text)
            if not data:
                return jsonify({"error": "فرمت متن ورودی نامعتبر است"}), 400

        signal = data.get("signal")  # LONG یا SELL
        symbol = data.get("symbol")
        buy_qty = data.get("buy_qty")
        close_qty = data.get("close_qty")
        price = data.get("price")

        if not all([signal, symbol, price]) or (signal.upper() == "LONG" and not buy_qty) or (signal.upper() == "SELL" and not close_qty):
            return jsonify({"error": "اطلاعات ناقص: signal، symbol، price، یا مقدار (buy_qty/close_qty) ارائه نشده است"}), 400

        # تبدیل مقادیر عددی
        try:
            price = float(price)
            qty = float(buy_qty) if signal.upper() == "LONG" else float(close_qty)
        except:
            return jsonify({"error": "مقادیر عددی (qty, price) نامعتبر است"}), 400

        # بررسی موجودی حساب
        account_balance = get_usdt_balance()
        if account_balance is None:
            return jsonify({"error": "خطا در دریافت موجودی حساب"}), 500

        required_amount = qty * price
        if account_balance < required_amount:
            return jsonify({"error": "موجودی حساب کافی نیست"}), 400

        side = "BUY" if signal.upper() == "LONG" else "SELL"

        # ساخت پارامترهای سفارش
        timestamp = str(int(time.time() * 1000))
        order_params = {
            "symbol": symbol,
            "side": side,
            "type": "LIMIT",
            "timeInForce": "GTC",
            "quantity": str(qty),
            "price": str(price),
            "timestamp": timestamp
        }
        order_params["signature"] = sign_params(order_params, secret_key)

        # ارسال سفارش
        result = place_order(order_params)
        if "error" in result:
            log_error(f"خطا در ارسال سفارش: {result['error']}")
            return jsonify({"error": result["error"]}), 500

        # لاگ سفارش
        log_data = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "signal": signal,
            "symbol": symbol,
            "side": side,
            "quantity": qty,
            "price": price,
            "order_response": str(result)
        }
        log_order(log_data)

        # ارسال پیام تلگرام
        telegram_msg = f"📥 سفارش {'خرید' if side=='BUY' else 'فروش'} ثبت شد\n\n" \
                       f"📌 جفت ارز: {symbol}\n" \
                       f"🔢 مقدار: {qty}\n" \
                       f"💵 قیمت: {price}\n" \
                       f"📝 وضعیت: {result.get('status', '---')}\n" \
                       f"💰 موجودی کل: {account_balance} USDT"
        send_telegram_message(telegram_msg)

        return jsonify(result), 200

    except Exception as e:
        log_error(f"خطا در پردازش وب‌هوک: {str(e)}")
        return jsonify({"error": f"خطا در پردازش وب‌هوک: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(port=5005)

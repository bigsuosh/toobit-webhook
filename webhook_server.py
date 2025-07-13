from flask import Flask, request, jsonify
import hmac
import hashlib
import requests
import time
import os
from dotenv import load_dotenv

# بارگذاری متغیرهای محیطی از فایل .env
load_dotenv()
api_key = os.getenv("API_KEY")
secret_key = os.getenv("SECRET_KEY")

# بررسی وجود متغیرهای محیطی
if not all([api_key, secret_key]):
    print("❌ خطا: متغیرهای محیطی در فایل .env یافت نشد")
    exit()

app = Flask(__name__)

# تابع ساخت امضا برای Toobit
def sign_params(params, secret_key):
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    signature = hmac.new(secret_key.encode(), query_string.encode(), hashlib.sha256).hexdigest()
    return signature

# تابع ارسال سفارش با تلاش مجدد
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
        except requests.exceptions.SSLError as e:
            print(f"❌ خطای SSL در ارسال سفارش (تلاش {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            continue
        except requests.exceptions.RequestException as e:
            print(f"❌ خطای شبکه در ارسال سفارش (تلاش {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            continue
    return {"error": f"خطا در ارسال سفارش پس از {max_retries} تلاش"}

# تابع لغو سفارش (غیرفعال)
def cancel_order(symbol, order_id, max_retries=3, retry_delay=2):
    for attempt in range(max_retries):
        try:
            timestamp = str(int(time.time() * 1000))
            params = {
                "symbol": symbol,
                "orderId": order_id,
                "timestamp": timestamp
            }
            params["signature"] = sign_params(params, secret_key)
            headers = {"X-BB-APIKEY": api_key}
            response = requests.delete(
                "https://api.toobit.com/api/v1/spot/order",
                headers=headers,
                params=params,
                timeout=10,
                verify=True
            )
            result = response.json()
            return result
        except requests.exceptions.SSLError as e:
            print(f"❌ خطای SSL در لغو سفارش (تلاش {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            continue
        except requests.exceptions.RequestException as e:
            print(f"❌ خطای شبکه در لغو سفارش (تلاش {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            continue
    return {"error": f"خطا در لغو سفارش پس از {max_retries} تلاش"}

# تابع تجزیه متن ورودی
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
    # بررسی نوع محتوا
    if request.content_type not in ['application/json', 'text/plain']:
        return jsonify({"error": "نوع محتوا باید application/json یا text/plain باشد"}), 415

    try:
        if request.content_type == 'application/json':
            data = request.get_json(silent=True)
            if not data:
                return jsonify({"error": "بدنه JSON نامعتبر است"}), 400
        else:  # text/plain
            text = request.get_data(as_text=True)
            data = parse_text_input(text)
            if not data:
                return jsonify({"error": "فرمت متن ورودی نامعتبر است"}), 400

        signal = data.get("signal")  # "LONG" یا "SELL"
        symbol = data.get("symbol")  # مثلاً "BTCUSDT"
        buy_qty = data.get("buy_qty")  # برای سیگنال LONG
        close_qty = data.get("close_qty")  # برای سیگنال SELL
        price = data.get("price")  # قیمت سفارش

        # اعتبارسنجی فیلدهای ضروری
        if not all([signal, symbol, price]) or (signal.upper() == "LONG" and not buy_qty) or (signal.upper() == "SELL" and not close_qty):
            return jsonify({"error": "اطلاعات ناقص: signal، symbol، price، یا مقدار (buy_qty/close_qty) ارائه نشده است"}), 400

        # نگاشت سیگنال به side
        if signal.upper() == "LONG":
            side = "BUY"
            qty = buy_qty
        elif signal.upper() == "SELL":
            side = "SELL"
            qty = close_qty
        else:
            return jsonify({"error": f"سیگنال نامعتبر: {signal} (باید LONG یا SELL باشد)"}), 400

        # آماده‌سازی پارامترهای سفارش
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
            return jsonify({"error": result["error"]}), 500

        # لغو سفارش (اختیاری، غیرفعال شده)
        # if "orderId" in result:
        #     order_id = result["orderId"]
        #     cancel_result = cancel_order(symbol, order_id)
        #     result["cancel_result"] = cancel_result

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": f"خطا در پردازش وب‌هوک: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(port=5005)
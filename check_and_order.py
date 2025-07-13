import requests
import hmac
import hashlib
import time
from dotenv import load_dotenv
import os

# بارگذاری کلیدها
load_dotenv()
api_key = os.getenv("API_KEY")
secret_key = os.getenv("SECRET_KEY")

# تابع امضای درخواست
def sign_params(params, secret_key):
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    signature = hmac.new(secret_key.encode(), query_string.encode(), hashlib.sha256).hexdigest()
    return signature

# مرحله 1: گرفتن موجودی USDT
timestamp = str(int(time.time() * 1000))
params = {"timestamp": timestamp}
params["signature"] = sign_params(params, secret_key)

headers = {"X-BB-APIKEY": api_key}
account_url = "https://api.toobit.com/api/v1/account"

response = requests.get(account_url, headers=headers, params=params)
data = response.json()

usdt_balance = 0
for asset in data.get("balances", []):
    if asset["asset"] == "USDT":
        usdt_balance = float(asset["free"])

print(f"📊 موجودی USDT شما: {usdt_balance} USDT")

# مرحله 2: بررسی حداقل مقدار مورد نیاز
required_amount = 10  # مقدار مورد نیاز برای خرید

if usdt_balance >= required_amount:
    print("✅ موجودی کافی است. در حال ارسال سفارش خرید...")

    # پارامترهای سفارش
    timestamp = str(int(time.time() * 1000))
    order_params = {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "type": "LIMIT",
        "timeInForce": "GTC",
        "quantity": "0.0001",  # مقدار تستی
        "price": "50000",      # قیمت فرضی
        "timestamp": timestamp
    }

    order_params["signature"] = sign_params(order_params, secret_key)
    order_url = "https://api.toobit.com/api/v1/spot/order"

    order_response = requests.post(order_url, headers=headers, data=order_params)
    print("📦 پاسخ سفارش:", order_response.json())

else:
    print("❌ موجودی کافی نیست. سفارش ارسال نشد.")

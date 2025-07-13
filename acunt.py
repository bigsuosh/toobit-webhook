import requests
import hmac
import hashlib
import time
from dotenv import load_dotenv
import os

# بارگذاری API Keyها از فایل .env
load_dotenv()
api_key = os.getenv("API_KEY")
secret_key = os.getenv("SECRET_KEY")

# گرفتن زمان فعلی
timestamp = str(int(time.time() * 1000))
query_string = f"timestamp={timestamp}"

# ساخت امضا
signature = hmac.new(secret_key.encode(), query_string.encode(), hashlib.sha256).hexdigest()

# پارامترها و هدر
params = {
    "timestamp": timestamp,
    "signature": signature
}
headers = {
    "X-BB-APIKEY": api_key
}

# آدرس API
url = "https://api.toobit.com/api/v1/spot/account"

# ارسال درخواست
try:
    response = requests.get(url, headers=headers, params=params)

    # بررسی اینکه پاسخ JSON معتبر است یا نه
    if response.status_code == 200:
        data = response.json()
        print("📊 موجودی حساب:")
        for asset in data.get("balances", []):
            print(f"{asset['asset']}: Free={asset['free']} | Locked={asset['locked']}")
    else:
        print("❌ پاسخ ناموفق از سرور:")
        print("Status Code:", response.status_code)
        print("Response Text:", response.text)

except Exception as e:
    print("❌ خطا:", str(e))

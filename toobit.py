import requests
import hmac
import hashlib
import time

api_key = "your_api_key"
secret_key = "your_secret_key"
symbol = "BTCUSDT"
side = "BUY"
order_type = "LIMIT"
time_in_force = "GTC"
quantity = "0.001"
price = "50000"

# Get current timestamp
timestamp = str(int(time.time() * 1000))

# Create query string
params = {
    "symbol": symbol,
    "side": side,
    "type": order_type,
    "timeInForce": time_in_force,
    "quantity": quantity,
    "price": price,
    "timestamp": timestamp
}
query_string = "&".join([f"{k}={v}" for k, v in params.items()])

# Generate signature
signature = hmac.new(secret_key.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

# Add signature to params
params["signature"] = signature

# Set headers
headers = {
    "X-BB-APIKEY": api_key
}

# Make the request (use orderTest for testing)
url = "https://api.toobit.com/api/v1/spot/orderTest"
response = requests.post(url, headers=headers, data=params)

print(response.text)
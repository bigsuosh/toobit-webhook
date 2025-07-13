import requests
import hmac
import hashlib
import time
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Get API key and Secret key
api_key = os.getenv("API_KEY")
secret_key = os.getenv("SECRET_KEY")

# API endpoint for real order
url = "https://api.toobit.com/api/v1/spot/order"

# Order parameters
symbol = "BTCUSDT"
side = "BUY"
order_type = "LIMIT"
time_in_force = "GTC"
quantity = "0.0001"  # Small quantity for testing
price = "50000"    # Adjust this based on current market price

# Get current timestamp
timestamp = str(int(time.time() * 1000))

# Create query string for signature
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

# Add signature to parameters
params["signature"] = signature

# Set headers
headers = {
    "X-BB-APIKEY": api_key
}

# Send POST request
try:
    response = requests.post(url, headers=headers, data=params)
    print("Response:", response.json())
except Exception as e:
    print("Error:", str(e))
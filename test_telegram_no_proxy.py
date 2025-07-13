import requests
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Get Telegram token and chat ID
telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

# Check if environment variables are loaded
if not telegram_token or not telegram_chat_id:
    print("❌ Error: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not found in .env file")
    exit()

# Function to send a Telegram message
def send_telegram_message(message):
    try:
        url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
        payload = {
            "chat_id": telegram_chat_id,
            "text": message
        }
        # Disable proxy explicitly
        proxies = {
            "http": None,
            "https": None
        }
        response = requests.post(url, json=payload, timeout=10, proxies=proxies)
        result = response.json()
        if result.get("ok"):
            print("✅ Message sent successfully:", result)
        else:
            print("❌ Error in sending message:", result)
        return result
    except requests.exceptions.RequestException as e:
        print("❌ Network error:", str(e))
        return None
    except Exception as e:
        print("❌ Unexpected error:", str(e))
        return None

# Test the function
if __name__ == "__main__":
    print("Testing Telegram API...")
    print("Token (partial):", telegram_token[:10] + "...")
    print("Chat ID:", telegram_chat_id)
    test_message = "This is a test message from your trading bot (no proxy)!"
    send_telegram_message(test_message)
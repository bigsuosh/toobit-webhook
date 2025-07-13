from dotenv import load_dotenv
import os
import requests

# Load environment variables from .env file
load_dotenv()

# Get Telegram token and chat ID
telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

# Function to send a Telegram message
def send_telegram_message(message):
    try:
        url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
        payload = {
            "chat_id": telegram_chat_id,
            "text": message
        }
        response = requests.post(url, json=payload)
        result = response.json()
        if result.get("ok"):
            print("✅ Message sent successfully:", result)
        else:
            print("❌ Error in sending message:", result)
        return result
    except Exception as e:
        print("❌ Exception occurred:", str(e))
        return None

# Test the function
if __name__ == "__main__":
    test_message = "This is a test message from your trading bot!"
    send_telegram_message(test_message)
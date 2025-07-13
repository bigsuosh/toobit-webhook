from dotenv import load_dotenv
import os

load_dotenv()

api_key = os.getenv("API_KEY")
secret_key = os.getenv("SECRET_KEY")

print("API Key:", api_key)
print("Secret Key:", secret_key)
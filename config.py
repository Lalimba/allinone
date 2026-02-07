# config.py
import os
from dotenv import load_dotenv

load_dotenv()

BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET")

BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET")

# Optional sanity check
if not BINANCE_API_KEY:
    print("⚠️ BINANCE_API_KEY not set")

if not BYBIT_API_KEY:
    print("⚠️ BYBIT_API_KEY not set")

# bybit_public.py
import time
import requests

BASE_URL = "https://api.bybit.com"

class BybitLinearPublic:
    def __init__(self, symbol="BTCUSDT"):
        self.symbol = symbol

    def price(self) -> float:
        r = requests.get(
            f"{BASE_URL}/v5/market/tickers",
            params={"category": "linear", "symbol": self.symbol},
            timeout=10
        )
        r.raise_for_status()
        j = r.json()
        return float(j["result"]["list"][0]["lastPrice"])

    def open_interest(self) -> float:
        # intervalTime is required; we just read the latest value
        r = requests.get(
            f"{BASE_URL}/v5/market/open-interest",
            params={"category": "linear", "symbol": self.symbol, "intervalTime": "5min"},
            timeout=10
        )
        r.raise_for_status()
        j = r.json()
        return float(j["result"]["list"][0]["openInterest"])

    def funding_rate(self) -> float:
        r = requests.get(
            f"{BASE_URL}/v5/market/funding/history",
            params={"category": "linear", "symbol": self.symbol, "limit": 1},
            timeout=10
        )
        r.raise_for_status()
        j = r.json()
        lst = j["result"]["list"]
        return float(lst[0]["fundingRate"]) if lst else 0.0

    def orderbook(self, limit=200):
        r = requests.get(
            f"{BASE_URL}/v5/market/orderbook",
            params={"category": "linear", "symbol": self.symbol, "limit": limit},
            timeout=10
        )
        r.raise_for_status()
        res = r.json()["result"]
        bids = [(float(p), float(q)) for p, q in res["b"]]
        asks = [(float(p), float(q)) for p, q in res["a"]]
        return bids, asks

    def recent_trades(self, window_seconds=5, limit=1000) -> dict:
        """
        Filled liquidity (executed trades) over the last window_seconds.
        Bybit v5 recent trades returns entries with: price, size, side, time(ms).
        We sum taker BUY and taker SELL in USD = price * size.
        """
        now_ms = int(time.time() * 1000)
        start_ms = now_ms - int(window_seconds * 1000)

        r = requests.get(
            f"{BASE_URL}/v5/market/recent-trade",
            params={"category": "linear", "symbol": self.symbol, "limit": min(limit, 1000)},
            timeout=10
        )
        r.raise_for_status()
        j = r.json()
        lst = (j.get("result") or {}).get("list") or []

        taker_buy_usd = 0.0
        taker_sell_usd = 0.0

        for t in lst:
            t_ms = int(t.get("time", 0))
            if t_ms < start_ms:
                continue

            price = float(t["price"])
            size = float(t["size"])
            usd = price * size

            side = (t.get("side") or "").lower()
            if side == "buy":
                taker_buy_usd += usd
            elif side == "sell":
                taker_sell_usd += usd

        return {"taker_buy_usd": taker_buy_usd, "taker_sell_usd": taker_sell_usd}


if __name__ == "__main__":
    api = BybitLinearPublic("BTCUSDT")
    print("Price:", api.price())
    print("OI:", api.open_interest())
    print("Funding:", api.funding_rate())
    print("Trades(5s):", api.recent_trades(window_seconds=5))

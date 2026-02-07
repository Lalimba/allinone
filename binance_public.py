# binance_public.py
import time
import requests

class BinanceFuturesPublic:
    BASE = "https://fapi.binance.com"

    def __init__(self, symbol="BTCUSDT"):
        self.symbol = symbol

    def price(self) -> float:
        r = requests.get(
            f"{self.BASE}/fapi/v1/ticker/price",
            params={"symbol": self.symbol},
            timeout=10
        )
        r.raise_for_status()
        return float(r.json()["price"])

    def open_interest(self) -> float:
        r = requests.get(
            f"{self.BASE}/fapi/v1/openInterest",
            params={"symbol": self.symbol},
            timeout=10
        )
        r.raise_for_status()
        return float(r.json()["openInterest"])

    def funding_rate(self) -> float:
        r = requests.get(
            f"{self.BASE}/fapi/v1/fundingRate",
            params={"symbol": self.symbol, "limit": 1},
            timeout=10
        )
        r.raise_for_status()
        data = r.json()
        return float(data[0]["fundingRate"]) if data else 0.0

    def orderbook(self, limit=100):
        # Binance allows only specific depth limits
        allowed = {5, 10, 20, 50, 100, 500, 1000}
        if limit not in allowed:
            limit = 100

        r = requests.get(
            f"{self.BASE}/fapi/v1/depth",
            params={"symbol": self.symbol, "limit": limit},
            timeout=10
        )
        r.raise_for_status()
        ob = r.json()
        bids = [(float(p), float(q)) for p, q in ob["bids"]]
        asks = [(float(p), float(q)) for p, q in ob["asks"]]
        return bids, asks

    def recent_trades(self, window_seconds=5, limit=1000) -> dict:
        """
        Filled liquidity (executed trades) over last window_seconds using aggTrades.

        Binance aggTrades fields:
          - T: trade time (ms)
          - p: price
          - q: qty
          - m: buyer is market maker
              m=True  => buyer is maker => taker SELL
              m=False => buyer is taker => taker BUY
        """
        now_ms = int(time.time() * 1000)
        start_ms = now_ms - int(window_seconds * 1000)

        r = requests.get(
            f"{self.BASE}/fapi/v1/aggTrades",
            params={"symbol": self.symbol, "limit": min(limit, 1000)},
            timeout=10
        )
        r.raise_for_status()
        trades = r.json()

        taker_buy_usd = 0.0
        taker_sell_usd = 0.0

        for t in trades:
            t_ms = int(t["T"])
            if t_ms < start_ms:
                continue

            price = float(t["p"])
            qty = float(t["q"])
            usd = price * qty

            if bool(t["m"]):   # buyer is maker => taker sell
                taker_sell_usd += usd
            else:              # buyer is taker => taker buy
                taker_buy_usd += usd

        return {"taker_buy_usd": taker_buy_usd, "taker_sell_usd": taker_sell_usd}


if __name__ == "__main__":
    api = BinanceFuturesPublic("BTCUSDT")
    print("Price:", api.price())
    print("OI:", api.open_interest())
    print("Funding:", api.funding_rate())
    print("Trades(5s):", api.recent_trades(window_seconds=5))
    b, a = api.orderbook(limit=100)
    print("Orderbook OK:", len(b), len(a))

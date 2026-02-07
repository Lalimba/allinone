# signal_engine.py
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Deque
from collections import deque

@dataclass
class EngineConfig:
    depth_band_pct: float = 0.01             # +/- 1% around current price
    min_depth_delta_usd: float = 3_000_000   # resting liquidity activity threshold
    min_taker_delta_usd: float = 2_000_000   # filled liquidity confirmation threshold
    min_oi_move_pct: float = 0.03            # leverage moved threshold (percent)
    max_abs_funding_pct: float = 0.03        # too hot => RED
    depth_persist_polls: int = 2             # anti-spoof: depth must persist N polls

    zones: Optional[List[Tuple[str, float]]] = None
    zone_proximity_pct: float = 0.0015       # 0.15% proximity

def pct_change(new: float, old: float) -> float:
    if old == 0:
        return 0.0
    return (new - old) / old * 100.0

def depth_usd_within_band(
    bids: List[Tuple[float, float]],
    asks: List[Tuple[float, float]],
    mid: float,
    band_pct: float
) -> Tuple[float, float]:
    lo = mid * (1 - band_pct)
    hi = mid * (1 + band_pct)

    bid_usd = 0.0
    for p, q in bids:
        if p < lo:
            break
        bid_usd += p * q

    ask_usd = 0.0
    for p, q in asks:
        if p > hi:
            break
        ask_usd += p * q

    return bid_usd, ask_usd

def nearest_zone(price: float, zones: List[Tuple[str, float]], proximity_pct: float):
    if not zones:
        return None
    best = None
    for name, lvl in zones:
        dist = abs(price - lvl) / lvl
        if best is None or dist < best[2]:
            best = (name, lvl, dist)
    if best and best[2] <= proximity_pct:
        return best
    return None

class GreenLightEngine:
    """
    Computes:
      - ΔDepth in USD within a +/- band (resting liquidity)
      - ΔOI% (leverage commitment)
      - ΔTaker in USD from executed trades (filled liquidity)

    Decision:
      - RED if funding too extreme
      - GREEN if depth active (persisted) + taker confirms + OI moved
      - otherwise WAIT
    """
    def __init__(self, cfg: EngineConfig):
        self.cfg = cfg
        self.prev_oi: Optional[float] = None
        self.prev_bid_usd: Optional[float] = None
        self.prev_ask_usd: Optional[float] = None
        self.depth_ok_hist: Deque[bool] = deque(maxlen=max(1, cfg.depth_persist_polls))

    def update(self, price: float, bids, asks, oi: float, funding_frac: float, trades: Optional[dict] = None):
        funding_pct = funding_frac * 100.0

        bid_usd, ask_usd = depth_usd_within_band(bids, asks, price, self.cfg.depth_band_pct)

        depth_delta = 0.0
        if self.prev_bid_usd is not None and self.prev_ask_usd is not None:
            depth_delta = (bid_usd - self.prev_bid_usd) - (ask_usd - self.prev_ask_usd)
        self.prev_bid_usd, self.prev_ask_usd = bid_usd, ask_usd

        oi_chg_pct = 0.0
        if self.prev_oi is not None:
            oi_chg_pct = pct_change(oi, self.prev_oi)
        self.prev_oi = oi

        zone_hit = nearest_zone(price, self.cfg.zones or [], self.cfg.zone_proximity_pct)

        taker_buy_usd = float(trades.get("taker_buy_usd", 0.0)) if trades else 0.0
        taker_sell_usd = float(trades.get("taker_sell_usd", 0.0)) if trades else 0.0
        taker_delta_usd = taker_buy_usd - taker_sell_usd

        status, comments = self._decide(zone_hit, depth_delta, oi_chg_pct, funding_pct, taker_delta_usd)

        metrics: Dict[str, object] = {
            "price": price,
            "oi": oi,
            "oi_chg_pct": oi_chg_pct,
            "funding_pct": funding_pct,
            "bid_usd": bid_usd,
            "ask_usd": ask_usd,
            "depth_delta_usd": depth_delta,
            "taker_delta_usd": taker_delta_usd,
            "zone": zone_hit,
        }
        return status, comments, metrics

    def _decide(self, zone_hit, depth_delta_usd: float, oi_chg_pct: float, funding_pct: float, taker_delta_usd: float):
        comments: List[str] = []

        # RED
        if abs(funding_pct) > self.cfg.max_abs_funding_pct:
            return "RED", [f"Funding extreme ({funding_pct:.4f}%) → whipsaw risk"]

        # Optional zones
        if self.cfg.zones:
            if zone_hit is None:
                comments.append("Not near your SMC zone → safer to wait")
            else:
                name, lvl, dist = zone_hit
                comments.append(f"Near SMC zone: {name} @ {lvl:.0f} (dist {dist*100:.2f}%)")

        depth_m = depth_delta_usd / 1e6
        taker_m = taker_delta_usd / 1e6

        # Anti-spoof persistence
        depth_ok_now = abs(depth_delta_usd) >= self.cfg.min_depth_delta_usd
        self.depth_ok_hist.append(depth_ok_now)
        depth_ok = all(self.depth_ok_hist) if self.cfg.depth_persist_polls > 1 else depth_ok_now

        oi_ok = abs(oi_chg_pct) >= self.cfg.min_oi_move_pct
        taker_ok = abs(taker_delta_usd) >= self.cfg.min_taker_delta_usd

        # Comments
        if not depth_ok_now:
            comments.append(f"Orderbook low (ΔDepth {depth_m:.1f}M)")
        else:
            if depth_ok:
                comments.append(f"Orderbook active (ΔDepth {depth_m:.1f}M) [persisted]")
            else:
                comments.append(f"Orderbook spike (ΔDepth {depth_m:.1f}M) [not persisted → possible spoof]")

        if not taker_ok:
            comments.append(f"Filled flow weak (ΔTaker {taker_m:.1f}M)")
        else:
            side = "buyers" if taker_delta_usd > 0 else "sellers"
            comments.append(f"Filled flow confirms ({side} aggressive, ΔTaker {taker_m:.1f}M)")

        if not oi_ok:
            comments.append(f"OI flat (ΔOI {oi_chg_pct:.2f}%) → no leverage commitment")
        else:
            comments.append(f"OI moved (ΔOI {oi_chg_pct:.2f}%)")

        if depth_ok and taker_ok and oi_ok:
            direction_hint = "buyers aggressive" if taker_delta_usd > 0 else "sellers aggressive"
            comments.append(f"GREEN: liquidity stress + filled flow + leverage ({direction_hint})")
            return "GREEN", comments

        return "WAIT", comments

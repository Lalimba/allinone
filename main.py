# main.py
import time
from colorama import init, Fore, Style

from bybit_public import BybitLinearPublic
from binance_public import BinanceFuturesPublic
from signal_engine import EngineConfig, GreenLightEngine

init(autoreset=True)

def c_status(s: str) -> str:
    if s == "GREEN":
        return Fore.GREEN + s + Style.RESET_ALL
    if s == "RED":
        return Fore.RED + s + Style.RESET_ALL
    return Fore.YELLOW + s + Style.RESET_ALL

def fmt_row(name: str, status: str, m: dict) -> str:
    return (
        f"{name:<7} | {c_status(status):<10} | "
        f"Price={m['price']:.2f} | "
        f"ΔOI={m['oi_chg_pct']:.2f}% | "
        f"Funding={m['funding_pct']:.4f}% | "
        f"ΔDepth={m['depth_delta_usd']/1e6:.1f}M | "
        f"ΔTaker={m['taker_delta_usd']/1e6:.1f}M"
    )

def print_comments(comments):
    for c in comments:
        print("  - " + c)

def main():
    symbol = "BTCUSDT"
    poll_seconds = 5

    # OPTIONAL SMC zones (set to None to disable)
    # zones = [("Range Low / EQL", 95000), ("Range High / EQH", 96500)]
    zones = None

    cfg = EngineConfig(
        depth_band_pct=0.01,
        min_depth_delta_usd=3_000_000,
        min_taker_delta_usd=2_000_000,
        min_oi_move_pct=0.03,
        max_abs_funding_pct=0.03,
        depth_persist_polls=2,
        zones=zones,
        zone_proximity_pct=0.0015
    )

    bybit = BybitLinearPublic(symbol)
    binance = BinanceFuturesPublic(symbol)

    eng_bybit = GreenLightEngine(cfg)
    eng_binance = GreenLightEngine(cfg)

    while True:
        try:
            # BYBIT
            p1 = bybit.price()
            oi1 = bybit.open_interest()
            f1 = bybit.funding_rate()
            b1, a1 = bybit.orderbook(limit=200)
            tr1 = bybit.recent_trades(window_seconds=poll_seconds)
            s1, com1, m1 = eng_bybit.update(p1, b1, a1, oi1, f1, tr1)

            # BINANCE
            p2 = binance.price()
            oi2 = binance.open_interest()
            f2 = binance.funding_rate()
            b2, a2 = binance.orderbook(limit=100)
            tr2 = binance.recent_trades(window_seconds=poll_seconds)
            s2, com2, m2 = eng_binance.update(p2, b2, a2, oi2, f2, tr2)

            print("=" * 120)
            print(fmt_row("BYBIT", s1, m1))
            print_comments(com1)

            print(fmt_row("BINANCE", s2, m2))
            print_comments(com2)

            # Combined signal (strict confirmation)
            if s1 == "RED" or s2 == "RED":
                combined = "RED"
            elif s1 == "GREEN" and s2 == "GREEN":
                combined = "GREEN"
            else:
                combined = "WAIT"

            print("\nCOMBINED SIGNAL:", c_status(combined))
            if combined == "GREEN":
                print("  - Tip: Use your SMC level for entry (don’t trade just because it’s green).")
            elif combined == "WAIT":
                print("  - Tip: WAIT often means balance/no commitment. Don’t force trades.")
            else:
                print("  - Tip: RED means unstable conditions (often funding too hot).")

        except Exception as e:
            print(Fore.RED + "[ERROR] " + str(e) + Style.RESET_ALL)

        time.sleep(poll_seconds)

if __name__ == "__main__":
    main()

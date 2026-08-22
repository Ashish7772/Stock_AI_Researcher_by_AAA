from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class ResearchResult:
    technical_score: float
    fundamental_score: float
    market_score: float
    technical_reasons: list[str]
    technical_risks: list[str]
    fundamental_reasons: list[str]
    fundamental_risks: list[str]
    market_reasons: list[str]
    market_risks: list[str]


def technical_score(f: dict) -> tuple[float, list[str], list[str]]:
    score = 0.0
    reasons, risks = [], []
    close = f.get("close")
    if close is None:
        return 0, [], ["Current price unavailable"]
    checks = [
        (f.get("sma20") is not None and close > f["sma20"], 10, "Price is above SMA20", "Price is below SMA20"),
        (f.get("sma50") is not None and close > f["sma50"], 14, "Price is above SMA50", "Price is below SMA50"),
        (f.get("sma200") is not None and close > f["sma200"], 16, "Price is above SMA200", "Price is below SMA200"),
        (f.get("ema20") is not None and f.get("ema50") is not None and f["ema20"] > f["ema50"], 10, "EMA20 is above EMA50", "EMA20 is below EMA50"),
        (f.get("macd_hist") is not None and f["macd_hist"] > 0, 10, "MACD histogram is positive", "MACD histogram is negative"),
        (f.get("rsi14") is not None and 50 <= f["rsi14"] <= 70, 10, "RSI is in a constructive momentum zone", "RSI is outside the preferred momentum zone"),
        (f.get("adx14") is not None and f["adx14"] >= 20, 10, "ADX indicates a meaningful trend", "ADX suggests a weak/unclear trend"),
        (f.get("volume_ratio") is not None and f["volume_ratio"] >= 1.1, 10, "Volume is above its 20-day average", "Volume is not confirming the move"),
    ]
    for cond, pts, yes, no in checks:
        if cond:
            score += pts; reasons.append(yes)
        else:
            risks.append(no)
    return score - 50, reasons, risks


def market_score(relative: dict[str, float | None]) -> tuple[float, list[str], list[str]]:
    rr = relative.get("relative_return")
    if rr is None:
        return 0.0, [], ["Relative strength versus NIFTY is unavailable"]
    score = max(-50, min(50, rr * 500))
    if rr > 0.05:
        return score, [f"Stock outperformed NIFTY by {rr*100:.1f}% over the selected history"], []
    if rr < -0.05:
        return score, [], [f"Stock underperformed NIFTY by {abs(rr)*100:.1f}% over the selected history"]
    return score, ["Stock performance broadly tracked NIFTY"], []


def combine_probs(ts: float, fs: float, ms: float, ml: dict[str, float] | None = None) -> dict[str, float]:
    # Baseline heuristic, then blended with ML probability if available.
    signal = 0.55 * ts + 0.30 * fs + 0.15 * ms
    base_bull = 50 + signal * 0.55
    base_bear = 50 - signal * 0.55
    base_side = max(10.0, 35 - abs(signal) * 0.30)
    if signal >= 0:
        base_bull += base_side / 2; base_bear -= base_side / 2
    else:
        base_bear += base_side / 2; base_bull -= base_side / 2
    base = {"bullish": max(1, base_bull), "sideways": max(1, base_side), "bearish": max(1, base_bear)}
    s = sum(base.values()); base = {k: v * 100 / s for k, v in base.items()}
    if ml:
        out = {k: 0.45 * base[k] + 0.55 * ml.get(k, 0) for k in base}
        s = sum(out.values())
        return {k: v * 100 / s for k, v in out.items()}
    return base


def action_from_probs(p: dict[str, float]) -> str:
    bull, bear = p["bullish"], p["bearish"]
    if bull >= 72 and bull - bear >= 25: return "STRONG BUY"
    if bull >= 58 and bull > bear: return "BUY"
    if bear >= 72 and bear - bull >= 25: return "STRONG SELL"
    if bear >= 58 and bear > bull: return "SELL"
    return "HOLD"


def scenario_range(price: float, atr: float | None, support: float, resistance: float, horizon_days: int) -> dict[str, float]:
    if atr is None or atr <= 0:
        return {"bear": max(0.0, support), "base": price, "bull": max(price, resistance)}
    scale = 1.25 if horizon_days == 21 else 1.75
    bear = min(support, price - 1.4 * atr * scale)
    bull = max(resistance, price + 1.4 * atr * scale)
    base = price + 0.15 * atr * scale
    return {"bear": max(0.0, bear), "base": max(0.0, base), "bull": max(0.0, bull)}


def expected_price_from_scenarios(target: dict[str, float], probs: dict[str, float]) -> float:
    """Probability-weighted scenario price estimate for a simple headline value."""
    return (
        target["bear"] * probs["bearish"]
        + target["base"] * probs["sideways"]
        + target["bull"] * probs["bullish"]
    ) / 100.0

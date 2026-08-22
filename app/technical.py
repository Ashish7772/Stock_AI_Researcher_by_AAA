from __future__ import annotations

import numpy as np
import pandas as pd


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    prev = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev).abs(),
        (df["low"] - prev).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def _adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    up = df["high"].diff()
    down = -df["low"].diff()
    plus_dm = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=df.index)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - df["close"].shift(1)).abs(),
        (df["low"] - df["close"].shift(1)).abs(),
    ], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    plus_di = 100 * plus_dm.rolling(period).mean() / atr.replace(0, np.nan)
    minus_di = 100 * minus_dm.rolling(period).mean() / atr.replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return dx.rolling(period).mean()


def build_indicators(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy().sort_values("date").reset_index(drop=True)
    for n in (20, 50, 100, 200):
        x[f"sma{n}"] = x["close"].rolling(n).mean()
    x["ema20"] = x["close"].ewm(span=20, adjust=False).mean()
    x["ema50"] = x["close"].ewm(span=50, adjust=False).mean()
    x["rsi14"] = _rsi(x["close"])
    ema12 = x["close"].ewm(span=12, adjust=False).mean()
    ema26 = x["close"].ewm(span=26, adjust=False).mean()
    x["macd"] = ema12 - ema26
    x["macd_signal"] = x["macd"].ewm(span=9, adjust=False).mean()
    x["macd_hist"] = x["macd"] - x["macd_signal"]
    x["atr14"] = _atr(x)
    x["adx14"] = _adx(x)
    mid = x["close"].rolling(20).mean()
    std = x["close"].rolling(20).std()
    x["bb_mid"] = mid
    x["bb_upper"] = mid + 2 * std
    x["bb_lower"] = mid - 2 * std
    x["vol20"] = x["volume"].rolling(20).mean()
    x["volume_ratio"] = x["volume"] / x["vol20"].replace(0, np.nan)
    x["ret5"] = x["close"].pct_change(5)
    x["ret20"] = x["close"].pct_change(20)
    x["ret60"] = x["close"].pct_change(60)
    x["volatility20"] = x["close"].pct_change().rolling(20).std() * np.sqrt(252)
    x["dist_sma20"] = x["close"] / x["sma20"] - 1
    x["dist_sma50"] = x["close"] / x["sma50"] - 1
    x["dist_sma200"] = x["close"] / x["sma200"] - 1
    return x


def feature_columns() -> list[str]:
    return [
        "rsi14", "macd", "macd_signal", "macd_hist", "adx14", "atr14",
        "volume_ratio", "ret5", "ret20", "ret60", "volatility20",
        "dist_sma20", "dist_sma50", "dist_sma200",
    ]


def latest_features(df: pd.DataFrame) -> dict:
    row = df.iloc[-1]
    out = {c: (float(row[c]) if pd.notna(row[c]) else None) for c in feature_columns()}
    out["close"] = float(row["close"])
    out["sma20"] = float(row["sma20"]) if pd.notna(row["sma20"]) else None
    out["sma50"] = float(row["sma50"]) if pd.notna(row["sma50"]) else None
    out["sma100"] = float(row["sma100"]) if pd.notna(row["sma100"]) else None
    out["sma200"] = float(row["sma200"]) if pd.notna(row["sma200"]) else None
    out["ema20"] = float(row["ema20"]) if pd.notna(row["ema20"]) else None
    out["ema50"] = float(row["ema50"]) if pd.notna(row["ema50"]) else None
    out["bb_upper"] = float(row["bb_upper"]) if pd.notna(row["bb_upper"]) else None
    out["bb_lower"] = float(row["bb_lower"]) if pd.notna(row["bb_lower"]) else None
    out["volume"] = float(row["volume"]) if pd.notna(row["volume"]) else None
    return out


def support_resistance(df: pd.DataFrame, lookback: int = 120) -> tuple[float, float]:
    x = df.tail(lookback)
    price = float(x["close"].iloc[-1])
    lows = x["low"].rolling(5, center=True).min().dropna()
    highs = x["high"].rolling(5, center=True).max().dropna()
    supports = lows[lows < price]
    resistances = highs[highs > price]
    support = float(supports.iloc[-1]) if not supports.empty else float(x["low"].min())
    resistance = float(resistances.iloc[-1]) if not resistances.empty else float(x["high"].max())
    return support, resistance

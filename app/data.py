from __future__ import annotations

import re
from functools import lru_cache
from typing import Any
from urllib.parse import quote_plus

import pandas as pd


def normalize_symbol(value: str) -> str:
    raw = value.strip().upper()
    raw = re.sub(r"\s+", "", raw)
    raw = re.sub(r"[^A-Z0-9._&-]", "", raw)
    if not raw:
        raise ValueError("Please enter an NSE ticker, for example WIPRO or TCS.")
    if raw.endswith(".NS") or raw.endswith(".BO") or raw.startswith("^"):
        return raw
    return f"{raw}.NS"


@lru_cache(maxsize=32)
def get_history(symbol: str, period: str = "5y") -> pd.DataFrame:
    import yfinance as yf
    t = yf.Ticker(symbol)
    try:
        df = t.history(period=period, interval="1d", auto_adjust=True, actions=False)
    except Exception as exc:
        raise RuntimeError(f"Market-data download failed for {symbol}: {exc}") from exc
    if df.empty:
        raise ValueError(f"No data returned for {symbol}. Try an NSE symbol such as TCS, INFY or WIPRO.")
    df = df.reset_index()
    df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]
    if "date" not in df.columns:
        date_col = next((c for c in df.columns if "date" in c), None)
        if date_col:
            df = df.rename(columns={date_col: "date"})
    dt = pd.to_datetime(df["date"], errors="coerce")
    if getattr(dt.dt, "tz", None) is not None:
        dt = dt.dt.tz_localize(None)
    df["date"] = dt
    return df.dropna(subset=["date", "close"]).reset_index(drop=True)


@lru_cache(maxsize=32)
def safe_info(symbol: str) -> dict[str, Any]:
    try:
        import yfinance as yf
        info = yf.Ticker(symbol).info
        return info if isinstance(info, dict) else {}
    except Exception:
        return {}


def _num(v):
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def get_financial_snapshot(symbol: str) -> dict[str, Any]:
    info = safe_info(symbol)
    keys = [
        "marketCap", "enterpriseValue", "trailingPE", "forwardPE", "priceToBook", "pegRatio",
        "returnOnEquity", "returnOnAssets", "debtToEquity", "profitMargins", "operatingMargins",
        "grossMargins", "revenueGrowth", "earningsGrowth", "dividendYield", "bookValue",
        "currentPrice", "regularMarketPrice", "fiftyTwoWeekHigh", "fiftyTwoWeekLow",
        "sector", "industry", "longName", "shortName", "currency", "recommendationKey",
        "totalCash", "totalDebt", "freeCashflow", "operatingCashflow", "sharesOutstanding",
        "trailingEps", "forwardEps",
    ]
    result = {k: info.get(k) for k in keys}
    result["currentPrice"] = result.get("currentPrice") or result.get("regularMarketPrice")
    for k in list(result):
        if k not in {"sector", "industry", "longName", "shortName", "currency", "recommendationKey"}:
            result[k] = _num(result[k])
    return result


def fundamental_score(fin: dict[str, Any]) -> tuple[float, list[str], list[str]]:
    """Score available fundamentals while treating missing data as unknown/neutral."""
    points = 0.0
    max_points = 0.0
    reasons, risks = [], []

    def metric(value, good, bad, weight, positive_text, negative_text):
        nonlocal points, max_points
        if value is None:
            risks.append(f"{positive_text} — data unavailable")
            return
        max_points += weight
        if good(value):
            points += weight
            reasons.append(positive_text)
        elif bad(value):
            points -= weight
            risks.append(negative_text)

    metric(fin.get("revenueGrowth"), lambda v: v > 0.05, lambda v: v < 0, 10,
           "Revenue growth is above 5%", "Revenue growth is negative")
    metric(fin.get("earningsGrowth"), lambda v: v > 0.05, lambda v: v < 0, 10,
           "Earnings growth is above 5%", "Earnings growth is negative")
    metric(fin.get("returnOnEquity"), lambda v: v > 0.12, lambda v: v < 0.08, 12,
           "ROE is above 12%", "ROE is below 8%")
    metric(fin.get("operatingMargins"), lambda v: v > 0.12, lambda v: v < 0.05, 10,
           "Operating margin is above 12%", "Operating margin is below 5%")
    metric(fin.get("debtToEquity"), lambda v: v < 80, lambda v: v > 150, 12,
           "Debt/equity is conservative", "Debt/equity is high")
    metric(fin.get("trailingPE"), lambda v: 0 < v < 30, lambda v: v > 45, 8,
           "Trailing P/E is below 30", "Trailing P/E is above 45")

    fcf = fin.get("freeCashflow")
    if fcf is not None:
        max_points += 10
        if fcf > 0:
            points += 10
            reasons.append("Free cash flow is positive")
        else:
            points -= 10
            risks.append("Free cash flow is negative")
    else:
        risks.append("Free cash flow data unavailable")

    cash, debt = fin.get("totalCash"), fin.get("totalDebt")
    if cash is not None and debt is not None:
        max_points += 8
        if cash > debt:
            points += 8
            reasons.append("Cash exceeds total debt")
        else:
            points -= 8
            risks.append("Total debt exceeds cash")
    else:
        risks.append("Cash/debt data unavailable")

    if max_points == 0:
        return 0.0, [], ["Fundamental data was unavailable"]
    return float(max(-100, min(100, points / max_points * 100))), reasons, risks


def get_news(symbol: str, company_name: str | None = None, limit: int = 10) -> list[dict[str, str]]:
    articles: list[dict[str, str]] = []
    try:
        import yfinance as yf
        items = yf.Ticker(symbol).news or []
        for item in items[:limit]:
            content = item.get("content", item)
            title = content.get("title") or item.get("title")
            provider = content.get("provider", {})
            publisher = provider.get("displayName") if isinstance(provider, dict) else item.get("publisher", "Yahoo Finance")
            canonical = content.get("canonicalUrl", {})
            link = canonical.get("url") if isinstance(canonical, dict) else item.get("link", "")
            pub = content.get("pubDate") or item.get("providerPublishTime") or ""
            if title:
                articles.append({"title": str(title), "publisher": str(publisher or ""), "link": str(link or ""), "date": str(pub)})
    except Exception:
        pass
    if articles:
        return articles[:limit]
    query = quote_plus(f"{company_name or symbol.replace('.NS','')} stock India")
    try:
        import requests
        import xml.etree.ElementTree as ET
        response = requests.get(f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en", timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        root = ET.fromstring(response.text)
        for item in root.findall("./channel/item")[:limit]:
            get = lambda tag: (item.findtext(tag) or "").strip()
            articles.append({"title": get("title"), "publisher": "Google News", "link": get("link"), "date": get("pubDate")})
    except Exception:
        pass
    return articles


def get_benchmark_history(period: str = "5y") -> pd.DataFrame:
    return get_history("^NSEI", period)


def relative_strength(stock_df: pd.DataFrame, benchmark_df: pd.DataFrame) -> dict[str, float | None]:
    try:
        a = stock_df.set_index("date")["close"].sort_index()
        b = benchmark_df.set_index("date")["close"].sort_index()
        joined = pd.concat([a, b], axis=1, join="inner").dropna()
        if len(joined) < 30:
            return {"stock_return": None, "market_return": None, "relative_return": None}
        sr = joined.iloc[-1, 0] / joined.iloc[0, 0] - 1
        mr = joined.iloc[-1, 1] / joined.iloc[0, 1] - 1
        return {"stock_return": float(sr), "market_return": float(mr), "relative_return": float(sr - mr)}
    except Exception:
        return {"stock_return": None, "market_return": None, "relative_return": None}

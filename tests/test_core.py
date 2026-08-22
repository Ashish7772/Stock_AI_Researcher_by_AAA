import numpy as np
import pandas as pd

from app.engine import action_from_probs, combine_probs, expected_price_from_scenarios, scenario_range, technical_score
from app.model import train_and_predict, walk_forward_backtest
from app.technical import build_indicators, latest_features


def synthetic(n=900):
    rng = np.random.default_rng(42)
    rets = rng.normal(0.0004, 0.018, n)
    close = 100 * np.exp(np.cumsum(rets))
    high = close * (1 + rng.uniform(0, 0.012, n))
    low = close * (1 - rng.uniform(0, 0.012, n))
    open_ = close * (1 + rng.normal(0, 0.004, n))
    volume = rng.integers(500_000, 2_000_000, n)
    return pd.DataFrame({"date": pd.date_range("2022-01-01", periods=n, freq="B"), "open": open_, "high": high, "low": low, "close": close, "volume": volume})


def test_indicators_and_model():
    df = build_indicators(synthetic())
    feats = latest_features(df)
    assert feats["close"] > 0
    assert df["sma200"].notna().sum() > 0
    probs = combine_probs(20, 10, 5)
    assert abs(sum(probs.values()) - 100) < 1e-6
    assert action_from_probs({"bullish": 80, "sideways": 10, "bearish": 10}) == "STRONG BUY"
    assert train_and_predict(df, 21, 0.04) is not None
    assert walk_forward_backtest(df, 21, 0.04) is not None


def test_scenarios():
    s = scenario_range(100, 2, 94, 108, 21)
    assert s["bear"] < s["base"] < s["bull"]
    probs = {"bearish": 20, "sideways": 30, "bullish": 50}
    expected = expected_price_from_scenarios(s, probs)
    assert s["bear"] <= expected <= s["bull"]


def test_normalize_and_optional_paths():
    from app.data import normalize_symbol
    assert normalize_symbol(" WIPRO ") == "WIPRO.NS"
    assert normalize_symbol("TCS.NS") == "TCS.NS"
    assert normalize_symbol("tcs-bo") == "TCS-BO.NS"


def test_fundamental_score_is_safe_with_empty_data():
    from app.data import fundamental_score
    score, reasons, risks = fundamental_score({})
    assert -100 <= score <= 100
    assert isinstance(reasons, list) and isinstance(risks, list)


def test_app_source_contracts():
    from pathlib import Path
    src = (Path(__file__).parents[1] / "app" / "main.py").read_text()
    assert "from app.data import fundamental_score," in src or "from app.data import fundamental_score, " in src
    assert '"expected1": expected1' in src
    assert '"expected2": expected2' in src
    assert 'Expected price' in src
    assert 'if analyze:' in src
    assert 'if "result" not in st.session_state:' in src


def test_pdf_report_generation():
    from app.report import build_pdf_report

    summary = {
        "symbol": "WIPRO.NS",
        "company": "Wipro Limited",
        "current_price": 300.0,
        "recommendation_1m": "BUY",
        "recommendation_2m": "HOLD",
        "expected_price_1m": 315.0,
        "expected_price_2m": 330.0,
        "probabilities_1m": {"bullish": 60.0, "sideways": 25.0, "bearish": 15.0},
        "probabilities_2m": {"bullish": 55.0, "sideways": 30.0, "bearish": 15.0},
        "technical_score": 20.0,
        "fundamental_score": 25.0,
        "market_score": 10.0,
        "support": 285.0,
        "resistance": 325.0,
        "scenario_1m": {"bear": 280.0, "base": 310.0, "bull": 335.0},
        "scenario_2m": {"bear": 270.0, "base": 325.0, "bull": 355.0},
        "technical_reasons": ["Price above SMA50"],
        "technical_risks": ["RSI elevated"],
        "fundamental_reasons": ["Positive earnings growth"],
        "fundamental_risks": ["Valuation above long-term average"],
        "market_reasons": ["Relative strength positive"],
        "market_risks": [],
        "validation_1m": None,
        "validation_2m": None,
        "data_as_of": "2026-08-23T00:00:00+05:30",
    }
    full = {
        "fundamentals": {"longName": "Wipro Limited", "trailingPE": 22.0},
        "indicators": {"close": 300.0, "rsi14": 58.0},
        "news": [],
    }
    pdf = build_pdf_report(summary, full)
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 2000

import sys
import types
import importlib
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _synthetic(n=520):
    rng = np.random.default_rng(123)
    rets = rng.normal(0.0006, 0.015, n)
    close = 100 * np.exp(np.cumsum(rets))
    return pd.DataFrame({
        "date": pd.date_range("2023-01-01", periods=n, freq="B"),
        "open": close * (1 + rng.normal(0, 0.003, n)),
        "high": close * (1 + rng.uniform(0.001, 0.012, n)),
        "low": close * (1 - rng.uniform(0.001, 0.012, n)),
        "close": close,
        "volume": rng.integers(500_000, 2_000_000, n),
    })


def test_run_analysis_full_path_with_deterministic_market_data(monkeypatch):
    # Fake Streamlit so we can execute the real run_analysis() without a browser.
    class Ctx:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def __getattr__(self, name):
            return lambda *a, **k: Ctx()

    class SessionState(dict):
        __getattr__ = dict.get
        def __setattr__(self, key, value): self[key] = value
    st = types.ModuleType("streamlit")
    st.session_state = SessionState()
    st.sidebar = Ctx()
    st.set_page_config = lambda *a, **k: None
    st.markdown = st.caption = st.header = st.divider = st.info = st.error = st.subheader = st.write = lambda *a, **k: None
    st.text_input = lambda *a, **k: "WIPRO"
    st.selectbox = lambda *a, **k: "5y"
    st.slider = lambda *a, **k: 0.04
    st.checkbox = lambda *a, **k: True
    st.button = lambda *a, **k: True
    st.columns = lambda *args, **kwargs: [Ctx() for _ in range(args[0] if args and isinstance(args[0], int) else 2)]
    st.stop = lambda: None
    st.spinner = lambda *a, **k: Ctx()
    st.plotly_chart = st.dataframe = st.bar_chart = st.download_button = st.metric = lambda *a, **k: None
    st.progress = lambda *a, **k: None
    monkeypatch.setitem(sys.modules, "streamlit", st)

    data = types.ModuleType("app.data")
    hist = _synthetic()
    data.normalize_symbol = lambda value: "WIPRO.NS"
    data.get_history = lambda symbol, period="5y": hist.copy()
    data.get_benchmark_history = lambda period="5y": hist.assign(close=hist["close"] * 0.98)
    data.relative_strength = lambda stock_df, benchmark_df: {"stock_return": 0.12, "market_return": 0.08, "relative_return": 0.04}
    data.get_financial_snapshot = lambda symbol: {
        "longName": "Wipro Limited", "shortName": "Wipro", "currency": "INR",
        "revenueGrowth": 0.08, "earningsGrowth": 0.10, "returnOnEquity": 0.16,
        "operatingMargins": 0.15, "debtToEquity": 40.0, "trailingPE": 22.0,
        "freeCashflow": 1_000_000.0, "totalCash": 2_000_000.0, "totalDebt": 500_000.0,
        "currentPrice": float(hist["close"].iloc[-1]),
    }
    data.fundamental_score = lambda fin: (70.0, ["Revenue growth is above 5%"], [])
    data.get_news = lambda symbol, company_name=None: []
    monkeypatch.setitem(sys.modules, "app.data", data)

    import app.main as main
    importlib.reload(main)
    result = main.run_analysis()

    assert result["company"] == "Wipro Limited"
    assert result["expected1"] > 0
    assert result["expected2"] > 0
    assert set(result["p1"]) == {"bullish", "sideways", "bearish"}
    assert abs(sum(result["p1"].values()) - 100) < 1e-6

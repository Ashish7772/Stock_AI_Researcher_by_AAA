from __future__ import annotations

import json
from datetime import datetime

import plotly.graph_objects as go
import streamlit as st

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data import fundamental_score, get_benchmark_history, get_financial_snapshot, get_history, get_news, normalize_symbol, relative_strength
from app.engine import action_from_probs, combine_probs, expected_price_from_scenarios, market_score, scenario_range, technical_score
from app.llm import explain_locally
from app.model import train_and_predict, walk_forward_backtest
from app.report import build_pdf_report
from app.technical import build_indicators, latest_features, support_resistance

st.set_page_config(page_title="Stock AI Researcher by AAA", page_icon="📈", layout="wide")

st.markdown("# 📈 Stock AI Researcher by AAA")
st.caption("AI research dashboard for Indian equities. This is a probabilistic research tool, not financial advice or a guaranteed price predictor.")

with st.sidebar:
    st.header("Analyze stock")
    raw = st.text_input("NSE ticker", "WIPRO", help="Examples: TCS, INFY, WIPRO, RELIANCE. You can also enter TCS.NS or a BSE .BO symbol.")
    period = st.selectbox("History", ["2y", "3y", "5y", "10y", "max"], index=2)
    threshold = st.slider("Bull/Bear threshold", 0.02, 0.10, 0.04, 0.01, help="A future return at or above this level is labeled bullish; at or below the negative level is bearish.")
    use_ml = st.checkbox("Use ML model", True)
    do_backtest = st.checkbox("Run walk-forward validation", True)
    analyze = st.button("🔎 Analyze", type="primary", use_container_width=True)
    st.divider()
    st.caption("Data is pulled live when you analyze. Free sources can occasionally rate-limit or return incomplete fundamentals/news.")


def run_analysis():
    symbol = normalize_symbol(raw)
    hist = get_history(symbol, period)
    if len(hist) < 220:
        raise ValueError("Not enough history for the full 200-day indicator set. Try a more established ticker or a longer history.")
    price = build_indicators(hist)
    fin = get_financial_snapshot(symbol)
    company = fin.get("longName") or fin.get("shortName") or symbol.replace(".NS", "")
    try:
        bench = get_benchmark_history(period)
        rel = relative_strength(hist, bench)
    except Exception:
        rel = {"stock_return": None, "market_return": None, "relative_return": None}
    feats = latest_features(price)
    ts, tpos, twarn = technical_score(feats)
    fs, fpos, fwarn = fundamental_score(fin)
    ms, mpos, mwarn = market_score(rel)
    ml1 = train_and_predict(price, 21, threshold) if use_ml else None
    ml2 = train_and_predict(price, 42, threshold) if use_ml else None
    p1 = combine_probs(ts, fs, ms, ml1)
    p2 = combine_probs(ts, fs, ms, ml2)
    support, resistance = support_resistance(price)
    tgt1 = scenario_range(feats["close"], feats.get("atr14"), support, resistance, 21)
    tgt2 = scenario_range(feats["close"], feats.get("atr14"), support, resistance, 42)
    expected1 = expected_price_from_scenarios(tgt1, p1)
    expected2 = expected_price_from_scenarios(tgt2, p2)
    bt1 = walk_forward_backtest(price, 21, threshold) if (use_ml and do_backtest) else None
    bt2 = walk_forward_backtest(price, 42, threshold) if (use_ml and do_backtest) else None
    news = get_news(symbol, company)
    return {
        "symbol": symbol, "company": company, "price": price, "hist_rows": len(hist), "fin": fin,
        "feats": feats, "technical": ts, "fundamental": fs, "market": ms,
        "technical_reasons": tpos, "technical_risks": twarn,
        "fundamental_reasons": fpos, "fundamental_risks": fwarn,
        "market_reasons": mpos, "market_risks": mwarn, "relative": rel,
        "p1": p1, "p2": p2, "ml1": ml1, "ml2": ml2,
        "support": support, "resistance": resistance, "target1": tgt1, "target2": tgt2,
        "expected1": expected1, "expected2": expected2,
        "bt1": bt1, "bt2": bt2, "news": news,
        "asof": datetime.now().astimezone().isoformat(), "threshold": threshold,
    }

if analyze:
    try:
        with st.spinner("Collecting live market data and running analysis…"):
            st.session_state.result = run_analysis()
    except Exception as exc:
        st.error(f"Analysis failed: {exc}")
        st.info("Check your internet connection, ticker symbol, and the Terminal output. Free market-data sources can also temporarily rate-limit requests.")
        st.stop()

if "result" not in st.session_state:
    st.info("Enter an NSE ticker on the left and click Analyze to start.")
    st.stop()

r = st.session_state.result
p1, p2 = r["p1"], r["p2"]
action1 = action_from_probs(p1)
action2 = action_from_probs(p2)

st.subheader(f"{r['company']}  •  {r['symbol']}")
st.caption(f"Current price: ₹{r['feats']['close']:.2f}  |  Analyzed: {r['asof']}  |  {r['hist_rows']:,} trading sessions")

st.markdown("## 🎯 Simple prediction")
st.caption("Expected price is a probability-weighted estimate across bear/base/bull scenarios. It is a model estimate, not a guaranteed target.")

hero1, hero2 = st.columns(2)
with hero1:
    st.markdown("### Next 1 Month")
    h = st.columns(3)
    h[0].metric("Expected price", f"₹{r['expected1']:.2f}", f"{(r['expected1']/r['feats']['close']-1)*100:+.1f}%")
    h[1].metric("Bullish chance", f"{p1['bullish']:.1f}%")
    h[2].metric("View", action1)
    st.progress(min(100, max(0, int(p1['bullish']))), text=f"Bullish {p1['bullish']:.1f}%  •  Sideways {p1['sideways']:.1f}%  •  Bearish {p1['bearish']:.1f}%")
    st.caption(f"Scenario range: ₹{r['target1']['bear']:.2f} – ₹{r['target1']['bull']:.2f}")

with hero2:
    st.markdown("### Next 2 Months")
    h = st.columns(3)
    h[0].metric("Expected price", f"₹{r['expected2']:.2f}", f"{(r['expected2']/r['feats']['close']-1)*100:+.1f}%")
    h[1].metric("Bullish chance", f"{p2['bullish']:.1f}%")
    h[2].metric("View", action2)
    st.progress(min(100, max(0, int(p2['bullish']))), text=f"Bullish {p2['bullish']:.1f}%  •  Sideways {p2['sideways']:.1f}%  •  Bearish {p2['bearish']:.1f}%")
    st.caption(f"Scenario range: ₹{r['target2']['bear']:.2f} – ₹{r['target2']['bull']:.2f}")

st.divider()

# Header cards
c = st.columns(5)
c[0].metric("Current price", f"₹{r['feats']['close']:.2f}")
c[1].metric("1M bullish", f"{p1['bullish']:.1f}%")
c[2].metric("2M bullish", f"{p2['bullish']:.1f}%")
c[3].metric("Technical", f"{(r['technical']+50):.0f}/100")
c[4].metric("Fundamental", f"{(r['fundamental']+50):.0f}/100")

st.caption(f"Analyzed: {r['asof']}  |  {r['hist_rows']:,} trading sessions  |  Bull/Bear threshold: ±{r['threshold']*100:.0f}%")

left, right = st.columns([1.6, 1])
with left:
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=r["price"]["date"], open=r["price"]["open"], high=r["price"]["high"], low=r["price"]["low"], close=r["price"]["close"], name="Price"))
    for col, name in (("sma20", "SMA20"), ("sma50", "SMA50"), ("sma200", "SMA200")):
        fig.add_trace(go.Scatter(x=r["price"]["date"], y=r["price"][col], mode="lines", name=name))
    fig.update_layout(height=550, xaxis_rangeslider_visible=False, margin=dict(l=10,r=10,t=25,b=10))
    st.plotly_chart(fig, use_container_width=True)
with right:
    st.markdown("### Direction probabilities")
    chart_df = __import__("pandas").DataFrame(
        {
            "1 Month": [p1["bearish"], p1["sideways"], p1["bullish"]],
            "2 Months": [p2["bearish"], p2["sideways"], p2["bullish"]],
        },
        index=["Bearish", "Sideways", "Bullish"],
    )
    st.bar_chart(chart_df)
    st.markdown("### Key levels")
    st.metric("Support", f"₹{r['support']:.2f}")
    st.metric("Resistance", f"₹{r['resistance']:.2f}")

st.markdown("## Scenario ranges")
cols = st.columns(2)
for col, label, target, probs in ((cols[0], "1 Month", r["target1"], p1), (cols[1], "2 Months", r["target2"], p2)):
    with col:
        st.markdown(f"### {label}")
        st.write(f"Bear scenario: **₹{target['bear']:.2f}**")
        st.write(f"Base scenario: **₹{target['base']:.2f}**")
        st.write(f"Bull scenario: **₹{target['bull']:.2f}**")
        st.progress(min(100, int(probs["bullish"])), text=f"Bullish probability {probs['bullish']:.1f}%")
        st.caption("Scenario range derived from ATR, support/resistance and model direction; it is not a price guarantee.")

st.markdown("## Research scorecard")
score_df = {"Signal": ["Technical", "Fundamental", "NIFTY relative strength"], "Score (-100 to +100)": [r["technical"], r["fundamental"], r["market"]]}
st.dataframe(score_df, hide_index=True, use_container_width=True)

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("### ✅ Bullish factors")
    for x in r["technical_reasons"] + r["fundamental_reasons"] + r["market_reasons"]:
        st.write(f"• {x}")
with c2:
    st.markdown("### ⚠ Risks / weaknesses")
    for x in r["technical_risks"] + r["fundamental_risks"] + r["market_risks"]:
        st.write(f"• {x}")
with c3:
    st.markdown("### Indicators")
    rows = [(k, v) for k, v in r["feats"].items() if v is not None]
    st.dataframe(rows, hide_index=True, use_container_width=True)

st.markdown("## Fundamentals")
fund_rows = [(k, v) for k, v in r["fin"].items() if v is not None]
st.dataframe(fund_rows, hide_index=True, use_container_width=True)

st.markdown("## ML validation")
if r["bt1"] or r["bt2"]:
    rows = []
    for label, bt in (("1 month", r["bt1"]), ("2 months", r["bt2"])):
        if bt:
            rows.append({"Horizon": label, "Accuracy": f"{bt['accuracy']*100:.1f}%", "Balanced accuracy": f"{bt['balanced_accuracy']*100:.1f}%", "Precision": f"{bt['precision_macro']*100:.1f}%", "Recall": f"{bt['recall_macro']*100:.1f}%", "Folds": int(bt["folds"])})
    st.dataframe(rows, hide_index=True, use_container_width=True)
    st.caption("Walk-forward metrics are historical diagnostics for this stock/history and can deteriorate materially in live markets.")
else:
    st.info("Validation skipped or insufficient history.")

st.markdown("## News")
if r["news"]:
    for item in r["news"]:
        title = item.get("title", "")
        link = item.get("link", "")
        pub = item.get("publisher", "")
        st.markdown(f"- [{title}]({link}) — {pub}" if link else f"- {title} — {pub}")
else:
    st.info("No news feed was returned by the free sources.")

summary = {
    "symbol": r["symbol"], "company": r["company"], "current_price": r["feats"]["close"],
    "recommendation_1m": action1, "recommendation_2m": action2,
    "expected_price_1m": r["expected1"], "expected_price_2m": r["expected2"],
    "probabilities_1m": p1, "probabilities_2m": p2,
    "technical_score": r["technical"], "fundamental_score": r["fundamental"], "market_score": r["market"],
    "support": r["support"], "resistance": r["resistance"], "scenario_1m": r["target1"], "scenario_2m": r["target2"],
    "technical_reasons": r["technical_reasons"], "technical_risks": r["technical_risks"],
    "fundamental_reasons": r["fundamental_reasons"], "fundamental_risks": r["fundamental_risks"],
    "market_reasons": r["market_reasons"], "market_risks": r["market_risks"],
    "validation_1m": r["bt1"], "validation_2m": r["bt2"], "data_as_of": r["asof"],
}
local_explanation = explain_locally(json.dumps(summary, default=str))
if local_explanation:
    st.markdown("## Local AI analyst")
    st.write(local_explanation)
else:
    st.markdown("## Local AI analyst (optional)")
    st.caption("For a free local LLM explanation, install Ollama, pull a model, then set OLLAMA_MODEL before launching. The core analyzer works without it.")

report = {**summary, "fundamentals": r["fin"], "indicators": r["feats"], "news": r["news"]}
pdf_report = build_pdf_report(summary, report)
st.download_button("⬇️ Download analysis JSON", json.dumps(report, indent=2, default=str), file_name=f"{r['symbol'].replace('.NS','').replace('.BO','')}_stock_ai.json", mime="application/json", use_container_width=True)
st.download_button("📄 Download analysis PDF", pdf_report, file_name=f"{r['symbol'].replace('.NS','').replace('.BO','')}_stock_ai_report.pdf", mime="application/pdf", use_container_width=True)

st.divider()
st.caption("Important: model probabilities are not probabilities supplied by the market. They are outputs of this app's heuristic + ML pipeline based on the available free data. Never treat them as certainty.")

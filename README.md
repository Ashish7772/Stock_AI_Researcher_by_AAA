# Stock AI Researcher by AAA V5 — Final Mac Build

Local/free research dashboard for Indian equities. Enter an NSE ticker such as `WIPRO`, `TCS`, `INFY`, or `RELIANCE`, then click **Analyze**.

## What it does
- Technical trend and momentum analysis
- Fundamental snapshot and score
- NIFTY-relative strength
- 1-month and 2-month Bullish / Sideways / Bearish probabilities
- BUY / HOLD / SELL classification
- Support/resistance
- Bear / Base / Bull scenario ranges
- Random Forest direction model
- Walk-forward validation diagnostics
- News feed with free-source fallbacks
- Optional local Ollama explanation
- JSON report export

## Mac setup

1. Extract this ZIP.
2. Open Terminal in the extracted `stock_ai_final` folder.
3. Run:

```bash
bash scripts/setup_mac.sh
```

4. Start the app:

```bash
bash scripts/run_mac.sh
```

5. Open `http://localhost:8501`.

## Verify
After setup, you can also run:

```bash
bash scripts/verify_mac.sh
```

## Notes
- The app requires internet access when you click Analyze because live market data and news are fetched from free external sources.
- Free sources can rate-limit or omit some fundamental/news fields. The app treats missing fundamentals as unknown rather than automatically bearish and continues when the NIFTY benchmark is temporarily unavailable.
- Model probabilities are app-generated estimates, not market-provided probabilities and not guarantees. Scenario ranges are model-derived research ranges, not guaranteed price targets.
- This build was fully checked locally for Python compilation, core tests, and a deterministic end-to-end `run_analysis` smoke test using synthetic market data. Live NSE/Yahoo retrieval could not be exercised in this restricted build environment.


### Simple prediction at the top
After clicking Analyze, the dashboard now shows a simple headline for the next 1 month and 2 months:
- probability-weighted expected price
- bullish probability
- BUY/HOLD/SELL view
- scenario range
- estimated upside/downside versus the current price

The expected price is calculated from the bear/base/bull scenario prices weighted by the model probabilities. It is a model estimate, not a guaranteed target.

## Deploy publicly for anyone

### Easiest: Streamlit Community Cloud (free)

1. Create a GitHub repository and upload the contents of this folder.
2. Make sure `requirements.txt` is at the repository root and keep `streamlit_app.py` at the root.
3. Go to https://share.streamlit.io/ and sign in with GitHub.
4. Click **Create app**.
5. Choose your GitHub repository and branch, and set the entrypoint to `streamlit_app.py`.
6. Choose an app subdomain such as `stock-ai-researcher-aaa` and deploy.
7. Share the resulting `https://<your-subdomain>.streamlit.app/` URL. Anyone can open the public app.

The app needs outbound internet access to pull live market/news data. The first analysis can take longer because the data sources are fetched live.

### Important

This build does not require paid API keys. The model is probabilistic and uses free data sources. Free sources can rate-limit or change, so production-scale/public traffic should eventually move to a more robust data backend and hosting setup.


## Verified final build
This package includes a deterministic end-to-end analysis-path test that exercises the real `run_analysis()` function with mocked market data, plus core ML/indicator tests. Run `bash scripts/verify_mac.sh` after setup.

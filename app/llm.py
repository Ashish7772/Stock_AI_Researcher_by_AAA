from __future__ import annotations

import os
import requests


def explain_locally(summary: str) -> str | None:
    model = os.getenv("OLLAMA_MODEL")
    if not model:
        return None
    prompt = f"""You are a cautious Indian equity research assistant. Explain the supplied structured analysis. Do not invent facts, do not claim certainty, and clearly separate model output from factual data. Keep it under 350 words. Mention the main bullish factors, bearish risks, 1-2 month scenario, and what would invalidate the thesis.\n\nDATA:\n{summary}"""
    try:
        r = requests.post("http://127.0.0.1:11434/api/generate", json={"model": model, "prompt": prompt, "stream": False}, timeout=90)
        r.raise_for_status()
        return r.json().get("response")
    except Exception:
        return None

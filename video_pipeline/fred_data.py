"""
FRED (Federal Reserve Economic Data) integration for Ch5's seven
finance niches -- personal_finance_mistakes, investing_fundamentals,
retirement_planning, credit_debt_repair, real_estate_affordability,
stock_market_crashes_history, budgeting_saving_strategies.

Direct user request: those scripts were running entirely on AI-invented
numbers dressed up with the word "documented" (confirmed by grep --
zero real data-source calls existed anywhere in collapse_index_pipeline.py
before this file). This replaces that with genuinely real observations
from the Federal Reserve Bank of St. Louis's free FRED API -- 800,000+
real economic series, no cost, a free API key from
https://fred.stlouisfed.org/docs/api/api_key.html (instant signup).

Reads FRED_API_KEY from the environment. If it's unset, or any request
fails for any reason, every public function here returns None/"" so
callers fall back to their existing AI-invented-data path untouched --
this module only ever ADDS real data on top of what already worked; it
is never required for the pipeline to keep running.
"""
import os
import random
import requests

FRED_API_KEY = os.environ.get("FRED_API_KEY", "")
FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"

# Real, well-established FRED series IDs picked per finance niche.
# Each has decades of real history -- not a guess at what might exist.
NICHE_FRED_SERIES = {
    "investing_fundamentals": [
        ("SP500", "S&P 500 Index"),
        ("DGS10", "10-Year Treasury Constant Maturity Rate"),
    ],
    "retirement_planning": [
        ("PSAVERT", "Personal Saving Rate"),
        ("SP500", "S&P 500 Index"),
    ],
    "personal_finance_mistakes": [
        ("PSAVERT", "Personal Saving Rate"),
        ("TDSP", "Household Debt Service Payments as a Percent of Disposable Personal Income"),
    ],
    "credit_debt_repair": [
        ("TERMCBCCALLNS", "Commercial Bank Credit Card Interest Rate"),
        ("TDSP", "Household Debt Service Payments as a Percent of Disposable Personal Income"),
    ],
    "real_estate_affordability": [
        ("MORTGAGE30US", "30-Year Fixed Rate Mortgage Average"),
        ("CSUSHPISA", "Case-Shiller U.S. National Home Price Index"),
    ],
    "stock_market_crashes_history": [
        ("SP500", "S&P 500 Index"),
        ("VIXCLS", "CBOE Volatility Index (VIX)"),
    ],
    "budgeting_saving_strategies": [
        ("PSAVERT", "Personal Saving Rate"),
        ("CPIAUCSL", "Consumer Price Index for All Urban Consumers"),
    ],
}

FINANCE_NICHE_NAMES = set(NICHE_FRED_SERIES.keys())


def _fetch_series(series_id, limit=200):
    """Real observations for one FRED series, oldest-first. None on any failure."""
    if not FRED_API_KEY:
        return None
    try:
        r = requests.get(FRED_BASE, params={
            "series_id": series_id,
            "api_key": FRED_API_KEY,
            "file_type": "json",
            "sort_order": "desc",
            "limit": limit,
        }, timeout=15)
        if r.status_code != 200:
            return None
        obs = [o for o in r.json().get("observations", [])
               if o.get("value") not in (None, ".", "")]
        if len(obs) < 4:
            return None
        obs.reverse()  # oldest first -> a left-to-right trend line reads correctly
        return obs
    except Exception:
        return None


def _yearly_downsample(obs, max_points=8):
    """
    Collapses raw observations (daily/weekly/monthly series all mixed)
    to one real point per year, the most recent `max_points` years --
    a chart-readable trend where every point is still a real value
    FRED actually reported, never an interpolation.
    """
    by_year = {}
    for o in obs:
        by_year[o["date"][:4]] = o["value"]
    years = sorted(by_year.keys())[-max_points:]
    return years, [round(float(by_year[y]), 2) for y in years]


def get_real_chart_data(niche_name):
    """
    Real chart_data in the exact shape the pipeline's existing
    AI-invented fallback already produces ({"chart_type","title",
    "y_label","labels","values"}, plus real provenance fields) -- so
    generate_data_chart/get_stage_matched_video/assemble_video need no
    changes to consume it. Returns None for any non-finance niche, any
    environment with no FRED_API_KEY set, or any failed fetch -- the
    caller's existing AI-data path already handles that case.
    """
    series_options = NICHE_FRED_SERIES.get(niche_name)
    if not series_options:
        return None
    series_id, description = random.choice(series_options)
    obs = _fetch_series(series_id)
    if not obs:
        return None
    years, values = _yearly_downsample(obs)
    if len(years) < 4:
        return None
    return {
        "chart_type": "line",
        "title": f"{description}: {years[0]}-{years[-1]}",
        "y_label": description,
        "labels": years,
        "values": values,
        "source": "FRED (Federal Reserve Bank of St. Louis)",
        "series_id": series_id,
        "as_of": obs[-1]["date"],
    }


def format_narration_block(chart_data):
    """
    A short block for the script prompt's research_context, so the
    spoken narration cites the same real FRED figures as the chart
    instead of the AI inventing its own separate set of numbers.
    """
    if not chart_data:
        return ""
    pairs = ", ".join(f"{l}: {v}" for l, v in zip(chart_data["labels"], chart_data["values"]))
    return (
        f"REAL SOURCED DATA (genuinely real, from {chart_data['source']}, "
        f"series {chart_data['series_id']}, most recent value as of "
        f"{chart_data['as_of']} -- cite these exact figures, do not invent "
        f"different ones):\n  {chart_data['y_label']}: {pairs}\n"
    )

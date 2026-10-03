"""Deterministic narrative generator. Explains facts; never recommends; never assumes motive."""
from __future__ import annotations

from datetime import date

from ..engines.util import pct

SECTIONS = ["why_it_may_matter", "since_trade", "since_disclosure", "bull_case", "bear_case",
            "key_risks", "invalidation", "watch_next"]
TITLES = {
    "why_it_may_matter": "WHY THIS TRADE MAY MATTER", "since_trade": "WHAT HAS HAPPENED SINCE THE TRADE",
    "since_disclosure": "WHAT HAS HAPPENED SINCE DISCLOSURE", "bull_case": "POTENTIAL BULL CASE",
    "bear_case": "POTENTIAL BEAR CASE", "key_risks": "KEY RISKS",
    "invalidation": "WHAT WOULD INVALIDATE THE THESIS", "watch_next": "WHAT TO WATCH NEXT",
}


def _money(x):
    return "n/a" if x is None else f"${x:,.2f}"


def rules_analysis(a: dict, ctx: dict) -> dict:
    t, f, dec, inst = ctx["tech"], ctx["fundamentals"], a["decay"], a["instrument"]
    buy = a["transaction_type"] != "SELL"
    verb = "purchase" if a["transaction_type"] == "BUY" else "option exercise" if a["transaction_type"] == "EXERCISE" else "sale"
    mom = t.get("momentum", {})
    rsi = t.get("rsi14")
    up = (f["target_price"] / a["price_now"] - 1) if f.get("target_price") and a.get("price_now") else None
    ne = f.get("next_earnings")
    dte = (date.fromisoformat(ne) - date.today()).days if ne else None
    mock = a["confidence_level"] == "mock" or a["price_data_type"] == "mock"
    s: dict[str, list[str]] = {k: [] for k in SECTIONS}

    amt = f"{_money(a['amount_min'])}–{_money(a['amount_max'])}" if a.get("amount_min") else "an undisclosed amount"
    s["why_it_may_matter"].append(
        f"A reported {verb} of {a['ticker']} ({a['asset_type'].replace('_', ' ')}) in the {amt} band. "
        "The actual motive is unknown; disclosures do not state reasons.")
    if inst["kind"] == "option":
        s["why_it_may_matter"].append(f"Instrument: {inst['nature']}. Option structures can imply a time-bound view, "
                                      "but premiums paid are not disclosed.")
    s["why_it_may_matter"].append(f"Trade Intelligence Score {a['score']['score']:.0f}/100 → "
                                  f"{a['score']['classification']} (relevance, not a recommendation).")

    s["since_trade"].append(f"Price moved from ~{_money(a['price_at_transaction'])} on the transaction date to "
                            f"{_money(a['price_now'])} now ({pct(a['change_since_transaction'])}).")
    if dec.get("available"):
        s["since_trade"].append(f"{pct(dec['move_before_disclosure'])} of that occurred during the "
                                f"{a['delay_days']}-day reporting lag, before the public could know.")

    if dec.get("available"):
        s["since_disclosure"].append(f"Since disclosure ({a['disclosure_date']}), price changed "
                                     f"{pct(dec['move_after_disclosure'])} over {dec['days_since_disclosure']} days.")
        s["since_disclosure"].append(f"Opportunity Decay {dec['score']:.0f}/100 — {dec['label']}.")
    s["since_disclosure"].append(f"Momentum: 1M {pct(mom.get('1m'))}, 3M {pct(mom.get('3m'))}, 6M {pct(mom.get('6m'))}.")

    # bull / bear built from the same facts, framed neutrally
    bull, bear = [], []
    if t.get("above_sma200"):
        bull.append("Price trades above its 200-day average — long-term trend still positive.")
    else:
        bear.append("Price is below its 200-day average — long-term trend has weakened.")
    if up is not None:
        (bull if up > 0.1 else bear).append(f"Average analyst target implies {pct(up)} vs current price.")
    if f.get("revenue_growth") is not None:
        (bull if f["revenue_growth"] > 0.1 else bear).append(f"Revenue growth {pct(f['revenue_growth'], 0)} YoY.")
    if f.get("forward_pe"):
        (bear if f["forward_pe"] > 40 else bull).append(f"Forward P/E {f['forward_pe']:.0f}x "
                                                       f"{'— demanding valuation' if f['forward_pe'] > 40 else '— not extreme'}.")
    if rsi is not None and rsi > 70:
        bear.append(f"RSI {rsi:.0f}: short-term overbought conditions.")
    if dec.get("available") and dec["favourable_before"] > 0.1:
        bear.append("A large part of the move happened before disclosure; late followers may face worse risk/reward.")
    if not buy:
        bull, bear = ([x + " (context for a disclosed SALE: may argue against the sale)" for x in bull],
                      [x + " (may be consistent with the disclosed sale)" for x in bear])
    s["bull_case"] = bull[:4] or ["No strong positive factors in the available data."]
    s["bear_case"] = bear[:4] or ["No strong negative factors in the available data."]

    s["key_risks"].append(f"Reporting lag of {a['delay_days']} days; the position may already have changed.")
    if dte is not None and dte <= 21:
        s["key_risks"].append(f"Earnings in {dte} days — elevated event risk.")
    if t.get("vol_3m"):
        s["key_risks"].append(f"3-month annualised volatility {t['vol_3m'] * 100:.0f}%.")
    if inst["kind"] == "option" and inst.get("days_to_expiry") is not None and inst["days_to_expiry"] < 90:
        s["key_risks"].append("Option is near or past expiry — the original structure may no longer be live.")

    ref = a["price_at_disclosure"] or a["price_now"]
    if buy and t.get("sma200"):
        s["invalidation"].append(f"Sustained close below the 200-day average (~{_money(t['sma200'])}).")
    if buy and ref:
        s["invalidation"].append(f"Price falling >15% below the disclosure price (~{_money(ref * 0.85)}).")
    s["invalidation"].append("A subsequent disclosure reversing the position (e.g. a sale of the same ticker).")
    s["invalidation"].append("Material deterioration of guidance or revenue growth at the next earnings.")

    if ne:
        s["watch_next"].append(f"Next earnings: {ne}.")
    s["watch_next"].append("New Periodic Transaction Reports for the same ticker.")
    if inst["kind"] == "option" and a.get("expiration"):
        s["watch_next"].append(f"Option expiration {a['expiration']} and strike {_money(a['strike'])} vs spot.")
    s["watch_next"].append(f"Relative strength vs SPY/QQQ and sector ETF {ctx.get('sector_etf') or ''}.")

    if mock:
        s["why_it_may_matter"].insert(0, "⚠ Based on MOCK development data — illustrative only.")
    return {"engine": "rules", "sections": s, "titles": TITLES,
            "disclaimer": "Generated explanation. Not investment advice. Motives behind the trade are unknown."}

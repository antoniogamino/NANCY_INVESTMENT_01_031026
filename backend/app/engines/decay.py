"""OPPORTUNITY DECAY — how much of the potential move already happened before the
public could know about the trade, and how much has happened since.

    before  = P_disclosure / P_transaction - 1     (move the public could NOT capture)
    after   = P_now        / P_disclosure  - 1     (move available to a public follower so far)
    total   = P_now        / P_transaction - 1

Moves are *signed by direction*: for a SELL a price decline is the "favourable" move.

Decay Score (0-100, higher = more opportunity plausibly remaining):
    100
    - 1.6 x favourable move before disclosure (in %)
    - 1.2 x favourable move after disclosure (in %)
    - 0.25 x days since disclosure (max 25 pts)
    + up to 10 pts if price moved AGAINST the trade before disclosure (public gets a better entry)
This is a heuristic, not a forecast.
"""
from __future__ import annotations

from .util import clamp, direction

LABELS = [
    (70, "OPPORTUNITY LIKELY INTACT", "positive"),
    (45, "PARTIALLY DECAYED", "warning"),
    (25, "MOSTLY PRICED IN", "warning"),
    (0, "LIKELY TOO LATE", "negative"),
]


def label_for(score: float) -> tuple[str, str]:
    for th, lab, tone in LABELS:
        if score >= th:
            return lab, tone
    return LABELS[-1][1], LABELS[-1][2]


def opportunity_decay(p_tx: float | None, p_disc: float | None, p_now: float | None,
                      days_since_disclosure: int, tx_type: str = "BUY") -> dict:
    if not (p_tx and p_disc and p_now):
        return {"available": False, "score": None, "label": "INSUFFICIENT DATA", "tone": "neutral"}
    d = direction(tx_type)
    before, after, total = p_disc / p_tx - 1, p_now / p_disc - 1, p_now / p_tx - 1
    b_s, a_s, t_s = before * d, after * d, total * d
    score = 100.0
    score -= 1.6 * max(0.0, b_s * 100)
    score -= 1.2 * max(0.0, a_s * 100)
    score -= min(25.0, 0.25 * max(0, days_since_disclosure))
    if b_s < 0:
        score += min(10.0, -b_s * 100 * 0.5)
    score = clamp(score)
    captured = (b_s / t_s) if t_s > 0 and b_s > 0 else (0.0 if t_s > 0 else None)
    lab, tone = label_for(score)
    return {
        "available": True,
        "price_transaction": p_tx, "price_disclosure": p_disc, "price_now": p_now,
        "move_before_disclosure": before, "move_after_disclosure": after, "move_total": total,
        "favourable_before": b_s, "favourable_after": a_s, "favourable_total": t_s,
        "share_captured_before_disclosure": captured,
        "days_since_disclosure": days_since_disclosure,
        "score": round(score, 1), "label": lab, "tone": tone,
        "method": "heuristic", "data_type": "calculated",
    }

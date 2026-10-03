from __future__ import annotations


def interp(x: float, pts: list[tuple[float, float]]) -> float:
    """Piecewise-linear interpolation with flat extrapolation. pts must be sorted by x."""
    if x <= pts[0][0]:
        return pts[0][1]
    if x >= pts[-1][0]:
        return pts[-1][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return pts[-1][1]


def clamp(x: float, lo: float = 0, hi: float = 100) -> float:
    return max(lo, min(hi, x))


def pct(x: float | None, nd: int = 1) -> str:
    return "n/a" if x is None else f"{x * 100:+.{nd}f}%"


def direction(tx_type: str) -> int:
    """+1 for bullish activity (BUY, EXERCISE of calls), -1 for SELL."""
    return -1 if tx_type.upper() == "SELL" else 1

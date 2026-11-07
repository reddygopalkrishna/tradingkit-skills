"""Deterministic synthetic market data for offline tests."""

from __future__ import annotations

import datetime as dt
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "core"))

from tradekit.frame import Bars  # noqa: E402


def business_days(start: str, n: int):
    d = dt.date.fromisoformat(start)
    out = []
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += dt.timedelta(days=1)
    return out


def gbm(symbol="TEST", n=600, start="2022-01-03", s0=100.0, drift=0.0004, vol=0.015, seed=1, volume=1_000_000):
    rng = random.Random(seed)
    dates = business_days(start, n)
    o, h, l, c, v = [], [], [], [], []
    price = s0
    for _ in range(n):
        ret = drift + vol * rng.gauss(0, 1)
        op = price * (1 + vol * 0.2 * rng.gauss(0, 1))
        cl = price * math.exp(ret)
        hi = max(op, cl) * (1 + abs(rng.gauss(0, vol * 0.5)))
        lo = min(op, cl) * (1 - abs(rng.gauss(0, vol * 0.5)))
        o.append(op)
        h.append(hi)
        l.append(lo)
        c.append(cl)
        v.append(volume * (0.6 + rng.random() * 0.8))
        price = cl
    return Bars(symbol, "1d", dates, o, h, l, c, v, {"source": "synthetic", "adjusted": True})


def from_closes(closes, symbol="X", start="2022-01-03", spread=0.01, volumes=None):
    dates = business_days(start, len(closes))
    o = [closes[0]] + closes[:-1]
    h = [max(a, b) * (1 + spread / 2) for a, b in zip(o, closes)]
    l = [min(a, b) * (1 - spread / 2) for a, b in zip(o, closes)]
    v = volumes or [1_000_000.0] * len(closes)
    return Bars(symbol, "1d", dates, list(o), h, l, list(closes), list(v), {"source": "synthetic", "adjusted": True})

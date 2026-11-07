---
name: chart-patterns
description: Detect live chart patterns on one symbol or a whole watchlist - VCP (volatility contraction), breakouts on volume, bull flags, cup and handle, double bottoms, inside bars, NR7 and pocket pivots - each with a score, trigger (pivot) price and invalidation stop. Use when the user asks for setups, "any breakouts?", "is X forming a cup and handle", Minervini/O'Neil style bases, or wants to scan a list for patterns. Works on any market with daily or intraday bars.
license: MIT
metadata:
  author: reddygopalkrishna
  version: "0.1.0"
  pack: trading-skills
---

# Chart Patterns

Transparent, parameterised detectors - every hit shows the measurements behind it.

```bash
python3 scripts/patterns.py --list                                   # what each pattern means
python3 scripts/patterns.py NVDA                                     # all patterns, one symbol
python3 scripts/patterns.py AAPL MSFT AMZN --patterns vcp,breakout --min-score 60
python3 scripts/patterns.py --universe assets/watchlists/global-large-caps.txt --min-score 70
python3 scripts/patterns.py --csv bars.csv --symbol XYZ --json
```

## Output fields

| field | meaning |
|---|---|
| `score` | 0-100 quality of the pattern by its own criteria (not a probability) |
| `pivot` | trigger price - the setup is "on" when price trades above it |
| `stop` | where the pattern is invalidated (use as a first stop candidate) |
| `to_pivot_%` | distance from the last close to the pivot |
| `risk_%` | pivot-to-stop distance; > 8-10% usually means the base is too loose |
| `details` | the measurements (contraction depths, pole gain, volume ratios...) |

## Workflow

1. Scan (this skill) -> 2. confirm trend/volume with **technical-analysis** ->
3. check the index with **market-regime** -> 4. build entry/stop/size with **trade-planner** ->
5. sanity-check odds with **monte-carlo-sim** -> 6. **pre-trade-gate** -> 7. **order-router**.

## Notes

- VCP and cup-and-handle need ~1 year of daily bars (use `--period 2y`).
- Daily patterns are the default; intraday works with `--interval 15m --period 1mo` (breakout, flag, inside bar, NR7).
- Prefer setups with `risk_%` small enough that a normal position size still fits the user's risk limit.
- A pattern is a hypothesis, not a signal. Many fail; say so when presenting results.

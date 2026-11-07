# Changelog

## 0.1.0 - 2026-11-08

First release: 15 skills on a zero-dependency core.

- **Skills:** trading-navigator, trading-setup, market-data, technical-analysis, chart-patterns,
  market-regime, stock-screener, trade-planner, position-sizer, pre-trade-gate, order-router,
  backtester, monte-carlo-sim, trade-journal, performance-review.
- **Core:** 25+ indicators, safe rule language with 50+ functions, 8 pattern detectors, regime model,
  portfolio backtester (no look-ahead, costs, stops/targets/trails, OOS split), Monte Carlo (trade
  resampling + block-bootstrap setup odds), SQLite journal, risk gate with approvals, HTML/SVG reports.
- **Data:** Yahoo (free, no key), CSV, Zerodha Kite (Connect plan).
- **Brokers:** paper (default, OCO exits, resting orders), Zerodha Kite (orders, GTT stops).
- **Safety:** preview -> confirm code -> submit, kill switch, live-trading switch, audit log.
- **Distribution:** Claude Code plugin marketplace, skills.sh, `.skill` packages for claude.ai.

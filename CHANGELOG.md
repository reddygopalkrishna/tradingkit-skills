# Changelog

## Unreleased

- **New skill `trading-fno`:** F&O analysis for India and US. Black-Scholes price and Greeks, implied volatility
  (bisection), multi-leg payoff with breakevens and max profit/loss (named strategies or custom legs, ASCII
  chart), and option-chain OI / PCR / max pain / ATM straddle. Chain sources: Cboe delayed JSON for US tickers,
  a user-downloaded NSE option-chain CSV (read by header name), Kite instruments + quotes. Analysis only.
  Core: new `tradekit.options`. 29 tests, offline.

## 0.2.0 - 2026-11-14

The pack is now **trading-skills**, with 20 skills under one `trading-` family name, and five new skills.

- **New skills**
  - `trading-news`: only what is new on your stocks, tagged and in exchange time; Google News for every
    market (India edition for NSE/BSE), Yahoo headlines and SEC 8-Ks for US tickers; MOVING flags.
  - `trading-earnings`: quarterly revenue, margins, EPS vs a year ago, TTM and one-off flags; Yahoo for any
    market (Indian companies in Rs crore), SEC XBRL filings for US companies with derived Q4.
  - `trading-insiders`: US Congress trades read straight from House PTR PDFs (owner, ticker, options strike and
    expiry, amount range, days to disclose; alerts once per new filing), SEC Form 4, NSE bulk/block deals,
    SEBI insider disclosures from the user's downloaded CSV.
  - `trading-entry`: bar-by-bar entry timer - opening-range or level breaks, long or short, volume filter,
    no-entries-near-the-close cutoff, each exchange's own session from the data, replays of past sessions.
  - `trading-alerts`: above/below, stop/target, % move, time, opening bell and before-the-close alerts on each
    exchange's clock; stop + target for every open journal trade in one go; optional desktop notifications.
- **Renamed** (same scripts, same commands): trading-navigator -> trading-start, market-data -> trading-data,
  market-regime -> trading-market, stock-screener -> trading-scanner, chart-patterns -> trading-patterns,
  technical-analysis -> trading-chart, trade-planner -> trading-plan, monte-carlo-sim -> trading-odds,
  backtester -> trading-backtest, position-sizer -> trading-size, pre-trade-gate -> trading-risk,
  order-router -> trading-broker, trade-journal -> trading-journal, performance-review -> trading-review.
- **Settings folder** is now `~/.trading-skills` (`TRADING_SKILLS_HOME`). An existing `~/.tradingkit-skills`
  folder and the `TRADINGKIT_SKILLS_HOME` variable keep working.
- **Core:** Yahoo charts now carry each exchange's regular sessions, company name and previous close; new
  modules `feeds`, `fundamentals`, `sec`, `disclosures` (standard-library PDF text, incl. RC4-encrypted PDFs),
  `session`, `alerts`. New settings `data.sec_user_agent`, `risk.no_entries_last_minutes`.
- **Tests:** 19 new tests on real saved data (Yahoo, Google News, NSE deal files, House index and PTR PDFs);
  79 in all, offline.
- New watchlist `india-large-caps.txt`.

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
- **Docs:** full usage guide in `docs/USAGE.md`.
- **Robustness:** HTTPS falls back to the operating system's CA bundle when Python ships without
  root certificates (python.org macOS installer); verification is never disabled.
- **Kite:** limit, stop and GTT prices are validated against the instrument's tick size at preview time.

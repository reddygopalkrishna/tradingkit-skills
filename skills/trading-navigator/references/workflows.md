# Workflows

Paths are relative to the `skills/` folder. Each step names the skill and the command.

## 1. First-time setup (5 minutes, no API keys)

1. trading-setup: `setup.py init --equity 100000 --currency USD --benchmark SPY --risk-pct 1`
2. trading-setup: `setup.py doctor`
3. trading-navigator: `brief.py --watchlist assets/watchlists/us-mega-caps.txt`

## 2. Idea -> trade (swing)

1. market-regime: is the tide in? (`regime.py`)
2. stock-screener or chart-patterns: find candidates
3. technical-analysis: confirm trend, volume, levels, weekly agreement
4. trade-planner: entry / stop / target / size (`--regime-adjust --save`)
5. monte-carlo-sim `setup`: odds of target before stop (optional, recommended)
6. pre-trade-gate `check`: must PASS
7. order-router `preview` -> user confirms -> `submit --confirm CODE`
8. trade-journal `note`: thesis and grade

## 3. Strategy research

1. Write rules (stock-screener `--check`)
2. backtester with `--oos-start` and `--report`, 10+ years, several symbols
3. Vary parameters with `--set`; reject fragile results
4. monte-carlo-sim `trades --csv` on the backtest trades for drawdown ranges
5. Paper-trade it (order-router, paper broker) for weeks before going live
6. performance-review `--setup NAME` to compare live/paper to the backtest

## 4. Daily routine

- **Pre-market:** `brief.py --watchlist list.txt --report brief.html`
- **During the session:** plan -> gate -> preview/confirm for each trade
- **End of day:** order-router `process` (paper), trade-journal `close` / `note`, `gate.py status`
- **Weekly:** performance-review `--period week --report week.html`

## 5. Automation (what to schedule, what never to)

Safe to schedule (read-only or paper):
- `brief.py` pre-market and after the close, emailed or posted
- `router.py process` after the close (paper fills, journal sync)
- `review.py --period week` every weekend
- screener / pattern scans on a watchlist, saving hits to a file

Scheduling options: the agent's own scheduled tasks, or system cron, e.g.
`35 21 * * 1-5 cd ~/trading-skills/skills/trading-navigator && python3 scripts/brief.py --watchlist ~/watchlist.txt --report ~/brief.html`

Never fully automate live order submission with these skills. The confirm step is a deliberate
human check. Fully automated live trading generally needs your own broker app with the controls
your broker and regulator require (registered static IP, algo identifiers, kill switches, audit).

## 6. Risk-off day

`gate.py status` shows the daily loss or streak limit hit -> stop opening trades.
Optionally `router.py kill on --reason "daily limit"`. Review tomorrow, not today.

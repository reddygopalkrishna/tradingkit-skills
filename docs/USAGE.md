# trading-skills usage guide

This guide takes you from install to your first paper trade, then covers every skill in detail.
You can use the pack two ways:

1. **Talk to your agent** (Claude Code, claude.ai, Codex, Cursor, Gemini CLI). The agent reads each
   skill's `SKILL.md` and runs the scripts for you. This is the normal way.
2. **Run the scripts yourself** from a terminal. Every command below works on its own, which is useful
   for scripting, scheduling and checking what the agent did.

All script paths below are relative to the skill's folder, e.g. `cd skills/trading-chart` first.

---

## Contents

1. [Install](#1-install)
2. [First 10 minutes](#2-first-10-minutes)
3. [What you can trade: symbols for any market](#3-what-you-can-trade-symbols-for-any-market)
4. [Configuration and risk limits](#4-configuration-and-risk-limits)
5. [The skills, one by one](#5-the-skills-one-by-one)
6. [Complete workflow: idea to journal](#6-complete-workflow-idea-to-journal)
7. [Live trading through a broker](#7-live-trading-through-a-broker)
8. [Using your own data (CSV)](#8-using-your-own-data-csv)
9. [Automation and scheduling](#9-automation-and-scheduling)
10. [Files and where things live](#10-files-and-where-things-live)
11. [Troubleshooting](#11-troubleshooting)
12. [FAQ](#12-faq)

---

## 1. Install

Requirements: **Python 3.9 or newer**. Nothing to `pip install`; the pack uses only the standard library.

```bash
python3 --version
```

**Claude Code (plugin marketplace)**

```text
/plugin marketplace add reddygopalkrishna/trading-skills
/plugin install trading-skills@trading-skills
```

**Any agent via skills.sh** (Claude Code, Codex, Cursor, Gemini CLI and others)

```bash
npx skills add reddygopalkrishna/trading-skills
```

**claude.ai / Claude desktop app**

1. Download the `.skill` files (or `trading-skills-all.zip`) from the
   [latest release](https://github.com/reddygopalkrishna/trading-skills/releases).
2. Open *Settings -> Capabilities* and make sure code execution is on.
3. Upload each `.skill` under *Customize -> Skills*. Start with `trading-start`, `trading-setup`,
   `trading-data` and `trading-chart`, then add the rest.

**Manual (any agent that reads a skills folder)**

```bash
git clone https://github.com/reddygopalkrishna/trading-skills
cp -r trading-skills/skills/* ~/.claude/skills/     # or ~/.codex/skills, ~/.cursor/skills, ~/.gemini/skills
```

Each skill folder is self-contained (it carries its own copy of the shared engine), so you can install
only the skills you want.

---

## 2. First 10 minutes

### Step 1 - check your machine

```bash
cd skills/trading-setup
python3 scripts/setup.py doctor
```

Every line should say `OK`. If `data_provider` fails with a certificate error, see
[Troubleshooting](#11-troubleshooting).

### Step 2 - tell it about your account

Pick your own currency and a benchmark index for your market:

```bash
python3 scripts/setup.py init --equity 50000 --currency USD --benchmark SPY       # US
python3 scripts/setup.py init --equity 500000 --currency INR --benchmark ^NSEI    # India
python3 scripts/setup.py init --equity 20000 --currency GBP --benchmark ^FTSE     # UK
python3 scripts/setup.py init --equity 10000 --currency USD --benchmark BTC-USD   # crypto
```

Or just say to your agent: *"Set up trading-skills: 50,000 USD account, benchmark SPY, risk 1% per trade."*

### Step 3 - look at the market and a chart

```bash
cd ../trading-market && python3 scripts/regime.py
cd ../trading-chart && python3 scripts/analyze.py AAPL
```

### Step 4 - plan, check and paper-trade one idea

```bash
cd ../trading-plan && python3 scripts/plan.py AAPL --save --setup "pullback" --thesis "holding 50-day"
cd ../trading-risk && python3 scripts/gate.py check --plan 1
cd ../trading-broker && python3 scripts/router.py preview --symbol AAPL --side buy --qty 10 \
    --type limit --limit-price 340 --stop-loss 330 --take-profit 365
# read the preview, then use the code it printed:
python3 scripts/router.py submit --confirm ABC123
python3 scripts/router.py process      # fills resting paper orders against new prices
```

The gate approval and the preview must match exactly (symbol, side, quantity, stop). Use the
values the planner printed.

You have now used the full safety flow on paper, at zero cost.

---

## 3. What you can trade: symbols for any market

The default data source is Yahoo Finance, which covers most of the world. Use Yahoo's symbol format:

| market | format | examples |
|---|---|---|
| US stocks and ETFs | ticker | `AAPL`, `MSFT`, `SPY`, `QQQ` |
| India (NSE / BSE) | `.NS` / `.BO` | `RELIANCE.NS`, `INFY.NS`, `TCS.BO` |
| UK (London) | `.L` | `HSBA.L`, `VOD.L` |
| Germany (Xetra) | `.DE` | `SAP.DE`, `BMW.DE` |
| France (Paris) | `.PA` | `MC.PA`, `AIR.PA` |
| Japan (Tokyo) | `.T` | `7203.T` (Toyota) |
| Hong Kong | `.HK` | `0700.HK` (Tencent) |
| Canada (Toronto) | `.TO` | `SHOP.TO`, `RY.TO` |
| Australia (ASX) | `.AX` | `BHP.AX`, `CBA.AX` |
| Indices | `^` prefix | `^GSPC` (S&P 500), `^NDX`, `^NSEI` (Nifty 50), `^FTSE`, `^N225` |
| Crypto | `COIN-QUOTE` | `BTC-USD`, `ETH-USD`, `SOL-USD` |
| Forex | `PAIR=X` | `EURUSD=X`, `USDJPY=X`, `USDINR=X` |
| Futures (continuous) | `=F` | `ES=F`, `NQ=F`, `GC=F` (gold), `CL=F` (crude) |

When you trade through a broker, use the **broker's** own symbol format for orders (equity and F&O).

**What works where.** Prices, charts, scans, patterns, plans, odds, risk, alerts and the entry timer work for
every market above. Market-specific sources:

| skill | US | India (NSE / BSE) | other markets |
|---|---|---|---|
| trading-news | Google News, Yahoo, SEC 8-K | Google News (India edition) | Google News (local edition) |
| trading-earnings | SEC filings or Yahoo | Yahoo (Rs crore) | Yahoo |
| trading-insiders | Congress (House), SEC Form 4 | NSE bulk/block deals, SEBI insider CSV | - |
| live orders | paper, or a broker adapter | paper, or a broker adapter | paper, or a broker adapter |

F&O analysis (option chains, Greeks, open interest) is not in this release; it is on the roadmap.

Bundled watchlists (in `assets/watchlists/` of the scanner, patterns, market, start, entry and news skills):
`us-mega-caps.txt`, `india-large-caps.txt`, `global-large-caps.txt`, `global-index-etfs.txt`,
`world-indices.txt`, `crypto-majors.txt`. A watchlist is a plain text file with one symbol per line; `#` starts a comment.

---

## 4. Configuration and risk limits

```bash
cd skills/trading-setup
python3 scripts/setup.py show                              # everything, with defaults
python3 scripts/setup.py get risk.risk_per_trade_pct
python3 scripts/setup.py set risk.risk_per_trade_pct 0.5
python3 scripts/setup.py set account.benchmark ^NSEI
```

Defaults (change any of them):

| key | default | meaning |
|---|---|---|
| `risk.risk_per_trade_pct` | 1.0 | max % of equity lost if the stop is hit |
| `risk.max_position_pct` | 20 | max position value as % of equity |
| `risk.max_open_risk_pct` | 6 | total open risk across all positions ("portfolio heat") |
| `risk.max_open_positions` | 8 | position count limit |
| `risk.max_daily_loss_pct` | 3 | stop opening trades after losing this much today |
| `risk.max_drawdown_pct` | 15 | stop opening trades below this drawdown from peak |
| `risk.min_reward_risk` | 1.5 | minimum target-to-stop ratio |
| `risk.max_consecutive_losses` | 3 | pause after this many losses in a row |
| `risk.approval_ttl_minutes` | 30 | how long a gate PASS stays valid |
| `risk.confirm_ttl_minutes` | 10 | how long an order confirm code stays valid |
| `costs.commission_pct` | 0.03 | % of notional per side (backtests, paper) |
| `costs.slippage_pct` | 0.05 | % per fill (backtests, paper) |
| `data.provider` | yahoo | `yahoo`, `csv`, or a broker data feed |
| `broker.name` | paper | `paper`, or a live broker adapter |
| `risk.no_entries_last_minutes` | 30 | trading-entry: no new intraday entries this close to the close |
| `data.sec_user_agent` | (none) | `"Your Name you@example.com"` - SEC asks for it; enables 8-Ks, SEC earnings and Form 4 for US stocks |

Settings live in `~/.trading-skills/config.json`. Set `TRADING_SKILLS_HOME` to keep separate
setups (for example one per account).

---

## 5. The skills, one by one

Each skill's own `SKILL.md` has the full reference; this section shows the commands you will use most.
Add `--json` to almost any command for machine-readable output, and `--help` for every option.

### trading-start - start here

Routes a goal to the right skills and produces a daily brief: regime, risk dashboard, open positions
versus their stops, screen hits and live chart patterns.

```bash
python3 scripts/brief.py --watchlist assets/watchlists/us-mega-caps.txt
python3 scripts/brief.py --watchlist my.txt --preset trend-template --patterns vcp,breakout --report brief.html
```

Ask: *"What should I look at today?"* or *"Give me my morning brief."*

### trading-setup - account, risk limits, broker

```bash
python3 scripts/setup.py init --equity 50000 --currency USD --benchmark SPY
python3 scripts/setup.py doctor --symbol AAPL
python3 scripts/setup.py paper-reset --cash 100000
python3 scripts/setup.py live on --i-understand-the-risks      # only for a real broker; see section 7
```

### trading-data - prices for any symbol

```bash
python3 scripts/data.py quote AAPL RELIANCE.NS BTC-USD EURUSD=X ^GSPC
python3 scripts/data.py bars AAPL --interval 1d --period 1y
python3 scripts/data.py bars BTC-USD --interval 1h --period 1mo --out btc.csv
python3 scripts/data.py bars INFY.NS --start 2020-01-01 --end 2024-12-31 --json
python3 scripts/data.py many --universe watchlist.txt --period 2y      # warm the cache
python3 scripts/data.py clear-cache
```

Intervals: `1m 2m 5m 15m 30m 60m 1h 1d 1wk 1mo`. Yahoo limits intraday history (about 7 days for
`1m`, about 60 days for other minute bars).

### trading-chart - read one chart

Trend stage, moving averages, RSI, MACD, ADX, ATR, Bollinger squeeze, Supertrend, OBV, support and
resistance, and a daily-versus-weekly check, rolled into an explained bias score.

```bash
python3 scripts/analyze.py AAPL
python3 scripts/analyze.py INFY.NS --period 5y
python3 scripts/analyze.py BTC-USD --interval 1h --period 3mo --no-mtf
python3 scripts/analyze.py AAPL --eval "close > sma(200) and rsi(14) < 40"
```

### trading-patterns - find setups with a pivot and stop

VCP, breakout on volume, bull flag, cup and handle, double bottom, inside bar, NR7, pocket pivot.

```bash
python3 scripts/patterns.py --list
python3 scripts/patterns.py AAPL NVDA MSFT --patterns vcp,cup_handle --min-score 60
python3 scripts/patterns.py --universe assets/watchlists/global-large-caps.txt --min-score 70
```

### trading-market - should you be aggressive or defensive?

Scores trend, volatility, drawdown and (optionally) breadth and suggests an exposure level.

```bash
python3 scripts/regime.py                                     # your configured benchmark
python3 scripts/regime.py --index ^GSPC ^NSEI ^FTSE ^N225      # compare markets
python3 scripts/regime.py --index ^GSPC --universe assets/watchlists/us-mega-caps.txt
```

### trading-scanner - scan a list with rules

Describe what you want in words and the agent turns it into the rule language, or use a preset.

```bash
python3 scripts/screen.py --presets                    # list the 14 presets
python3 scripts/screen.py --universe assets/watchlists/us-mega-caps.txt --preset trend-template
python3 scripts/screen.py AAPL MSFT NVDA --rule "close > sma(200) and rsi(2) < 10" --rank "-rsi(2)"
python3 scripts/screen.py --universe my.txt --rule "rel_volume(50) > 2 and close > shift(high, 1)" --min-price 5
python3 scripts/screen.py --functions                  # every function the rule language supports
python3 scripts/screen.py --check "cross_above(ema(20), ema(50))"
```

The rule language is a safe, whitelisted expression language: `and or not`, comparisons, arithmetic and
functions such as `sma ema rsi atr adx macd_hist bb_width highest lowest shift cross_above
pct_from_high rel_volume roc`. It cannot run arbitrary code.

### trading-plan - turn an idea into exact numbers

Entry, stop options, targets, reward-to-risk, invalidation and position size.

```bash
python3 scripts/plan.py AAPL                                        # auto stop and targets
python3 scripts/plan.py AAPL --entry 195.5 --stop 188 --target 215
python3 scripts/plan.py NVDA --entry pivot --stop pattern            # from the best live pattern
python3 scripts/plan.py TSLA --side short --stop atr:2.5 --target r:2
python3 scripts/plan.py BTC-USD --stop pct:6 --fractional --lot 0.0001
python3 scripts/plan.py ES=F --stop atr:1.5 --multiplier 50 --lot 1
python3 scripts/plan.py AAPL --regime-adjust --save --setup "VCP breakout" --thesis "3rd contraction"
```

`--save` stores the plan in the journal so the gate can check it with `--plan ID`.

### trading-size - how much to buy

```bash
python3 scripts/size.py risk --equity 50000 --entry 120 --stop 114 --risk-pct 1
python3 scripts/size.py risk --equity 2000000 --entry 22500 --stop 22350 --lot 50 --margin-pct 12   # futures lots
python3 scripts/size.py risk --equity 10000 --entry 64000 --stop 61000 --fractional --lot 0.0001     # crypto
python3 scripts/size.py table --equity 50000 --entry 120 --stop 114
python3 scripts/size.py kelly --win-rate 0.45 --payoff 2.2
python3 scripts/size.py vol --equity 100000 --price 50 --annual-vol 35 --target-vol 10
python3 scripts/size.py ruin --win-rate 0.45 --payoff 2 --risk-pct 1 --ruin-pct 30
```

### trading-risk - your rules, enforced

Runs hard checks (stop present, risk per trade, reward-to-risk, position size, portfolio heat, position
count, duplicates, daily loss, losing streak, drawdown, kill switch). A PASS writes a short-lived
approval for that exact symbol, side, quantity and stop; the order router will not open a position
without it.

```bash
python3 scripts/gate.py check --symbol AAPL --side long --entry 195 --stop 188 --target 212 --qty 70 --setup VCP
python3 scripts/gate.py check --symbol AAPL --side long --entry 195 --stop 188 --target 212 --auto-size
python3 scripts/gate.py check --plan 12
python3 scripts/gate.py status          # risk dashboard
```

### trading-broker - place orders safely

Two steps, always: **preview** prints the order and a one-time confirm code; **submit** needs that
code. Paper broker by default.

```bash
python3 scripts/router.py preview --symbol AAPL --side buy --qty 70 --type limit --limit-price 195 \
    --stop-loss 188 --take-profit 212
python3 scripts/router.py submit --confirm 7KQ2XD
python3 scripts/router.py preview --symbol AAPL --side sell --qty 70 --type market --close   # exit
python3 scripts/router.py account
python3 scripts/router.py positions
python3 scripts/router.py orders --open
python3 scripts/router.py cancel P1a2b3c4d5
python3 scripts/router.py process                   # paper: fill orders, trigger stops/targets, sync journal
python3 scripts/router.py kill on --reason "stepping away"
python3 scripts/router.py kill on --flatten         # also cancel orders and close paper positions
python3 scripts/router.py kill off
```

Order types: `market`, `limit`, `stop`, `stop_limit`. On paper, `--stop-loss` and `--take-profit` become
a one-cancels-other exit pair after the entry fills.

### trading-backtest - test a strategy on history

Portfolio backtests with no look-ahead, commissions, slippage, stops, targets, trailing stops,
ranking, position limits and an optional out-of-sample split. Six example strategies ship in
`assets/strategies/`.

```bash
python3 scripts/backtest.py --spec assets/strategies/donchian-breakout.json \
    --universe SPY,QQQ,GLD,TLT --start 2008-01-01 --oos-start 2018-01-01 --report donchian.html
python3 scripts/backtest.py --entry "cross_above(ema(20), ema(50))" --exit "cross_below(ema(20), ema(50))" \
    --stop atr:3 --start 2010-01-01 SPY
python3 scripts/backtest.py --spec my.json --universe list.txt --set n=10 --set mult=2.5
python3 scripts/backtest.py --spec my.json --trades-csv trades.csv     # feed trading-odds / trading-review
```

The strategy file format is documented in `skills/trading-backtest/references/strategy-spec.md`. Read the
caveats the report prints (trade count, survivorship bias, missing out-of-sample period).

### trading-odds - odds and ranges

```bash
python3 scripts/mc.py setup AAPL --entry 195 --stop 188 --target 212 --horizon 20      # target before stop?
python3 scripts/mc.py trades --journal --risk-pct 1 --trades 100                       # drawdown ranges
python3 scripts/mc.py trades --csv trades.csv --risk-pct 0.5 --report mc.html
python3 scripts/mc.py trades --r "2.1,-1,-1,0.4,3,-1,-0.6,1.8,-1,2.5" --trades 200
```

### trading-journal - record every trade

```bash
python3 scripts/journal.py plan --symbol AAPL --side long --entry 195 --stop 188 --target 212 --qty 70 --setup VCP
python3 scripts/journal.py open --id 3 --price 195.4 --qty 70
python3 scripts/journal.py close --id 3 --price 209.8 --reason target --fees 2.5
python3 scripts/journal.py note --id 3 --text "moved stop to breakeven" --grade A --tags discipline
python3 scripts/journal.py list --status open
python3 scripts/journal.py import --file broker_trades.csv
python3 scripts/journal.py export --file trades.csv
```

Paper fills are journaled automatically by the order router.

### trading-review - learn from your results

Win rate, average R, expectancy, profit factor and drawdown, broken down by setup, side and month, plus
coaching on common leaks (cutting winners early, holding losers, ignoring stops).

```bash
python3 scripts/review.py
python3 scripts/review.py --period week
python3 scripts/review.py --since 2026-01-01 --report review.html
python3 scripts/review.py --setup VCP
```

### trading-news - what is new on your stocks

Only items not shown before, newest first, in the exchange's local time, tagged (earnings, analyst, deal,
capital, people, legal, regulatory, halt, risk, macro), with the move from yesterday's close.

```bash
python3 scripts/news.py RELIANCE.NS TCS.NS AAPL
python3 scripts/news.py --watchlist my.txt --hours 12
python3 scripts/news.py --journal                 # tickers of open and planned trades
```

Google News for every market (India edition for `.NS` / `.BO`), Yahoo headlines and SEC 8-Ks for US tickers.

### trading-earnings - quarterly results

```bash
python3 scripts/earnings.py RELIANCE.NS INFY.NS   # Rs crore, any market via Yahoo
python3 scripts/earnings.py AAPL --source sec     # US filings, years deep (needs data.sec_user_agent)
```

### trading-insiders - insiders, Congress, big deals

```bash
python3 scripts/insiders.py congress --member pelosi --read      # US House reports, read from the PDFs
python3 scripts/insiders.py congress --new --read                # only filings not seen before
python3 scripts/insiders.py form4 NVDA --buys-sells              # US company insiders (SEC)
python3 scripts/insiders.py deals --min-value-cr 25              # NSE bulk + block deals
python3 scripts/insiders.py sebi ~/Downloads/insider.csv         # SEBI insider CSV from nseindia.com
```

NSE's website blocks programs, so for SEBI insider trades download the CSV yourself (nseindia.com >
Companies > Corporate filings > Insider trading > Download .csv) and pass the file.

### trading-entry - the moment to get in

Opening-range breakout or a level break, long or short, on closed bars only.

```bash
python3 scripts/entry.py check RELIANCE.NS                 # NSE range 09:15-09:30
python3 scripts/entry.py check AAPL --side short
python3 scripts/entry.py watch INFY.NS --until 14:30        # prints each closed bar, exits on the trigger
python3 scripts/entry.py watchlist --watchlist my.txt
```

Practise on past sessions: save a chart and replay it with `--offline FILE --now "YYYY-MM-DD HH:MM"`.

### trading-fno - options: Greeks, payoff, option chain

Analysis only; it never places an order. Lot sizes are yours (or Kite's) to give, never guessed.

```bash
python3 scripts/fno.py greeks --spot 24500 --strike 24600 --kind call --days 7 --iv 14 --lot-size 75
python3 scripts/fno.py iv --price 120 --spot 24500 --strike 24600 --kind call --days 7
python3 scripts/fno.py strategies                             # named shapes
python3 scripts/fno.py strategy --name iron-condor --strikes 24000,24200,24800,25000 --premiums 20,60,55,18 --lot-size 75 --spot 24500 --chart
python3 scripts/fno.py strategy --legs +1C24600@120 -1C24800@60 --lot-size 75
python3 scripts/fno.py chain AAPL                             # US: Cboe delayed data, nearest expiry
python3 scripts/fno.py chain NIFTY --file ~/Downloads/option-chain.csv --spot 24512 --expiry 2026-11-27
python3 scripts/fno.py chain NIFTY --kite                     # Kite instruments + quotes (market-data plan)
```

- **India:** nseindia.com blocks programs, so download the option-chain CSV from its Option Chain page
  (Download) and pass it with `--file`, plus `--spot` and `--expiry` (the file has neither). Or use `--kite`.
- **US:** Cboe's public delayed JSON, no key, about 15 minutes late, unofficial and able to change. Yahoo's
  options endpoint needs a cookie and crumb, so it is not used.
- The chain shows OI, PCR, max pain, the biggest call and put OI strikes, and the ATM straddle (the market's
  implied move). Payoff is at expiry; Black-Scholes is European with `--rate` (default 5%) - set your own.

### trading-alerts - let the numbers call you

```bash
python3 scripts/alerts.py add --symbol RELIANCE.NS --above 1400
python3 scripts/alerts.py add --from-journal                  # stop + target of every open trade
python3 scripts/alerts.py add --symbol RELIANCE.NS --close 10  # 10 min before NSE closes
python3 scripts/alerts.py check --notify                       # run every few minutes
python3 scripts/alerts.py clock RELIANCE.NS AAPL               # is each exchange open?
```

---

## 6. Complete workflow: idea to journal

A typical session, in plain words to your agent:

1. *"How's the market?"* - **trading-market** sets how aggressive to be.
2. *"Scan my watchlist for stocks near 52-week highs with rising volume."* - **trading-scanner**.
3. *"Any VCPs or flags among those?"* - **trading-patterns**.
4. *"Analyze the best one, daily and weekly."* - **trading-chart**.
5. *"Plan a long with 1% risk and save it."* - **trading-plan** (sizes it, saves to the journal).
6. *"Check it against my rules."* - **trading-risk** (PASS or a list of reasons it is blocked).
7. *"What are the odds it hits 2R before the stop?"* - **trading-odds** (optional).
8. *"Paper-buy it."* - **trading-broker** shows a preview and a confirm code; you say *"confirm"*.
9. Later: *"Process paper orders"* and *"Review my trades this week."* - **trading-broker**,
   **trading-review**.

The agent cannot skip steps 6 and 8: the router refuses opening orders without a matching gate
approval, and every submission needs the confirm code from a preview you have seen.

---

## 7. Live trading through a broker

Every skill except order placement works whichever broker you use: plan and size the trade here, then place it in
your broker's app. For orders straight from your agent, the pack talks to brokers through adapters behind one small
interface (`core/tradekit/brokers/base.py`), so adding a broker is a contained change. The same risk gate, preview
and confirm step apply to every broker.

Adapters available now (all Indian brokers with an official API):

| Broker | Status | Symbol format | Cost of API | Daily login | Notes |
|---|---|---|---|---|---|
| Zerodha Kite | tested in use | `NSE:INFY` | Personal plan free (orders); data needs paid Connect | yes | GTT stops |
| Fyers (API v3) | beta | `NSE:SBIN-EQ` | Standard plan free | yes | static IP may be required |
| Upstox | beta | `NSE_EQ\|INE669E01016` (instrument key) | not stated in docs | yes (until 03:30) | no MARKET orders since Apr 2026 |
| Dhan (DhanHQ v2) | beta | `NSE_EQ:11536` (securityId) | Trading APIs free | token valid 24 h | static IP mandatory for orders |
| Groww | beta | `NSE:RELIANCE` | Trading API subscription (price not in docs) | token expires 06:00 | no quotes: values at cost |
| Angel One (SmartAPI) | **not supported yet** | - | - | - | see "Brokers not supported" below |

*Beta* means: written against each broker's official API documentation and covered by offline tests that use
mocked responses; it has **not** been exercised against a live account by the maintainers. Place one very small
order first and check it in your broker's app. Contributions that confirm or fix a field are welcome.

Every adapter uses the same Broker interface and the same flow: trading-risk approval, then preview with a confirm
code, then your explicit yes, then submit. The kill switch and `live on --i-understand-the-risks` apply to all of
them. Credentials go in `~/.trading-skills/secrets.json` (mode 600) or environment variables and are never printed.

Set `broker.default_exchange` / `broker.default_product` with `setup.py set`. Product names are mapped per broker:
`CNC` (delivery), `MIS` (intraday), `NRML` (carry-forward derivatives). Entry orders on all live brokers do not
carry the stop: after the fill, place a protective stop order (`preview --type stop --stop-price X --close`).
Kite also supports a broker-side GTT stop (`--protect`).

**Static IP / algo rules.** SEBI's retail algo rules (effective April 2026) mean several brokers require orders
to come from a registered static IP, and algo registration above 10 orders per second. These are your
responsibility; check your broker's current notice before going live.

### Zerodha Kite

**Plans.** Kite's free *Personal* API plan covers orders, GTT and portfolio. Historical and live market
data need the paid *Connect* plan; without it, keep `data.provider` set to `yahoo`.

**Before you start.** Check your broker's and regulator's current rules for API trading (for example a
registered static IP or algorithm identifiers). These are your responsibility.

1. Create an app at the Kite developer console and note the API key and secret.
2. Save the credentials (stored in `~/.trading-skills/secrets.json` with permissions 600; environment
   variables `KITE_API_KEY`, `KITE_API_SECRET`, `KITE_ACCESS_TOKEN` take precedence):

   ```bash
   cd skills/trading-setup
   python3 scripts/setup.py kite-login --api-key YOUR_KEY --api-secret YOUR_SECRET
   ```

3. Open the login URL it prints, log in, and copy `request_token` from the redirect URL. Then:

   ```bash
   python3 scripts/setup.py kite-session --request-token THE_TOKEN
   ```

   Kite access tokens expire every day, so repeat steps 3 each trading morning.

4. Point the pack at Kite and set your defaults:

   ```bash
   python3 scripts/setup.py set broker.name kite
   python3 scripts/setup.py set broker.default_exchange NSE
   python3 scripts/setup.py set broker.default_product CNC
   python3 scripts/setup.py doctor
   ```

5. Turn on live trading explicitly. Until you do, the router refuses to send live orders:

   ```bash
   python3 scripts/setup.py live on --i-understand-the-risks
   ```

**Placing orders.** Symbols use Kite's format: `NSE:INFY`. Limit and stop prices must be on the
instrument's tick size; the preview rejects prices that are not and suggests valid ones. Kite entry
orders do not carry a stop, so after the entry fills place a protective GTT stop:

```bash
cd skills/trading-broker
python3 scripts/router.py preview --symbol NSE:INFY --side buy --qty 10 --type limit --limit-price 1500 --stop-loss 1450
python3 scripts/router.py submit --confirm CODE
python3 scripts/router.py preview --protect --symbol NSE:INFY --qty 10 --stop-price 1450
python3 scripts/router.py submit --confirm CODE2
```

**Recommended first steps.** Paper-trade the same workflow first, then place one very small live order
and check it in the Kite app before you rely on the integration.

Turn live trading off any time with `setup.py live off`, or halt everything with `router.py kill on`.

### Fyers

1. Create an app in the Fyers API dashboard with the *Order Placement* permission (add *Transactions Info* for
   balances) and note the App ID, secret and the redirect URL you registered. The Standard plan is free.
2. ```bash
   cd skills/trading-setup
   python3 scripts/setup.py fyers-login --app-id ABCD1234-100 --secret YOUR_SECRET --redirect-uri https://127.0.0.1/
   python3 scripts/setup.py fyers-session --auth-code THE_AUTH_CODE
   python3 scripts/setup.py set broker.name fyers
   ```
   Open the printed URL, log in, copy `auth_code` from the redirect URL. Tokens expire daily (about 06:30 IST).
   Env vars: `FYERS_APP_ID`, `FYERS_SECRET`, `FYERS_REDIRECT_URI`, `FYERS_ACCESS_TOKEN`.
3. Symbols: `NSE:SBIN-EQ` (a bare `SBIN` becomes `NSE:SBIN-EQ` when `broker.default_exchange` is NSE). Products
   `CNC`, `INTRADAY`/`MIS`, `MARGIN`/`NRML`, `MTF`. Fyers limits: 10 order calls/s.
4. Positions list is the day's positions only (no delivery holdings call yet).

### Upstox

1. Create an app in the Upstox developer console; note API key, secret and redirect URL.
2. ```bash
   python3 scripts/setup.py upstox-login --api-key KEY --api-secret SECRET --redirect-uri https://127.0.0.1/
   python3 scripts/setup.py upstox-session --code THE_CODE
   python3 scripts/setup.py set broker.name upstox
   ```
   The token is valid until 03:30 the next day. Env vars: `UPSTOX_API_KEY`, `UPSTOX_API_SECRET`,
   `UPSTOX_REDIRECT_URI`, `UPSTOX_ACCESS_TOKEN`.
3. Symbols are **instrument keys** such as `NSE_EQ|INE669E01016`; find them in Upstox's daily instrument file
   (`assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz`). Products `D`/`CNC`, `I`/`MIS`, `MTF`.
4. MARKET orders are rejected by Upstox's API rules; the preview refuses them. Use limit orders.
5. Holdings are not listed (only the day's positions).

### Dhan

1. In web.dhan.co open *My Profile > Access DhanHQ APIs*, create an access token (valid 24 hours), and register your
   static IP with Dhan (mandatory for placing and cancelling orders). Trading APIs are free.
2. ```bash
   python3 scripts/setup.py dhan-login --client-id YOUR_CLIENT_ID --access-token THE_TOKEN
   python3 scripts/setup.py set broker.name dhan
   ```
   Env vars: `DHAN_CLIENT_ID`, `DHAN_ACCESS_TOKEN`.
3. Symbols are `SEGMENT:securityId`, e.g. `NSE_EQ:11536`. Look the id up in Dhan's scrip master CSV
   (`images.dhan.co/api-data/api-scrip-master.csv`). Products `CNC`, `INTRADAY`/`MIS`, `MARGIN`/`NRML`, `MTF`.
4. Dhan returns no last price on positions, so position values are shown at cost.

### Groww

1. Subscribe to the Trading API in Groww (*Profile > Trading APIs*), then create an access token there
   (it expires daily at 06:00).
2. ```bash
   python3 scripts/setup.py groww-login --access-token THE_TOKEN
   python3 scripts/setup.py set broker.name groww
   ```
   Or let the pack mint it from an approved API key: `groww-login --api-key KEY --api-secret SECRET`.
   Env var: `GROWW_ACCESS_TOKEN`.
3. Symbols `NSE:RELIANCE` (exchange and trading symbol), cash segment only. Products `CNC`, `MIS`, `NRML`.
   Groww has no quote call in this adapter, so position values are at cost.

### Brokers not supported yet

- **Angel One (SmartAPI)** has an official API (free), but it needs a fresh TOTP at every login, a registered
  static IP for order calls, and instrument tokens from its scrip master. We could not verify the current login
  and order documentation well enough to ship an adapter we would describe as tested, so it is left out. A
  contribution is welcome.
- Any broker without an official public API (we do not use unofficial or reverse-engineered endpoints).

---

## 8. Using your own data (CSV)

Point the pack at a folder of `SYMBOL.csv` files (columns `date,open,high,low,close,volume`;
the header names are matched case-insensitively):

```bash
cd skills/trading-setup
python3 scripts/setup.py set data.provider csv
python3 scripts/setup.py set data.csv_dir /path/to/folder
```

Or per command: `--provider csv`, `--csv file.csv --symbol XYZ` (analysis, patterns, regime), or
`--csv-dir ./data` (trading-backtest). This works for any market, including ones Yahoo does not cover, and
for fully offline research.

---

## 9. Automation and scheduling

Read-only and paper tasks are safe to schedule:

| task | command |
|---|---|
| morning brief | `trading-start/scripts/brief.py --watchlist my.txt --report brief.html` |
| scans | `trading-scanner/scripts/screen.py --universe my.txt --preset trend-template --save hits.txt` |
| paper fills | `trading-broker/scripts/router.py process` |
| weekly review | `trading-review/scripts/review.py --period week --report week.html` |

Use cron, launchd, Task Scheduler or your agent's scheduled tasks. Live order submission always keeps a
human confirmation step by design. See `skills/trading-start/references/workflows.md` for daily and
weekly routines.

---

## 10. Files and where things live

Everything is under `~/.trading-skills/` (or `TRADING_SKILLS_HOME`):

| path | contents |
|---|---|
| `config.json` | your settings and risk limits |
| `secrets.json` | broker credentials (permissions 600) |
| `cache/` | downloaded market data |
| `journal.db` | SQLite trade journal |
| `paper/` | paper broker account and orders |
| `approvals/` | gate approvals waiting to be used |
| `pending/` | order previews waiting for a confirm code |
| `audit.log` | JSON lines: every preview, submit, cancel and gate decision |
| `alerts.json` | your alert rules (`state/alerts.json`: what rang) |
| `state/` | news already shown, insider filings already seen, the last entry trigger |
| `KILL_SWITCH` | exists while the kill switch is on |

Back up `journal.db` and `config.json` if your history matters to you. Upgrading from v0.1
(tradingkit-skills)? Your existing `~/.tradingkit-skills` folder keeps being used automatically.

---

## 11. Troubleshooting

**`CERTIFICATE_VERIFY_FAILED`** - Python cannot find root certificates. The pack falls back to your
operating system's certificate bundle automatically; if that still fails, on macOS run
*Install Certificates.command* from your Python folder (`/Applications/Python 3.x/`), or set
`SSL_CERT_FILE` to a CA bundle.

**`no index: pass --index SYMBOL`** - set a benchmark once:
`setup.py set account.benchmark ^GSPC` (use your market's index).

**Empty or missing data** - check the symbol format in [section 3](#3-what-you-can-trade-symbols-for-any-market).
Yahoo's endpoint is unofficial; if it is rate-limiting you, wait a few minutes or run
`data.py clear-cache` if you suspect a bad cached file.

**`no valid trading-risk approval`** - the preview must match the gate check exactly (symbol, side,
quantity, stop), and approvals expire after `risk.approval_ttl_minutes`. Run the gate again.

**`no pending order with code`** - confirm codes are single-use and expire after
`risk.confirm_ttl_minutes`. Preview again.

**`KILL SWITCH is ON`** - `router.py kill status` shows why; `router.py kill off` resumes.

**Kite `403`** - the access token expired (log in again) or your plan does not include that API.

Still stuck? Open an issue with the command, the full output and `setup.py doctor` output.

---

## 12. FAQ

**Is it only for stocks?** No. Anything with price bars works: stocks and ETFs on most exchanges,
indices, forex, crypto and continuous futures. Position sizing handles share counts, futures lots and
multipliers, and fractional crypto quantities.

**Do I need an API key or to pay anything?** No. Data (Yahoo), the paper broker, analysis, screening,
backtesting and the journal are free with no account. You only pay a broker if you choose its paid API or
data plan.

**Does the AI make up the numbers?** No. Every indicator, size, backtest and probability is computed by
the tested Python scripts; the agent explains the results.

**Can the agent trade without me?** Not for live orders. Each order needs a confirm code from a preview,
and opening orders need a fresh gate PASS. You can schedule analysis and paper processing.

**Options?** Not yet; an options strategy builder is on the roadmap.

**Is this financial advice?** No. It is educational and research software. You are responsible for
every decision and order.

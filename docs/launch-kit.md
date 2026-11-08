# Launch kit

## Before you post (30 minutes that decide most of the stars)

- [ ] Repo description: *Trading skills for AI agents - any market, any broker, zero API keys. Analysis, screening, patterns, risk gate, backtests, Monte Carlo, journal, paper/live orders.*
- [ ] Topics: `agent-skills` `claude-skills` `claude-code` `trading` `algorithmic-trading` `backtesting` `technical-analysis` `risk-management` `paper-trading` `stock-screener` `python` `zero-dependency`
- [ ] Social preview image (Settings -> General): a dark card with the 15 skill names.
- [ ] Record a 30-45s screen GIF of one prompt going plan -> gate -> preview -> confirm (paper). Put it at the top of the README.
- [ ] Tag `v0.1.0` so the Release workflow attaches `.skill` packages.
- [ ] Install it yourself through all three channels (plugin, `npx skills add`, `.skill` upload) once.
- [ ] Pin the repo on your profile.

## Where to share

| place | angle | note |
|---|---|---|
| X / Twitter thread | "I built 15 trading skills for AI agents that work on any market with zero API keys" + GIF | tag the agent communities, not individuals |
| LinkedIn | builder story: why deterministic math + a risk gate matter for AI trading tools | |
| Reddit r/ClaudeAI, r/ClaudeCode | show the plugin install + one workflow | follow each sub's self-promo rules |
| Reddit r/algotrading | lead with the backtester's honest defaults (next-open fills, costs, OOS, survivorship warning) | read the rules; post as a discussion, not an ad |
| Hacker News | `Show HN: Trading skills for AI agents - zero deps, any market, human-confirmed orders` | post on a weekday morning US time, reply to every comment |
| Instagram / YouTube Shorts | 30s reel: one prompt -> live chart analysis -> trade plan -> gate PASS -> confirm code | script below |
| Awesome lists | PRs to awesome lists for Claude skills / agent skills / algorithmic trading | one line, honest description |

skills.sh ranks by install telemetry from `npx skills add`, so every README and post should show that command.

## X thread draft

1/ I open-sourced **tradingkit-skills**: 15 skills that turn Claude Code, Codex, Cursor or Gemini CLI into a disciplined trading co-pilot. Any market. Any broker. Zero API keys to start. [GIF]

2/ Most AI trading tools let the model "estimate" numbers. Here every indicator, pattern, size and backtest is deterministic Python - tested, reproducible, zero dependencies.

3/ Risk is enforced, not suggested: a pre-trade gate checks stop, risk per trade, R:R, position size, portfolio heat, daily loss, losing streak and drawdown. FAIL = the order router refuses.

4/ Orders are paper by default. Live orders need an explicit switch, a fresh gate approval and a one-time confirm code you approve in chat. Kill switch + audit log included.

5/ Also: a backtester with no look-ahead and honest caveats, Monte Carlo odds for any setup, a journal and performance coaching ("you hold losers 2x longer than winners").

6/ Free data out of the box, works on global stocks, ETFs, indices, FX, futures and crypto. Install:
`npx skills add reddygopalkrishna/tradingkit-skills`
github.com/reddygopalkrishna/tradingkit-skills - stars and PRs welcome. Not financial advice.

## Show HN text

Trading-skills is a set of 15 Agent Skills (the open SKILL.md format) for trading research and execution. Design choices: (1) all math in a zero-dependency Python core, never estimated by the model; (2) a safe AST-whitelisted rule language shared by the screener and backtester; (3) a hard risk gate whose approval the order router requires; (4) preview -> human confirm code -> submit, with paper trading as the default. Backtests fill at the next open with costs and print survivorship and sample-size caveats. Feedback on the execution model and the gate's checks is very welcome.

## 30-second reel script

- 0-3s hook (screen + face): "I gave my AI agent a risk manager it can't argue with."
- 3-10s: type "Scan my watchlist for breakouts" -> pattern table appears.
- 10-17s: "Plan the best one with 1% risk" -> entry/stop/target/size table.
- 17-24s: gate runs -> 12 green PASS rows -> preview with confirm code.
- 24-30s: "15 free skills, any market, link in bio. Not financial advice." + repo URL on screen.

## Keeping momentum

- Ship one wave every 1-2 weeks (roadmap in README) and post each as a short update.
- Label 5-10 `good first issue`s (new presets, indicators, a broker adapter).
- Answer issues within a day for the first month.

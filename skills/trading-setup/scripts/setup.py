#!/usr/bin/env python3
"""Configure trading-skills: account, risk limits, data provider, broker, credentials.

Examples
  python3 scripts/setup.py init --equity 500000 --currency USD --benchmark SPY
  python3 scripts/setup.py show
  python3 scripts/setup.py set risk.risk_per_trade_pct 0.5
  python3 scripts/setup.py doctor --symbol AAPL
  python3 scripts/setup.py kite-login --api-key XXXX --api-secret YYYY
  python3 scripts/setup.py kite-session --request-token ZZZZ
  python3 scripts/setup.py paper-reset --cash 100000
  python3 scripts/setup.py live on --i-understand-the-risks
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "_vendor"))

import platform  # noqa: E402

from tradekit import DISCLAIMER, __version__, cli, config  # noqa: E402


def cmd_init(a):
    existed = config.exists()
    cfg = config.load()
    if existed and not a.force and not any([a.equity, a.currency, a.benchmark, a.timezone, a.provider, a.broker,
                                            a.risk_pct, a.csv_dir, a.exchange, a.product]):
        print(f"Config already exists at {config.home() / 'config.json'} (use --force or `set`).")
        return cmd_show(a)
    if a.equity is not None:
        cfg["account"]["equity"] = float(a.equity)
    if a.currency:
        cfg["account"]["currency"] = a.currency.upper()
    if a.benchmark:
        cfg["account"]["benchmark"] = a.benchmark
    if a.timezone:
        cfg["account"]["timezone"] = a.timezone
    if a.provider:
        cfg["data"]["provider"] = a.provider
    if a.csv_dir:
        cfg["data"]["csv_dir"] = a.csv_dir
    if a.broker:
        cfg["broker"]["name"] = a.broker
    if a.exchange:
        cfg["broker"]["default_exchange"] = a.exchange.upper()
    if a.product:
        cfg["broker"]["default_product"] = a.product.upper()
    if a.risk_pct is not None:
        cfg["risk"]["risk_per_trade_pct"] = float(a.risk_pct)
    f = config.save(cfg)
    print(f"Saved {f}")
    cmd_show(a)


def cmd_show(a):
    cfg = config.load()
    s = config.load_secrets()
    out = {"home": str(config.home()), "config": cfg,
           "secrets": {k: config.mask(v) for k, v in s.items()},
           "kill_switch": config.kill_switch_on(), "version": __version__}
    if getattr(a, "json", False):
        print(cli.dump(out))
        return
    acc, risk, data, br = cfg["account"], cfg["risk"], cfg["data"], cfg["broker"]
    print(f"## trading-skills config  (v{__version__})\n")
    print(f"Home: `{out['home']}`")
    print(f"- Account: equity {acc['equity']:,.2f} {acc['currency']}, benchmark {acc['benchmark'] or '(not set)'}, tz {acc['timezone']}")
    print(f"- Data: {data['provider']}" + (f" ({data['csv_dir']})" if data.get('csv_dir') else ""))
    print(f"- Broker: {br['name']}  live_trading_enabled={br['live_trading_enabled']}  "
          f"default_order_type={br['default_order_type']}")
    print(f"- Risk: {risk['risk_per_trade_pct']}%/trade, max position {risk['max_position_pct']}%, "
          f"max open risk {risk['max_open_risk_pct']}%, max positions {risk['max_open_positions']}, "
          f"daily loss stop {risk['max_daily_loss_pct']}%, drawdown stop {risk['max_drawdown_pct']}%, "
          f"min R:R {risk['min_reward_risk']}, pause after {risk['max_consecutive_losses']} losses")
    print(f"- Costs: commission {cfg['costs']['commission_pct']}% + {cfg['costs']['commission_fixed']} fixed, "
          f"slippage {cfg['costs']['slippage_pct']}%")
    print(f"- Kill switch: {'ON' if out['kill_switch'] else 'off'}")
    if out["secrets"]:
        print("- Secrets: " + ", ".join(f"{k}={v}" for k, v in out["secrets"].items()))


def cmd_set(a):
    cfg = config.load()
    if a.key.startswith("broker.live_trading_enabled"):
        cli.fail("use `setup.py live on --i-understand-the-risks` to enable live trading")
    config.set_key(cfg, a.key, config.coerce(a.value))
    config.save(cfg)
    print(f"{a.key} = {config.get_key(cfg, a.key)!r}")


def cmd_get(a):
    print(cli.dump(config.get_key(config.load(), a.key)))


def cmd_doctor(a):
    checks = []

    def add(name, ok, detail):
        checks.append({"check": name, "ok": ok, "detail": detail})

    add("python", sys.version_info >= (3, 9), platform.python_version())
    try:
        config.path("doctor.tmp").write_text("ok")
        config.path("doctor.tmp").unlink()
        add("home_writable", True, str(config.home()))
    except OSError as e:
        add("home_writable", False, str(e))
    try:
        cfg = config.load()
        add("config", True, "config.json valid" if config.exists() else "using defaults (run init)")
    except RuntimeError as e:
        add("config", False, str(e))
        cfg = config.DEFAULTS
    sym = a.symbol or cfg["account"].get("benchmark") or "SPY"
    try:
        from tradekit import data
        b = data.get_bars(sym, "1d", "1mo", use_cache=False)
        add("data_provider", len(b) > 0, f"{cfg['data']['provider']}: {sym} {len(b)} bars, last {b.date[-1]} close {b.close[-1]:.2f}")
    except Exception as e:  # noqa: BLE001
        add("data_provider", False, f"{cfg['data']['provider']}: {e}")
    try:
        from tradekit.brokers import get_broker
        acct = get_broker().account()
        add("broker", True, f"{acct['broker']} equity {acct['equity']:,.2f} (live={acct['live']})")
    except Exception as e:  # noqa: BLE001
        add("broker", False, str(e))
    try:
        from tradekit.journal import Journal
        j = Journal()
        add("journal", True, f"{len(j.list())} trades in {j.path}")
    except Exception as e:  # noqa: BLE001
        add("journal", False, str(e))
    add("kill_switch", not config.kill_switch_on(), "ON - orders blocked" if config.kill_switch_on() else "off")
    if a.json:
        print(cli.dump(checks))
    else:
        for c in checks:
            print(f"{'OK ' if c['ok'] else 'XX '} {c['check']:<14} {c['detail']}")
    if not all(c["ok"] for c in checks if c["check"] != "kill_switch"):
        sys.exit(1)


def cmd_kite_login(a):
    s = config.load_secrets()
    if a.api_key:
        s["kite_api_key"] = a.api_key
    if a.api_secret:
        s["kite_api_secret"] = a.api_secret
    config.save_secrets(s)
    from tradekit.brokers.kite import KiteClient
    c = KiteClient(api_key=s.get("kite_api_key") or os.environ.get("KITE_API_KEY"))
    print("1. Open this URL and log in to Kite:")
    print(f"   {c.login_url()}")
    print("2. After login you are redirected to your app's redirect URL with ?request_token=XXXX")
    print("3. Run: python3 scripts/setup.py kite-session --request-token XXXX")


def cmd_kite_session(a):
    s = config.load_secrets()
    secret = a.api_secret or config.secret("kite_api_secret", "KITE_API_SECRET")
    if not secret:
        cli.fail("api secret missing: pass --api-secret or run kite-login --api-secret")
    from tradekit.brokers.kite import KiteClient
    c = KiteClient()
    data = c.generate_session(a.request_token, secret)
    s["kite_access_token"] = data["access_token"]
    config.save_secrets(s)
    print(f"Kite session saved for user {data.get('user_id', '?')} (token {config.mask(data['access_token'])}). "
          "Tokens expire daily - repeat kite-login each trading day.")


def cmd_paper_reset(a):
    from tradekit.brokers.paper import PaperBroker
    acct = PaperBroker().reset(a.cash)
    print(f"Paper account reset: cash {acct['cash']:,.2f} {acct['currency']}")


def cmd_live(a):
    cfg = config.load()
    if a.state == "on":
        if not a.i_understand_the_risks:
            cli.fail("live trading sends REAL orders. Re-run with --i-understand-the-risks")
        if cfg["broker"]["name"] == "paper":
            cli.fail("broker is 'paper'. Set a live broker first: setup.py set broker.name kite")
        cfg["broker"]["live_trading_enabled"] = True
        print("Live trading ENABLED. Every order still needs a passing pre-trade-gate and an explicit confirm code.")
    else:
        cfg["broker"]["live_trading_enabled"] = False
        print("Live trading disabled.")
    config.save(cfg)


def main():
    p = cli.parser(__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("init", help="create or update config")
    i.add_argument("--equity", type=float)
    i.add_argument("--currency")
    i.add_argument("--benchmark", help="index/ETF used for regime and comparisons, e.g. SPY, ^GSPC, ^NSEI, BTC-USD")
    i.add_argument("--timezone")
    i.add_argument("--provider", choices=["yahoo", "csv", "kite"])
    i.add_argument("--csv-dir")
    i.add_argument("--broker", choices=["paper", "kite"])
    i.add_argument("--exchange", help="default exchange for broker symbols")
    i.add_argument("--product", help="default broker product (kite: CNC/MIS/NRML)")
    i.add_argument("--risk-pct", type=float, help="risk per trade in percent of equity")
    i.add_argument("--force", action="store_true")
    i.add_argument("--json", action="store_true")
    s = sub.add_parser("show")
    s.add_argument("--json", action="store_true")
    st = sub.add_parser("set")
    st.add_argument("key")
    st.add_argument("value")
    g = sub.add_parser("get")
    g.add_argument("key")
    d = sub.add_parser("doctor")
    d.add_argument("--symbol")
    d.add_argument("--json", action="store_true")
    kl = sub.add_parser("kite-login")
    kl.add_argument("--api-key")
    kl.add_argument("--api-secret")
    ks = sub.add_parser("kite-session")
    ks.add_argument("--request-token", required=True)
    ks.add_argument("--api-secret")
    pr = sub.add_parser("paper-reset")
    pr.add_argument("--cash", type=float)
    lv = sub.add_parser("live")
    lv.add_argument("state", choices=["on", "off"])
    lv.add_argument("--i-understand-the-risks", action="store_true")
    a = p.parse_args()
    {"init": cmd_init, "show": cmd_show, "set": cmd_set, "get": cmd_get, "doctor": cmd_doctor,
     "kite-login": cmd_kite_login, "kite-session": cmd_kite_session, "paper-reset": cmd_paper_reset,
     "live": cmd_live}[a.cmd](a)


if __name__ == "__main__":
    cli.run(main)

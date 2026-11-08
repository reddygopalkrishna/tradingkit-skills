"""End-to-end CLI tests: every skill script runs standalone (vendored core) on offline CSV data."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SK = ROOT / "skills"
sys.path.insert(0, str(ROOT / "tests"))
from synth import gbm  # noqa: E402


class SkillCLI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.home = tempfile.mkdtemp(prefix="tskills-cli-")
        cls.data = tempfile.mkdtemp(prefix="tskills-data-")
        for i, s in enumerate(["AAA", "BBB", "CCC", "DDD", "IDX"]):
            gbm(s, n=900, seed=i + 11, drift=0.0004 + 0.0002 * i).to_csv(Path(cls.data) / f"{s}.csv")
        cls.env = dict(os.environ, TRADINGKIT_SKILLS_HOME=cls.home, PYTHONDONTWRITEBYTECODE="1")
        cls.run_ok("trading-setup/scripts/setup.py", "init", "--equity", "100000", "--currency", "USD",
                   "--benchmark", "IDX", "--provider", "csv", "--csv-dir", cls.data)

    @classmethod
    def run_ok(cls, script, *args, code=0):
        r = subprocess.run([sys.executable, "-I", str(SK / script), *args], capture_output=True, text=True,
                           env=cls.env, timeout=180)
        if r.returncode != code:
            raise AssertionError(f"{script} {' '.join(args)} -> {r.returncode}\nSTDOUT:{r.stdout[-1500:]}\nSTDERR:{r.stderr[-1500:]}")
        return r.stdout

    def j(self, script, *args, code=0):
        return json.loads(self.run_ok(script, *args, "--json", code=code))

    def test_01_setup_and_data(self):
        self.run_ok("trading-setup/scripts/setup.py", "doctor", "--symbol", "AAA")
        self.run_ok("trading-setup/scripts/setup.py", "set", "risk.min_reward_risk", "1.5")
        out = self.j("market-data/scripts/data.py", "bars", "AAA", "--period", "1y")
        self.assertGreater(out["bars"], 200)
        q = self.j("market-data/scripts/data.py", "quote", "AAA", "BBB")
        self.assertEqual(len(q["quotes"]), 2)
        self.run_ok("trading-setup/scripts/setup.py", "set", "broker.live_trading_enabled", "true", code=2)

    def test_02_analysis(self):
        r = self.j("technical-analysis/scripts/analyze.py", "AAA", "--eval", "close > sma(200)")
        self.assertIn("daily", r)
        self.assertIn("higher_tf", r)
        p = self.j("chart-patterns/scripts/patterns.py", "AAA", "BBB", "CCC")
        self.assertEqual(p["scanned"], 3)
        g = self.j("market-regime/scripts/regime.py", "--universe", "AAA,BBB,CCC,DDD")
        self.assertEqual(g["regimes"][0]["index"], "IDX")

    def test_03_screener(self):
        s = self.j("stock-screener/scripts/screen.py", "--universe", "AAA,BBB,CCC,DDD", "--rule", "close > 0", "--rank", "roc(63)")
        self.assertEqual(len(s["matches"]), 4)
        ranks = [m["rank"] for m in s["matches"]]
        self.assertEqual(ranks, sorted(ranks, reverse=True))
        for preset in ("trend-template", "squeeze", "macd-bull-cross", "gap-up-volume"):
            self.j("stock-screener/scripts/screen.py", "--universe", "AAA,BBB", "--preset", preset)
        self.run_ok("stock-screener/scripts/screen.py", "--check", "import os", code=2)

    def test_04_sizer(self):
        r = self.j("position-sizer/scripts/size.py", "risk", "--entry", "100", "--stop", "95")
        self.assertEqual(r["qty"], 200)
        self.j("position-sizer/scripts/size.py", "kelly", "--win-rate", "0.5", "--payoff", "2")

    def test_05_plan_gate_route_journal(self):
        plan = self.j("trade-planner/scripts/plan.py", "AAA", "--stop", "atr:2", "--target", "r:3", "--save",
                      "--setup", "pullback", "--thesis", "test")
        self.assertGreater(plan["size"]["qty"], 0)
        g = self.j("pre-trade-gate/scripts/gate.py", "check", "--plan", str(plan["journal_id"]))
        self.assertIn(g["verdict"], ("PASS", "PASS_WITH_WARNINGS"))
        qty = str(g["qty"])
        router = "order-router/scripts/router.py"
        # no approval for a different qty
        self.run_ok(router, "preview", "--symbol", "AAA", "--side", "buy", "--qty", "1", "--type", "market",
                    "--stop-loss", str(plan["stop"]), code=2)
        pv = self.j(router, "preview", "--symbol", "AAA", "--side", "buy", "--qty", qty, "--type", "market",
                    "--stop-loss", str(plan["stop"]), "--take-profit", str(plan["target"]))
        self.run_ok(router, "submit", "--confirm", "ZZZZZZ", code=2)
        res = self.j(router, "submit", "--confirm", pv["code"])
        self.assertEqual(res["status"], "filled")
        self.run_ok(router, "submit", "--confirm", pv["code"], code=2)  # single use
        pos = self.j(router, "positions")
        self.assertEqual(pos[0]["symbol"], "AAA")
        trades = self.j("trade-journal/scripts/journal.py", "list", "--status", "open")
        self.assertEqual(trades[0]["setup"], "pullback")
        # kill switch blocks
        self.run_ok(router, "kill", "on", "--reason", "test")
        self.run_ok(router, "preview", "--symbol", "AAA", "--side", "sell", "--qty", qty, "--type", "market", "--close", code=2)
        self.run_ok(router, "kill", "off")
        pv2 = self.j(router, "preview", "--symbol", "AAA", "--side", "sell", "--qty", qty, "--type", "market", "--close")
        self.j(router, "submit", "--confirm", pv2["code"])
        self.assertEqual(self.j(router, "positions"), [])
        self.assertEqual(self.j(router, "orders", "--open"), [])
        closed = self.j("trade-journal/scripts/journal.py", "list", "--status", "closed")
        self.assertEqual(len(closed), 1)
        self.j("pre-trade-gate/scripts/gate.py", "status")

    def test_06_backtest_mc_review(self):
        out = Path(self.home) / "bt.html"
        tcsv = Path(self.home) / "trades.csv"
        r = self.j("backtester/scripts/backtest.py", "--spec", str(ROOT / "examples/strategies/rsi2-pullback.json"),
                   "--universe", "AAA,BBB,CCC", "--oos-start", "2024-01-01", "--report", str(out),
                   "--trades-csv", str(tcsv), "--set", "oversold=15")
        self.assertGreater(r["metrics"]["trades"], 10)
        self.assertTrue(out.exists() and "<svg" in out.read_text())
        for spec in (ROOT / "examples/strategies").glob("*.json"):
            self.j("backtester/scripts/backtest.py", "--spec", str(spec), "--universe", "AAA,BBB")
        mc = self.j("monte-carlo-sim/scripts/mc.py", "trades", "--csv", str(tcsv), "--sims", "2000")
        self.assertIn("risk_of_ruin_pct", mc)
        rv = self.j("performance-review/scripts/review.py", "--csv", str(tcsv), "--report", str(Path(self.home) / "rv.html"))
        self.assertGreater(rv["trades"], 10)

    def test_07_mc_setup_and_brief(self):
        b = self.j("market-data/scripts/data.py", "bars", "AAA", "--period", "1mo")
        last = b["rows"][-1]["close"]
        st = self.j("monte-carlo-sim/scripts/mc.py", "setup", "AAA", "--stop", str(last * 0.95), "--target",
                    str(last * 1.1), "--sims", "1000")
        self.assertIn("verdict", st)
        br = self.j("trading-navigator/scripts/brief.py", "--watchlist", "AAA,BBB,CCC", "--report",
                    str(Path(self.home) / "brief.html"))
        self.assertTrue(br["regimes"])


if __name__ == "__main__":
    unittest.main()

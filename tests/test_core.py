"""Unit tests for the tradekit core. Offline, deterministic, standard library only.

Run:  python3 -m unittest discover -s tests -v
"""

import math
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "core"))
sys.path.insert(0, str(ROOT / "tests"))

_home = tempfile.mkdtemp(prefix="tskills-test-")
os.environ["TRADING_SKILLS_HOME"] = _home

from synth import from_closes, gbm  # noqa: E402
from tradekit import analysis, backtest, config, expr, gate, indicators as ind, metrics, montecarlo, patterns, risk  # noqa: E402
from tradekit.brokers.base import BrokerError, normalize_order  # noqa: E402
from tradekit.brokers.paper import PaperBroker  # noqa: E402
from tradekit.frame import Bars, normalize_date  # noqa: E402
from tradekit.journal import Journal  # noqa: E402


def approx(a, b, tol=1e-6):
    return abs(a - b) <= tol * max(1.0, abs(b))


class TestFrame(unittest.TestCase):
    def test_csv_roundtrip_and_aliases(self):
        text = "Date,Open,High,Low,Close,Adj Close,Volume\n2024-01-03,10,11,9,10.5,10.4,100\n2024-01-02,9,10,8,9.5,9.4,90\n"
        b = Bars.from_csv(text, symbol="X")
        self.assertEqual(b.date, ["2024-01-02", "2024-01-03"])  # sorted
        self.assertEqual(b.close, [9.5, 10.5])
        b2 = Bars.from_csv(b.to_csv(), symbol="X")
        self.assertEqual(b2.close, b.close)

    def test_bad_rows_dropped_and_hl_fixed(self):
        text = "date,open,high,low,close,volume\n2024-01-02,10,9,11,10,1\n2024-01-03,,,,,\n2024-01-04,10,10,10,0,1\n"
        b = Bars.from_csv(text, symbol="X")
        self.assertEqual(len(b), 1)
        self.assertGreaterEqual(b.high[0], b.low[0])

    def test_normalize_date(self):
        self.assertEqual(normalize_date("2024-03-05 09:15:00"), "2024-03-05T09:15")
        self.assertEqual(normalize_date("05-03-2024"), "2024-03-05")
        self.assertEqual(normalize_date("2024/03/05"), "2024-03-05")

    def test_resample_weekly(self):
        b = gbm(n=50)
        w = b.resample("1wk")
        self.assertLess(len(w), len(b))
        self.assertAlmostEqual(w.close[-1], b.close[-1])
        self.assertEqual(max(b.high), max(w.high))


class TestIndicators(unittest.TestCase):
    def test_sma_ema(self):
        x = [1, 2, 3, 4, 5, 6]
        self.assertEqual(ind.sma(x, 3), [None, None, 2.0, 3.0, 4.0, 5.0])
        e = ind.ema(x, 3)
        self.assertEqual(e[2], 2.0)
        self.assertTrue(approx(e[3], 3.0))

    def test_rsi_extremes(self):
        up = list(range(1, 40))
        self.assertEqual(ind.rsi(up, 14)[-1], 100.0)
        down = list(range(40, 1, -1))
        self.assertTrue(ind.rsi(down, 14)[-1] < 1)

    def test_rsi_reference_value(self):
        # Wilder's classic example (New Concepts in Technical Trading Systems): RSI ~ 70.53 at bar 15
        closes = [44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84, 46.08, 45.89, 46.03, 45.61,
                  46.28, 46.28, 46.00, 46.03, 46.41, 46.22, 45.64]
        r = ind.rsi(closes, 14)
        self.assertAlmostEqual(r[14], 70.53, delta=0.3)

    def test_atr_constant_range(self):
        h = [11.0] * 30
        l = [9.0] * 30
        c = [10.0] * 30
        self.assertTrue(approx(ind.atr(h, l, c, 14)[-1], 2.0))

    def test_bbands_macd_constant(self):
        c = [5.0] * 60
        mid, up, lo = ind.bbands(c, 20, 2)
        self.assertEqual(mid[-1], up[-1])
        line, sig, hist = ind.macd(c)
        self.assertTrue(approx(line[-1], 0.0) and approx(hist[-1], 0.0))

    def test_cross_and_shift(self):
        a = [1, 2, 3, 4]
        b = [2, 2, 2, 2]
        self.assertEqual(ind.crossed_above(a, b), [False, False, True, False])
        self.assertEqual(ind.shift(a, 1), [None, 1, 2, 3])
        self.assertEqual(ind.shift(a, -1), [2, 3, 4, None])

    def test_supertrend_direction(self):
        b = from_closes([100 + i for i in range(60)])
        _, d = ind.supertrend(b.high, b.low, b.close, 10, 3)
        self.assertEqual(d[-1], 1)
        b2 = from_closes([200 - i for i in range(60)])
        _, d2 = ind.supertrend(b2.high, b2.low, b2.close, 10, 3)
        self.assertEqual(d2[-1], -1)

    def test_adx_trending(self):
        b = from_closes([100 * 1.01 ** i for i in range(80)])
        a, p, m = ind.adx(b.high, b.low, b.close, 14)
        self.assertGreater(a[-1], 25)
        self.assertGreater(p[-1], m[-1])


class TestExpr(unittest.TestCase):
    def setUp(self):
        self.b = gbm(n=300)

    def test_basic_rule(self):
        s = expr.evaluate("close > sma(close, 20)", self.b)
        self.assertEqual(len(s), len(self.b))
        self.assertFalse(s[5])  # warm-up -> False

    def test_forms_equivalent(self):
        a = expr.evaluate("sma(20)", self.b)
        b = expr.evaluate("sma(close, 20)", self.b)
        self.assertEqual(a, b)

    def test_rejects_unsafe(self):
        for bad in ("__import__('os')", "close.__class__", "open('x')()", "lambda: 1", "[1,2]", "'abc'"):
            with self.assertRaises(expr.ExprError):
                expr.compile_expr(bad)

    def test_unknown_function_message(self):
        with self.assertRaises(expr.ExprError) as cm:
            expr.compile_expr("foo(3)")
        self.assertIn("unknown function", str(cm.exception))

    def test_boolean_ops_and_aliases(self):
        s1 = expr.evaluate("rsi(14) > 50 and close > sma(50)", self.b)
        s2 = expr.evaluate("rsi(14) > 50 AND close > sma(50)", self.b)
        self.assertEqual(s1, s2)
        neg = expr.evaluate("not (rsi(14) > 50)", self.b)
        pos = expr.evaluate("rsi(14) > 50", self.b)
        self.assertTrue(all((not x) == y for x, y in zip(pos, neg) if x is not None))

    def test_every_function_runs(self):
        calls = {
            "shift": "shift(close, 2)", "ref": "ref(close, 2)", "cross_above": "cross_above(ema(5), ema(20))",
            "cross_below": "cross_below(ema(5), ema(20))", "max": "max(open, close)", "min": "min(open, close)",
            "percentile": "percentile(close, 50)", "highest": "highest(high, 10)", "lowest": "lowest(10)",
            "abs": "abs(change(close))", "sqrt": "sqrt(close)", "log": "log(close)",
        }
        for name in expr.FUNCTIONS:
            rule = calls.get(name, f"{name}()")
            s = expr.evaluate(rule, self.b)
            self.assertEqual(len(s), len(self.b), name)

    def test_chained_compare(self):
        s = expr.evaluate("30 < rsi(14) < 70", self.b)
        self.assertEqual(len(s), len(self.b))


class TestRisk(unittest.TestCase):
    def test_position_size(self):
        r = risk.position_size(100000, 50, 48, 1.0)
        self.assertEqual(r["qty"], 500)
        self.assertEqual(r["binding_constraint"], "risk")
        r2 = risk.position_size(100000, 50, 49.9, 1.0, max_position_pct=20)
        self.assertEqual(r2["binding_constraint"], "max_position")
        self.assertEqual(r2["qty"], 400)

    def test_lots_multiplier_fractional(self):
        r = risk.position_size(1_000_000, 100, 98, 1.0, lot_size=50, multiplier=1)
        self.assertEqual(r["qty"] % 50, 0)
        c = risk.position_size(10000, 60000, 57000, 1.0, fractional=True, lot_size=0.0001)
        self.assertTrue(0 < c["qty"] < 1)
        self.assertLessEqual(c["actual_risk"], 100.0 + 1e-6)
        f = risk.position_size(100000, 5000, 4990, 1.0, multiplier=50)
        self.assertEqual(f["qty"], 2)

    def test_short_side(self):
        r = risk.position_size(100000, 50, 52, 1.0)
        self.assertEqual(r["side"], "short")
        self.assertEqual(r["qty"], 500)

    def test_kelly_ruin(self):
        self.assertAlmostEqual(risk.kelly(0.5, 2), 0.25)
        self.assertEqual(risk.kelly(0.3, 1), 0.0)
        self.assertEqual(risk.risk_of_ruin(0.3, 1, 1), 1.0)
        self.assertLess(risk.risk_of_ruin(0.5, 2, 1, 50), 0.01)


class TestMetrics(unittest.TestCase):
    def test_drawdown(self):
        eq = [100, 120, 90, 130, 117]
        dd = metrics.max_drawdown(eq)
        self.assertAlmostEqual(dd["max_drawdown_pct"], -25.0)

    def test_trade_stats(self):
        t = [{"pnl": 200, "r_multiple": 2}, {"pnl": -100, "r_multiple": -1}, {"pnl": -100, "r_multiple": -1},
             {"pnl": 300, "r_multiple": 3}]
        s = metrics.trade_stats(t)
        self.assertEqual(s["win_rate_pct"], 50.0)
        self.assertEqual(s["profit_factor"], 2.5)
        self.assertEqual(s["avg_r"], 0.75)
        self.assertEqual(s["max_consecutive_losses"], 2)


class TestBacktest(unittest.TestCase):
    def test_no_lookahead_entry_next_open(self):
        closes = [100 + i for i in range(40)]
        b = from_closes(closes, "T")
        spec = {"entry": "bar_index == 10", "stop": {"type": "pct", "value": 50}, "max_bars": 5,
                "sizing": {"type": "percent", "pct": 50}, "costs": {"commission_pct": 0, "slippage_pct": 0}}
        r = backtest.run(spec, {"T": b})
        t = r["trades"][0]
        self.assertEqual(t["entry_date"], b.date[11])
        self.assertAlmostEqual(t["entry_price"], b.open[11], places=6)
        self.assertEqual(t["exit_reason"], "max_bars")
        self.assertEqual(t["bars_held"], 5)

    def test_stop_and_gap(self):
        closes = [100] * 20 + [100, 99, 80, 79]
        b = from_closes(closes, "T")
        b.open[22] = 81.0  # gap down through the 5% stop
        b.high[22] = max(b.high[22], 81.0)
        spec = {"entry": "bar_index == 19", "stop": {"type": "pct", "value": 5}, "sizing": {"type": "risk", "risk_pct": 1},
                "costs": {"commission_pct": 0, "slippage_pct": 0}}
        r = backtest.run(spec, {"T": b})
        t = r["trades"][0]
        self.assertIn(t["exit_reason"], ("stop", "stop_gap"))
        self.assertLess(t["r_multiple"], -1.0)  # gapped through the stop: worse than -1R

    def test_target_r(self):
        closes = [100] * 20 + [100, 101, 103, 106, 110, 115]
        b = from_closes(closes, "T", spread=0.002)
        spec = {"entry": "bar_index == 19", "stop": {"type": "pct", "value": 4}, "target": {"type": "r", "value": 2},
                "costs": {"commission_pct": 0, "slippage_pct": 0}}
        r = backtest.run(spec, {"T": b})
        t = r["trades"][0]
        self.assertTrue(t["exit_reason"].startswith("target"))
        self.assertAlmostEqual(t["r_multiple"], 2.0, delta=0.15)

    def test_costs_reduce_returns(self):
        data = {"A": gbm("A", seed=3), "B": gbm("B", seed=4)}
        base = {"entry": "close > sma(50) and rsi(2) < 20", "exit": "close > sma(5)", "stop": {"type": "atr", "mult": 2}}
        free = backtest.run({**base, "costs": {"commission_pct": 0, "slippage_pct": 0}}, data)
        paid = backtest.run({**base, "costs": {"commission_pct": 0.2, "slippage_pct": 0.2}}, data)
        self.assertGreater(free["metrics"]["total_return_pct"], paid["metrics"]["total_return_pct"])

    def test_max_positions_and_short(self):
        data = {s: gbm(s, seed=i, drift=-0.0005) for i, s in enumerate("ABCDEF")}
        spec = {"entry": "close < sma(20)", "side": "short", "stop": {"type": "atr", "mult": 2}, "max_positions": 2,
                "max_bars": 10}
        r = backtest.run(spec, data)
        self.assertGreater(r["metrics"]["trades"], 0)
        # never more than 2 concurrent positions
        events = []
        for t in r["trades"]:
            events.append((t["entry_date"], 1))
            events.append((t["exit_date"], -1))
        # exits processed before entries on the same date
        events.sort(key=lambda e: (e[0], e[1]))
        cur = peak = 0
        for _, d in events:
            cur += d
            peak = max(peak, cur)
        self.assertLessEqual(peak, 2)

    def test_oos_and_warnings(self):
        r = backtest.run({"entry": "rsi(2) < 10", "exit": "rsi(2) > 70", "stop": "lowest(low, 10)",
                          "oos_start": "2023-06-01"}, {"A": gbm("A", n=700)})
        self.assertIn("out_of_sample", r)
        self.assertTrue(any("survivorship" in w for w in r["warnings"]))

    def test_spec_validation(self):
        with self.assertRaises(backtest.BacktestError):
            backtest.run({"exit": "close > 1"}, {"A": gbm("A")})
        with self.assertRaises(backtest.BacktestError):
            backtest.run({"entry": "close > 1", "stop": {"type": "none"}}, {"A": gbm("A")})


class TestMonteCarlo(unittest.TestCase):
    def test_trades_deterministic(self):
        rs = [2, -1, -1, 1.5, -1, 3, -1, 0.5, -1, 2]
        a = montecarlo.simulate_trades(rs, 1.0, 50, 2000, seed=1)
        b = montecarlo.simulate_trades(rs, 1.0, 50, 2000, seed=1)
        self.assertEqual(a["final_return_pct"], b["final_return_pct"])
        self.assertGreater(a["final_return_pct"][50], 0)

    def test_setup_probabilities_sum(self):
        b = gbm(n=400)
        last = b.close[-1]
        r = montecarlo.simulate_setup(b, last, last * 0.95, last * 1.10, horizon=30, n_sims=3000)
        total = r["prob_target_first_pct"] + r["prob_stop_first_pct"] + r["prob_neither_pct"]
        self.assertAlmostEqual(total, 100.0, delta=0.05)
        with self.assertRaises(ValueError):
            montecarlo.simulate_setup(b, last, last * 1.05, last * 1.10)


class TestPatternsAnalysis(unittest.TestCase):
    def test_breakout_detected(self):
        closes = [100 + math.sin(i / 3) for i in range(80)] + [104]
        vols = [1_000_000.0] * 80 + [3_000_000.0]
        b = from_closes(closes, volumes=vols)
        hit = patterns.breakout(b)
        self.assertIsNotNone(hit)
        self.assertEqual(hit["pattern"], "breakout")

    def test_flag_detected(self):
        base = [100.0] * 70
        pole = [100 * 1.02 ** i for i in range(1, 13)]
        flag = [pole[-1] * (1 - 0.01 * i) for i in range(1, 6)]
        vols = [1e6] * 70 + [2e6] * 12 + [6e5] * 5
        b = from_closes(base + pole + flag, volumes=vols)
        hit = patterns.bull_flag(b)
        self.assertIsNotNone(hit)

    def test_scan_and_snapshot(self):
        b = gbm(n=700, drift=0.0008, seed=5)
        res = patterns.scan(b)
        self.assertIsInstance(res, list)
        s = analysis.snapshot(b)
        self.assertTrue(-100 <= s["score"] <= 100)
        self.assertIn("support", s["levels"])
        r = analysis.regime(b)
        self.assertIn(r["suggested_exposure_pct"], (0, 25, 50, 75, 100))

    def test_swings_alternate(self):
        b = gbm(n=300)
        piv = patterns.swings(b.high, b.low, 4)
        for a, c in zip(piv, piv[1:]):
            self.assertNotEqual(a["type"], c["type"])


class TestJournalGate(unittest.TestCase):
    def setUp(self):
        self.j = Journal(Path(tempfile.mkdtemp()) / "j.db")

    def test_lifecycle_and_r(self):
        t = self.j.plan("AAA", "long", 100, 95, 110, 10, setup="x")
        t = self.j.open(t["id"], entry_price=100, qty=10)
        t = self.j.close(t["id"], 110, fees=0)
        self.assertEqual(t["pnl"], 100)
        self.assertEqual(t["r_multiple"], 2.0)
        s = self.j.open(symbol="BBB", side="short", entry_price=50, qty=10, stop=52)
        s = self.j.close(s["id"], 54)
        self.assertEqual(s["r_multiple"], -2.0)
        self.assertEqual(self.j.consecutive_losses(), 1)

    def test_import_export(self):
        csv_text = "symbol,side,qty,entry_price,exit_price,entry_time,exit_time,stop\nAAA,long,10,100,105,2024-01-02,2024-01-05,98\n"
        self.assertEqual(self.j.import_csv(csv_text), 1)
        self.assertIn("AAA", self.j.export_csv())

    def test_gate_pass_fail(self):
        ok = gate.evaluate({"symbol": "AAA", "side": "long", "entry": 100, "stop": 98, "target": 106, "qty": 150,
                            "setup": "t"}, 100000, self.j)
        self.assertEqual(ok["verdict"], "PASS")
        bad = gate.evaluate({"symbol": "AAA", "side": "long", "entry": 100, "stop": 90, "target": 105, "qty": 1000},
                            100000, self.j)
        self.assertEqual(bad["verdict"], "FAIL")
        self.assertIn("risk_per_trade", bad["blocking"])
        self.assertIn("reward_risk", bad["blocking"])
        wrong = gate.evaluate({"symbol": "AAA", "side": "long", "entry": 100, "stop": 101, "qty": 1}, 100000, self.j)
        self.assertIn("stop_defined", wrong["blocking"])

    def test_gate_loss_streak_and_kill(self):
        for _ in range(3):
            t = self.j.open(symbol="L", side="long", entry_price=10, qty=10, stop=9)
            self.j.close(t["id"], 9)
        r = gate.evaluate({"symbol": "Z", "side": "long", "entry": 100, "stop": 98, "target": 110, "qty": 10, "setup": "x"},
                          100000, self.j)
        self.assertIn("loss_streak", r["blocking"])
        config.set_kill_switch(True)
        try:
            r2 = gate.evaluate({"symbol": "Z", "side": "long", "entry": 100, "stop": 98, "qty": 10}, 100000, self.j)
            self.assertIn("kill_switch_off", r2["blocking"])
        finally:
            config.set_kill_switch(False)

    def test_approval_roundtrip(self):
        r = gate.evaluate({"symbol": "AAA", "side": "long", "entry": 100, "stop": 98, "target": 106, "qty": 100,
                           "setup": "t"}, 100000, self.j)
        a = gate.write_approval(r)
        self.assertIsNotNone(gate.find_approval("AAA", "buy", 100, 98))
        self.assertIsNone(gate.find_approval("AAA", "buy", 101, 98))
        gate.consume_approval(a["approval_id"])
        self.assertIsNone(gate.find_approval("AAA", "buy", 100, 98))


class TestPaperBroker(unittest.TestCase):
    def setUp(self):
        os.environ["TRADING_SKILLS_HOME"] = tempfile.mkdtemp()
        self.price = {"AAA": 100.0}
        self.bar = {"AAA": {"open": 100, "high": 101, "low": 99, "close": 100, "date": "2024-01-02"}}
        self.b = PaperBroker(price_fn=lambda s: self.price[s], bar_fn=lambda s: self.bar[s], starting_cash=10000)

    def tearDown(self):
        os.environ["TRADING_SKILLS_HOME"] = _home

    def test_market_fill_and_costs(self):
        r = self.b.place({"symbol": "AAA", "side": "buy", "qty": 10, "type": "market"})
        self.assertEqual(r["status"], "filled")
        self.assertGreater(r["avg_fill_price"], 100)  # slippage
        acct = self.b.account()
        self.assertLess(acct["equity"], 10000)  # costs

    def test_oco_stop_cancels_target(self):
        self.b.place({"symbol": "AAA", "side": "buy", "qty": 10, "type": "market", "stop_loss": 95, "take_profit": 110})
        self.assertEqual(len(self.b.orders(open_only=True)), 2)
        self.bar["AAA"] = {"open": 98, "high": 98, "low": 94, "close": 95, "date": "2024-01-03"}
        fills = self.b.process()
        self.assertEqual(len(fills), 1)
        self.assertEqual(fills[0]["tag"], "stop_loss")
        self.assertEqual(len(self.b.orders(open_only=True)), 0)
        self.assertEqual(self.b.positions(), [])

    def test_resting_limit_then_fill(self):
        r = self.b.place({"symbol": "AAA", "side": "buy", "qty": 5, "type": "limit", "limit_price": 97})
        self.assertEqual(r["status"], "open")
        self.bar["AAA"] = {"open": 99, "high": 99.5, "low": 96.5, "close": 98, "date": "2024-01-03"}
        fills = self.b.process()
        self.assertEqual(fills[0]["avg_fill_price"], 97)

    def test_manual_close_cancels_children(self):
        self.b.place({"symbol": "AAA", "side": "buy", "qty": 10, "type": "market", "stop_loss": 95, "take_profit": 110})
        self.b.place({"symbol": "AAA", "side": "sell", "qty": 10, "type": "market"})
        self.assertEqual(self.b.orders(open_only=True), [])
        self.assertEqual(self.b.positions(), [])

    def test_validation(self):
        with self.assertRaises(BrokerError):
            normalize_order({"symbol": "A", "side": "buy", "qty": 1, "type": "limit"})
        with self.assertRaises(BrokerError):
            normalize_order({"symbol": "A", "side": "buy", "qty": 1, "type": "limit", "limit_price": 10, "stop_loss": 11})
        with self.assertRaises(BrokerError):
            normalize_order({"symbol": "A", "side": "buy", "qty": -1, "type": "market"})


class TestKiteMapping(unittest.TestCase):
    def test_params(self):
        from tradekit.brokers.kite import KiteBroker

        class FakeClient:
            pass

        kb = KiteBroker(client=FakeClient())
        p = kb.to_kite_params({"symbol": "NSE:INFY", "side": "buy", "qty": 5, "type": "stop_limit",
                               "limit_price": 1510, "stop_price": 1505, "product": "MIS"})
        self.assertEqual(p["exchange"], "NSE")
        self.assertEqual(p["tradingsymbol"], "INFY")
        self.assertEqual(p["order_type"], "SL")
        self.assertEqual(p["trigger_price"], 1505)
        self.assertEqual(p["product"], "MIS")
        with self.assertRaises(BrokerError):
            kb.to_kite_params({"symbol": "NSE:INFY", "side": "buy", "qty": 1.5, "type": "market"})


if __name__ == "__main__":
    unittest.main()

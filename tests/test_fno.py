"""Tests for core/tradekit/options.py and the trading-fno skill. Offline, hand-checked values.

Black-Scholes reference (S=K=100, T=1, r=5%, sigma=20%): call 10.4506, put 5.5735, call delta 0.6368,
gamma 0.018762, vega 0.37524 per vol point (the standard textbook figures).
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "core"))
os.environ.setdefault("TRADING_SKILLS_HOME", tempfile.mkdtemp(prefix="tskills-fno-"))

from tradekit import options as O  # noqa: E402

CSV = ROOT / "tests" / "fixtures" / "nse_option_chain_sample.csv"
SCRIPT = ROOT / "skills" / "trading-fno" / "scripts" / "fno.py"


class TestBlackScholes(unittest.TestCase):
    def test_known_prices(self):
        self.assertAlmostEqual(O.bs_price(100, 100, 1, 0.05, 0.2, "call"), 10.4506, 3)
        self.assertAlmostEqual(O.bs_price(100, 100, 1, 0.05, 0.2, "put"), 5.5735, 3)

    def test_put_call_parity(self):
        S, K, T, r, q, s = 120, 110, 0.5, 0.06, 0.02, 0.3
        c, p = O.bs_price(S, K, T, r, s, "call", q), O.bs_price(S, K, T, r, s, "put", q)
        import math
        self.assertAlmostEqual(c - p, S * math.exp(-q * T) - K * math.exp(-r * T), 9)

    def test_greeks(self):
        g = O.greeks(100, 100, 1, 0.05, 0.2, "call")
        self.assertAlmostEqual(g["delta"], 0.6368, 3)
        self.assertAlmostEqual(g["gamma"], 0.018762, 5)
        self.assertAlmostEqual(g["vega"], 0.37524, 4)
        self.assertAlmostEqual(g["theta"], -0.017573, 4)  # per calendar day
        p = O.greeks(100, 100, 1, 0.05, 0.2, "put")
        self.assertAlmostEqual(p["delta"], g["delta"] - 1, 9)
        self.assertAlmostEqual(p["gamma"], g["gamma"], 12)

    def test_greeks_match_finite_difference(self):
        S, K, T, r, s = 100, 105, 0.25, 0.04, 0.35
        h = 0.01
        up, dn = O.bs_price(S + h, K, T, r, s, "put"), O.bs_price(S - h, K, T, r, s, "put")
        self.assertAlmostEqual(O.greeks(S, K, T, r, s, "put")["delta"], (up - dn) / (2 * h), 5)
        vup, vdn = O.bs_price(S, K, T, r, s + 0.0001, "put"), O.bs_price(S, K, T, r, s - 0.0001, "put")
        self.assertAlmostEqual(O.greeks(S, K, T, r, s, "put")["vega"], (vup - vdn) / 0.0002 / 100, 4)

    def test_expiry_and_edges(self):
        self.assertEqual(O.bs_price(110, 100, 0, 0.05, 0.2, "call"), 10)
        self.assertEqual(O.greeks(90, 100, 0, 0.05, 0.2, "call")["delta"], 0.0)
        with self.assertRaises(ValueError):
            O.bs_price(100, 100, 1, 0.05, 0.2, "straddle")

    def test_implied_vol_round_trip(self):
        for kind in ("call", "put"):
            for K in (80, 100, 125):
                price = O.bs_price(100, K, 0.3, 0.06, 0.37, kind)
                self.assertAlmostEqual(O.implied_vol(price, 100, K, 0.3, 0.06, kind), 0.37, 5)

    def test_implied_vol_impossible_price(self):
        self.assertIsNone(O.implied_vol(0.5, 100, 80, 0.5, 0.05, "call"))   # below intrinsic
        self.assertIsNone(O.implied_vol(150, 100, 100, 0.5, 0.05, "call"))  # above spot
        self.assertIsNone(O.implied_vol(5, 100, 100, 0, 0.05, "call"))      # expired


class TestPayoff(unittest.TestCase):
    def test_long_call(self):
        a = O.analyze([O.leg("call", "long", 100, 5)])
        self.assertEqual(a["breakevens"], [105.0])
        self.assertEqual(a["max_loss"], -5.0)
        self.assertTrue(a["max_profit_unlimited"])

    def test_bull_call_spread(self):
        legs = O.build_strategy("bull-call-spread", [100, 110], [6, 2])
        a = O.analyze(legs, 50)
        self.assertEqual(a["breakevens"], [104.0])
        self.assertEqual(a["max_loss"], -4 * 50)
        self.assertEqual(a["max_profit"], 6 * 50)
        self.assertFalse(a["max_profit_unlimited"] or a["max_loss_unlimited"])

    def test_straddles(self):
        long = O.analyze(O.build_strategy("long-straddle", [100], [4, 3]))
        self.assertEqual(long["breakevens"], [93.0, 107.0])
        self.assertEqual(long["max_loss"], -7.0)
        short = O.analyze(O.build_strategy("short-straddle", [100], [4, 3]))
        self.assertTrue(short["max_loss_unlimited"])
        self.assertEqual(short["max_profit"], 7.0)

    def test_iron_condor(self):
        legs = O.build_strategy("iron-condor", [24000, 24200, 24800, 25000], [20, 60, 55, 18])
        a = O.analyze(legs, 75)
        self.assertEqual(a["max_profit"], 77 * 75)
        self.assertEqual(a["max_loss"], -(200 - 77) * 75)
        self.assertEqual(a["breakevens"], [24123.0, 24877.0])
        self.assertEqual(a["net_credit"], 77 * 75)

    def test_naked_short_put_loss_is_large_not_unlimited(self):
        a = O.analyze([O.leg("put", "short", 100, 3)])
        self.assertEqual(a["max_loss"], -97.0)
        self.assertFalse(a["max_loss_unlimited"])
        self.assertTrue(O.analyze([O.leg("call", "short", 100, 3)])["max_loss_unlimited"])

    def test_covered_call_with_stock_leg(self):
        a = O.analyze([O.leg("stock", "long", 100), O.leg("call", "short", 110, 3)])
        self.assertEqual(a["max_profit"], 13.0)
        self.assertEqual(a["breakevens"], [97.0])

    def test_parse_leg(self):
        l = O.parse_leg("-2P90@1.5")
        self.assertEqual((l["kind"], l["side"], l["strike"], l["premium"], l["qty"]), ("put", "short", 90.0, 1.5, 2.0))
        self.assertFalse(O.parse_leg("+1C100")["premium_known"])
        with self.assertRaises(ValueError):
            O.parse_leg("buy a call")

    def test_bad_strategy_input(self):
        with self.assertRaises(ValueError):
            O.build_strategy("iron-condor", [1, 2, 3])
        with self.assertRaises(ValueError):
            O.build_strategy("bull-call-spread", [110, 100])
        with self.assertRaises(ValueError):
            O.build_strategy("nonsense", [100])

    def test_ascii_chart_runs(self):
        rows = O.payoff_table(O.build_strategy("long-straddle", [100], [4, 3]), 80, 120, 41)
        self.assertIn("#", O.ascii_payoff(rows, spot=100))


class TestChain(unittest.TestCase):
    def setUp(self):
        self.chain = O.parse_nse_csv(CSV.read_text(), 24512, "2026-11-27", "NIFTY")

    def test_parse_by_header_names(self):
        rows = {r["strike"]: r for r in self.chain["rows"]}
        self.assertEqual(sorted(rows), [24000, 24200, 24500, 24800, 25000])
        r = rows[24500]
        self.assertEqual((r["c_oi"], r["p_oi"], r["c_chg_oi"], r["p_chg_oi"]), (15000, 50000, 1200, 2000))
        self.assertEqual((r["c_ltp"], r["p_ltp"]), (125.0, 60.5))
        self.assertAlmostEqual(r["c_iv"], 0.134)       # percent in the file -> fraction
        self.assertEqual(rows[24800]["c_chg_oi"], -2000)
        self.assertIsNone(rows[25000]["p_iv"])         # "-" means missing

    def test_column_order_does_not_matter(self):
        text = "STRIKE,OI,LTP\n100,5,1\n"   # call side missing (left of STRIKE is empty): only puts parsed
        ch = O.parse_nse_csv(text)
        self.assertEqual(ch["rows"][0]["p_oi"], 5.0)
        self.assertIsNone(ch["rows"][0]["c_oi"])

    def test_rejects_other_files(self):
        with self.assertRaises(ValueError):
            O.parse_nse_csv("a,b\n1,2\n")

    def test_summary(self):
        s = O.chain_summary(self.chain)
        self.assertEqual((s["call_oi"], s["put_oi"]), (110000, 88000))
        self.assertAlmostEqual(s["pcr_oi"], 0.8)
        self.assertEqual(s["max_pain"]["strike"], 24500)
        self.assertEqual(s["max_pain"]["payout_per_unit"], 3_700_000)  # hand-computed
        self.assertEqual(s["call_oi_walls"][0]["strike"], 24800)
        self.assertEqual(s["put_oi_walls"][0]["strike"], 24500)
        self.assertEqual(s["atm_strike"], 24500)
        self.assertAlmostEqual(s["atm_straddle"], 125.0 + 60.5)  # midpoints: call 125.0, put 60.5
        self.assertAlmostEqual(s["implied_move_pct"], 186 / 24512 * 100, 1)

    def test_cboe_parse(self):
        payload = {"timestamp": "2026-11-13 20:00:00", "data": {"symbol": "XYZ", "current_price": 100.0, "options": [
            {"option": "XYZ261120C00100000", "bid": 2.0, "ask": 2.2, "iv": 0.3, "open_interest": 10, "volume": 5, "last_trade_price": 2.1},
            {"option": "XYZ261120P00100000", "bid": 1.9, "ask": 2.1, "iv": 0.0, "open_interest": 30, "volume": 7, "last_trade_price": 0.0},
            {"option": "XYZ261127C00100000", "bid": 3.0, "ask": 3.2, "iv": 0.3, "open_interest": 1, "volume": 1, "last_trade_price": 3.1},
        ]}}
        ch = O.parse_cboe(payload, "2026-11-20")
        self.assertEqual(ch["expiry"], "2026-11-20")
        self.assertEqual(ch["expiries"], ["2026-11-20", "2026-11-27"])
        r = ch["rows"][0]
        self.assertEqual((r["strike"], r["c_oi"], r["p_oi"]), (100.0, 10, 30))
        self.assertIsNone(r["p_iv"])      # 0 means "no IV" at Cboe
        self.assertIsNone(r["p_ltp"])
        self.assertAlmostEqual(O.chain_summary(ch)["pcr_oi"], 3.0)
        with self.assertRaises(ValueError):
            O.parse_cboe(payload, "2030-01-01")

    def test_kite_chain_with_fake_client(self):
        class Fake:
            def instruments(self, ex):
                return [
                    {"name": "NIFTY", "instrument_type": "CE", "expiry": "2999-01-30", "strike": "100", "tradingsymbol": "NIFTYC100", "lot_size": "25"},
                    {"name": "NIFTY", "instrument_type": "PE", "expiry": "2999-01-30", "strike": "100", "tradingsymbol": "NIFTYP100", "lot_size": "25"},
                    {"name": "OTHER", "instrument_type": "CE", "expiry": "2999-01-30", "strike": "100", "tradingsymbol": "OTHERC100", "lot_size": "9"},
                ]

            def quote(self, keys):
                return {"NFO:NIFTYC100": {"last_price": 4.0, "oi": 70, "volume": 9, "depth": {"buy": [{"price": 3.9}], "sell": [{"price": 4.1}]}},
                        "NFO:NIFTYP100": {"last_price": 3.0, "oi": 35, "volume": 4, "depth": {"buy": [{"price": 2.9}], "sell": [{"price": 3.1}]}}}

            def ltp(self, keys):
                return {keys[0]: {"last_price": 101.0}}
        ch = O.kite_chain(Fake(), "nifty")
        self.assertEqual((ch["lot_size"], ch["spot"], ch["expiry"]), (25.0, 101.0, "2999-01-30"))
        self.assertAlmostEqual(O.chain_summary(ch)["pcr_oi"], 0.5)
        with self.assertRaises(ValueError):
            O.kite_chain(Fake(), "MISSING")


class TestCLI(unittest.TestCase):
    def run_fno(self, *args, code=0):
        r = subprocess.run([sys.executable, "-I", str(SCRIPT), *args], capture_output=True, text=True, timeout=60,
                           env={**os.environ, "KITE_API_KEY": "", "KITE_ACCESS_TOKEN": ""})
        self.assertEqual(r.returncode, code, r.stderr + r.stdout)
        return r

    def test_greeks_json(self):
        j = json.loads(self.run_fno("greeks", "--spot", "100", "--strike", "100", "--kind", "call", "--days", "365",
                                    "--iv", "20", "--json").stdout)
        self.assertAlmostEqual(j["price"], 10.4506, 3)

    def test_iv_and_error(self):
        self.assertIn("20.00%", self.run_fno("iv", "--price", "10.4506", "--spot", "100", "--strike", "100", "--kind", "call", "--days", "365").stdout)
        self.assertIn("no implied volatility", self.run_fno("iv", "--price", "0.5", "--spot", "100", "--strike", "80",
                                                           "--kind", "call", "--days", "180", code=2).stderr)

    def test_strategy_chart_and_unlimited(self):
        out = self.run_fno("strategy", "--name", "short-strangle", "--strikes", "90,110", "--premiums", "2,3",
                           "--spot", "100", "--chart").stdout
        self.assertIn("Max loss:   UNLIMITED", out)
        self.assertIn("Net credit received: 5.00", out)
        self.assertIn("#", out)

    def test_leg_without_premium_needs_inputs(self):
        self.assertIn("no premium", self.run_fno("strategy", "--legs", "+1C100", code=2).stderr)

    def test_chain_csv(self):
        out = self.run_fno("chain", "NIFTY", "--file", str(CSV), "--spot", "24512", "--expiry", "2026-11-27").stdout
        self.assertIn("PCR (OI) 0.80", out)
        self.assertIn("Max pain 24,500.00", out)
        self.assertIn("Lot size unknown", out)
        j = json.loads(self.run_fno("chain", "--file", str(CSV), "--spot", "24512", "--lot-size", "75", "--json").stdout)
        self.assertEqual(j["lot_size"], 75)

    def test_nse_symbol_is_refused_plainly(self):
        self.assertIn("nseindia.com blocks programs", self.run_fno("chain", "RELIANCE.NS", code=2).stderr)

    def test_kite_without_credentials_says_so(self):
        r = self.run_fno("chain", "NIFTY", "--kite", code=2)
        self.assertIn("Kite is not usable", r.stderr)
        self.assertIn("--file", r.stderr)


if __name__ == "__main__":
    unittest.main()

"""Tests for the v0.2 skills (news, earnings, insiders, alerts, entry) and their core modules.

Offline: fixtures in tests/fixtures/live are real responses saved on 2026-11-13/14 (Yahoo charts,
fundamentals and news, Google News, NSE bulk/block deal files, the House Clerk index and two
PTR PDFs). SEC and NSE-insider inputs are small hand-written documents in the published formats.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures" / "live"
SK = ROOT / "skills"
sys.path.insert(0, str(ROOT / "core"))
os.environ.setdefault("TRADING_SKILLS_HOME", tempfile.mkdtemp(prefix="tskills-new-"))

from tradekit import alerts, data, disclosures as D, feeds, fundamentals, sec, session  # noqa: E402


def chart(sym):
    return data.parse_yahoo_chart(json.loads((FIX / f"chart-{sym}-5m.json").read_text()), sym, "5m")


class TestSession(unittest.TestCase):
    def test_sessions_from_data(self):
        b = chart("RELIANCE.NS")
        self.assertEqual(b.meta["sessions"][-1], {"date": "2026-11-13", "open": "09:15", "close": "15:30"})
        self.assertEqual(chart("AAPL").meta["sessions"][-1]["open"], "09:30")
        self.assertEqual(session.market_status(b, "2026-11-13T09:00")["status"], "pre-open")
        self.assertEqual(session.market_status(b, "2026-11-13T12:00")["status"], "open")
        self.assertEqual(session.market_status(b, "2026-11-13T15:30")["status"], "closed")
        self.assertEqual(session.market_status(b, "2026-11-14T11:00")["status"], "closed")  # Saturday

    def test_orb_long_nse(self):
        b = chart("RELIANCE.NS")
        r = session.entry_check(b, "2026-11-13T09:58")
        self.assertEqual(r["status"], "waiting")
        self.assertEqual(r["forming"]["bar"], "09:55")       # a bar that has not closed never counts
        r = session.entry_check(b, "2026-11-13T10:05")
        self.assertEqual((r["status"], r["trigger_time"], r["price"]), ("triggered", "10:05", 1334.0))
        self.assertEqual(r["opening_range"]["high"], 1333.4)
        self.assertEqual(session.entry_check(b, "2026-11-13T09:25")["status"], "forming")
        self.assertEqual(session.entry_check(b, "2026-11-13T09:00")["status"], "not-open")

    def test_orb_short_and_expiry_us(self):
        b = chart("AAPL")
        r = session.entry_check(b, "2026-11-13T10:15", side="short")
        self.assertEqual((r["status"], r["trigger_time"], r["price"]), ("triggered", "10:15", 357.69))
        self.assertEqual(session.entry_check(b, "2026-11-13T10:13", side="short")["status"], "waiting")
        self.assertEqual(session.entry_check(b, "2026-11-13T15:40")["status"], "expired")

    def test_volume_filter_and_level(self):
        b = chart("RELIANCE.NS")
        r = session.entry_check(b, "2026-11-13T11:00", min_volume_x=1.0)
        self.assertEqual(r["trigger_bar"], "10:05")          # the 10:00 bar was too thin (0.49x)
        r = session.entry_check(b, "2026-11-13T11:00", setup="level", level=1340.0)
        self.assertEqual(r["status"], "triggered")
        self.assertGreater(r["price"], 1340.0)
        with self.assertRaises(ValueError):
            session.entry_check(b, "2026-11-13T11:00", setup="level")


class TestFeeds(unittest.TestCase):
    def test_google_and_yahoo(self):
        g = feeds.parse_rss((FIX / "google-news-RELIANCE.NS.xml").read_text(), "google")
        self.assertGreater(len(g), 20)
        self.assertTrue(all(i["published"] and i["link"] for i in g))
        self.assertFalse(any(i["title"].endswith(" - " + i["publisher"]) for i in g if i["publisher"]))
        y = feeds.parse_rss((FIX / "yahoo-news-AAPL.xml").read_text(), "yahoo")
        self.assertTrue(y and y[0]["title"])

    def test_tags_editions_and_markets(self):
        self.assertEqual(feeds.tag_text("Infosys Q2 results: net profit rises 8%"), ["earnings"])
        self.assertIn("analyst", feeds.tag_text("Brokerage upgrades TCS, raises target price"))
        self.assertEqual(feeds.tag_text("competitors pounce on GPU rental prices"), [])
        self.assertIn("gl=IN", feeds.google_url("RELIANCE.NS", "Reliance Industries Limited"))
        self.assertIn("gl=US", feeds.google_url("AAPL", "Apple Inc."))
        self.assertTrue(feeds.is_us("AAPL"))
        for s in ("RELIANCE.NS", "^NSEI", "BTC-USD", "EURUSD=X", "NSE:INFY"):
            self.assertFalse(feeds.is_us(s), s)

    def test_seen_state(self):
        items = [{"id": "x:1", "title": "a"}, {"id": "x:2", "title": "b"}]
        feeds.mark_seen(items[:1])
        seen = feeds.load_seen()
        self.assertIn(feeds.item_key(items[0]), seen)
        self.assertNotIn(feeds.item_key(items[1]), seen)


class TestFundamentals(unittest.TestCase):
    def test_yahoo_india_and_us(self):
        rows = fundamentals.parse_yahoo(json.loads((FIX / "fundamentals-RELIANCE.NS.json").read_text()))
        self.assertEqual(rows[-1]["currency"], "INR")
        res = fundamentals.analyse(rows, "RELIANCE.NS", "yahoo")
        q = {r["period_end"]: r for r in res["quarters"]}
        self.assertAlmostEqual(q["2026-06-30"]["revenue_yoy_pct"], 27.0, places=1)
        self.assertIn("ttm", res)
        aapl = fundamentals.analyse(fundamentals.parse_yahoo(
            json.loads((FIX / "fundamentals-AAPL.json").read_text())), "AAPL", "yahoo")
        self.assertAlmostEqual(aapl["latest"]["revenue_yoy_pct"], 11.7, places=1)
        self.assertTrue(all(r.get("revenue") is not None or r.get("net_income") is not None for r in aapl["quarters"]))

    def test_sec_quarters_with_derived_q4(self):
        def fact(start, end, val, form="10-Q", filed="2026-01-01"):
            return {"start": start, "end": end, "val": val, "form": form, "filed": filed}
        rev = [fact("2025-01-01", "2025-03-31", 100), fact("2025-04-01", "2025-06-30", 110),
               fact("2025-07-01", "2025-09-30", 120), fact("2025-01-01", "2025-12-31", 480, "10-K"),
               fact("2026-01-01", "2026-03-31", 130)]
        ni = [fact(r["start"], r["end"], r["val"] / 10, r["form"]) for r in rev]
        facts = {"facts": {"us-gaap": {"Revenues": {"units": {"USD": rev}}, "NetIncomeLoss": {"units": {"USD": ni}}}}}
        rows = sec.quarters_from_facts(facts)
        q4 = next(r for r in rows if r["period_end"] == "2025-12-31")
        self.assertTrue(q4["derived"])
        self.assertEqual(q4["revenue"], 150)
        res = fundamentals.analyse(rows, "TEST", "sec")
        self.assertAlmostEqual(res["latest"]["revenue_yoy_pct"], 30.0)
        self.assertEqual(res["ttm"]["revenue"], 510)

    def test_form4_and_filings(self):
        xml = """<?xml version="1.0"?><ownershipDocument><periodOfReport>2026-11-10</periodOfReport>
        <issuer><issuerName>Example Corp</issuerName><issuerTradingSymbol>EXM</issuerTradingSymbol></issuer>
        <reportingOwner><reportingOwnerId><rptOwnerName>Jane Doe</rptOwnerName></reportingOwnerId>
        <reportingOwnerRelationship><isDirector>1</isDirector><isOfficer>1</isOfficer><officerTitle>CEO</officerTitle>
        </reportingOwnerRelationship></reportingOwner><nonDerivativeTable><nonDerivativeTransaction>
        <securityTitle><value>Common Stock</value></securityTitle><transactionDate><value>2026-11-10</value></transactionDate>
        <transactionCoding><transactionCode>P</transactionCode></transactionCoding><transactionAmounts>
        <transactionShares><value>1000</value></transactionShares><transactionPricePerShare><value>25.5</value></transactionPricePerShare>
        <transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode></transactionAmounts>
        <postTransactionAmounts><sharesOwnedFollowingTransaction><value>5000</value></sharesOwnedFollowingTransaction></postTransactionAmounts>
        </nonDerivativeTransaction></nonDerivativeTable></ownershipDocument>"""
        doc = sec.parse_form4(xml)
        self.assertEqual(doc["owners"][0]["roles"], ["director", "CEO"])
        t = doc["transactions"][0]
        self.assertEqual((t["code"], t["meaning"], t["value"]), ("P", "open-market buy", 25500.0))
        subs = {"cik": 123, "filings": {"recent": {"accessionNumber": ["0001-26-000001"], "form": ["8-K"],
                "filingDate": ["2026-11-12"], "items": ["2.02,9.01"], "primaryDocument": ["x.htm"],
                "acceptanceDateTime": ["2026-11-12T16:05:00.000Z"], "reportDate": ["2026-11-12"]}}}
        f = sec.recent_filings(subs, ["8-K"])[0]
        self.assertEqual(f["important"], ["2.02 earnings results"])
        self.assertIn("/123/000126000001/x.htm", f["url"])
        self.assertEqual(sec.cik_for("BRK.B", {"0": {"cik_str": 1067983, "ticker": "BRK-B", "title": "Berkshire"}})["cik"], 1067983)
        self.assertIn("/xyz.xml", sec.form4_xml_url(1, {"accession": "1-2", "document": "xslF345X05/xyz.xml"}))


class TestDisclosures(unittest.TestCase):
    def test_house_index(self):
        rows = D.parse_house_index((FIX / "house-2026FD-excerpt.zip").read_bytes())
        pel = [r for r in rows if D.member_matches(r, "Nancy Pelosi")]
        self.assertEqual([r["doc_id"] for r in pel][-1], "20035780")
        self.assertEqual(pel[0]["district"], "CA11")
        self.assertTrue(D.ptr_url(pel[0]).endswith("/2026/20033725.pdf"))

    def test_ptr_pdf_plain_and_encrypted(self):
        r = D.parse_ptr(D.pdf_text((FIX / "ptr-20035780.pdf").read_bytes()))
        self.assertEqual((r["member"], r["filed"], len(r["rows"])), ("Hon. Nancy Pelosi", "2026-11-06", 1))
        row = r["rows"][0]
        self.assertEqual((row["owner"], row["ticker"], row["type"], row["amount"]),
                         ("spouse", "WBD", "sale", "$50,001 - $100,000"))
        r = D.parse_ptr(D.pdf_text((FIX / "ptr-20035143.pdf").read_bytes()))   # RC4-encrypted PDF
        self.assertEqual(len(r["rows"]), 7)
        opt = r["rows"][1]
        self.assertEqual(opt["option"], {"contracts": 100, "kind": "call", "strike": 100.0, "expires": "6/17/27"})
        self.assertEqual(opt["days_to_disclose"], 28)
        self.assertEqual(r["rows"][0]["description"], "Purchased 10,000 shares.")
        self.assertEqual({x["ticker"] for x in r["rows"]}, {"BE", "INTC", None})
        with self.assertRaises(ValueError):
            D.pdf_text(b"not a pdf")

    def test_nse_deals_and_pit(self):
        bulk = D.parse_nse_deals((FIX / "nse-bulk-2026-11-13.csv").read_text(), "bulk")
        self.assertGreater(len(bulk), 100)
        self.assertEqual(bulk[0]["date"], "2026-11-13")
        self.assertTrue(all(r["side"] in ("BUY", "SELL") for r in bulk))
        block = D.parse_nse_deals((FIX / "nse-block-2026-11-13.csv").read_text(), "block")
        self.assertTrue(any(r["symbol"] == "MEESHO" for r in block))
        csv_text = ("SYMBOL ,COMPANY ,NAME OF THE ACQUIRER/DISPOSER ,CATEGORY OF PERSON ,NO. OF SECURITIES "
                    "(ACQUIRED/DISPLOSED) ,VALUE OF SECURITY (ACQUIRED/DISPLOSED) ,ACQUISITION/DISPOSAL TRANSACTION TYPE ,"
                    "DATE OF ALLOTMENT/ACQUISITION FROM ,DATE OF ALLOTMENT/ACQUISITION TO ,DATE OF INITMATION TO COMPANY ,"
                    "MODE OF ACQUISITION\nINFY,Infosys,A Director,Director,500,\"7,50,000\",Buy,10-Nov-2026,10-Nov-2026,"
                    "11-Nov-2026,Market Purchase\n")
        rows = D.parse_nse_pit_csv(csv_text)
        self.assertEqual((rows[0]["side"], rows[0]["value"], rows[0]["date_to"]), ("buy", 750000.0, "2026-11-10"))
        with self.assertRaises(ValueError):
            D.parse_nse_pit_csv("a,b\n1,2\n")


class TestAlerts(unittest.TestCase):
    def test_evaluate(self):
        sess = {"date": "2026-11-13", "open": "09:30", "close": "16:00"}
        q = {"price": 356.27, "previous_close": 354.89, "session": sess, "status": "open"}
        now = "2026-11-13T15:57"
        rang = {}
        self.assertTrue(alerts.evaluate({"id": "a", "type": "above", "symbol": "X", "price": 356}, q, now, rang))
        self.assertIsNone(alerts.evaluate({"id": "b", "type": "below", "symbol": "X", "price": 356}, q, now, rang))
        self.assertIsNone(alerts.evaluate({"id": "c", "type": "stop", "symbol": "X", "price": 357, "side": "short"}, q, now, rang))
        self.assertTrue(alerts.evaluate({"id": "d", "type": "stop", "symbol": "X", "price": 356.5, "side": "long"}, q, now, rang))
        self.assertIsNone(alerts.evaluate({"id": "e", "type": "pct", "symbol": "X", "pct": 1}, q, now, rang))
        self.assertTrue(alerts.evaluate({"id": "f", "type": "close", "symbol": "X", "minutes": 5}, q, now, rang))
        self.assertTrue(alerts.evaluate({"id": "g", "type": "time", "at": "15:55"}, q, now, rang))
        self.assertIsNone(alerts.evaluate({"id": "g", "type": "time", "at": "15:55"}, {**q, "session": None}, now, rang))
        rang["a"] = now   # rang once: not again
        self.assertIsNone(alerts.evaluate({"id": "a", "type": "above", "symbol": "X", "price": 356}, q, now, rang))
        rule = {"id": "a", "type": "above", "symbol": "X", "price": 356, "rearm": True}
        self.assertFalse(alerts.rearm(rule, q, rang))
        self.assertTrue(alerts.rearm(rule, {**q, "price": 355}, rang))
        self.assertNotIn("a", rang)

    def test_from_trades(self):
        new = alerts.from_trades([{"id": 7, "symbol": "TCS.NS", "side": "long", "stop": 3900, "target": 4200}], [])
        self.assertEqual([(r["type"], r["price"]) for r in new], [("stop", 3900.0), ("target", 4200.0)])


class TestNewSkillCLIs(unittest.TestCase):
    """Run each new script standalone (vendored core, isolated interpreter) on the saved data."""

    @classmethod
    def setUpClass(cls):
        cls.env = dict(os.environ, TRADING_SKILLS_HOME=tempfile.mkdtemp(prefix="tskills-newcli-"),
                       PYTHONDONTWRITEBYTECODE="1")

    def run_ok(self, script, *args, code=0):
        r = subprocess.run([sys.executable, "-I", str(SK / script), *args], capture_output=True, text=True,
                           env=self.env, timeout=120)
        if r.returncode != code:
            raise AssertionError(f"{script} {' '.join(args)} -> {r.returncode}\n{r.stdout[-1500:]}\n{r.stderr[-1500:]}")
        return r.stdout

    def test_news(self):
        out = json.loads(self.run_ok("trading-news/scripts/news.py", "AAPL", "RELIANCE.NS", "--offline", str(FIX),
                                     "--now", "2026-11-14T01:00", "--json"))
        self.assertGreater(out["new_items"], 0)
        rel = out["tickers"][1]
        self.assertEqual(rel["name"], "Reliance Industries Limited")
        self.assertTrue(all(i["source"] == "google" for i in rel["items"]))
        self.run_ok("trading-news/scripts/news.py", "AAPL", "RELIANCE.NS", "--offline", str(FIX), "--now",
                    "2026-11-14T01:00", "--limit", "100", code=0)
        self.run_ok("trading-news/scripts/news.py", "AAPL", "RELIANCE.NS", "--offline", str(FIX), "--now",
                    "2026-11-14T01:00", code=1)      # everything already shown

    def test_earnings(self):
        out = json.loads(self.run_ok("trading-earnings/scripts/earnings.py", "RELIANCE.NS", "AAPL", "--offline",
                                     str(FIX), "--json"))
        self.assertEqual([c["symbol"] for c in out["companies"]], ["RELIANCE.NS", "AAPL"])
        self.assertIn("Rs", self.run_ok("trading-earnings/scripts/earnings.py", "RELIANCE.NS", "--offline", str(FIX)))

    def test_insiders(self):
        s = "trading-insiders/scripts/insiders.py"
        out = json.loads(self.run_ok(s, "congress", "--member", "pelosi", "--year", "2026", "--offline", str(FIX),
                                     "--read", "--limit", "1", "--json"))
        self.assertEqual(out["filings"][0]["report"]["rows"][0]["ticker"], "WBD")
        out = json.loads(self.run_ok(s, "deals", "--offline", str(FIX), "--min-value-cr", "100", "--json"))
        self.assertTrue(all(d["value"] >= 1e9 for d in out["deals"]))
        self.run_ok(s, "sebi", "/no/such/file.csv", code=2)

    def test_alerts_and_entry(self):
        a = "trading-alerts/scripts/alerts.py"
        self.run_ok(a, "add", "--symbol", "RELIANCE.NS", "--above", "1335")
        self.run_ok(a, "add", "--symbol", "AAPL", "--close", "5")
        self.run_ok(a, "add", "--symbol", "AAPL", code=2)
        out = json.loads(self.run_ok(a, "check", "--offline", str(FIX), "--now", "2026-11-13 15:57", "--json"))
        self.assertEqual(len(out["rang"]), 2)
        self.run_ok(a, "check", "--offline", str(FIX), "--now", "2026-11-13 15:58", code=1)
        e = "trading-entry/scripts/entry.py"
        r = json.loads(self.run_ok(e, "check", "RELIANCE.NS", "--offline", str(FIX), "--now", "2026-11-13 10:05", "--json"))
        self.assertEqual(r["stop_ideas"], {"range_mid": 1328.85, "range_far_side": 1324.3})
        self.assertIn("plan.py RELIANCE.NS", r["next"])
        out = self.run_ok(e, "watch", "AAPL", "--side", "short", "--offline", str(FIX), "--now", "2026-11-13 09:40")
        self.assertIn("TRIGGERED at 10:15", out)
        self.run_ok(e, "watch", "AAPL", "--offline", str(FIX), "--now", "2026-11-13 15:00", code=1)


if __name__ == "__main__":
    unittest.main()

"""Offline tests for the Fyers, Upstox, Dhan and Groww adapters.

HTTP is mocked; response bodies follow the examples in each broker's official API docs.
No network, no live orders.
"""

import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "core"))

os.environ.setdefault("TRADING_SKILLS_HOME", tempfile.mkdtemp(prefix="tskills-india-"))

from tradekit import http  # noqa: E402
from tradekit.brokers import BrokerError, get_broker  # noqa: E402
from tradekit.brokers.dhan import DhanBroker, DhanClient  # noqa: E402
from tradekit.brokers.fyers import FyersBroker, FyersClient  # noqa: E402
from tradekit.brokers.groww import GrowwBroker, GrowwClient  # noqa: E402
from tradekit.brokers.upstox import UpstoxBroker, UpstoxClient  # noqa: E402

SECRET_TOKEN = "SUPERSECRETTOKEN123456"


class FakeHTTP:
    """Routes (METHOD, url-suffix) to canned JSON and records every request."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def __call__(self, method, url, params=None, data=None, headers=None, timeout=20.0, retries=2, backoff=1.5,
                 json_body=None):
        self.calls.append({"method": method, "url": url, "params": params, "data": data, "headers": headers or {},
                           "json": json_body})
        for (m, suffix), resp in self.routes.items():
            if m == method and url.endswith(suffix):
                if isinstance(resp, Exception):
                    raise resp
                return json.dumps(resp).encode()
        raise AssertionError(f"unexpected request {method} {url}")

    def last(self, suffix):
        return [c for c in self.calls if c["url"].endswith(suffix)][-1]


def patched(routes):
    fake = FakeHTTP(routes)
    return fake, mock.patch.object(http, "request", fake)


class TestFyers(unittest.TestCase):
    def broker(self):
        return FyersBroker(FyersClient(app_id="ABCD1234-100", access_token=SECRET_TOKEN))

    def test_params_and_place(self):
        fake, p = patched({("POST", "/api/v3/orders/sync"): {"s": "ok", "code": 1101, "message": "Order submitted", "id": "808058117761"}})
        with p:
            r = self.broker().place({"symbol": "NSE:SBIN-EQ", "side": "buy", "qty": 3, "type": "limit", "limit_price": 600.5,
                                     "product": "MIS"})
        c = fake.last("/orders/sync")
        self.assertEqual(c["headers"]["Authorization"], f"ABCD1234-100:{SECRET_TOKEN}")
        self.assertEqual((c["json"]["symbol"], c["json"]["type"], c["json"]["side"], c["json"]["productType"]),
                         ("NSE:SBIN-EQ", 1, 1, "INTRADAY"))
        self.assertEqual(c["json"]["limitPrice"], 600.5)
        self.assertEqual(r["order_id"], "808058117761")

    def test_sell_stop_and_bare_symbol(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            from tradekit import config
            cfg = config.load()
            cfg["broker"]["default_exchange"] = "NSE"
            config.save(cfg)
            b = self.broker()
            q = b.to_params({"symbol": "sbin", "side": "sell", "qty": 2, "type": "stop", "stop_price": 590})
            cfg["broker"]["default_exchange"] = None
            config.save(cfg)
        self.assertEqual((q["symbol"], q["side"], q["type"], q["stopPrice"]), ("NSE:SBIN-EQ", -1, 3, 590))

    def test_rejects_fractional_qty(self):
        with self.assertRaises(BrokerError):
            self.broker().to_params({"symbol": "NSE:SBIN-EQ", "side": "buy", "qty": 1.5, "type": "market"})

    def test_error_response_raises(self):
        fake, p = patched({("POST", "/api/v3/orders/sync"): {"s": "error", "code": -50, "message": "Algo orders are not allowed"}})
        with p, self.assertRaises(BrokerError) as cm:
            self.broker().place({"symbol": "NSE:SBIN-EQ", "side": "buy", "qty": 1, "type": "market"})
        self.assertIn("Algo orders", str(cm.exception))

    def test_http_error_hides_token(self):
        err = http.HTTPError(401, "Unauthorized", '{"s":"error","message":"invalid token"}')
        fake, p = patched({("POST", "/api/v3/orders/sync"): err})
        with p, self.assertRaises(BrokerError) as cm:
            self.broker().place({"symbol": "NSE:SBIN-EQ", "side": "buy", "qty": 1, "type": "market"})
        self.assertNotIn(SECRET_TOKEN, str(cm.exception))
        self.assertIn("401", str(cm.exception))

    def test_orders_positions_account_cancel(self):
        fake, p = patched({
            ("GET", "/api/v3/orders"): {"s": "ok", "orderBook": [
                {"id": "1", "symbol": "NSE:SBIN-EQ", "qty": 3, "side": 1, "type": 1, "status": 6, "limitPrice": 600.5, "stopPrice": 0,
                 "filledQty": 0, "tradedPrice": 0, "productType": "INTRADAY"},
                {"id": "2", "symbol": "NSE:SBIN-EQ", "qty": 3, "side": -1, "type": 2, "status": 2, "filledQty": 3, "tradedPrice": 610}]},
            ("GET", "/api/v3/positions"): {"s": "ok", "netPositions": [
                {"symbol": "NSE:SBIN-EQ", "netQty": 3, "netAvg": 600.0, "ltp": 610.0, "unrealized_profit": 30.0, "productType": "INTRADAY"},
                {"symbol": "NSE:IDEA-EQ", "netQty": 0, "netAvg": 0, "ltp": 1}]},
            ("GET", "/api/v3/funds"): {"s": "ok", "fund_limit": [{"id": 1, "title": "Total Balance", "equityAmount": 100000},
                                                                   {"id": 10, "title": "Available Balance", "equityAmount": 75000.5}]},
            ("DELETE", "/api/v3/orders/sync"): {"s": "ok", "code": 1103, "id": "1"}})
        b = self.broker()
        with p:
            self.assertEqual([o["order_id"] for o in b.orders(open_only=True)], ["1"])
            self.assertEqual(b.orders()[1]["status"], "filled")
            pos = b.positions()
            self.assertEqual(len(pos), 1)
            self.assertEqual((pos[0]["qty"], pos[0]["market_value"]), (3.0, 1830.0))
            a = b.account()
            self.assertEqual((a["equity"], a["cash"]), (100000, 75000.5))
            self.assertEqual(b.cancel("1")["status"], "cancel_requested")
        self.assertEqual(fake.last("/orders/sync")["json"], {"id": "1"})

    def test_session_hash(self):
        fake, p = patched({("POST", "/api/v3/validate-authcode"): {"s": "ok", "code": 200, "access_token": "tok"}})
        c = FyersClient(app_id="ABCD1234-100")
        with p:
            c.generate_session("AUTHCODE", "sec")
        body = fake.last("/validate-authcode")["json"]
        self.assertEqual(body["appIdHash"], hashlib.sha256(b"ABCD1234-100:sec").hexdigest())
        self.assertEqual((body["grant_type"], body["code"]), ("authorization_code", "AUTHCODE"))
        self.assertIn("client_id=ABCD1234-100", c.login_url("https://127.0.0.1/"))

    def test_missing_credentials_message(self):
        env = {"TRADING_SKILLS_HOME": os.environ["TRADING_SKILLS_HOME"]}  # keep the home folder; Windows needs it too
        with mock.patch.dict(os.environ, env, clear=True), self.assertRaises(BrokerError) as cm:
            FyersBroker(FyersClient(app_id=None, access_token=None)).account()
        self.assertIn("access_token", str(cm.exception))


class TestDhan(unittest.TestCase):
    def broker(self):
        return DhanBroker(DhanClient(client_id="1000000003", access_token=SECRET_TOKEN))

    def test_place_limit(self):
        fake, p = patched({("POST", "/v2/orders"): {"orderId": "112111182198", "orderStatus": "PENDING"}})
        with p:
            r = self.broker().place({"symbol": "NSE_EQ:11536", "side": "buy", "qty": 5, "type": "limit", "limit_price": 3345.8,
                                     "product": "CNC"})
        c = fake.last("/v2/orders")
        self.assertEqual(c["headers"]["access-token"], SECRET_TOKEN)
        j = c["json"]
        self.assertEqual((j["dhanClientId"], j["transactionType"], j["exchangeSegment"], j["productType"], j["orderType"],
                          j["securityId"], j["quantity"], j["price"]),
                         ("1000000003", "BUY", "NSE_EQ", "CNC", "LIMIT", "11536", 5, 3345.8))
        self.assertEqual(r["order_id"], "112111182198")

    def test_symbol_and_stop_mapping(self):
        b = self.broker()
        with self.assertRaises(BrokerError):
            b.to_params({"symbol": "TCS", "side": "buy", "qty": 1, "type": "market"})
        j = b.to_params({"symbol": "NSE_EQ:11536", "side": "sell", "qty": 1, "type": "stop", "stop_price": 3300, "product": "MIS"})
        self.assertEqual((j["orderType"], j["triggerPrice"], j["productType"]), ("STOP_LOSS_MARKET", 3300, "INTRADAY"))
        with self.assertRaises(BrokerError):
            b.to_params({"symbol": "NSE_EQ:11536", "side": "buy", "qty": 1, "type": "market", "product": "BOGUS"})

    def test_reads(self):
        fake, p = patched({
            ("GET", "/v2/orders"): [{"orderId": "1", "exchangeSegment": "NSE_EQ", "securityId": "11536", "transactionType": "BUY",
                                     "quantity": 5, "orderType": "LIMIT", "price": 3345.8, "orderStatus": "PENDING", "filledQty": 0},
                                    {"orderId": "2", "exchangeSegment": "NSE_EQ", "securityId": "11536", "transactionType": "SELL",
                                     "quantity": 5, "orderType": "MARKET", "orderStatus": "TRADED", "filledQty": 5}],
            ("GET", "/v2/positions"): [{"tradingSymbol": "TCS", "securityId": "11536", "exchangeSegment": "NSE_EQ", "netQty": 5,
                                        "costPrice": 3345.8, "unrealizedProfit": 12.5, "productType": "CNC"}],
            ("GET", "/v2/holdings"): {"errorType": "Data_API_Error"},
            ("GET", "/v2/fundlimit"): {"dhanClientId": "1000000003", "availabelBalance": 98440.0, "utilizedAmount": 1560.0},
            ("DELETE", "/v2/orders/1"): {"orderId": "1", "orderStatus": "CANCELLED"}})
        b = self.broker()
        with p:
            self.assertEqual([o["order_id"] for o in b.orders(open_only=True)], ["1"])
            pos = b.positions()
            self.assertEqual((pos[0]["symbol"], pos[0]["qty"]), ("NSE_EQ:11536", 5.0))
            self.assertEqual(b.account()["cash"], 98440.0)
            self.assertEqual(b.cancel("1")["status"], "cancel_requested")

    def test_error_hides_token(self):
        err = http.HTTPError(400, "Bad Request", '{"errorType":"Order_Error","errorCode":"DH-906","errorMessage":"Missing required fields"}')
        fake, p = patched({("POST", "/v2/orders"): err})
        with p, self.assertRaises(BrokerError) as cm:
            self.broker().place({"symbol": "NSE_EQ:11536", "side": "buy", "qty": 1, "type": "market"})
        self.assertIn("DH-906", str(cm.exception))
        self.assertNotIn(SECRET_TOKEN, str(cm.exception))


class TestUpstox(unittest.TestCase):
    def broker(self):
        return UpstoxBroker(UpstoxClient(api_key="KEY", access_token=SECRET_TOKEN))

    def test_place_v3(self):
        fake, p = patched({("POST", "/v3/order/place"): {"status": "success", "data": {"order_ids": ["1644490272000"]},
                                                         "metadata": {"latency": 30}}})
        with p:
            r = self.broker().place({"symbol": "NSE_EQ|INE669E01016", "side": "buy", "qty": 1, "type": "limit",
                                     "limit_price": 11.5, "product": "CNC"})
        c = fake.last("/v3/order/place")
        self.assertEqual(c["headers"]["Authorization"], f"Bearer {SECRET_TOKEN}")
        self.assertTrue(c["url"].startswith("https://api-hft.upstox.com"))
        j = c["json"]
        self.assertEqual((j["instrument_token"], j["product"], j["order_type"], j["transaction_type"], j["price"]),
                         ("NSE_EQ|INE669E01016", "D", "LIMIT", "BUY", 11.5))
        self.assertEqual(r["order_id"], "1644490272000")

    def test_market_orders_and_bad_symbol_rejected(self):
        b = self.broker()
        with self.assertRaises(BrokerError) as cm:
            b.to_params({"symbol": "NSE_EQ|INE669E01016", "side": "buy", "qty": 1, "type": "market"})
        self.assertIn("MARKET", str(cm.exception))
        with self.assertRaises(BrokerError):
            b.to_params({"symbol": "RELIANCE", "side": "buy", "qty": 1, "type": "limit", "limit_price": 1})

    def test_reads(self):
        fake, p = patched({
            ("GET", "/v2/order/retrieve-all"): {"status": "success", "data": [
                {"order_id": "1", "instrument_token": "NSE_EQ|INE669E01016", "transaction_type": "BUY", "quantity": 1,
                 "order_type": "LIMIT", "price": 11.5, "status": "open", "filled_quantity": 0},
                {"order_id": "2", "instrument_token": "NSE_EQ|INE669E01016", "transaction_type": "SELL", "quantity": 1,
                 "status": "complete", "filled_quantity": 1, "average_price": 12.0}]},
            ("GET", "/v2/portfolio/short-term-positions"): {"status": "success", "data": [
                {"instrument_token": "NSE_EQ|INE669E01016", "quantity": 1, "average_price": 11.5, "last_price": 12.0,
                 "unrealised": 0.5, "product": "D", "trading_symbol": "IDEA"}]},
            ("GET", "/v2/user/get-funds-and-margin"): {"status": "success", "data": {"equity": {"available_margin": 5000.0, "used_margin": 250.0}}},
            ("DELETE", "/v2/order/cancel"): {"status": "success", "data": {"order_id": "1"}}})
        b = self.broker()
        with p:
            self.assertEqual([o["order_id"] for o in b.orders(open_only=True)], ["1"])
            self.assertEqual(b.orders()[1]["status"], "filled")
            self.assertEqual(b.positions()[0]["market_value"], 12.0)
            a = b.account()
            self.assertEqual((a["cash"], a["equity"]), (5000.0, 5250.0))
            b.cancel("1")
        self.assertEqual(fake.last("/v2/order/cancel")["params"], {"order_id": "1"})

    def test_error_body(self):
        fake, p = patched({("POST", "/v3/order/place"): {"status": "error", "errors": [{"errorCode": "UDAPI1154", "message": "static IP"}]}})
        with p, self.assertRaises(BrokerError) as cm:
            self.broker().place({"symbol": "NSE_EQ|INE669E01016", "side": "buy", "qty": 1, "type": "limit", "limit_price": 1})
        self.assertIn("UDAPI1154", str(cm.exception))

    def test_session_form(self):
        fake, p = patched({("POST", "/v2/login/authorization/token"): {"access_token": "tok", "user_id": "U1"}})
        c = UpstoxClient(api_key="KEY")
        with p:
            c.generate_session("CODE", "SEC", "https://127.0.0.1/")
        d = fake.last("/login/authorization/token")["data"]
        self.assertEqual((d["grant_type"], d["code"], d["client_id"], d["redirect_uri"]),
                         ("authorization_code", "CODE", "KEY", "https://127.0.0.1/"))
        self.assertIn("response_type=code", c.login_url("https://127.0.0.1/"))


class TestGroww(unittest.TestCase):
    def broker(self):
        return GrowwBroker(GrowwClient(access_token=SECRET_TOKEN))

    def test_place(self):
        fake, p = patched({("POST", "/v1/order/create"): {"status": "SUCCESS", "payload": {
            "groww_order_id": "GMK39038RDT490CCVRO", "order_status": "OPEN", "order_reference_id": "x", "remark": "ok"}}})
        with p:
            r = self.broker().place({"symbol": "NSE:RELIANCE", "side": "buy", "qty": 2, "type": "limit", "limit_price": 1400.5,
                                     "product": "CNC"})
        c = fake.last("/order/create")
        h = c["headers"]
        self.assertEqual((h["Authorization"], h["X-API-VERSION"]), (f"Bearer {SECRET_TOKEN}", "1.0"))
        j = c["json"]
        self.assertEqual((j["trading_symbol"], j["exchange"], j["segment"], j["product"], j["order_type"], j["transaction_type"],
                          j["price"], j["validity"]), ("RELIANCE", "NSE", "CASH", "CNC", "LIMIT", "BUY", 1400.5, "DAY"))
        self.assertTrue(8 <= len(j["order_reference_id"]) <= 20 and j["order_reference_id"].isalnum())
        self.assertEqual(r["order_id"], "GMK39038RDT490CCVRO")

    def test_stop_types(self):
        b = self.broker()
        self.assertEqual(b.to_params({"symbol": "NSE:X", "side": "sell", "qty": 1, "type": "stop", "stop_price": 5})["order_type"], "SL_M")
        j = b.to_params({"symbol": "NSE:X", "side": "sell", "qty": 1, "type": "stop_limit", "stop_price": 5, "limit_price": 4.9})
        self.assertEqual((j["order_type"], j["trigger_price"], j["price"]), ("SL", 5, 4.9))
        with self.assertRaises(BrokerError):
            b.to_params({"symbol": "MCX:X", "side": "buy", "qty": 1, "type": "market"})

    def test_failure_payload(self):
        fake, p = patched({("POST", "/v1/order/create"): {"status": "FAILURE", "error": {"code": "GA007", "message": "Duplicate order reference id"}}})
        with p, self.assertRaises(BrokerError) as cm:
            self.broker().place({"symbol": "NSE:X", "side": "buy", "qty": 1, "type": "market"})
        self.assertIn("GA007", str(cm.exception))

    def test_reads(self):
        fake, p = patched({
            ("GET", "/v1/order/list"): {"status": "SUCCESS", "payload": {"order_list": [
                {"groww_order_id": "A", "trading_symbol": "RELIANCE", "exchange": "NSE", "order_status": "ACKED", "quantity": 2,
                 "price": 1400.5, "transaction_type": "BUY", "order_type": "LIMIT", "filled_quantity": 0},
                {"groww_order_id": "B", "trading_symbol": "RELIANCE", "exchange": "NSE", "order_status": "EXECUTED", "quantity": 2,
                 "transaction_type": "SELL", "filled_quantity": 2, "average_fill_price": 1410}]}},
            ("GET", "/v1/holdings/user"): {"status": "SUCCESS", "payload": {"holdings": [{"trading_symbol": "WIPRO", "quantity": 10, "average_price": 250.0}]}},
            ("GET", "/v1/positions/user"): {"status": "SUCCESS", "payload": {"positions": [
                {"trading_symbol": "RELIANCE", "exchange": "NSE", "product": "MIS", "quantity": 2, "net_price": 1400.5, "realised_pnl": 0}]}},
            ("GET", "/v1/margins/detail/user"): {"status": "SUCCESS", "payload": {"clear_cash": 12345.6, "net_margin_used": 100}},
            ("POST", "/v1/order/cancel"): {"status": "SUCCESS", "payload": {"groww_order_id": "A", "order_status": "CANCELLED"}}})
        b = self.broker()
        with p:
            self.assertEqual([o["order_id"] for o in b.orders(open_only=True)], ["A"])
            self.assertEqual(b.orders()[1]["status"], "filled")
            self.assertEqual([x["symbol"] for x in b.positions()], ["NSE:WIPRO", "NSE:RELIANCE"])
            self.assertEqual(b.account()["cash"], 12345.6)
            b.cancel("A")
        self.assertEqual(fake.last("/order/cancel")["json"], {"segment": "CASH", "groww_order_id": "A"})

    def test_token_checksum(self):
        fake, p = patched({("POST", "/v1/token/api/access"): {"payload": {"token": "newtok", "expiry": "2026-11-15T06:00:00"}}})
        with p, mock.patch("time.time", return_value=1700000000):
            d = GrowwClient().generate_token("APIKEY", "APISECRET")
        j = fake.last("/token/api/access")["json"]
        self.assertEqual((j["key_type"], j["timestamp"], j["checksum"]),
                         ("approval", "1700000000", hashlib.sha256(b"APISECRET1700000000").hexdigest()))
        self.assertEqual(d["token"], "newtok")


class TestRegistryAndRouter(unittest.TestCase):
    def test_get_broker_names(self):
        for n, cls in (("fyers", "FyersBroker"), ("upstox", "UpstoxBroker"), ("dhan", "DhanBroker"), ("groww", "GrowwBroker")):
            self.assertEqual(type(get_broker(n)).__name__, cls)
            self.assertTrue(get_broker(n).live)
        with self.assertRaises(BrokerError):
            get_broker("angelone")

    def test_http_json_body_encoding(self):
        captured = {}

        class Resp:
            def read(self):
                return b"{}"

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def fake_open(req, timeout=None, context=None):
            captured["data"], captured["ct"] = req.data, req.get_header("Content-type")
            return Resp()

        with mock.patch("urllib.request.urlopen", fake_open):
            http.request("POST", "https://example.invalid/x", json_body={"a": 1, "b": [2]})
        self.assertEqual(json.loads(captured["data"]), {"a": 1, "b": [2]})
        self.assertEqual(captured["ct"], "application/json")


if __name__ == "__main__":
    unittest.main()

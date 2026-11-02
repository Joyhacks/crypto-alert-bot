import json
import os
import tempfile
import unittest

import requests

import main
from main import Alerter, Rule


class FakeResponse:
    def __init__(self, status=200, body=None):
        self.status_code = status
        self.ok = status < 400
        self._body = body or {}

    def json(self):
        return self._body

    def raise_for_status(self):
        if not self.ok:
            raise requests.HTTPError(f"{self.status_code}")


class FakeSession:
    def __init__(self, response=None, error=None):
        self.response, self.error, self.calls = response, error, []

    def get(self, url, **kw):
        self.calls.append((url, kw))
        if self.error:
            raise self.error
        return self.response

    post = get


def write_config(data):
    f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    if isinstance(data, str):
        f.write(data)
    else:
        json.dump(data, f)
    f.close()
    return f.name


class LoadConfigTest(unittest.TestCase):
    def test_example_config_is_valid(self):
        path = os.path.join(os.path.dirname(__file__), "config.json")
        rules, interval = main.load_config(path)
        self.assertTrue(rules)
        self.assertGreaterEqual(interval, main.MIN_INTERVAL_SECONDS)

    def test_parses_rules(self):
        rules, interval = main.load_config(write_config({
            "interval_seconds": 120,
            "alerts": [{"coin": " Bitcoin ", "above": 65000, "change_24h": 5}, {"coin": "ethereum", "below": 2500}],
        }))
        self.assertEqual(interval, 120)
        self.assertEqual(rules[0], Rule("bitcoin", above=65000.0, change_24h=5.0))
        self.assertEqual(rules[1], Rule("ethereum", below=2500.0))

    def test_rejects_bad_configs(self):
        bad = [
            "{ not json",
            {"alerts": []},
            {"alerts": [{"above": 1}]},
            {"alerts": [{"coin": "bitcoin"}]},
            {"alerts": [{"coin": "bitcoin", "above": -5}]},
            {"alerts": [{"coin": "bitcoin", "above": "65000"}]},
            {"alerts": [{"coin": "bitcoin", "above": True}]},
            {"interval_seconds": 5, "alerts": [{"coin": "bitcoin", "above": 1}]},
        ]
        for data in bad:
            with self.subTest(data=data), self.assertRaises(ValueError):
                main.load_config(write_config(data))


class FetchPricesTest(unittest.TestCase):
    def test_one_request_for_all_coins_and_unknown_coins_dropped(self):
        session = FakeSession(FakeResponse(body={
            "bitcoin": {"usd": 65000, "usd_24h_change": 2.5},
            "solana": {"usd": 150, "usd_24h_change": None},
        }))
        prices = main.fetch_prices(["solana", "bitcoin", "not-a-coin", "bitcoin"], session)
        self.assertEqual(prices, {"bitcoin": (65000.0, 2.5), "solana": (150.0, 0.0)})
        self.assertEqual(len(session.calls), 1)
        self.assertEqual(session.calls[0][1]["params"]["ids"], "bitcoin,not-a-coin,solana")

    def test_http_error_raises(self):
        with self.assertRaises(requests.HTTPError):
            main.fetch_prices(["bitcoin"], FakeSession(FakeResponse(429)))


class AlerterTest(unittest.TestCase):
    def setUp(self):
        self.sent = []
        self.send = lambda text: self.sent.append(text) or True

    def test_alerts_once_then_rearms_after_clearing(self):
        alerter = Alerter([Rule("bitcoin", above=100)])
        for price in [90, 101, 105, 110]:
            alerter.check({"bitcoin": (price, 0)}, self.send)
        self.assertEqual(len(self.sent), 1)
        alerter.check({"bitcoin": (95, 0)}, self.send)
        alerter.check({"bitcoin": (102, 0)}, self.send)
        self.assertEqual(len(self.sent), 2)

    def test_conditions_are_independent(self):
        alerter = Alerter([Rule("bitcoin", above=100, change_24h=5)])
        alerter.check({"bitcoin": (101, 6)}, self.send)
        self.assertEqual(len(self.sent), 2)
        # The move cools off but the price target still holds: only the change alert re-arms.
        alerter.check({"bitcoin": (101, 1)}, self.send)
        alerter.check({"bitcoin": (101, -7)}, self.send)
        self.assertEqual(len(self.sent), 3)
        self.assertIn("down 7.00% in 24h", self.sent[-1])

    def test_below_rule(self):
        alerter = Alerter([Rule("ethereum", below=2500)])
        alerter.check({"ethereum": (2400, -3)}, self.send)
        self.assertIn("at or below $2,500.00", self.sent[0])

    def test_missing_price_keeps_state(self):
        alerter = Alerter([Rule("bitcoin", above=100)])
        alerter.check({"bitcoin": (101, 0)}, self.send)
        alerter.check({}, self.send)
        alerter.check({"bitcoin": (101, 0)}, self.send)
        self.assertEqual(len(self.sent), 1)

    def test_failed_send_is_retried(self):
        alerter = Alerter([Rule("bitcoin", above=100)])
        self.assertEqual(alerter.check({"bitcoin": (101, 0)}, lambda text: False), 0)
        self.assertEqual(alerter.check({"bitcoin": (101, 0)}, self.send), 1)

    def test_two_rules_for_one_coin_do_not_share_state(self):
        alerter = Alerter([Rule("bitcoin", above=100), Rule("bitcoin", above=200)])
        alerter.check({"bitcoin": (150, 0)}, self.send)
        alerter.check({"bitcoin": (250, 0)}, self.send)
        self.assertEqual(len(self.sent), 2)

    def test_message_is_html_escaped(self):
        self.assertIn("&lt;B&gt;", main.format_message("<b>", 1, 0, "x"))


class SendTelegramTest(unittest.TestCase):
    def test_success_and_http_failure(self):
        self.assertTrue(main.send_telegram("t", "c", "hi", FakeSession(FakeResponse(200))))
        self.assertFalse(main.send_telegram("t", "c", "hi", FakeSession(FakeResponse(400))))

    def test_network_error_never_logs_the_token(self):
        token = "123456:SECRET-TOKEN"
        error = requests.ConnectionError(f"failed for https://api.telegram.org/bot{token}/sendMessage")
        with self.assertLogs("crypto-alert-bot", "WARNING") as logs:
            self.assertFalse(main.send_telegram(token, "c", "hi", FakeSession(error=error)))
        self.assertNotIn("SECRET", "\n".join(logs.output))


if __name__ == "__main__":
    unittest.main()

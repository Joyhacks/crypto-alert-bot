"""Telegram alerts for crypto price targets and 24h moves, using CoinGecko's free API."""
from __future__ import annotations

import html
import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from typing import Callable, Iterator

import requests

COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"
TELEGRAM_URL = "https://api.telegram.org/bot{token}/sendMessage"
MIN_INTERVAL_SECONDS = 30  # CoinGecko's free tier rate-limits anything tighter

log = logging.getLogger("crypto-alert-bot")

Prices = dict[str, tuple[float, float]]  # coin id -> (usd price, 24h change %)


@dataclass(frozen=True)
class Rule:
    coin: str
    above: float | None = None
    below: float | None = None
    change_24h: float | None = None


def _positive_number(raw: dict, key: str, index: int) -> float | None:
    value = raw.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ValueError(f"alerts[{index}].{key} must be a positive number")
    return float(value)


def load_config(path: str) -> tuple[list[Rule], int]:
    with open(path, encoding="utf-8") as f:
        config = json.load(f)

    rules = []
    for i, raw in enumerate(config.get("alerts", [])):
        coin = str(raw.get("coin", "")).strip().lower()
        if not coin:
            raise ValueError(f"alerts[{i}] needs a coin id")
        rule = Rule(
            coin=coin,
            above=_positive_number(raw, "above", i),
            below=_positive_number(raw, "below", i),
            change_24h=_positive_number(raw, "change_24h", i),
        )
        if rule.above is None and rule.below is None and rule.change_24h is None:
            raise ValueError(f"alerts[{i}] ({coin}) needs at least one of above, below or change_24h")
        rules.append(rule)

    if not rules:
        raise ValueError("config has no alerts")

    interval = config.get("interval_seconds", 60)
    if isinstance(interval, bool) or not isinstance(interval, int) or interval < MIN_INTERVAL_SECONDS:
        raise ValueError(f"interval_seconds must be a whole number of at least {MIN_INTERVAL_SECONDS}")
    return rules, interval


def fetch_prices(coins: list[str], session=requests) -> Prices:
    """One request for every coin. Coins CoinGecko doesn't know are left out of the result."""
    response = session.get(
        COINGECKO_URL,
        params={"ids": ",".join(sorted(set(coins))), "vs_currencies": "usd", "include_24hr_change": "true"},
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()
    prices = {}
    for coin in set(coins):
        entry = data.get(coin) or {}
        if "usd" in entry:
            prices[coin] = (float(entry["usd"]), float(entry.get("usd_24h_change") or 0.0))
    return prices


def conditions(rule: Rule, price: float, change: float) -> Iterator[tuple[str, str]]:
    """Every condition of the rule that holds right now, as (kind, description)."""
    if rule.above is not None and price >= rule.above:
        yield "above", f"at or above ${rule.above:,.2f}"
    if rule.below is not None and price <= rule.below:
        yield "below", f"at or below ${rule.below:,.2f}"
    if rule.change_24h is not None and abs(change) >= rule.change_24h:
        direction = "up" if change > 0 else "down"
        yield "change", f"{direction} {abs(change):.2f}% in 24h (threshold {rule.change_24h:g}%)"


def format_message(coin: str, price: float, change: float, description: str) -> str:
    return (
        f"<b>{html.escape(coin.upper())}</b> is {html.escape(description)}\n"
        f"Price: ${price:,.2f}\n"
        f"24h: {change:+.2f}%"
    )


class Alerter:
    """Edge-triggered alerts.

    A condition sends one message when it becomes true, then stays quiet until it
    clears and becomes true again. A coin with no price this cycle keeps its state,
    so an API hiccup doesn't cause a repeat alert. If a send fails the condition
    isn't marked as alerted, so it's retried on the next cycle.
    """

    def __init__(self, rules: list[Rule]):
        self.rules = rules
        self.active: set[str] = set()

    def check(self, prices: Prices, send: Callable[[str], bool]) -> int:
        sent = 0
        for i, rule in enumerate(self.rules):
            if rule.coin not in prices:
                continue
            price, change = prices[rule.coin]
            holding = {f"{i}:{kind}": text for kind, text in conditions(rule, price, change)}
            self.active = {k for k in self.active if not k.startswith(f"{i}:") or k in holding}
            for key, text in holding.items():
                if key in self.active:
                    continue
                if send(format_message(rule.coin, price, change, text)):
                    self.active.add(key)
                    sent += 1
        return sent


def send_telegram(token: str, chat_id: str, text: str, session=requests) -> bool:
    try:
        response = session.post(
            TELEGRAM_URL.format(token=token),
            data={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
    except requests.RequestException as e:
        # The exception text contains the request URL, and the URL contains the token.
        log.warning("Telegram request failed: %s", type(e).__name__)
        return False
    if not response.ok:
        log.warning("Telegram returned HTTP %s", response.status_code)
        return False
    return True


def run(config_path: str) -> int:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        log.error("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID first (see README).")
        return 1
    try:
        rules, interval = load_config(config_path)
    except (OSError, ValueError) as e:
        log.error("Config problem in %s: %s", config_path, e)
        return 1

    coins = sorted({rule.coin for rule in rules})
    alerter = Alerter(rules)
    session = requests.Session()
    log.info("Watching %s every %ss", ", ".join(coins), interval)

    while True:
        try:
            prices = fetch_prices(coins, session)
        except (requests.RequestException, ValueError) as e:
            log.warning("CoinGecko request failed (%s), trying again next cycle", type(e).__name__)
            prices = {}
        for coin in coins:
            if coin in prices:
                price, change = prices[coin]
                log.info("%s $%s (%+.2f%%)", coin, f"{price:,.2f}", change)
            elif prices:
                log.warning("%s: no price from CoinGecko. Check the coin id.", coin)
        sent = alerter.check(prices, lambda text: send_telegram(token, chat_id, text, session))
        if sent:
            log.info("Sent %d alert(s)", sent)
        time.sleep(interval)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.json"
    try:
        return run(config_path)
    except KeyboardInterrupt:
        log.info("Stopped.")
        return 0


if __name__ == "__main__":
    sys.exit(main())

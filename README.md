# crypto-alert-bot

A small Python bot that watches coin prices on CoinGecko and messages you on Telegram when a price crosses a level or moves more than a set percentage in 24 hours.

One request covers every coin you watch, so a minute-by-minute check stays well inside CoinGecko's free rate limit. Alerts are edge-triggered: you get one message when a condition becomes true, not one every minute while it stays true. It re-arms once the condition clears.

## Setup

You need a Telegram bot token and your chat ID.

1. In Telegram, message `@BotFather`, send `/newbot` and follow the prompts. It gives you a token like `123456789:AA...`.
2. Send any message to your new bot, then open `https://api.telegram.org/bot<token>/getUpdates` in a browser. Your chat ID is the `"chat":{"id": ...}` value.

Then:

```bash
pip install -r requirements.txt
export TELEGRAM_BOT_TOKEN=123456789:AA...
export TELEGRAM_CHAT_ID=987654321
python main.py               # reads config.json
python main.py other.json    # or a different config
```

The token stays in the environment, never in the config file, and it's kept out of the logs. Telegram's error messages include the request URL, which contains the token.

## Config

```json
{
  "interval_seconds": 60,
  "alerts": [
    { "coin": "bitcoin", "above": 120000, "change_24h": 5 },
    { "coin": "ethereum", "below": 2500 },
    { "coin": "dogecoin", "above": 0.5, "below": 0.1 }
  ]
}
```

Each alert needs a CoinGecko coin ID and at least one of:

| Field | Fires when |
|---|---|
| `above` | the USD price is at or above this |
| `below` | the USD price is at or below this |
| `change_24h` | the 24h change is at least this many percent, up or down |

Coin IDs are CoinGecko's, which aren't always the ticker (`ripple`, not `xrp`). The full list is at `https://api.coingecko.com/api/v3/coins/list`. If an ID is wrong the bot logs it every cycle instead of failing silently.

`interval_seconds` has a floor of 30. A bad config stops the bot at startup with the field that's wrong.

## Tests

```bash
python -m unittest -v
```

The tests cover config validation, the alert state machine (fire once, re-arm, retry after a failed send, no repeat after an API gap) and that the token never reaches the logs. No network calls.

## Running it long-term

It's a plain loop, so anything that keeps a process alive works: a systemd service, a `tmux` session, or a small container on Fly.io or Railway. Alert state lives in memory, so a restart while a condition holds sends that alert once more.

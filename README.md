# Telegram Crypto Price Alert Bot

A Python bot that monitors cryptocurrency prices using the CoinGecko API and sends Telegram alerts when price targets or percentage changes are met.

## Features

- 🔍 Monitors cryptocurrency prices every 60 seconds
- 💰 Sends alerts when price reaches your target
- 📊 Sends alerts when 24h price change exceeds your threshold
- 📱 Delivers notifications via Telegram
- 🖥️ Displays real-time price logs in console

## Setup Instructions

### Step 1: Create a Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Start a chat and send the command: `/newbot`
3. Follow the prompts:
   - Choose a name for your bot (e.g., "My Crypto Alert Bot")
   - Choose a username for your bot (must end in 'bot', e.g., "my_crypto_alert_bot")
4. BotFather will give you a **bot token** that looks like this:
   ```
   123456789:ABCdefGHIjklMNOpqrsTUVwxyz1234567890
   ```
5. Save this token - you'll need it for the config file

### Step 2: Find Your Chat ID

**Method 1: Using @userinfobot**
1. Search for **@userinfobot** in Telegram
2. Start a chat with the bot
3. It will automatically send you your chat ID

**Method 2: Using @raw_data_bot**
1. Search for **@raw_data_bot** in Telegram
2. Start a chat with the bot
3. Send any message
4. Look for the `"id"` field in the response (your chat ID)

**Method 3: Using your bot's API**
1. Send a message to your newly created bot (the one from Step 1)
2. Open this URL in your browser (replace `YOUR_BOT_TOKEN` with your actual token):
   ```
   https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates
   ```
3. Look for the `"chat":{"id":` field in the JSON response

### Step 3: Configure the Bot

1. Open the `config.json` file
2. Replace the placeholder values with your actual settings:

```json
{
  "coin_id": "bitcoin",
  "target_price": 65000,
  "percentage_change": 5,
  "telegram_bot_token": "123456789:ABCdefGHIjklMNOpqrsTUVwxyz1234567890",
  "telegram_chat_id": "987654321"
}
```

**Configuration Options:**

- `coin_id`: The cryptocurrency to monitor (e.g., "bitcoin", "ethereum", "solana", "dogecoin")
  - Find valid coin IDs at: https://api.coingecko.com/api/v3/coins/list
- `target_price`: Price threshold in USD (e.g., 65000). Set to 0 to disable.
- `percentage_change`: 24-hour change threshold (e.g., 5 for ±5%). Set to 0 to disable.
- `telegram_bot_token`: Your bot token from BotFather
- `telegram_chat_id`: Your Telegram chat ID

### Step 4: Run the Bot on Replit

1. Click the **Run** button at the top of the Replit editor
2. The bot will start monitoring prices and display logs in the console
3. You'll receive Telegram alerts when your conditions are met

The bot runs continuously and checks prices every 60 seconds.

## How It Works

1. **Price Monitoring**: The bot fetches live cryptocurrency prices from the CoinGecko API
2. **Target Price Alert**: If the price reaches or exceeds your `target_price`, you get an alert
3. **Percentage Change Alert**: If the 24-hour price change is ±`percentage_change`% or more, you get an alert
4. **Smart Alerts**: Each alert is sent only once until the condition resets (e.g., price drops below target)

## Example Output

Console logs will look like this:
```
Starting Crypto Price Alert Bot...
==================================================
Monitoring: BITCOIN
Target Price: $65,000.00
24h Change Alert: ±5%
==================================================

[2025-10-03 14:30:15] BITCOIN: $64,234.50 | 24h Change: +3.21%
[2025-10-03 14:31:15] BITCOIN: $64,289.75 | 24h Change: +3.28%
[2025-10-03 14:32:15] BITCOIN: $65,012.00 | 24h Change: +5.45%
  ✓ Alert sent: Price reached target: $65,012.00 (Target: $65,000.00)
  ✓ Alert sent: 24h change alert: increased by 5.45% (Threshold: ±5%)
```

## Troubleshooting

**Bot doesn't send messages:**
- Make sure you've started a chat with your bot first (send it any message)
- Verify your bot token and chat ID are correct in `config.json`
- Check the console for error messages

**"Coin not found" error:**
- Check that your `coin_id` is valid using the CoinGecko API
- Use lowercase names (e.g., "bitcoin" not "Bitcoin")

**API rate limits:**
- The free CoinGecko API allows ~50 calls per minute
- This bot makes 1 call per minute, well within limits

## Supported Cryptocurrencies

You can monitor any cryptocurrency available on CoinGecko. Popular options:
- bitcoin
- ethereum
- solana
- cardano
- dogecoin
- shiba-inu
- ripple
- polkadot

For a complete list, visit: https://api.coingecko.com/api/v3/coins/list

## Notes

- The bot uses the free CoinGecko API (no authentication required)
- Alerts are sent only once per condition until it resets
- The bot will keep running until you stop it manually
- All logs are displayed in the console for monitoring

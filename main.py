import requests
import json
import time
import os
from datetime import datetime

def load_config():
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        print("Error: config.json not found. Please create it with the required settings.")
        exit(1)
    except json.JSONDecodeError:
        print("Error: config.json is not valid JSON.")
        exit(1)

def get_crypto_price(coin_id):
    url = f"https://api.coingecko.com/api/v3/simple/price"
    params = {
        'ids': coin_id,
        'vs_currencies': 'usd',
        'include_24hr_change': 'true'
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if coin_id not in data:
            print(f"Error: Coin '{coin_id}' not found in CoinGecko API.")
            return None, None
        
        price = data[coin_id]['usd']
        change_24h = data[coin_id].get('usd_24h_change', 0)
        
        return price, change_24h
    except requests.exceptions.RequestException as e:
        print(f"Error fetching price: {e}")
        return None, None

def send_telegram_message(bot_token, chat_id, message):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'HTML'
    }
    
    try:
        response = requests.post(url, data=data, timeout=10)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error sending Telegram message: {e}")
        return False

def check_alert_conditions(price, change_24h, target_price, percentage_change):
    alerts = []
    
    if target_price > 0:
        if price >= target_price:
            alerts.append(f"Price reached target: ${price:,.2f} (Target: ${target_price:,.2f})")
    
    if percentage_change > 0:
        if abs(change_24h) >= percentage_change:
            direction = "increased" if change_24h > 0 else "decreased"
            alerts.append(f"24h change alert: {direction} by {abs(change_24h):.2f}% (Threshold: ±{percentage_change}%)")
    
    return alerts

def main():
    print("Starting Crypto Price Alert Bot...")
    print("=" * 50)
    
    config = load_config()
    
    coin_id = config.get('coin_id', 'bitcoin')
    target_price = config.get('target_price', 0)
    percentage_change = config.get('percentage_change', 0)
    
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID', '')
    
    if not bot_token or not chat_id:
        print("Error: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables must be set")
        exit(1)
    
    print(f"Monitoring: {coin_id.upper()}")
    print(f"Target Price: ${target_price:,.2f}" if target_price > 0 else "Target Price: Not set")
    print(f"24h Change Alert: ±{percentage_change}%" if percentage_change > 0 else "24h Change Alert: Not set")
    print("=" * 50)
    print()
    
    alert_sent = {
        'target_price': False,
        'percentage_change': False
    }
    
    while True:
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            price, change_24h = get_crypto_price(coin_id)
            
            if price is not None:
                print(f"[{timestamp}] {coin_id.upper()}: ${price:,.2f} | 24h Change: {change_24h:+.2f}%")
                
                alerts = check_alert_conditions(price, change_24h, target_price, percentage_change)
                
                if alerts:
                    for alert in alerts:
                        if 'target' in alert.lower() and not alert_sent['target_price']:
                            message = f"🚨 <b>CRYPTO ALERT</b> 🚨\n\n"
                            message += f"<b>Coin:</b> {coin_id.upper()}\n"
                            message += f"<b>Current Price:</b> ${price:,.2f}\n"
                            message += f"<b>24h Change:</b> {change_24h:+.2f}%\n\n"
                            message += f"✅ {alert}"
                            
                            if send_telegram_message(bot_token, chat_id, message):
                                print(f"  ✓ Alert sent: {alert}")
                                alert_sent['target_price'] = True
                            else:
                                print(f"  ✗ Failed to send alert: {alert}")
                        
                        elif 'change' in alert.lower() and not alert_sent['percentage_change']:
                            message = f"🚨 <b>CRYPTO ALERT</b> 🚨\n\n"
                            message += f"<b>Coin:</b> {coin_id.upper()}\n"
                            message += f"<b>Current Price:</b> ${price:,.2f}\n"
                            message += f"<b>24h Change:</b> {change_24h:+.2f}%\n\n"
                            message += f"✅ {alert}"
                            
                            if send_telegram_message(bot_token, chat_id, message):
                                print(f"  ✓ Alert sent: {alert}")
                                alert_sent['percentage_change'] = True
                            else:
                                print(f"  ✗ Failed to send alert: {alert}")
                else:
                    if price < target_price or target_price == 0:
                        alert_sent['target_price'] = False
                    
                    if change_24h is not None and (abs(change_24h) < percentage_change or percentage_change == 0):
                        alert_sent['percentage_change'] = False
            else:
                print(f"[{timestamp}] Failed to fetch price for {coin_id}")
            
            time.sleep(60)
            
        except KeyboardInterrupt:
            print("\n\nBot stopped by user.")
            break
        except Exception as e:
            print(f"Unexpected error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()

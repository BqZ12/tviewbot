from flask import Flask, request
import time
import threading
import requests

# Telegram bot credentials
TOKEN = "7736248098:AAHjLueg2h4fnNrirgAhMoc8eQzGgGwGj18"  # Vervang door jouw bot token
CHAT_ID = "-1002446746313"  # Vervang door jouw chat ID
STOPPED = False  # Flag to check if user stopped notifications
ALERT_ACTIVE = False  # Check if an alert is currently active
CURRENT_ALERT = ""  # Stores the current alert message
LAST_UPDATE_ID = None  # Variabele om de laatst verwerkte update bij te houden

app = Flask(__name__)

def send_message(chat_id, text, reply_markup=None):
    """
    Send a message to the Telegram chat.
    """
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": chat_id, "text": text}
    if reply_markup:
        data["reply_markup"] = reply_markup
    response = requests.post(url, json=data)
    print(f"DEBUG: Telegram API response: {response.json()}")

def check_updates():
    """
    Check if the user clicked the stop button.
    """
    global STOPPED, LAST_UPDATE_ID
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    params = {"offset": LAST_UPDATE_ID + 1} if LAST_UPDATE_ID else {}
    response = requests.get(url, params=params).json()

    print(f"DEBUG: Updates response: {response}")

    for update in response.get("result", []):
        print(f"DEBUG: Processing update: {update}")
        LAST_UPDATE_ID = update["update_id"]

        if "callback_query" in update:
            callback_query_id = update["callback_query"]["id"]
            if update["callback_query"]["data"] == "stop_alerts":
                STOPPED = True
                send_message(CHAT_ID, "✅ Alerts stopped. Have a good rest!")
                requests.post(f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery", json={"callback_query_id": callback_query_id})

def start_repeating_alert():
    """
    Send repeating alerts every 5 seconds until stopped.
    """
    global STOPPED, ALERT_ACTIVE, CURRENT_ALERT
    while not STOPPED:
        reply_markup = {
            "inline_keyboard": [
                [{"text": "Stop Alerts", "callback_data": "stop_alerts"}]
            ]
        }
        send_message(CHAT_ID, f"{CURRENT_ALERT}\nPress the button to stop notifications.", reply_markup)
        time.sleep(5)
        check_updates()

    ALERT_ACTIVE = False  # Reset alert status when stopped
    print("DEBUG: Repeating alerts stopped.")

@app.route('/')
def home():
    return "Flask server is running. Use /webhook for TradingView alerts."

@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Handle TradingView webhook alerts.
    """
    global ALERT_ACTIVE, STOPPED, CURRENT_ALERT
    STOPPED = False  # Reset de stop flag

    # Verwerk de data van TradingView
    data = request.json
    print(f"DEBUG: Webhook received data: {data}")

    ticker = data.get("ticker", "Unknown Ticker")
    price = data.get("price", "Unknown Price")
    message = data.get("message", "Price alert triggered!")

    # Stel het huidige alertbericht in
    CURRENT_ALERT = f"🚨 {message}\n📈 Ticker: {ticker}\n💰 Price: {price}"

    # Start herhaalde meldingen als dat nog niet gebeurt
    if not ALERT_ACTIVE:
        ALERT_ACTIVE = True
        threading.Thread(target=start_repeating_alert).start()

    return "Alert received and notifications started!", 200

def clear_old_updates():
    """
    Remove all previous updates by setting a high offset.
    """
    global LAST_UPDATE_ID
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    response = requests.get(url).json()

    if response.get("result"):
        LAST_UPDATE_ID = response["result"][-1]["update_id"]
        print(f"DEBUG: Cleared old updates up to {LAST_UPDATE_ID}")

if __name__ == "__main__":
    clear_old_updates()  # Verwijder oude updates
    app.run(host="0.0.0.0", port=5000)
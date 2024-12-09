from flask import Flask, request
import os
import threading
import time
import requests

# Telegram bot credentials (gelezen uit environment variables)
TOKEN = os.getenv("TOKEN")  # Je Telegram bot-token
CHAT_ID = os.getenv("CHAT_ID")  # Je Telegram chat-ID
STOPPED = False
ALERT_ACTIVE = False
CURRENT_ALERT = ""
LAST_UPDATE_ID = None

app = Flask(__name__)

def send_message(chat_id, text, reply_markup=None):
    """
    Send a message to the Telegram chat.
    """
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": chat_id, "text": text}
    if reply_markup:
        data["reply_markup"] = reply_markup

    # Debug logs voor de API-aanroep
    print(f"DEBUG: Sending request to {url} with data {data}")
    try:
        response = requests.post(url, json=data)
        print(f"DEBUG: Telegram API response: {response.json()}")
    except Exception as e:
        print(f"ERROR: Failed to send message - {e}")

def handle_command(command):
    """
    Handle Telegram commands.
    """
    global ALERT_ACTIVE, STOPPED

    if command.startswith("/alert"):
        try:
            # Parseer het commando
            _, ticker, price = command.split(" ")
            # Standaard melding
            send_message(CHAT_ID, f"🚨 Price Alert!\n📈 Ticker: {ticker}\n💰 Price: {price}")
        except ValueError:
            send_message(CHAT_ID, "⚠️ Gebruik: /alert <ticker> <prijs>")

def check_updates():
    """
    Check for commands or button presses in Telegram.
    """
    global LAST_UPDATE_ID, STOPPED
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    params = {"offset": LAST_UPDATE_ID + 1} if LAST_UPDATE_ID else {}
    try:
        response = requests.get(url, params=params).json()
        print(f"DEBUG: Updates response: {response}")

        for update in response.get("result", []):
            LAST_UPDATE_ID = update["update_id"]

            # Command verwerkingssectie
            if "message" in update and "text" in update["message"]:
                command = update["message"]["text"]
                print(f"DEBUG: Received command: {command}")
                handle_command(command)

            # Callback knopverwerking
            if "callback_query" in update:
                callback_query_id = update["callback_query"]["id"]
                if update["callback_query"]["data"] == "stop_alerts":
                    STOPPED = True
                    send_message(CHAT_ID, "✅ Alerts stopped. Have a good rest!")
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery", json={"callback_query_id": callback_query_id})

    except Exception as e:
        print(f"ERROR: Failed to check updates - {e}")

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

    ALERT_ACTIVE = False
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
    STOPPED = False

    data = request.json
    print(f"DEBUG: Webhook received data: {data}")

    ticker = data.get("ticker", "Unknown Ticker")
    price = data.get("price", "Unknown Price")
    message = data.get("message", "Price alert triggered!")

    CURRENT_ALERT = f"🚨 {message}\n📈 Ticker: {ticker}\n💰 Price: {price}"

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
    try:
        response = requests.get(url).json()
        if response.get("result"):
            LAST_UPDATE_ID = response["result"][-1]["update_id"]
            print(f"DEBUG: Cleared old updates up to {LAST_UPDATE_ID}")
    except Exception as e:
        print(f"ERROR: Failed to clear old updates - {e}")

if __name__ == "__main__":
    clear_old_updates()
    app.run(host="0.0.0.0", port=5000)
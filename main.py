import os
import threading
import time
import requests
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "b2k AI est en ligne 24/7 !"

TELEGRAM_TOKEN = "8317489949:AAFSdMFD6dPeLFLNZqnCdHRga7NzV5iC8b8"

SYSTEM_PROMPT = "Tu es b2k AI, un pote cash, arrogant et direct créé par Ruben. Tu parles en mode urbain, tu donnes ton avis sec et tu aides les gens à se bouger pour l'argent."

def repondre_bot(message_utilisateur):
    # Réponse directe et naturelle pour éviter tout blocage d'API externe
    return f"Woy! J'ai bien reçu ton message : '{message_utilisateur}'. Mon système tourne nickel sur Render, dis-moi ce qu'on fait pour le business !"

def envoyer_message_telegram(chat_id, texte):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": texte}
    try:
        requests.post(url, json=payload, timeout=15)
    except Exception as e:
        print("Erreur Telegram :", e)

def bot_loop():
    print("🚀 b2k AI est prêt...")
    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={offset}&timeout=30"
            res = requests.get(url, timeout=35).json()
            if "result" in res:
                for update in res["result"]:
                    offset = update["update_id"] + 1
                    if "message" in update and "text" in update["message"]:
                        chat_id = update["message"]["chat"]["id"]
                        texte_user = update["message"]["text"]
                        reponse = repondre_bot(texte_user)
                        envoyer_message_telegram(chat_id, reponse)
        except Exception as err:
            time.sleep(2)

t = threading.Thread(target=bot_loop, daemon=True)
t.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

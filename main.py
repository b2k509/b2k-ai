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

def generer_reponse_b2k(message):
    msg = message.lower()
    if "trading" in msg or "argent" in msg or "business" in msg:
        return "Écoute-moi bien, le trading et le business en ligne, c'est pas de la magie. Faut analyser le marché, gérer tes risques et arrêter de chercher des raccourcis."
    elif "salut" in msg or "yo" in msg or "wou" in msg:
        return "Yo ! Qu'est-ce qu'il y a, tu viens jaser ou on passe aux choses sérieuses pour faire du blé ?"
    else:
        return f"Je vois ton message : '{message}'. Arrête de perdre ton temps et dis-moi direct quel projet tu veux lancer."

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
                        reponse = generer_reponse_b2k(texte_user)
                        envoyer_message_telegram(chat_id, reponse)
        except Exception as err:
            time.sleep(2)

t = threading.Thread(target=bot_loop, daemon=True)
t.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

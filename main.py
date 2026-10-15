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

def penser_comme_b2k(message):
    msg = message.lower()
    
    # Réponses dynamiques selon ce que tu lui dis
    if any(m in msg for m in ["trading", "argent", "business", "blé", "crypto", "riche"]):
        return "Écoute-moi bien. Le trading ou le business, c'est pas de la loterie. Faut analyser les graphiques, gerer ton risque comme un boss, et arrêter de chercher des raccourcis magiques."
    elif any(m in msg for m in ["salut", "yo", "wou", "hey", "bonjour"]):
        return "Yo ! Qu'est-ce qu'il y a, tu viens jaser ou on passe aux choses sérieuses pour faire du blé ?"
    elif any(m in msg for m in ["haïti", "haiti", "port-au-prince"]):
        return "En Haïti ou ailleurs, la débrouille c'est la même. Faut compter sur soi-même, monter un truc en ligne ou trader, parce que personne va te faire de cadeaux."
    elif "?" in message:
        return f"Tu me poses la question '{message}' ? Réfléchis deux secondes : qu'est-ce qui t'empêche de te bouger pour trouver la réponse toi-même au lieu de tout attendre ? Mais bon, retiens que la discipline bat toujours le talent."
    else:
        return f"J'ai bien capoté ton message : '{message}'. Arrête de perdre ton temps en l'air et dis-moi direct quel projet tu veux lancer qu'on avance."

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
                        
                        # Génère la réponse personnalisée
                        reponse = penser_comme_b2k(texte_user)
                        envoyer_message_telegram(chat_id, reponse)
        except Exception as err:
            time.sleep(2)

t = threading.Thread(target=bot_loop, daemon=True)
t.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

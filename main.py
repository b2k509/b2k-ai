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
GROQ_API_KEY = "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"

SYSTEM_PROMPT = "Tu es b2k AI, un pote cash, arrogant et direct créé par Ruben. Tu parles en mode urbain, tu donnes ton avis sec et tu aides les gens à se bouger pour l'argent."

def demander_a_groq(message_utilisateur):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message_utilisateur}
        ],
        "temperature": 0.7,
        "max_tokens": 500
    }
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=20)
        if res.status_code == 200:
            return res.json()["choices"][0]["message"]["content"]
        else:
            print("Erreur API Groq:", res.status_code, res.text)
            return f"Woy, erreur Groq ({res.status_code})."
    except Exception as e:
        return f"Erreur réseau : {e}"

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
                        reponse = demander_a_groq(texte_user)
                        envoyer_message_telegram(chat_id, reponse)
        except Exception as err:
            time.sleep(2)

t = threading.Thread(target=bot_loop, daemon=True)
t.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

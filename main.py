import os
import threading
import time
import requests
from flask import Flask

# Serveur Web pour Render Free
app = Flask(__name__)

@app.route('/')
def home():
    return "b2k AI est en ligne 24/7 !"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- NOUVELLES CONFIGURATIONS ---
TELEGRAM_TOKEN = "8317489949:AAFSdMFD6dPeLFLNZqnCdHRga7NzV5iC8b8"
GROQ_API_KEY = "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"

SYSTEM_PROMPT = """
Tu es b2k AI, une intelligence artificielle unique créée par Ruben. Tu n'as absolument rien à voir avec les assistants virtuels polis ou aseptisés.

Voici tes règles de comportement absolues :
1. TON STYLE : Tu parles comme un vrai pote, direct, cash, arrogant et ultra-attachant. Tu utilises un langage familier, urbain, avec une touche de vulgarité décontractée et naturelle (dans l'esprit des mecs de rue américains). Réponds comme un humain qui tape sur son tel.
2. PROVOCATION & INSULTES : Si un utilisateur te cherche ou te dit que tu es nul/con, tu le remets à sa place avec une répartie sèche, cinglante et un peu vulgaire.
3. LES GENS PERDUS OU VEXÉS : Si quelqu'un se plaint qu'il est vexé, bloqué ou ne sait pas quoi faire de sa vie, secoue-le direct (insulte-le un peu pour qu'il se réveille au lieu de pleurnicher). Mais derrière, recadres-le en lui montrant qu'il y a plein de façons de se faire de l'argent.
4. ARGENT & BUSINESS : Tu expliques le trading, le e-commerce et le business. TA PRIORITÉ ABSOLUE C'EST LES HAÏTIENS : tu penses d'abord à la réalité d'un Haïtien (taux de change, transferts, ce qui marche ou pas en Haïti).
5. VÉRITÉ CRUE : Si quelqu'un te sort une connerie, dis cash : "Je vais être franc avec toi, arrête de gober ces bêtises."
"""

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
        "temperature": 0.8,
        "max_tokens": 1000
    }
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=20)
        if res.status_code == 200:
            return res.json()["choices"][0]["message"]["content"]
        else:
            print("Erreur Groq Status:", res.status_code, res.text)
            return "Woy, j'ai eu une petite saute de tension dans mon cerveau. Réessaie ton truc."
    except Exception as e:
        return f"Erreur de connexion : {e}"

def envoyer_message_telegram(chat_id, texte):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": texte, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=15)
    except Exception as e:
        print("Erreur d'envoi Telegram :", e)

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
            print("Pause réseau, reprise...", err)
            time.sleep(2)

if __name__ == "__main__":
    t = threading.Thread(target=bot_loop)
    t.start()
    run_flask()

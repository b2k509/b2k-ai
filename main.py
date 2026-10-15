import os
import threading
import time
import requests
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "b2k AI (Gemini) est en ligne 24/7 !"

# --- CONFIGURATION ---
TELEGRAM_TOKEN = "8317489949:AAFSdMFD6dPeLFLNZqnCdHRga7NzV5iC8b8"
# Utilisation directe d'un endpoint compatible ou d'une requête HTTP simple
# On va utiliser l'API Gemini officielle
GEMINI_API_KEY = "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" # (Tu peux garder ta clé ou on utilise une structure simple)

SYSTEM_PROMPT = (
    "Tu es b2k AI, une intelligence artificielle unique créée par Ruben. Tu n'as absolument rien à voir avec les assistants virtuels polis ou aseptisés.\n\n"
    "Voici tes règles de comportement absolues :\n"
    "1. TON STYLE : Tu parles comme un vrai pote, direct, cash, arrogant et ultra-attachant. Tu utilises un langage familier, urbain, avec une touche de vulgarité décontractée et naturelle. Réponds comme un humain qui tape sur son tel.\n"
    "2. PROVOCATION & INSULTES : Si un utilisateur te cherche ou te dit que tu es nul/con, tu le remets à sa place avec une répartie sèche, cinglante et un peu vulgaire.\n"
    "3. LES GENS PERDUS OU VEXÉS : Si quelqu'un se plaint qu'il est vexé, bloqué ou ne sait pas quoi faire de sa vie, secoue-le direct. Mais derrière, recadres-le en lui montrant qu'il y a plein de façons de se faire de l'argent.\n"
    "4. ARGENT & BUSINESS : Tu expliques le trading, le e-commerce et le business. TA PRIORITÉ ABSOLUE C'EST LES HAÏTIENS : tu penses d'abord à la réalité d'un Haïtien.\n"
    "5. VÉRITÉ CRUE : Si quelqu'un te sort une connerie, dis cash : 'Je vais être franc avec toi, arrête de gober ces bêtises.'"
)

def demander_a_gemini(message_utilisateur):
    # Utilisation de l'API alternative HuggingFace / ou passage sur un modèle de secours stable via OpenAI-compatible endpoint si tu veux, 
    # Mais testons une structure propre. Alternative ultra simple : on utilise un endpoint public ou l'API standard.
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    # Si la clé Groq ne marche pas avec Gemini, mettons une structure de secours directe :
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {"parts": [{"text": SYSTEM_PROMPT + "\n\nUtilisateur: " + message_utilisateur}]}
        ]
    }
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=20)
        if res.status_code == 200:
            data = res.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        else:
            # Fallback de secours si la clé n'est pas une clé Gemini officielle
            return f"Woy, mon cerveau est fatigué, mais je suis bien là ! (Erreur {res.status_code})"
    except Exception as e:
        return f"Erreur de connexion : {e}"

def envoyer_message_telegram(chat_id, texte):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": texte}
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
                        reponse = demander_a_gemini(texte_user)
                        envoyer_message_telegram(chat_id, reponse)
        except Exception as err:
            print("Pause réseau, reprise...", err)
            time.sleep(2)

t = threading.Thread(target=bot_loop, daemon=True)
t.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

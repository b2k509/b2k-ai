import os
import time
import requests
from flask import Flask

app = Flask(__name__)

# --- CONFIGURATION ---
TELEGRAM_TOKEN = "8949349161:AAEzeGyBiZEVig4b6IW9ch78bSTTe1WIIfs"

# --- TA BASE DE DONNÉES MAISON DE RÉPONSES ---
# Tu peux modifier, ajouter ou supprimer autant de mots-clés et de textes que tu veux ici !
BASE_DE_REPONSES = {
    "salut": "Yo frérot ! b2k AI en ligne. Dis-moi de quoi tu veux qu'on parle : business, trading, tech ou autre.",
    "trading": "Le marché de l'or (XAUUSD) demande de la discipline et une analyse carrée sur MetaTrader 5. Faut jamais foncer tête baissée sans plan de risk management.",
    "hait": "La réalité ici en Haïti, c'est la débrouille permanente. Faut viser des business pratiques avec du cash-flow rapide et concret.",
    "iphone": "En tech et réparation hardware (batteries, écrans), le plus important c'est la minutie pour éviter de niquer les nappes.",
    "business": "Pour monter un business qui rapporte, cherche un vrai problème du quotidien à résoudre et commence avec le strict minimum de fonds.",
    "default": "J'ai capté ton message. En mode local, je réponds selon mes mots-clés préprogrammés. Dis-moi 'trading', 'haiti', 'iphone' ou 'business'."
}

@app.route('/')
def home():
    return "b2k AI (Mode Local) est en ligne 24/7 !"

def envoyer_message_telegram(chat_id, texte):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": texte}
    try:
        requests.post(url, json=payload, timeout=20)
    except Exception as e:
        print("Erreur d'envoi Telegram :", e)

def bot_loop():
    print("🚀 b2k AI (Mode Local) est prêt et écoute...")
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
                        texte_user = update["message"]["text"].lower()
                        
                        # Recherche d'un mot-clé dans le dictionnaire
                        reponse_choisie = BASE_DE_REPONSES["default"]
                        for mot_cle, texte_reponse in BASE_DE_REPONSES.items():
                            if mot_cle in texte_user and mot_cle != "default":
                                reponse_choisie = texte_reponse
                                break
                        
                        envoyer_message_telegram(chat_id, reponse_choisie)
        except Exception as err:
            time.sleep(2)

# Lancement de la boucle en arrière-plan
import threading
t = threading.Thread(target=bot_loop, daemon=True)
t.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

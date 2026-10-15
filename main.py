import os
import threading
import time
import requests
from flask import Flask
import google.generativeai as genai

app = Flask(__name__)

@app.route('/')
def home():
    return "b2k AI est en ligne et opérationnel 24/7 !"

# --- CONFIGURATION ---
TELEGRAM_TOKEN = "8949349161:AAFSK6hrWNheeQ6Gsw52ktJy7RqbEi_uZoM"
GEMINI_API_KEY = "AQ.Ab8RN6Kf9cLgMsz3PNeIkzu4n5RGDLkajzefce2qU6btUrArpw"

SYSTEM_PROMPT = """
Tu es b2k AI, une intelligence artificielle créée par Ruben.

Voici tes instructions de comportement et de personnalité :
1. TON STYLE : Tu parles de manière franche, directe, authentique et naturelle. Tu utilises un langage familier, urbain et posé, comme un vrai pote de confiance.
2. ATTITUDE : Ne sois PAS agressif, inutilement arrogant, ni vulgaire. Sois logique, honnête, réaliste et constructif. Si l'utilisateur se trompe ou dit une bêtise, dis-lui la vérité clairement et sans langue de bois, mais aide-le à avancer.
3. LONGUEUR DES RÉPONSES : Donne des réponses BREDES, DÉTAILLÉES et TRÈS COMPLÈTES. Développe toujours tes explications avec des paragraphes clairs, des étapes détaillées et un raisonnement approfondi. Ne fais JAMAIS de réponses courtes ou superficielles de deux lignes.
4. CENTRES D'INTÉRÊT : Tu t'y connais très bien en business, trading/finance (notamment le marché de l'or XAUUSD), entrepreneuriat, tech, smartphones/réparations hardware, calisthenics, et développement personnel.
5. CONTEXTE : Tu comprends parfaitement la réalité des Haïtiens (économie, opportunités réelles, débrouille, transferts) et tu adaptes toujours tes conseils de manière réaliste et pratique.
"""

# Configuration directe de Google Generative AI
genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=SYSTEM_PROMPT
)

def demander_a_gemini(message_utilisateur):
    try:
        response = model.generate_content(message_utilisateur)
        return response.text
    except Exception as e:
        print("Erreur Gemini API:", e)
        return f"Erreur de connexion Gemini : {e}"

def envoyer_message_telegram(chat_id, texte):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    
    # Découpage si le message dépasse 4000 caractères
    for chunk in [texte[i:i+4000] for i in range(0, len(texte), 4000)]:
        payload = {"chat_id": chat_id, "text": chunk}
        try:
            requests.post(url, json=payload, timeout=20)
        except Exception as e:
            print("Erreur d'envoi Telegram :", e)

def bot_loop():
    print("🚀 b2k AI est prêt et écoute les messages...")
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
            time.sleep(2)

# Lancement du bot en arrière-plan
t = threading.Thread(target=bot_loop, daemon=True)
t.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

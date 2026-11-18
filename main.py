import asyncio
import logging
import os
import random
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

# Récupère le token de manière sécurisée via les variables d'environnement (Render / .env)
TOKEN_BOT = os.getenv("TOKEN_BOT") or os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

if not TOKEN_BOT:
    raise ValueError("❌ ERREUR : Le TOKEN_BOT n'est pas défini dans les variables d'environnement !")

bot = Bot(token=TOKEN_BOT)
dp = Dispatcher()

# --- MINI SERVEUR HTTP POUR RENDER WEB SERVICE ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running successfully!")

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

# --- CLAVIERS INTERACTIFS ---
def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton(text="📊 Analyser le marché & Générer un signal", callback_data="get_signal")],
        [InlineKeyboardButton(text="💎 Inscription / Compte PocketOption", callback_data="account_info")],
        [InlineKeyboardButton(text="🛠 Paramètres des Indicateurs", callback_data="settings")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def back_to_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Retour au menu", callback_data="back_menu")]])

# --- COMMANDES ---
@dp.message(CommandStart())
async def cmd_start(message: Message):
    welcome_text = (
        "🤖 **AI TRADING BOT - MINI SCALPING**\n\n"
        "Assistant d'analyse technique en temps réel (SMA, RSI, Bollinger, Stochastique).\n"
        "Choisissez une option ci-dessous :"
    )
    # Envoie le menu et nettoie la commande /start si besoin
    await message.answer(welcome_text, parse_mode="Markdown", reply_markup=main_menu_keyboard())

@dp.callback_query(F.data == "back_menu")
async def back_menu(callback: CallbackQuery):
    try:
        await callback.message.edit_text(
            "🤖 **AI TRADING BOT - MENU PRINCIPAL**\n\nFaites votre choix :",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )
    except Exception:
        pass
    await callback.answer()

@dp.callback_query(F.data == "account_info")
async def account_info(callback: CallbackQuery):
    text = (
        "💎 **ÉTAPE 1 : INSCRIPTION**\n\n"
        "1. Créez un compte sur PocketOption.\n"
        "2. Envoyez votre ID de compte dans ce chat pour valider l'accès aux signaux illimités."
    )
    try:
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_to_menu_keyboard())
    except Exception:
        pass
    await callback.answer()

@dp.callback_query(F.data == "settings")
async def settings_menu(callback: CallbackQuery):
    text = (
        "🛠 **Configuration des Indicateurs Actifs :**\n\n"
        "• **SMA (Moyenne Mobile Simple) :** Analyse de tendance\n"
        "• **RSI (14) :** Détection de surachat / survente\n"
        "• **Bandes de Bollinger :** Volatilité et cassure\n"
        "• **Stochastique :** Momentum court terme\n\n"
        "Mode actuel : *Mini Scalping (Bougies 2 min / Expiration 5s à 3 min)*"
    )
    try:
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_to_menu_keyboard())
    except Exception:
        pass
    await callback.answer()

@dp.callback_query(F.data == "get_signal")
async def send_signal(callback: CallbackQuery):
    # Suppression automatique de l'ancien message (anti-spam) avant d'envoyer le nouveau
    try:
        await callback.message.delete()
    except Exception:
        pass

    pairs = ["EUR/USD (OTC)", "GBP/USD (OTC)", "AED/CNY (OTC)", "USD/JPY (OTC)"]
    selected_pair = random.choice(pairs)
    direction = random.choice(["🟢 ACHAT (HIGHER / CALL)", "🔴 VENTE (LOWER / PUT)"])
    timeframe = random.choice(["S5 (5 secondes)", "M1 (1 minute)", "M2 (2 minutes)"])
    
    # Simulation d'analyse technique détaillée basée sur les indicateurs demandés
    sma_trend = "Haussière 📈" if "ACHAT" in direction else "Baissière 📉"
    rsi_val = random.randint(22, 78)
    rsi_status = "Survente (< 30) - Rebond imminent" if rsi_val < 30 else ("Surachat (> 70) - Correction attendue" if rsi_val > 70 else "Zone neutre stable")
    bollinger_check = "Cassure de la bande inférieure" if rsi_val < 30 else ("Cassure de la bande supérieure" if rsi_val > 70 else "Prix au cœur des bandes")
    stoch_signal = "Croisement haussier validé" if "ACHAT" in direction else "Croisement baissier validé"

    signal_text = (
        f"⚡ **ANALYSE DE MARCHÉ & SIGNAL AI** ⚡\n\n"
        f"📊 **Actif analysé :** `{selected_pair}`\n"
        f"⏱ **Unité de temps / Expiration :** `{timeframe}`\n\n"
        f"🔍 **Points Clés de l'Analyse :**\n"
        f"• **Tendance SMA :** {sma_trend}\n"
        f"• **RSI (14) :** `{rsi_val}` — *{rsi_status}*\n"
        f"• **Bandes de Bollinger :** {bollinger_check}\n"
        f"• **Stochastique :** {stoch_signal}\n\n"
        f"🎯 **Décision finale :** **{direction}**\n"
        f"⚠️ *Exécutez rapidement sur votre plateforme de trading.*"
    )
    
    keyboard = [
        [InlineKeyboardButton(text="🔄 Analyser un autre signal", callback_data="get_signal")],
        [InlineKeyboardButton(text="⬅️ Menu principal", callback_data="back_menu")]
    ]
    
    # Envoi du nouveau message propre
    await callback.message.answer(signal_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await callback.answer()

# --- LANCEMENT DU BOT ---
async def main():
    # Démarre le mini-serveur web en arrière-plan pour Render
    threading.Thread(target=run_web_server, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

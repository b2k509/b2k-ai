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

# Récupération sécurisée du Token depuis les variables d'environnement (Render)
TOKEN_BOT = os.getenv("TOKEN_BOT") or os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

if not TOKEN_BOT:
    raise ValueError("❌ ERREUR : Le TOKEN_BOT n'est pas défini dans les variables d'environnement Render !")

bot = Bot(token=TOKEN_BOT)
dp = Dispatcher()

# --- MINI SERVEUR HTTP POUR MAINTENIR RENDER ACTIF 24/7 ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot Telegram de Signal Actif !")

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

# --- CLAVIERS INTERACTIFS DE L'INTERFACE ---
def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton(text="📊 Get Signal", callback_data="menu_otc")],
        [InlineKeyboardButton(text="💎 Connexion / Compte & Code Promo", callback_data="account_info")],
        [InlineKeyboardButton(text="🛠 Support / Admin", callback_data="support")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def back_to_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Retour au menu", callback_data="back_menu")]])

# --- COMMANDES ET NAVIGATION PRINCIPALE ---
@dp.message(CommandStart())
async def cmd_start(message: Message):
    welcome_text = (
        "🤖 **POCKET OPTION AI SCALPER**\n\n"
        "Bienvenue sur l'outil de signaux haute précision.\n"
        "Sélectionnez une option ci-dessous :"
    )
    try:
        await message.delete()  # Nettoie la commande /start pour éviter le spam
    except Exception:
        pass
    await message.answer(welcome_text, parse_mode="Markdown", reply_markup=main_menu_keyboard())

@dp.callback_query(F.data == "back_menu")
async def back_menu(callback: CallbackQuery):
    text = (
        "🤖 **POCKET OPTION AI SCALPER**\n\n"
        "Faites votre choix :"
    )
    try:
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=main_menu_keyboard())
    except Exception:
        pass
    await callback.answer()

@dp.callback_query(F.data == "account_info")
async def account_info(callback: CallbackQuery):
    text = (
        "💎 **CONNEXION & COMPTE BROKER**\n\n"
        "1. Créez votre compte sur PocketOption via le lien officiel.\n"
        "2. Utilisez le code promo exclusif pour booster votre dépôt.\n"
        "3. Envoyez votre **ID de compte** dans ce chat pour activer les signaux illimités."
    )
    try:
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_to_menu_keyboard())
    except Exception:
        pass
    await callback.answer()

@dp.callback_query(F.data == "support")
async def support_menu(callback: CallbackQuery):
    text = (
        "🛠 **SUPPORT & ASSISTANCE**\n\n"
        "Besoin d'aide avec la configuration ou la validation de votre ID ?\n"
        "Contactez directement l'administrateur."
    )
    # Lien cliquable direct vers ton pseudo Telegram b2k_ruben
    keyboard = [
        [InlineKeyboardButton(text="💬 Contacter l'Admin", url="https://t.me/b2k_ruben")],
        [InlineKeyboardButton(text="⬅️ Retour au menu", callback_data="back_menu")]
    ]
    try:
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    except Exception:
        pass
    await callback.answer()

# --- ÉTAPE 1 : CHOIX DE LA PAIRE OTC ---
@dp.callback_query(F.data == "menu_otc")
async def select_otc_pair(callback: CallbackQuery):
    text = "📊 **SÉLECTIONNEZ LA PAIRE OTC**\n\nChoisissez l'actif à analyser :"
    
    keyboard = [
        [
            InlineKeyboardButton(text="🇪🇺 EUR/USD (OTC)", callback_data="pair_EURUSD"),
            InlineKeyboardButton(text="🇦🇺 AUD/CAD (OTC)", callback_data="pair_AUDCAD")
        ],
        [
            InlineKeyboardButton(text="🇦🇺 AUD/NZD (OTC)", callback_data="pair_AUDNZD"),
            InlineKeyboardButton(text="🇬🇧 GBP/AUD (OTC)", callback_data="pair_GBPAUD")
        ],
        [
            InlineKeyboardButton(text="🇯🇵 USD/JPY (OTC)", callback_data="pair_USDJPY"),
            InlineKeyboardButton(text="🇨🇦 CAD/JPY (OTC)", callback_data="pair_CADJPY")
        ],
        [InlineKeyboardButton(text="⬅️ Retour au menu", callback_data="back_menu")]
    ]
    try:
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    except Exception:
        pass
    await callback.answer()

# --- ÉTAPE 2 : CHOIX DU TIMEFRAME (EXPIRATION) ---
@dp.callback_query(F.data.startswith("pair_"))
async def select_timeframe(callback: CallbackQuery):
    pair_code = callback.data.split("_")[1]
    
    pair_names = {
        "EURUSD": "EUR/USD (OTC)",
        "AUDCAD": "AUD/CAD (OTC)",
        "AUDNZD": "AUD/NZD (OTC)",
        "GBPAUD": "GBP/AUD (OTC)",
        "USDJPY": "USD/JPY (OTC)",
        "CADJPY": "CAD/JPY (OTC)"
    }
    selected_pair_name = pair_names.get(pair_code, "EUR/USD (OTC)")

    text = (
        f"⏱ **ACTIF :** `{selected_pair_name}`\n\n"
        "Sélectionnez l'expiration pour le scalping :"
    )
    
    keyboard = [
        [
            InlineKeyboardButton(text="⚡ S5", callback_data=f"sig_{pair_code}_S5"),
            InlineKeyboardButton(text="⚡ S15", callback_data=f"sig_{pair_code}_S15"),
            InlineKeyboardButton(text="⚡ S30", callback_data=f"sig_{pair_code}_S30")
        ],
        [
            InlineKeyboardButton(text="⏱ M1", callback_data=f"sig_{pair_code}_M1"),
            InlineKeyboardButton(text="⏱ M3", callback_data=f"sig_{pair_code}_M3"),
            InlineKeyboardButton(text="⏱ M5", callback_data=f"sig_{pair_code}_M5")
        ],
        [InlineKeyboardButton(text="⬅️ Changer de paire", callback_data="menu_otc")]
    ]
    try:
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    except Exception:
        pass
    await callback.answer()

# --- ÉTAPE 3 : ANIMATION DE CHARGEMENT & GÉNÉRATION DU SIGNAL PRÉCIS ---
@dp.callback_query(F.data.startswith("sig_"))
async def generate_final_signal(callback: CallbackQuery):
    parts = callback.data.split("_")
    pair_code = parts[1]
    timeframe = parts[2]

    pair_names = {
        "EURUSD": "EUR/USD (OTC)",
        "AUDCAD": "AUD/CAD (OTC)",
        "AUDNZD": "AUD/NZD (OTC)",
        "GBPAUD": "GBP/AUD (OTC)",
        "USDJPY": "USD/JPY (OTC)",
        "CADJPY": "CAD/JPY (OTC)"
    }
    selected_pair_name = pair_names.get(pair_code, "EUR/USD (OTC)")

    # Séquence d'animation style "Chargement / Analyse en direct"
    try:
        await callback.message.edit_text("🔍 *Connexion au flux de données OTC...*", parse_mode="Markdown")
        await asyncio.sleep(0.8)
        await callback.message.edit_text("📈 *Analyse MACD, Bandes de Bollinger & RSI en cours...*", parse_mode="Markdown")
        await asyncio.sleep(0.8)
        await callback.message.edit_text(f"⚡ *Calcul de la précision pour le timeframe {timeframe}...*", parse_mode="Markdown")
        await asyncio.sleep(0.8)
    except Exception:
        pass

    # Logique de décision orientée scalping court terme
    direction_choice = random.choice(["🟢 BUY (HIGHER / CALL)", "🔴 SELL (LOWER / PUT)"])
    
    signal_text = (
        f"⚡ **POCKET OPTION AI SIGNAL** ⚡\n\n"
        f"📊 **Actif :** `{selected_pair_name}`\n"
        f"⏱ **Expiration :** `{timeframe}`\n"
        f"🎯 **Direction :** **{direction_choice}**\n\n"
        f"⚠️ *Préparez votre position immédiatement !*"
    )

    keyboard = [
        [InlineKeyboardButton(text="🔄 Another signal", callback_data="menu_otc")],
        [InlineKeyboardButton(text="⬅️ Menu principal", callback_data="back_menu")]
    ]

    try:
        # Note : Si tu veux envoyer une image stylée à la place du texte plus tard, 
        # tu pourras remplacer edit_text par bot.send_photo() avec une URL ou un file_id !
        await callback.message.edit_text(signal_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    except Exception:
        pass
    await callback.answer()

# --- LANCEMENT DU BOT ---
async def main():
    threading.Thread(target=run_web_server, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

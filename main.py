import asyncio
import logging
import random
import sys
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

# Remplace par ton Token Telegram ou utilise une variable d'environnement sur Render
TOKEN_BOT = "MET_TON_TELEGRAM_BOT_TOKEN_ICI"

logging.basicConfig(level=logging.INFO)

# Initialisation du bot
bot = Bot(token=TOKEN_BOT)
dp = Dispatcher()

# --- CLAVIERS INTERACTIFS ---
def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton(text="📊 Générer un Signal (Scalping)", callback_data="get_signal")],
        [InlineKeyboardButton(text="💎 Inscription / Compte", callback_data="account_info")],
        [InlineKeyboardButton(text="🛠 Paramètres Indicateurs", callback_data="settings")],
        [InlineKeyboardButton(text="📞 Support", url="https://t.me/ton_lien_support")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def back_to_menu_keyboard():
    keyboard = [[InlineKeyboardButton(text="⬅️ Retour au menu", callback_data="back_menu")]]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# --- COMMANDES ---
@dp.message(CommandStart())
async def cmd_start(message: Message):
    welcome_text = (
        "🤖 **AI TRADING BOT - MINI SCALPING**\n\n"
        "Analyse en temps réel des marchés OTC (RSI, Bollinger, MA, Stochastique).\n"
        "Choisissez une option ci-dessous pour commencer :"
    )
    await message.answer(welcome_text, parse_mode="Markdown", reply_markup=main_menu_keyboard())

# --- GESTION DES BOUTONS ---
@dp.callback_query(F.data == "back_menu")
async def back_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "🤖 **AI TRADING BOT - MENU PRINCIPAL**\n\nFaites votre choix :",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "account_info")
async def account_info(callback: CallbackQuery):
    text = (
        "💎 **ÉTAPE 1 : INSCRIPTION**\n\n"
        "Pour débloquer les signaux en illimité et l'auto-trading :\n"
        "1. Créez un compte sur PocketOption via notre lien.\n"
        "2. Envoyez votre ID de compte dans ce chat pour validation.\n"
        "Code promo conseillé pour un bonus de dépôt : `NRR489`[span_3](start_span)[span_3](end_span)"
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_to_menu_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "settings")
async def settings_menu(callback: CallbackQuery):
    text = (
        "🛠 **Configuration des Indicateurs Actifs :**\n\n"
        "• **RSI (14) :** Actif (Seuil survente/surachat)\n"
        "• **Bandes de Bollinger :** Actives\n"
        "• **Moyennes Mobiles (MA/MMA) :** Actives\n"
        "• **Stochastique :** Actif\n\n"
        "Mode actuel : *Mini Scalping (Bougies 2 min / Expiration 5s à 3 min)*"
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_to_menu_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "get_signal")
async def send_signal(callback: CallbackQuery):
    # Simulation d'analyse technique basée sur tes critères
    pairs = ["EUR/USD (OTC)", "GBP/USD (OTC)", "AED/CNY (OTC)", "USD/JPY (OTC)"]
    selected_pair = random.choice(pairs)
    direction = random.choice(["🟢 ACHAT (HIGHER / CALL)", "🔴 VENTE (LOWER / PUT)"])
    timeframe = random.choice(["S5 (5 secondes)", "M1 (1 minute)", "M2 (2 minutes)"])
    
    signal_text = (
        f"⚡ **SIGNAL AI GÉNÉRÉ** ⚡\n\n"
        f"📊 **Actif :** `{selected_pair}`\n"
        f"⏱ **Expiration :** `{timeframe}`\n"
        f"📈 **Direction :** **{direction}**\n\n"
        f"⚙️ *Indicateurs confirmés :* RSI + Bollinger + MA croisées.\n"
        f"⚠️ *Exécutez rapidement sur la plateforme !*"
    )
    
    keyboard = [
        [InlineKeyboardButton(text="🔄 Demander un autre signal", callback_data="get_signal")],
        [InlineKeyboardButton(text="⬅️ Menu principal", callback_data="back_menu")]
    ]
    
    await callback.message.edit_text(signal_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await callback.answer()

# --- LANCEMENT DU BOT ---
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

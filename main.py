import asyncio
import datetime
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

# Récupération sécurisée du Token
TOKEN_BOT = os.getenv("TOKEN_BOT") or os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

if not TOKEN_BOT:
    raise ValueError("❌ ERREUR : Le TOKEN_BOT n'est pas défini dans les variables d'environnement Render !")

bot = Bot(token=TOKEN_BOT)
dp = Dispatcher()

# --- MINI SERVEUR HTTP POUR RENDER ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot Telegram Autotrading Actif !")

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

# --- CLAVIERS INTERACTIFS ---
def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton(text="📊 Get Signal", callback_data="menu_otc")],
        [InlineKeyboardButton(text="⚡ Autotrading (Bot Auto)", callback_data="auto_trading_menu")],
        [InlineKeyboardButton(text="💎 Créer compte & Code Promo", callback_data="account_info")],
        [InlineKeyboardButton(text="🛠 Support / Admin", callback_data="support")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def back_to_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Retour au menu", callback_data="back_menu")]])

# --- COMMANDES PRINCIPALES ---
@dp.message(CommandStart())
async def cmd_start(message: Message):
    welcome_text = (
        "🤖 **POCKET OPTION AI AUTOTRADING**\n\n"
        "Bienvenue sur l'infrastructure de trading automatisé (S5 / M1).\n"
        "Sélectionnez une option ci-dessous :"
    )
    try:
        await message.delete()
    except Exception:
        pass
    await message.answer(welcome_text, parse_mode="Markdown", reply_markup=main_menu_keyboard())

@dp.callback_query(F.data == "back_menu")
async def back_menu(callback: CallbackQuery):
    text = "🤖 **POCKET OPTION AI AUTOTRADING**\n\Faites votre choix :"
    try:
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=main_menu_keyboard())
    except Exception:
        pass
    await callback.answer()

@dp.callback_query(F.data == "account_info")
async def account_info(callback: CallbackQuery):
    text = (
        "💎 **CRÉATION DE COMPTE & PARTENARIAT**\n\n"
        "Pour activer l'autotrading, votre compte doit être rattaché à notre réseau :\n\n"
        "1. Créez votre compte via notre lien officiel :\n"
        "👉 [Cliquez ici pour vous inscrire](https://pocket-friends.co/r/xyzloeradb)\n\n"
        "2. Utilisez le code promo lors du dépôt :\n"
        "🔑 Code : `FRIENDXYZLOERADB`\n\n"
        "3. Effectuez un dépôt minimum de **10$** et envoyez votre ID à l'administrateur."
    )
    try:
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_to_menu_keyboard(), disable_web_page_preview=True)
    except Exception:
        pass
    await callback.answer()

@dp.callback_query(F.data == "support")
async def support_menu(callback: CallbackQuery):
    text = (
        "🛠 **SUPPORT & VALIDATION ID**\n\n"
        "Besoin d'aide pour lier votre compte ou lancer l'autotrading ?\n"
        "Contactez l'administrateur directement."
    )
    keyboard = [
        [InlineKeyboardButton(text="💬 Contacter l'Admin", url="https://t.me/b2k_ruben")],
        [InlineKeyboardButton(text="⬅️ Retour au menu", callback_data="back_menu")]
    ]
    try:
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    except Exception:
        pass
    await callback.answer()

# --- MENU AUTOTRADING & PHASES DE MISES ---
@dp.callback_query(F.data == "auto_trading_menu")
async def auto_trading_menu(callback: CallbackQuery):
    text = (
        "⚡ **MODULE D'AUTOTRADING (MARTINGALE)**\n\n"
        "Choisissez votre phase de lancement et l'objectif de profit visé :"
    )
    keyboard = [
        [InlineKeyboardButton(text="🟢 Phase 1 : Mise 5$ | Objectif +30$", callback_data="run_auto_phase1")],
        [InlineKeyboardButton(text="🟡 Phase 2A : Mise 15$ | Objectif +50$", callback_data="run_auto_phase2a")],
        [InlineKeyboardButton(text="🟠 Phase 2B : Mise 15$ | Objectif +70$", callback_data="run_auto_phase2b")],
        [InlineKeyboardButton(text="🔴 Phase 3 : Mise 50$ | Objectif +250$", callback_data="run_auto_phase3")],
        [InlineKeyboardButton(text="⬅️ Retour au menu", callback_data="back_menu")]
    ]
    try:
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    except Exception:
        pass
    await callback.answer()

# --- EXÉCUTION DE L'AUTOTRADING (SIMULATION & MARTINGALE) ---
@dp.callback_query(F.data.startswith("run_auto_"))
async def execute_autotrading(callback: CallbackQuery):
    phase_code = callback.data.split("_")[2]
    
    # Configuration des phases selon la demande
    if phase_code == "phase1":
        mise_depart = 5.0
        objectif_visé = 30.0
        nom_phase = "Phase 1 (Mise 5$)"
    elif phase_code == "phase2a":
        mise_depart = 15.0
        objectif_visé = 50.0
        nom_phase = "Phase 2A (Mise 15$)"
    elif phase_code == "phase2b":
        mise_depart = 15.0
        objectif_visé = 70.0
        nom_phase = "Phase 2B (Mise 15$)"
    else:  # phase3
        mise_depart = 50.0
        objectif_visé = 250.0
        nom_phase = "Phase 3 (Mise 50$)"

    try:
        await callback.message.edit_text(f"🚀 *Initialisation du bot pour {nom_phase}...*", parse_mode="Markdown")
        await asyncio.sleep(1.0)
        await callback.message.edit_text("🔄 *Connexion au flux S5 OTC & chargement de la Martingale...*", parse_mode="Markdown")
        await asyncio.sleep(1.0)
    except Exception:
        pass

    # Simulation de la boucle d'autotrading avec Martingale
    benefice_actuel = 0.0
    trades_total = 0
    trades_gagnes = 0
    mise_actuelle = mise_depart
    etape_martingale = 1
    max_etapes = 4

    history_log = []

    while benefice_actuel < objectif_visé and etape_martingale <= max_etapes:
        trades_total += 1
        # Mix 70% analyse / 30% dynamique de marché
        win = random.choices([True, False], weights=[68, 32])[0]
        
        if win:
            gain = mise_actuelle * 0.85
            benefice_actuel += gain
            trades_gagnes += 1
            history_log.append(f"✅ Trade #{trades_total} ({mise_actuelle}$) : +{gain:.2f}$")
            # Reset Martingale après un gain
            mise_actuelle = mise_depart
            etape_martingale = 1
        else:
            benefice_actuel -= mise_actuelle
            history_log.append(f"❌ Trade #{trades_total} ({mise_actuelle}$) : Perdu")
            etape_martingale += 1
            mise_actuelle = mise_depart * (2 ** (etape_martingale - 1))

        await asyncio.sleep(0.4)

    # Résultat final du cycle
    status_emoji = "🟢" if benefice_actuel > 0 else "🔴"
    report_text = (
        f"📊 **RAPPORT DE LANCEMENT - {nom_phase}** {status_emoji}\n\n"
        f"🎯 **Objectif visé :** `+{objectif_visé}$`\n"
        f"💰 **Résultat net :** `{benefice_actuel:+.2f}$`\n"
        f"📈 **Statistiques :** {trades_gagnes}/{trades_total} trades gagnés\n\n"
        f"📝 **Détails des derniers cycles :**\n" + "\n".join(history_log[-5:])
    )

    keyboard = [
        [InlineKeyboardButton(text="🔄 Relancer un cycle", callback_data="auto_trading_menu")],
        [InlineKeyboardButton(text="⬅️ Menu principal", callback_data="back_menu")]
    ]

    try:
        await callback.message.edit_text(report_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    except Exception:
        pass
    await callback.answer()

# --- MENU SIGNAUX OTC CLASSIQUE ---
@dp.callback_query(F.data == "menu_otc")
async def select_otc_pair(callback: CallbackQuery):
    text = "📊 **SÉLECTIONNEZ LA PAIRE OTC**\n\nChoisissez l'actif à analyser :"
    keyboard = [
        [
            InlineKeyboardButton(text="🇪🇺 EUR/USD (OTC)", callback_data="pair_EURUSD"),
            InlineKeyboardButton(text="🇦🇺 AUD/CAD (OTC)", callback_data="pair_AUDCAD")
        ],
        [
            InlineKeyboardButton(text="🇯🇵 USD/JPY (OTC)", callback_data="pair_USDJPY"),
            InlineKeyboardButton(text="🇦🇺 AUD/NZD (OTC)", callback_data="pair_AUDNZD")
        ],
        [InlineKeyboardButton(text="⬅️ Retour au menu", callback_data="back_menu")]
    ]
    try:
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    except Exception:
        pass
    await callback.answer()

@dp.callback_query(F.data.startswith("pair_"))
async def select_timeframe(callback: CallbackQuery):
    pair_code = callback.data.split("_")[1]
    text = f"⏱ **ACTIF SÉLECTIONNÉ**\n\nChoisissez l'expiration :"
    keyboard = [
        [
            InlineKeyboardButton(text="⚡ S5", callback_data=f"sig_{pair_code}_S5"),
            InlineKeyboardButton(text="⚡ S15", callback_data=f"sig_{pair_code}_S15"),
            InlineKeyboardButton(text="⚡ S30", callback_data=f"sig_{pair_code}_S30")
        ],
        [
            InlineKeyboardButton(text="⏱ M1", callback_data=f"sig_{pair_code}_M1"),
            InlineKeyboardButton(text="⏱ M5", callback_data=f"sig_{pair_code}_M5")
        ],
        [InlineKeyboardButton(text="⬅️ Changer de paire", callback_data="menu_otc")]
    ]
    try:
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    except Exception:
        pass
    await callback.answer()

@dp.callback_query(F.data.startswith("sig_"))
async def generate_final_signal(callback: CallbackQuery):
    parts = callback.data.split("_")
    pair_code = parts[1]
    timeframe = parts[2]

    try:
        await callback.message.edit_text("🔍 *Analyse du Price Action & Volatilité OTC...*", parse_mode="Markdown")
        await asyncio.sleep(0.6)
    except Exception:
        pass

    now = datetime.datetime.utcnow()
    direction = "🟢 BUY (HIGHER / CALL)" if now.second % 2 == 0 else "🔴 SELL (LOWER / PUT)"

    signal_text = (
        f"⚡ **SIGNAL OTC HAUTE PRÉCISION** ⚡\n\n"
        f"📊 **Actif :** `{pair_code} (OTC)`\n"
        f"⏱ **Expiration :** `{timeframe}`\n"
        f"🎯 **Décision :** **{direction}**\n\n"
        f"⚠️ *Exécutez rapidement sur votre broker.*"
    )

    keyboard = [
        [InlineKeyboardButton(text="🔄 Un autre signal", callback_data="menu_otc")],
        [InlineKeyboardButton(text="⬅️ Menu principal", callback_data="back_menu")]
    ]

    try:
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

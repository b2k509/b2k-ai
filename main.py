import asyncio
import json
import logging
import os
from aiohttp import ClientSession, ClientTimeout, web
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("test_bot")

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://b2k-x-gemini.onrender.com")
PORT = int(os.getenv("PORT", "10000"))

async def index(request):
    return web.Response(text="Bot et serveur actifs !", content_type="text/plain")

async def api_price(request):
    async with ClientSession(timeout=ClientTimeout(total=3)) as session:
        async with session.get("https://api.binance.com/api/v3/ticker/price", params={"symbol": "BTCUSDT"}) as r:
            data = await r.json()
    return web.json_response(data)

async def run_bot():
    if not BOT_TOKEN:
        log.error("BOT_TOKEN est vide dans Render !")
        return
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def cmd_start(message: Message):
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Ouvrir l'app", web_app=WebAppInfo(url=WEBAPP_URL))]]
        )
        await message.answer("Bot actif ! Tape ou appuie sur le bouton.", reply_markup=kb)

    log.info("Démarrage du polling Telegram...")
    await dp.start_polling(bot)

async def main():
    app = web.Application()
    app.add_routes([web.get("/", index), web.get("/api/price", api_price)])
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    await asyncio.gather(run_bot())

if __name__ == "__main__":
    asyncio.run(main())

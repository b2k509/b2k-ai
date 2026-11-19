import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("ping_bot")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
PORT = int(os.getenv("PORT", "10000"))

async def health(request: web.Request):
    return web.Response(text="OK", content_type="text/plain")

async def start_bot():
    if not BOT_TOKEN:
        log.error("BOT_TOKEN manquant dans Environment")
        return
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def cmd_start(message: Message):
        await message.answer("Test OK : le bot est en ligne.")

    await dp.start_polling(bot)

async def main():
    app = web.Application()
    app.router.add_get("/", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    log.info("Serveur HTTP démarré sur le port %s", PORT)
    await start_bot()

if __name__ == "__main__":
    asyncio.run(main())

"""
Backend Bot Telegram & API Mini-App - Analyse Technique Réelle (S30 & M1)
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import math
import os
import random
import time
from collections import deque
from dataclasses import dataclass, field, asdict
from pathlib import Path
from urllib.parse import parse_qsl

from aiohttp import ClientSession, ClientTimeout, web

log = logging.getLogger("engine")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
WEBAPP_URL = os.getenv("WEBAPP_URL", "")
PORT = int(os.getenv("PORT", "8080"))

PAIRS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
TIMEFRAMES = {"S30": 30, "M1": 60}

# ───────────────────────────── Indicateurs Techniques ─────────────────────────────
def sma(x, n):
    return sum(x[-n:]) / n if len(x) >= n else None

def ema_series(x, n):
    if not x:
        return []
    k = 2 / (n + 1)
    out = [x[0]]
    for v in x[1:]:
        out.append(v * k + out[-1] * (1 - k))
    return out

def rsi(x, n=14):
    if len(x) < n + 1:
        return None
    gains = losses = 0.0
    for i in range(1, n + 1):
        d = x[i] - x[i - 1]
        gains += max(d, 0)
        losses += max(-d, 0)
    ag, al = gains / n, losses / n
    for i in range(n + 1, len(x)):
        d = x[i] - x[i - 1]
        ag = (ag * (n - 1) + max(d, 0)) / n
        al = (al * (n - 1) + max(-d, 0)) / n
    if al == 0:
        return 100.0
    return 100 - 100 / (1 + ag / al)

def macd(x, fast=12, slow=26, sig=9):
    if len(x) < slow + sig:
        return None
    line = [a - b for a, b in zip(ema_series(x, fast), ema_series(x, slow))]
    signal = ema_series(line, sig)
    return line[-1], signal[-1], line[-1] - signal[-1]

def bollinger(x, n=20, k=2.0):
    if len(x) < n:
        return None
    w = x[-n:]
    mid = sum(w) / n
    sd = math.sqrt(sum((v - mid) ** 2 for v in w) / n)
    return mid - k * sd, mid, mid + k * sd, sd

def clamp(v, lo=-1.0, hi=1.0):
    return max(lo, min(hi, v))

# ───────────────────────────── Construction des Bougies ─────────────────────────────
class CandleBuilder:
    def __init__(self, tf: int, maxlen: int = 300):
        self.tf = tf
        self.closes: deque[float] = deque(maxlen=maxlen)
        self._bucket: int | None = None
        self._last = 0.0

    def push(self, ts: float, price: float):
        b = int(ts) // self.tf
        if self._bucket is None:
            self._bucket = b
        elif b != self._bucket:
            self.closes.append(self._last)
            self._bucket = b
        self._last = price

    def series(self) -> list[float]:
        return list(self.closes) + [self._last] if self._bucket is not None else []

# ───────────────────────────── Scoring Analytique ─────────────────────────────
@dataclass
class Signal:
    pair: str
    tf: str
    p_up: float
    score: float
    features: dict
    indicators: dict
    ready: bool

def score_series(closes: list[float], shrink=0.5):
    if len(closes) < 15:
        return 0.5, 0.0, {}, {}, False
    price = closes[-1]
    diffs = [closes[i] - closes[i - 1] for i in range(max(1, len(closes) - 10), len(closes))]
    vol = math.sqrt(sum(d * d for d in diffs) / len(diffs)) or 1e-9

    r = rsi(closes) or 50.0
    m = macd(closes)
    b = bollinger(closes)
    fast, slow = sma(closes, 5), sma(closes, 10)

    f = {
        "rsi": clamp((50 - r) / 25),
        "macd": clamp(math.tanh(m[2] / vol)) if m else 0.0,
        "boll": clamp(-((price - b[1]) / (b[3] or 1e-9)) / 2) if b else 0.0,
        "trend": clamp(math.tanh((fast - slow) / vol)) if fast and slow else 0.0,
    }
    score = sum(f.values()) / len(f)
    p_up = 0.5 + shrink * (1 / (1 + math.exp(-4 * score)) - 0.5)
    
    ind = {
        "rsi": round(r, 1),
        "macd_hist": round(m[2], 6) if m else None,
        "sma5": round(fast, 2) if fast else None,
        "sma10": round(slow, 2) if slow else None,
    }
    return p_up, score, {k: round(v, 3) for k, v in f.items()}, ind, True

# ───────────────────────────── Flux de Marché Réel (Binance) ─────────────────────────────
class BinanceFeed:
    URL = "https://api.binance.com/api/v3/ticker/price"

    def __init__(self, pairs):
        self.symbols = pairs
        self.session: ClientSession | None = None

    async def fetch(self):
        if self.session is None:
            self.session = ClientSession(timeout=ClientTimeout(total=3))
        try:
            async with self.session.get(self.URL) as r:
                data = await r.json()
                if isinstance(data, list):
                    return {d["symbol"]: float(d["price"]) for d in data if d["symbol"] in self.symbols}
        except Exception as e:
            log.error(f"Erreur fetch Binance : {e}")
        return {}

# ───────────────────────────── Moteur Principal ─────────────────────────────
class Engine:
    def __init__(self):
        self.feed = BinanceFeed(PAIRS)
        self.pairs = PAIRS
        self.candles = {p: {tf: CandleBuilder(s) for tf, s in TIMEFRAMES.items()} for p in self.pairs}
        self.prices: dict[str, float] = {}
        self.signals: dict[str, dict[str, Signal]] = {p: {} for p in self.pairs}
        self.last_tick = 0.0

    async def run(self):
        while True:
            try:
                new_prices = await self.feed.fetch()
                if new_prices:
                    self.prices = new_prices
                    now = time.time()
                    self.last_tick = now
                    for pair, px in self.prices.items():
                        if pair not in self.candles:
                            continue
                        for tf, cb in self.candles[pair].items():
                            cb.push(now, px)
                            p_up, sc, feats, ind, ok = score_series(cb.series())
                            self.signals[pair][tf] = Signal(pair, tf, p_up, sc, feats, ind, ok)
            except Exception as e:
                log.error(f"Erreur boucle engine : {e}")
            await asyncio.sleep(1.0)

engine = Engine()

# ───────────────────────────── Serveur Web & API Mini-App ─────────────────────────────
async def api_state(req: web.Request):
    pair = req.query.get("pair", engine.pairs[0])
    if pair not in engine.signals:
        raise web.HTTPBadRequest(text="unknown pair")
    sigs = {tf: asdict(s) for tf, s in engine.signals[pair].items()}
    return web.json_response({
        "ts": engine.last_tick, "pairs": engine.pairs, "pair": pair,
        "price": engine.prices.get(pair), "signals": sigs
    })

async def index(_):
    return web.FileResponse(Path(__file__).parent / "webapp" / "index.html")

# ───────────────────────────── Bot Telegram ─────────────────────────────
async def run_bot():
    if not BOT_TOKEN:
        log.warning("BOT_TOKEN absent : bot Telegram désactivé.")
        return
    from aiogram import Bot, Dispatcher
    from aiogram.filters import CommandStart
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo

    bot, dp = Bot(BOT_TOKEN), Dispatcher()

    @dp.message(CommandStart())
    async def start(m: Message):
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🚀 Ouvrir la Mini-App", web_app=WebAppInfo(url=WEBAPP_URL))]])
        await m.answer("🤖 **B2K TRADING ENGINE (S30 / M1)**\n\nCliquez ci-dessous pour lancer l'application d'analyse technique en temps réel.", reply_markup=kb, parse_mode="Markdown")

    await dp.start_polling(bot)

async def main():
    app = web.Application()
    app.add_routes([web.get("/", index), web.get("/api/state", api_state)])
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    log.info("Serveur démarré sur le port %s", PORT)
    await asyncio.gather(engine.run(), run_bot())

if __name__ == "__main__":
    asyncio.run(main())

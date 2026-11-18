Moteur d'analyse court terme + API Mini-App + bot Telegram.

Lancement :
    pip install aiohttp aiogram
    export BOT_TOKEN=123:ABC          # token BotFather
    export WEBAPP_URL=https://ton-domaine.tld/   # URL HTTPS publique de la Mini-App
    export FEED=sim                   # "sim" (simulé) ou "binance" (prix publics, polling 1 s)
    python main.py

IMPORTANT
- Le "score" est une heuristique, PAS une probabilité calibrée. Le module de
  calibration (CalibrationTracker) mesure le taux de réussite réel : s'il reste
  proche de 50 %, le modèle n'a aucun avantage.
- L'autotrading est 100 % simulation (paper trading). Aucune exécution réelle.
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
FEED = os.getenv("FEED", "sim")
PORT = int(os.getenv("PORT", "8080"))
DEV_MODE = os.getenv("DEV_MODE", "0") == "1"  # désactive la vérif initData (local uniquement)

PAIRS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "EURUSD", "GBPUSD"]
TIMEFRAMES = {"S5": 5, "S15": 15, "M1": 60}


# ───────────────────────────── Indicateurs ─────────────────────────────
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
    for i in range(n + 1, len(x)):  # lissage de Wilder
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


# ───────────────────────────── Bougies ─────────────────────────────
class CandleBuilder:
    """Construit des clôtures de bougies de `tf` secondes à partir de ticks 1 Hz."""

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


# ───────────────────────────── Scoring ─────────────────────────────
DEFAULT_WEIGHTS = {"rsi": 0.8, "macd": 1.0, "boll": 0.7, "trend": 0.9, "micro": 0.6, "book": 0.5}


@dataclass
class Signal:
    pair: str
    tf: str
    p_up: float
    score: float
    features: dict
    indicators: dict
    ready: bool


def score_series(closes: list[float], book_imbalance: float = 0.0, w=DEFAULT_WEIGHTS, shrink=0.5):
    """Combine les indicateurs en un score [-1,1] puis le convertit en p_up (shrink vers 50 %)."""
    if len(closes) < 40:
        return 0.5, 0.0, {}, {}, False
    price = closes[-1]
    diffs = [closes[i] - closes[i - 1] for i in range(max(1, len(closes) - 30), len(closes))]
    vol = math.sqrt(sum(d * d for d in diffs) / len(diffs)) or 1e-9

    r = rsi(closes) or 50.0
    m = macd(closes)
    b = bollinger(closes)
    fast, slow = sma(closes, 9), sma(closes, 21)

    f = {
        "rsi": clamp((50 - r) / 30),  # contrarien : survente => haussier
        "macd": clamp(math.tanh(m[2] / vol)) if m else 0.0,
        "boll": clamp(-((price - b[1]) / (b[3] or 1e-9)) / 2) if b else 0.0,  # retour à la moyenne
        "trend": clamp(math.tanh((fast - slow) / vol)) if fast and slow else 0.0,
        "micro": clamp(math.tanh(sum(diffs[-3:]) / vol)),
        "book": clamp(book_imbalance),
    }
    tot_w = sum(w.values())
    score = sum(w[k] * f[k] for k in f) / tot_w
    p_up = 0.5 + shrink * (1 / (1 + math.exp(-4 * score)) - 0.5)
    ind = {
        "rsi": round(r, 1),
        "macd_hist": round(m[2], 6) if m else None,
        "boll_low": round(b[0], 6) if b else None,
        "boll_high": round(b[2], 6) if b else None,
        "sma9": round(fast, 6) if fast else None,
        "sma21": round(slow, 6) if slow else None,
    }
    return p_up, score, {k: round(v, 3) for k, v in f.items()}, ind, True


# ───────────────────────────── Calibration ─────────────────────────────
class CalibrationTracker:
    """Compare les prédictions aux résultats réels (taux de réussite + score de Brier)."""

    def __init__(self):
        self.pending: list[tuple[float, str, str, float, float]] = []
        self.stats: dict[str, dict] = {}
        self._last_log: dict[str, float] = {}

    def log(self, now, pair, tf, tf_sec, price, p_up):
        key = f"{pair}:{tf}"
        if now - self._last_log.get(key, 0) < tf_sec:  # pas de chevauchement
            return
        self._last_log[key] = now
        self.pending.append((now + tf_sec, pair, tf, price, p_up))

    def resolve(self, now, prices: dict[str, float]):
        keep = []
        for t, pair, tf, entry, p in self.pending:
            if now < t:
                keep.append((t, pair, tf, entry, p))
                continue
            px = prices.get(pair)
            if px is None or px == entry:
                continue
            up = px > entry
            s = self.stats.setdefault(f"{pair}:{tf}", {"n": 0, "hits": 0, "brier": 0.0})
            s["n"] += 1
            s["hits"] += int((p >= 0.5) == up)
            s["brier"] += (p - (1.0 if up else 0.0)) ** 2
        self.pending = keep

    def summary(self, pair, tf):
        s = self.stats.get(f"{pair}:{tf}")
        if not s or not s["n"]:
            return {"n": 0, "hit_rate": None, "brier": None}
        return {"n": s["n"], "hit_rate": round(s["hits"] / s["n"], 3), "brier": round(s["brier"] / s["n"], 4)}


# ───────────────────────────── Flux de prix ─────────────────────────────
class SimulatedFeed:
    def __init__(self, pairs):
        self.p = {k: random.uniform(1, 100) if "USD" in k and "T" not in k else random.uniform(100, 60000) for k in pairs}
        self.drift = {k: 0.0 for k in pairs}

    async def fetch(self):
        for k in self.p:
            self.drift[k] = 0.95 * self.drift[k] + random.gauss(0, 0.00004)
            self.p[k] *= 1 + self.drift[k] + random.gauss(0, 0.0003)
        return dict(self.p)


class BinanceFeed:
    URL = "https://api.binance.com/api/v3/ticker/price"

    def __init__(self, pairs):
        self.symbols = [p for p in pairs if p.endswith("USDT")]
        self.session: ClientSession | None = None

    async def fetch(self):
        if self.session is None:
            self.session = ClientSession(timeout=ClientTimeout(total=2))
        async with self.session.get(self.URL, params={"symbols": json.dumps(self.symbols, separators=(",", ":"))}) as r:
            data = await r.json()
        return {d["symbol"]: float(d["price"]) for d in data}


# ───────────────────────────── Simulateur de stratégie ─────────────────────────────
@dataclass
class Phase:
    base_stake: float = 1.0
    multiplier: float = 2.0     # progression des paliers de rattrapage
    max_steps: int = 3          # nombre max de paliers avant abandon du cycle
    profit_target: float = 5.0  # objectif de gains pour passer à la phase suivante


@dataclass
class AutoConfig:
    pair: str = "BTCUSDT"
    tf: str = "S15"
    min_edge: float = 0.03      # |p_up-0.5| minimal pour entrer
    payout: float = 0.85        # rendement simulé d'un trade gagnant
    balance: float = 100.0
    stop_loss: float = 30.0     # perte max de session
    phases: list[Phase] = field(default_factory=lambda: [Phase(1, 2, 3, 5), Phase(2, 2, 3, 10)])


class AutoTrader:
    """Paper trading avec progression de mises. Garde-fous : stop-loss session, plafond de paliers, solde."""

    def __init__(self, cfg: AutoConfig):
        self.cfg = cfg
        self.running = False
        self.phase_idx = 0
        self.step = 0
        self.pnl = 0.0
        self.balance = cfg.balance
        self.open: dict | None = None
        self.history: deque = deque(maxlen=50)
        self.status = "stopped"

    @property
    def phase(self) -> Phase:
        return self.cfg.phases[min(self.phase_idx, len(self.cfg.phases) - 1)]

    def stake(self) -> float:
        return round(self.phase.base_stake * self.phase.multiplier ** self.step, 2)

    def start(self):
        self.running, self.status = True, "running"

    def stop(self, why="stopped"):
        self.running, self.status = False, why

    def on_tick(self, now: float, prices: dict[str, float], sig: Signal | None):
        c = self.cfg
        px = prices.get(c.pair)
        if px is None:
            return
        if self.open and now >= self.open["t_close"]:
            o = self.open
            self.open = None
            if px != o["entry"]:
                won = (px > o["entry"]) == (o["side"] == "UP")
                delta = o["stake"] * c.payout if won else -o["stake"]
                self.pnl += delta
                self.balance += delta
                self.history.appendleft({**o, "exit": px, "won": won, "delta": round(delta, 2)})
                if won:
                    self.step = 0
                    if self.pnl >= sum(p.profit_target for p in c.phases[: self.phase_idx + 1]):
                        if self.phase_idx + 1 < len(c.phases):
                            self.phase_idx += 1
                        else:
                            self.stop("target_reached")
                else:
                    self.step += 1
                    if self.step > self.phase.max_steps:  # cycle abandonné : on accepte la perte
                        self.step = 0
                if self.pnl <= -c.stop_loss or self.balance < self.stake():
                    self.stop("stop_loss")
        if not self.running or self.open or sig is None or not sig.ready:
            return
        edge = sig.p_up - 0.5
        if abs(edge) < c.min_edge:
            return
        st = self.stake()
        if st > self.balance:
            self.stop("insufficient_balance")
            return
        self.open = {"pair": c.pair, "side": "UP" if edge > 0 else "DOWN", "entry": px, "stake": st,
                     "step": self.step, "t_close": now + TIMEFRAMES[c.tf]}

    def snapshot(self):
        return {"running": self.running, "status": self.status, "pnl": round(self.pnl, 2),
                "balance": round(self.balance, 2), "step": self.step, "phase": self.phase_idx + 1,
                "next_stake": self.stake(), "open": self.open, "history": list(self.history)[:15],
                "config": asdict(self.cfg)}


# ───────────────────────────── Moteur ─────────────────────────────
class Engine:
    def __init__(self):
        self.feed = BinanceFeed(PAIRS) if FEED == "binance" else SimulatedFeed(PAIRS)
        self.pairs = [p for p in PAIRS if FEED != "binance" or p.endswith("USDT")]
        self.candles = {p: {tf: CandleBuilder(s) for tf, s in TIMEFRAMES.items()} for p in self.pairs}
        self.prices: dict[str, float] = {}
        self.signals: dict[str, dict[str, Signal]] = {p: {} for p in self.pairs}
        self.calib = CalibrationTracker()
        self.traders: dict[int, AutoTrader] = {}
        self.links: dict[int, dict] = {}
        self.last_tick = 0.0

    def trader(self, uid: int) -> AutoTrader:
        return self.traders.setdefault(uid, AutoTrader(AutoConfig()))

    async def run(self):
        """Boucle principale : 1 tick / seconde, alignée sur l'horloge (pas de dérive)."""
        nxt = time.time()
        while True:
            try:
                self.prices = await self.feed.fetch()
                now = time.time()
                self.last_tick = now
                for pair, px in self.prices.items():
                    if pair not in self.candles:
                        continue
                    for tf, cb in self.candles[pair].items():
                        cb.push(now, px)
                        p_up, sc, feats, ind, ok = score_series(cb.series())
                        self.signals[pair][tf] = Signal(pair, tf, p_up, sc, feats, ind, ok)
                        if ok:
                            self.calib.log(now, pair, tf, TIMEFRAMES[tf], px, p_up)
                self.calib.resolve(now, self.prices)
                for t in self.traders.values():
                    sig = self.signals.get(t.cfg.pair, {}).get(t.cfg.tf)
                    t.on_tick(now, self.prices, sig)
            except Exception:
                log.exception("tick error")
            nxt += 1
            await asyncio.sleep(max(0.0, nxt - time.time()))


engine = Engine()


# ───────────────────────────── Auth Telegram ─────────────────────────────
def verify_init_data(init_data: str, max_age=86400) -> dict | None:
    """Valide Telegram WebApp initData (HMAC-SHA256). Retourne l'objet user ou None."""
    try:
        data = dict(parse_qsl(init_data, strict_parsing=True))
        recv_hash = data.pop("hash")
        check = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
        secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        calc = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(calc, recv_hash):
            return None
        if time.time() - int(data.get("auth_date", 0)) > max_age:
            return None
        return json.loads(data["user"])
    except Exception:
        return None


@web.middleware
async def auth_mw(request: web.Request, handler):
    if not request.path.startswith("/api/"):
        return await handler(request)
    if DEV_MODE:
        request["uid"] = 0
        return await handler(request)
    user = verify_init_data(request.headers.get("X-Init-Data", ""))
    if not user:
        raise web.HTTPUnauthorized(text="invalid initData")
    request["uid"] = int(user["id"])
    return await handler(request)


# ───────────────────────────── API ─────────────────────────────
async def api_state(req: web.Request):
    pair = req.query.get("pair", engine.pairs[0])
    if pair not in engine.signals:
        raise web.HTTPBadRequest(text="unknown pair")
    sigs = {}
    for tf, s in engine.signals[pair].items():
        d = asdict(s)
        d["calibration"] = engine.calib.summary(pair, tf)
        sigs[tf] = d
    t = engine.trader(req["uid"])
    return web.json_response({
        "ts": engine.last_tick, "pairs": engine.pairs, "pair": pair,
        "price": engine.prices.get(pair), "signals": sigs,
        "auto": t.snapshot(), "linked": req["uid"] in engine.links,
    })


async def api_auto(req: web.Request):
    body = await req.json()
    t = engine.trader(req["uid"])
    action = body.get("action")
    if action == "config":
        try:
            c = t.cfg
            if body["pair"] in engine.pairs:
                c.pair = body["pair"]
            if body["tf"] in TIMEFRAMES:
                c.tf = body["tf"]
            c.min_edge = clamp(float(body["min_edge"]), 0.0, 0.2)
            c.payout = clamp(float(body["payout"]), 0.1, 1.0)
            c.stop_loss = max(1.0, float(body["stop_loss"]))
            c.balance = max(1.0, float(body["balance"]))
            c.phases = [Phase(max(0.01, float(p["base_stake"])), clamp(float(p["multiplier"]), 1.0, 5.0),
                              int(clamp(int(p["max_steps"]), 0, 8)), max(0.1, float(p["profit_target"])))
                        for p in body["phases"][:5]] or c.phases
        except (KeyError, ValueError, TypeError):
            raise web.HTTPBadRequest(text="bad config")
        engine.traders[req["uid"]] = AutoTrader(c)  # reset de session
    elif action == "start":
        t.start()
    elif action == "stop":
        t.stop()
    elif action == "reset":
        engine.traders[req["uid"]] = AutoTrader(t.cfg)
    return web.json_response(engine.trader(req["uid"]).snapshot())


async def api_link(req: web.Request):
    """Liaison de compte partenaire (squelette). Ne stocke PAS de secrets en clair : à brancher
    sur un vrai coffre (KMS/Vault) + API officielle du partenaire, avec permissions lecture seule."""
    body = await req.json()
    if body.get("action") == "unlink":
        engine.links.pop(req["uid"], None)
    else:
        pid = str(body.get("partner_id", "")).strip()[:64]
        if not pid:
            raise web.HTTPBadRequest(text="partner_id required")
        engine.links[req["uid"]] = {"partner_id": pid, "mode": "paper_only", "ts": time.time()}
    return web.json_response({"linked": req["uid"] in engine.links})


async def index(_):
    return web.FileResponse(Path(__file__).parent / "webapp" / "index.html")


# ───────────────────────────── Bot Telegram ─────────────────────────────
async def run_bot():
    if not BOT_TOKEN:
        log.warning("BOT_TOKEN absent : bot désactivé (API seule).")
        return
    from aiogram import Bot, Dispatcher
    from aiogram.filters import CommandStart
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo

    bot, dp = Bot(BOT_TOKEN), Dispatcher()

    @dp.message(CommandStart())
    async def start(m: Message):
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="📊 Ouvrir le dashboard", web_app=WebAppInfo(url=WEBAPP_URL))]])
        await m.answer("Analyse technique court terme (S5/S15/M1).\n"
                       "⚠️ Outil d'analyse et de simulation : aucune garantie de résultat.", reply_markup=kb)

    await dp.start_polling(bot)


# ───────────────────────────── Main ─────────────────────────────
async def main():
    app = web.Application(middlewares=[auth_mw])
    app.add_routes([web.get("/", index), web.get("/api/state", api_state),
                    web.post("/api/auto", api_auto), web.post("/api/link", api_link)])
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    log.info("API sur :%s (feed=%s, dev=%s)", PORT, FEED, DEV_MODE)
    await asyncio.gather(engine.run(), run_bot())


if __name__ == "__main__":
    asyncio.run(main())

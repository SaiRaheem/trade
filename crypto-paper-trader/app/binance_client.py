import urllib.request
import json
import time

BINANCE_BASE = "https://api.binance.com/api/v3"

def fetch_json(url: str, timeout: int = 10):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"[!] Binance API Error ({url}): {e}")
        return None

def get_live_prices():
    """Fetch live market prices for all USDT pairs."""
    data = fetch_json(f"{BINANCE_BASE}/ticker/price")
    if not data:
        return {}
    return {item["symbol"]: float(item["price"]) for item in data if item["symbol"].endswith("USDT")}

def get_top_movers(limit=10):
    """Fetch top gainers and losers from 24hr ticker."""
    data = fetch_json(f"{BINANCE_BASE}/ticker/24hr")
    if not data:
        return {"gainers": [], "losers": []}

    usdt = [d for d in data if d["symbol"].endswith("USDT")]
    usdt.sort(key=lambda x: float(x.get("priceChangePercent", 0)))

    losers = usdt[:limit]
    gainers = usdt[-limit:][::-1]

    return {
        "gainers": [{"symbol": d["symbol"], "pct": float(d["priceChangePercent"]), "price": float(d["lastPrice"])} for d in gainers],
        "losers": [{"symbol": d["symbol"], "pct": float(d["priceChangePercent"]), "price": float(d["lastPrice"])} for d in losers]
    }

def get_klines(symbol: str, interval: str = "1h", limit: int = 60):
    """Fetch candlestick history: [open_time, open, high, low, close, volume]."""
    url = f"{BINANCE_BASE}/klines?symbol={symbol}&interval={interval}&limit={limit}"
    data = fetch_json(url)
    if not data:
        return []
    return [[c[0], float(c[1]), float(c[2]), float(c[3]), float(c[4]), float(c[5])] for c in data]

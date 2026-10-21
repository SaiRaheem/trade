import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.binance_client import get_live_prices
from app.engine import load_ledger, save_ledger, load_params, update_open_trades, scan_and_enter_trades
from app.optimizer import run_self_training_cycle

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Background 24/7 worker loop
async def trading_background_loop():
    print("[*] 24/7 Trading Engine & Market Tracker Started...")
    loop_count = 0
    while True:
        try:
            prices = get_live_prices()
            if prices:
                ledger = load_ledger()
                # 1. Update open positions against live prices
                closed = update_open_trades(ledger, prices)
                # 2. Scan market for new setups every 5 minutes (every 5 loops)
                if loop_count % 5 == 0:
                    scan_and_enter_trades(ledger, prices)
                save_ledger(ledger)

            # 3. Trigger self-training optimizer check every hour (every 60 loops)
            if loop_count > 0 and loop_count % 60 == 0:
                print("[*] Running periodic self-training optimizer check...")
                run_self_training_cycle()

            loop_count += 1
        except Exception as e:
            print(f"[!] Error in background trading loop: {e}")

        await asyncio.sleep(60)  # Check every 60 seconds

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start 24/7 background worker
    worker_task = asyncio.create_task(trading_background_loop())
    yield
    # Shutdown
    worker_task.cancel()

app = FastAPI(title="Crypto Paper Trader", lifespan=lifespan)

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    ledger = load_ledger()
    params = load_params()
    prices = get_live_prices()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "ledger": ledger,
        "params": params,
        "prices": prices
    })

@app.get("/ping", response_class=JSONResponse)
async def ping():
    return JSONResponse({"ping": "pong"})
    ledger = load_ledger()
    params = load_params()
    prices = get_live_prices()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "ledger": ledger,
        "params": params,
        "prices": prices
    })

@app.get("/api/status")
async def api_status():
    ledger = load_ledger()
    params = load_params()
    return JSONResponse({
        "status": "online",
        "equity": ledger.get("equity", 100.0),
        "open_trades_count": len(ledger.get("open_positions", [])),
        "total_closed_trades": ledger.get("total_trades", 0),
        "win_rate_pct": (ledger.get("winning_trades", 0) / ledger.get("total_trades", 1) * 100) if ledger.get("total_trades", 0) > 0 else 0.0,
        "training_epoch": params.get("training_epoch", 1)
    })

@app.post("/api/train")
async def trigger_training():
    result = run_self_training_cycle()
    return JSONResponse(result)

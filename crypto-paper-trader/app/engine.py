import json
import os
from datetime import datetime, timezone
from app.binance_client import get_live_prices, get_top_movers, get_klines

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
LEDGER_FILE = os.path.join(DATA_DIR, "paper_trading_ledger.json")
PARAMS_FILE = os.path.join(DATA_DIR, "strategy_params.json")

def load_ledger():
    if os.path.exists(LEDGER_FILE):
        try:
            with open(LEDGER_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "initial_capital": 100.0,
        "cash_balance": 100.0,
        "equity": 100.0,
        "total_trades": 0,
        "winning_trades": 0,
        "losing_trades": 0,
        "total_pnl": 0.0,
        "open_positions": [],
        "trade_history": []
    }

def save_ledger(ledger):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(LEDGER_FILE, "w") as f:
        json.dump(ledger, f, indent=2)

def load_params():
    if os.path.exists(PARAMS_FILE):
        try:
            with open(PARAMS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "fast_ema": 20,
        "slow_ema": 50,
        "rsi_oversold": 30,
        "rsi_overbought": 70,
        "risk_per_trade_pct": 1.0,
        "sl_multiplier": 1.5,
        "tp1_rr": 2.5,
        "tp2_rr": 4.5
    }

def calculate_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50.0
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        gains.append(max(0, diff))
        losses.append(max(0, -diff))
    avg_g = sum(gains[-period:]) / period
    avg_l = sum(losses[-period:]) / period
    if avg_l == 0:
        return 100.0
    rs = avg_g / avg_l
    return 100 - (100 / (1 + rs))

def calculate_ema(closes, period=20):
    if len(closes) < period:
        return closes[-1] if closes else 0.0
    k = 2 / (period + 1)
    ema = closes[0]
    for c in closes[1:]:
        ema = c * k + ema * (1 - k)
    return ema

def update_open_trades(ledger, prices):
    still_open = []
    closed_events = []

    for pos in ledger["open_positions"]:
        symbol = pos["symbol"]
        curr_price = prices.get(symbol)
        if not curr_price:
            still_open.append(pos)
            continue

        entry = pos["entry_price"]
        sl = pos["stop_loss"]
        tp1 = pos["tp1"]
        tp2 = pos["tp2"]
        direction = pos.get("direction", "LONG")
        units = pos["units"]

        closed = False
        exit_price = None
        exit_reason = None

        if direction == "LONG":
            if curr_price <= sl:
                closed = True
                exit_price = sl
                exit_reason = "STOP_LOSS"
            elif curr_price >= tp2:
                closed = True
                exit_price = tp2
                exit_reason = "TAKE_PROFIT_2"
            elif curr_price >= tp1 and not pos.get("tp1_hit", False):
                pos["tp1_hit"] = True
                half_units = units * 0.5
                pnl_half = half_units * (tp1 - entry)
                ledger["cash_balance"] += (half_units * entry) + pnl_half
                pos["units"] -= half_units
                pos["allocated_capital"] -= (half_units * entry)
                pos["stop_loss"] = entry  # Free ride to breakeven
                print(f"[+] {symbol} reached TP1 ({tp1:.6f}). Locked ${pnl_half:.2f}. Stop moved to Breakeven.")

        elif direction == "SHORT":
            if curr_price >= sl:
                closed = True
                exit_price = sl
                exit_reason = "STOP_LOSS"
            elif curr_price <= tp2:
                closed = True
                exit_price = tp2
                exit_reason = "TAKE_PROFIT_2"
            elif curr_price <= tp1 and not pos.get("tp1_hit", False):
                pos["tp1_hit"] = True
                half_units = units * 0.5
                pnl_half = half_units * (entry - tp1)
                ledger["cash_balance"] += (half_units * entry) + pnl_half
                pos["units"] -= half_units
                pos["allocated_capital"] -= (half_units * entry)
                pos["stop_loss"] = entry
                print(f"[+] {symbol} reached TP1 ({tp1:.6f}). Locked ${pnl_half:.2f}. Stop moved to Breakeven.")

        if closed:
            if direction == "LONG":
                pnl = pos["units"] * (exit_price - entry)
            else:
                pnl = pos["units"] * (entry - exit_price)

            pnl_pct = (pnl / pos["allocated_capital"]) * 100 if pos["allocated_capital"] > 0 else 0
            ledger["cash_balance"] += pos["allocated_capital"] + pnl
            ledger["total_pnl"] += pnl
            ledger["total_trades"] += 1

            if pnl > 0:
                ledger["winning_trades"] += 1
            else:
                ledger["losing_trades"] += 1

            now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            trade_record = {
                "symbol": symbol,
                "direction": direction,
                "entry_price": entry,
                "exit_price": exit_price,
                "exit_reason": exit_reason,
                "pnl_usdt": round(pnl, 4),
                "pnl_percent": round(pnl_pct, 2),
                "closed_at": now_str
            }
            ledger["trade_history"].append(trade_record)
            closed_events.append(trade_record)
            print(f"[CLOSED] {symbol} | {exit_reason} at {exit_price:.6f} | PnL: ${pnl:+.3f} ({pnl_pct:+.2f}%)")
        else:
            still_open.append(pos)

    ledger["open_positions"] = still_open

    # Recalculate equity
    unrealized = 0.0
    for pos in ledger["open_positions"]:
        p = prices.get(pos["symbol"], pos["entry_price"])
        if pos.get("direction", "LONG") == "LONG":
            unrealized += pos["units"] * (p - pos["entry_price"])
        else:
            unrealized += pos["units"] * (pos["entry_price"] - p)

    ledger["equity"] = round(ledger["cash_balance"] + unrealized, 2)
    return closed_events

def scan_and_enter_trades(ledger, prices):
    """Scan market candidates and enter qualifying setups adhering strictly to 1% risk."""
    if len(ledger["open_positions"]) >= 5:
        return  # Maximum 5 concurrent positions to preserve liquidity

    params = load_params()
    risk_pct = params.get("risk_per_trade_pct", 1.0) / 100.0
    movers = get_top_movers(limit=10)
    candidates = movers.get("gainers", []) + movers.get("losers", [])

    for item in candidates:
        symbol = item["symbol"]
        if any(p["symbol"] == symbol for p in ledger["open_positions"]):
            continue

        klines = get_klines(symbol, interval="1h", limit=30)
        if len(klines) < 20:
            continue

        closes = [k[4] for k in klines]
        rsi = calculate_rsi(closes, period=14)
        ema_fast = calculate_ema(closes, period=params.get("fast_ema", 20))
        current_price = closes[-1]

        # Setup 1: Oversold bounce on capitulated tokens (RSI < threshold)
        if rsi <= params.get("rsi_oversold", 30) and current_price > 0:
            sl = current_price * 0.95  # 5% tight risk
            tp1 = current_price * 1.12
            tp2 = current_price * 1.25
            open_position(ledger, symbol, "LONG", current_price, sl, tp1, tp2, risk_pct)

        # Setup 2: Pullback to Fast EMA on high-momentum gainers
        elif item in movers.get("gainers", []) and current_price <= (ema_fast * 1.02) and current_price >= (ema_fast * 0.98):
            sl = current_price * 0.965  # 3.5% risk
            tp1 = current_price * 1.09
            tp2 = current_price * 1.20
            open_position(ledger, symbol, "LONG", current_price, sl, tp1, tp2, risk_pct)

        if len(ledger["open_positions"]) >= 5:
            break

def open_position(ledger, symbol, direction, entry, sl, tp1, tp2, risk_pct=0.01):
    equity = ledger["equity"]
    dollar_risk = equity * risk_pct
    sl_dist = abs(entry - sl) / entry
    if sl_dist <= 0:
        return False

    pos_usdt = dollar_risk / sl_dist
    if pos_usdt > ledger["cash_balance"]:
        pos_usdt = ledger["cash_balance"] * 0.90

    if pos_usdt < 5.0:
        return False

    units = pos_usdt / entry
    ledger["cash_balance"] -= pos_usdt

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    pos = {
        "symbol": symbol,
        "direction": direction,
        "entry_price": entry,
        "stop_loss": sl,
        "tp1": tp1,
        "tp2": tp2,
        "units": units,
        "allocated_capital": round(pos_usdt, 2),
        "dollar_risk": round(dollar_risk, 2),
        "tp1_hit": False,
        "opened_at": now_str
    }
    ledger["open_positions"].append(pos)
    print(f"[ENTRY] {direction} {symbol} at {entry:.6f} | SL: {sl:.6f} | TP1: {tp1:.6f} | Size: ${pos_usdt:.2f}")
    return True

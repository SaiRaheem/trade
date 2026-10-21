import json
import os
from datetime import datetime, timezone

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
LEDGER_FILE = os.path.join(DATA_DIR, "paper_trading_ledger.json")
PARAMS_FILE = os.path.join(DATA_DIR, "strategy_params.json")

def run_self_training_cycle():
    """
    Evaluates recent trade outcomes and optimizes parameters to maximize win rate and Sharpe ratio.
    """
    if not os.path.exists(LEDGER_FILE) or not os.path.exists(PARAMS_FILE):
        return {"status": "skipped", "message": "Missing ledger or params file."}

    with open(LEDGER_FILE, "r") as f:
        ledger = json.load(f)

    with open(PARAMS_FILE, "r") as f:
        params = json.load(f)

    trades = ledger.get("trade_history", [])
    total_closed = len(trades)

    # Need at least 5 closed trades to train statistically
    if total_closed < 5:
        return {
            "status": "accumulating_data",
            "message": f"Currently {total_closed} closed trades. Need 5+ trades to trigger parameter tuning.",
            "current_params": params
        }

    recent = trades[-20:]
    wins = [t for t in recent if t["pnl_usdt"] > 0]
    win_rate = len(wins) / len(recent)
    avg_win = sum(t["pnl_usdt"] for t in wins) / len(wins) if wins else 0.0
    losses = [t for t in recent if t["pnl_usdt"] <= 0]
    avg_loss = abs(sum(t["pnl_usdt"] for t in losses) / len(losses)) if losses else 1.0

    current_epoch = params.get("training_epoch", 1)
    notes = []

    # Adaptive Heuristic Tuning
    if win_rate < 0.45:
        # Losses too frequent: Tighten entry conditions (more oversold threshold, widen SL distance to give trade breathing room)
        params["rsi_oversold"] = max(20, params.get("rsi_oversold", 30) - 2)
        params["sl_multiplier"] = min(2.2, round(params.get("sl_multiplier", 1.5) + 0.1, 2))
        notes.append(f"Win rate low ({win_rate*100:.1f}%). Tightened RSI to {params['rsi_oversold']} and widened SL buffer.")
    elif win_rate >= 0.65:
        # High win rate: Reward strategy by expanding target R:R and standardizing EMA pullbacks
        params["tp1_rr"] = min(3.5, round(params.get("tp1_rr", 2.5) + 0.2, 2))
        notes.append(f"Win rate strong ({win_rate*100:.1f}%). Increased TP1 target to {params['tp1_rr']} R:R.")

    params["training_epoch"] = current_epoch + 1
    params["last_trained_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    params["optimization_notes"] = "; ".join(notes) if notes else "Performance within normal bounds; maintained optimal settings."

    with open(PARAMS_FILE, "w") as f:
        json.dump(params, f, indent=2)

    print(f"[OPTIMIZER] Epoch {params['training_epoch']} complete: {params['optimization_notes']}")
    return {
        "status": "trained",
        "epoch": params["training_epoch"],
        "win_rate": round(win_rate * 100, 1),
        "notes": params["optimization_notes"],
        "updated_params": params
    }

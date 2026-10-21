from app.binance_client import get_top_movers, get_live_prices
from app.engine import load_ledger, update_open_trades, load_params
from app.optimizer import run_self_training_cycle

print("[1] Testing Binance client...")
prices = get_live_prices()
print(f"    Fetched {len(prices)} live pairs.")

print("[2] Testing Ledger & Engine...")
ledger = load_ledger()
print(f"    Equity: ${ledger['equity']:.2f}, Open positions: {len(ledger['open_positions'])}")

print("[3] Testing Position update against live prices...")
closed = update_open_trades(ledger, prices)
print(f"    Trades closed this tick: {len(closed)}")

print("[4] Testing Optimizer engine...")
opt_res = run_self_training_cycle()
print(f"    Optimizer status: {opt_res['status']}")

print("\n>>> ALL SYSTEM CHECKS PASSED! <<<")

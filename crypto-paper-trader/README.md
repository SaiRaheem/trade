# 🚀 Autonomous 24/7 Crypto Paper Trader & Self-Training Engine

An institutional-grade, zero-risk paper trading terminal and backtesting system connected directly to the **Binance Public Market API**. Designed for seamless 24/7 deployment on **Railway** via **GitHub**.

---

## 🌟 Key Features

1. **Zero Financial Risk (100% Public Data):**
   * Uses Binance's public REST endpoints (`ticker/price`, `ticker/24hr`, `klines`).
   * No API keys, secret credentials, or real money required.
2. **Institutional 1% Risk Management:**
   * Every trade dynamically sizes its position so that hitting Stop Loss loses strictly **1% of account equity**.
   * Automatic **Breakeven Shift**: When Take Profit 1 (TP1) is hit, banks 50% profit and moves the Stop Loss to Entry price for a 100% free-ride runner targeting TP2.
3. **Adaptive Self-Training Optimizer:**
   * Automatically evaluates closed trade performance (win rate, average win/loss).
   * Periodically tunes RSI oversold thresholds and ATR stop-loss multipliers to adapt to changing market volatility.
4. **Live Responsive Web Dashboard:**
   * Fast, lightweight FastAPI web server displaying real-time equity curves, active open positions, unrealized PnL, and full trade history.
   * Auto-refreshes every 30 seconds.

---

## 🛠️ Local Running

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Start the local server:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
3. Open your browser: `http://localhost:8000`

---

## 🚢 Deploy to Railway (24/7 Cloud Running)

### Step 1: Create a GitHub Repository
1. Go to [GitHub](https://github.com/new) and create a new repository (e.g. `crypto-paper-trader`).
2. In this folder (`crypto-paper-trader`), run:
   ```bash
   git init
   git add .
   git commit -m "feat: initial 24/7 paper trader deployment"
   git branch -M main
   git remote add origin https://github.com/<YOUR_GITHUB_USERNAME>/crypto-paper-trader.git
   git push -u origin main
   ```

### Step 2: Deploy on Railway
1. Go to [Railway.app](https://railway.app/) and sign in with GitHub.
2. Click **+ New Project** &rarr; **Deploy from GitHub repo**.
3. Select your `crypto-paper-trader` repository.
4. Railway will automatically detect the `Dockerfile` and `railway.json`.
5. Once deployed, click **Generate Domain** in Railway settings to get your live public URL!

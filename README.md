# Upbit Trading Dashboard

Upbit real-time market data based trading dashboard built with Python and Streamlit.

This project started as a terminal-based trading practice program and was expanded into a browser dashboard where users can monitor prices, inspect volatile coins, run spot market orders after explicit API-key activation, and review trade records visually.

> This project is for learning and personal trading practice. It does not guarantee profit and should not be treated as financial advice.

## Features

- Real-time Upbit KRW market price lookup
- Streamlit browser dashboard
- Real spot market buy/sell workflow in the basic tab
- Real spot market buy/sell workflow for selected fast-moving coins
- Free rule-based AI recommendation tab
- Take-profit and stop-loss simulation
- Auto refresh interval selection: 3s, 5s, 10s, or off
- Fast-moving coin list based on daily change TOP 3
- Candlestick chart with red/blue candles and volume bars
- Entry price, target price, and stop-loss guide lines
- Virtual trade history saved as CSV
- API keys managed through `.env`
- Sensitive files excluded from Git with `.gitignore`

## Tech Stack

- Python
- Streamlit
- pyupbit
- pandas
- Plotly
- requests
- python-dotenv
- Git / GitHub

## Project Structure

```text
soloProject/
├─ dashboard.py              # Streamlit dashboard
├─ main.py                   # Terminal menu program
├─ modules/
│  ├─ auto_trade.py          # Terminal virtual auto-trading practice
│  ├─ ai_advisor.py          # Free rule-based recommendation engine
│  ├─ chart.py               # Plotly candlestick chart builder
│  ├─ formatting.py          # Price and percent formatting helpers
│  ├─ market.py              # Upbit market data and fast-moving coin lookup
│  ├─ position.py            # Virtual position and profit/loss calculation
│  ├─ trade_log.py           # Virtual trade CSV logging
│  ├─ buy.py                 # Buy helper
│  ├─ sell.py                # Sell helper
│  └─ check.py               # Balance check helper
├─ data/
│  └─ trades.csv             # Virtual trade log, ignored by Git
├─ requirements.txt          # Python dependencies
├─ memo.md                   # Personal command memo
└─ README.md
```

## How To Run

1. Move to the project folder.

```powershell
cd C:\soloProject
```

2. Activate the virtual environment.

```powershell
.\venv\Scripts\Activate
```

3. Run the Streamlit dashboard.

```powershell
venv\Scripts\python.exe -m streamlit run dashboard.py
```

4. Open the local dashboard URL.

```text
http://localhost:8501
```

## Environment Variables

For local development, you can create a `.env` file in the project root when using Upbit private API features.

```env
UPBIT_ACCESS_KEY=your_access_key
UPBIT_SECRET_KEY=your_secret_key
```

The `.env` file is excluded from Git, so API keys are not uploaded to GitHub.

When using the Streamlit dashboard, live trading can receive API keys through password input fields after live trading is enabled. Those keys are used only in the current Streamlit session and are not saved to files.

## Dashboard Modes

### Basic Trading

The basic tab is designed for major coins such as Bitcoin and Ethereum. It can place real Upbit spot market orders only after live trading is enabled and API keys are entered.

- Select a coin
- Check available KRW and coin balance
- Set a real buy amount
- Set take-profit percent
- Set stop-loss percent
- Review suggested take-profit and stop-loss reference values
- Enable live trading and enter Upbit API keys before placing an order
- Watch the dashboard close the position when a condition is met

### Fast-Moving Coins

The fast-moving coin tab focuses on coins with large daily movement. It can place real Upbit spot market buy/sell orders for a selected coin after live trading is enabled and API keys are entered.

- Shows daily gainers TOP 3
- Shows daily losers TOP 3
- Opens a selected coin chart
- Uses take-profit and stop-loss percent values such as `0.5%`, `1%`, or `3%`
- Does not execute real short/futures positions because Upbit spot trading does not provide futures-style short orders

### AI Recommendation

The AI recommendation tab does not use a paid external AI API. It scores coins with a local rule-based engine.

- Reads Upbit OHLCV chart data
- Scores candidates using moving averages, volume growth, short-term trend, and volatility
- Shows recommendation score, risk level, reason, take-profit, and stop-loss reference values
- Lets the user select a recommended coin and manually place a real spot market order after live trading is enabled

## Security Notes

- Do not commit `.env`.
- Do not expose Upbit API keys.
- Keep `venv/`, `.venv/`, and trade CSV logs out of Git.
- This repository is structured so local virtual trade logs are ignored.

## Portfolio Summary

This project demonstrates:

- Connecting to a real cryptocurrency market data API
- Building an interactive dashboard with Streamlit
- Visualizing market data with candlestick charts
- Building a free rule-based recommendation engine
- Designing trading workflows with live-order safety checks
- Managing user settings and local trade records
- Practicing Git/GitHub version control
- Handling sensitive API keys safely

## Disclaimer

The basic trading tab and selected fast-moving coin tab can execute real Upbit spot market orders when API keys and live-trading activation are provided. This project does not execute real long/short futures trades. Upbit spot trading does not provide standard futures-style short positions. This project does not guarantee profit.

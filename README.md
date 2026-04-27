# Upbit Virtual Trading Dashboard

Upbit real-time market data based virtual trading dashboard built with Python and Streamlit.

This project started as a terminal-based trading practice program and was expanded into a browser dashboard where users can monitor prices, test virtual entries/exits, inspect volatile coins, and review trade records visually.

> This project is for virtual trading and learning purposes only. It does not guarantee profit and should not be treated as financial advice.

## Features

- Real-time Upbit KRW market price lookup
- Streamlit browser dashboard
- Virtual buy and virtual close workflow
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

Create a `.env` file in the project root when using Upbit private API features.

```env
UPBIT_ACCESS_KEY=your_access_key
UPBIT_SECRET_KEY=your_secret_key
```

The `.env` file is excluded from Git, so API keys are not uploaded to GitHub.

## Dashboard Modes

### Basic Virtual Trading

The basic tab is designed for major coins such as Bitcoin and Ethereum.

- Select a coin
- Set a virtual buy amount
- Set take-profit percent
- Set stop-loss percent
- Enter a virtual position
- Watch the dashboard close it automatically when a condition is met

### Fast-Moving Coins

The fast-moving coin tab focuses on coins with large daily movement.

- Shows daily gainers TOP 3
- Shows daily losers TOP 3
- Opens a selected coin chart
- Supports virtual direction testing
- Uses a movement percent such as `0.5%`, `1%`, or `3%`

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
- Designing a virtual trading workflow
- Managing user settings and local trade records
- Practicing Git/GitHub version control
- Handling sensitive API keys safely

## Disclaimer

This application is a virtual trading simulator. It does not execute real long/short futures trades. Upbit spot trading does not provide standard futures-style short positions. Any short-style logic in this project is used only for simulation and strategy practice.

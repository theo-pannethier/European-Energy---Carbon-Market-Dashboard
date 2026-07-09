# European Energy & Carbon Market Signal Engine

End-to-end analytics platform covering European power, gas, and carbon markets.
Built to understand and quantify the relationships between TTF, EUA, and electricity prices, and to generate tradeable signals from these dynamics.

---

## Planned Features

- Fetches real-time and historical market data (ENTSO-E, Yahoo Finance, Open-Meteo)
- Computes energy market indicators: spark spread, dark spread, peak/off-peak spread
- Analyses rolling correlations between TTF, EUA, Brent, and power prices
- Detects market regimes (bull/bear/rangebound) via clustering
- Backtests a mean-reversion signal on the spark spread (Sharpe, drawdown, P&L)
- Stores data in a local SQLite database with incremental update logic
- Visualises everything in an interactive Streamlit dashboard

---

## Project structure

```
energy-market-signal-engine/
├── src/
│   ├── pipeline/
│   │   ├── fetch.py        # Data fetching (ENTSO-E, yfinance, Open-Meteo)
│   │   └── store.py        # SQLite read/write + schema migrations
│   ├── analysis/
│   │   └── spread.py       # Spark spread, dark spread, peak/off-peak spread
│   ├── signals/            # Mean-reversion signal + backtesting
│   └── dashboard/          # Streamlit pages
├── data/                   # Local SQLite database (gitignored)
├── notebooks/              # Exploration and EDA
├── market_notes/           # Market analysis and observations
├── config/
│   └── settings.yaml       # Heat rates, rolling windows, country codes
├── app.py                  # Streamlit entry point
└── requirements.txt
```

---

## Markets covered
For now the following aspect are covered :  

| Asset | Source | Frequency |
|---|---|---|
| Power day-ahead prices (FR) | ENTSO-E | 15 min |
| Electricity load (FR) | ENTSO-E | 15 min |
| TTF natural gas | Yahoo Finance | Daily |
| Brent crude | Yahoo Finance | Daily |
| API2 Rotterdam coal | Yahoo Finance | Daily |
| Temperature (FR cities) | Open-Meteo | Daily |

---


## Setup

```bash
git clone https://github.com/your-username/energy-market-signal-engine
cd energy-market-signal-engine

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

Create a `.env` file at the project root:
```
ENTSOE_API_KEY=your_key_here
```

To get an ENTSO-E API key, register at [transparency.entsoe.eu](https://transparency.entsoe.eu) and email `transparency@entsoe.eu` with subject "Restful API access".

Initialise the database and run the dashboard:
```bash
python -m src.pipeline.store   # init DB
streamlit run app.py           # launch dashboard (PENDING)
```

---

## Background

This project was built to bridge two sides of the carbon and energy market: the physical side (supply chain emissions, compliance constraints) and the financial side (EUA futures pricing, power market dynamics). The spark spread and its mean-reversion properties are the core trading intuition behind the signal engine.

---

## Stack

Python, Pandas, NumPy, SQLite, ENTSO-E API, Yahoo Finance
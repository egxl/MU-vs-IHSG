# Manchester United vs. IHSG Hypothesis

A data-driven backtesting tool to investigate whether **Manchester United match results correlate with Indonesian Stock Exchange (IHSG/^JKSE) market movements** on the next trading day.

## The Hypothesis

> When Manchester United wins a match, the IHSG tends to close **red** (negative) the following trading session.

This project fetches real match results and stock data, aligns them to the next available trading day, and computes statistical accuracy + a simulated short strategy.

---

## Features

- **Multi-source football data**: FBref scraping → Football-Data.org API → optional synthetic mock fallback
- **Local CSV caching**: avoids redundant network requests on re-runs
- **Statistical summary**: win count, red-day frequency, average returns
- **Visualizations**: bar chart of average returns + cumulative strategy curve

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/your-username/muihsghypothesis.git
cd muihsghypothesis
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

Open `muihsg.py` and replace the `FOOTBALL_API_KEY` constant with your own key from [football-data.org](https://www.football-data.org/). 

### 5. Configure Data Sources (Optional)

By default, the script will only use real data from FBref or the API. If both fail, it will stop. To enable the synthetic mock data generator for testing purposes:
1. Open `muihsg.py`.
2. Set `ENABLE_MOCK_FALLBACK = True`.

---

## Usage

```bash
python muihsg.py
```

The script will:
1. Load cached data if available, otherwise fetch live data
2. Align match dates to the next trading session
3. Print a statistical summary to the console
4. Display two charts

---

## Data Sources

| Source | Type | Notes |
|---|---|---|
| [FBref](https://fbref.com) | Scraping | Primary — full match logs |
| [football-data.org](https://www.football-data.org/) | API | Secondary fallback |
| Synthetic generator | Mock | Tertiary fallback (Disabled by default) |
| [Yahoo Finance (^JKSE)](https://finance.yahoo.com/quote/%5EJKSE/) | API via `yfinance` | IHSG daily data |

---

## Project Structure

```
muihsghypothesis/
├── muihsg.py           # Main analysis script
├── requirements.txt    # Python dependencies
├── README.md           # This file
└── .gitignore          # Excludes cache CSVs and build artifacts
```

> **Note:** CSV cache files (`*_cache.csv`) are excluded from version control via `.gitignore`. They are generated locally on first run.

---

## Disclaimer

This project is for **educational and entertainment purposes only**. It does not constitute financial advice. Correlation is not causation — especially when the cause is a football team.

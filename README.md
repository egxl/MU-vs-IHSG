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
- **Sophisticated Analytics Dashboard**: A premium 6-panel visualization including:
    - Average returns comparison
    - Return distribution density (KDE)
    - Hypothesis accuracy gauge
    - Cumulative strategy vs. Buy & Hold benchmark
    - Rolling 10-day correlation
    - Monthly performance heatmap
- **Smart Data Alignment**: Automatically clips charts to the MU match date range for accurate strategy visualization.

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

### 4. API Key Configuration

Open `muihsg.py` and replace the `FOOTBALL_API_KEY` constant with your own key from [football-data.org](https://www.football-data.org/). 

### 5. Configure Data Sources (Optional)

By default, the script will only use real data from FBref or the API. If both fail, it will stop. To enable the synthetic mock data generator for testing purposes:
1. Open `muihsg.py`.
2. Set `ENABLE_MOCK_FALLBACK = True`.

---

## Usage

```bash
# Run with default settings (uses local cache if available)
python muihsg.py

# Force refresh data (ignores cache and fetches fresh data)
python muihsg.py --refresh
```

The script will:
1. Load cached data (unless `--refresh` is used)
2. Align match dates to the next trading session
3. Print a detailed statistical summary to the console
4. Display a sophisticated 6-panel analytics dashboard

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

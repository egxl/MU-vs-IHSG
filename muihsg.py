import os
import requests
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import time
from datetime import datetime, timedelta

# ==========================================
# 1. CONSTANTS & CONFIGURATION
# ==========================================
MU_CACHE_FILE = "mu_history_cache.csv"
IHSG_CACHE_FILE = "ihsg_history_cache.csv"
MU_FBREF_ID = "19538871" # Manchester United ID on FBref
FOOTBALL_API_KEY = "1b5347948e7b4eb5a916e3c422555905" # From previous script

# ==========================================
# 2. FOOTBALL DATA MODULE
# ==========================================

def fetch_mu_history_fbref(years=5):
    """Scrapes MU match logs from FBref (Primary Source)."""
    all_matches = []
    current_year = datetime.now().year
    # More robust headers
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    print(f"Attempting to scrape MU match logs from FBref (Last {years} seasons)...")
    
    for i in range(years):
        season_start = current_year - i - 1
        season_end = current_year - i
        season_str = f"{season_start}-{season_end}"
        url = f"https://fbref.com/en/squads/{MU_FBREF_ID}/{season_str}/matchlogs/all_comps/Manchester-United-Match-Logs-All-Competitions"
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                tables = pd.read_html(response.text)
                df = tables[0]
                df.columns = [col[-1] if isinstance(col, tuple) else col for col in df.columns]
                
                if 'Date' in df.columns and 'Result' in df.columns:
                    df = df[['Date', 'Result']].dropna()
                    df['MU_Won'] = df['Result'].str.contains('W', na=False)
                    df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize(None)
                    all_matches.append(df)
                    print(f"  Successfully fetched {season_str} season.")
                
                time.sleep(5) # Respectful delay
            else:
                print(f"  [ERROR] FBref Status {response.status_code} for {season_str}")
        except Exception as e:
            print(f"  [ERROR] Scraping error for {season_str}: {e}")
            continue

    if all_matches:
        return pd.concat(all_matches).sort_values('Date').reset_index(drop=True)
    return pd.DataFrame()

def fetch_mu_matches_api(api_key, years=5):
    """Retrieves MU matches from football-data.org (Secondary Source)."""
    print(f"Attempting to fetch MU matches from Football-Data.org API...")
    url = "https://api.football-data.org/v4/teams/66/matches?status=FINISHED"
    headers = {"X-Auth-Token": api_key}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            matches = []
            for match in data.get('matches', []):
                home_team = match['homeTeam']['name']
                away_team = match['awayTeam']['name']
                winner = match['score']['winner']
                
                mu_won = (winner == 'HOME_TEAM' and 'Manchester United' in home_team) or \
                         (winner == 'AWAY_TEAM' and 'Manchester United' in away_team)
                
                match_date = pd.to_datetime(match['utcDate']).tz_localize(None).normalize()
                matches.append({'Date': match_date, 'MU_Won': mu_won})
            
            print(f"  Successfully fetched {len(matches)} matches from API.")
            return pd.DataFrame(matches)
        else:
            print(f"  [ERROR] API Status {response.status_code}")
    except Exception as e:
        print(f"  [ERROR] API request failed: {e}")
    
    return pd.DataFrame()

def generate_mock_mu_data(years=5):
    """Generates synthetic MU match data (Fallback)."""
    print("Generating mock MU match data for fallback demonstration...")
    end_date = datetime.now()
    start_date = end_date - timedelta(days=years*365)
    dates = pd.date_range(start=start_date, end=end_date, freq='W-SAT') 
    np.random.seed(42)
    wins = np.random.choice([True, False], size=len(dates), p=[0.55, 0.45])
    return pd.DataFrame({'Date': dates, 'MU_Won': wins})

# ==========================================
# 3. STOCK DATA MODULE
# ==========================================
def fetch_ihsg_data(years=6, use_cache=True):
    """Fetches IHSG data from Yahoo Finance with caching."""
    if use_cache and os.path.exists(IHSG_CACHE_FILE):
        print(f"[CACHE] Loading IHSG data from {IHSG_CACHE_FILE}")
        ihsg = pd.read_csv(IHSG_CACHE_FILE, index_col=0, parse_dates=True)
    else:
        print(f"Fetching IHSG (^JKSE) data for the last {years} years...")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=years*365)
        ihsg = yf.download("^JKSE", start=start_date, end=end_date, progress=False)
        
        if isinstance(ihsg.columns, pd.MultiIndex):
            ihsg.columns = ihsg.columns.get_level_values(0)
            
        ihsg.to_csv(IHSG_CACHE_FILE)
        print(f"[SUCCESS] IHSG data saved to {IHSG_CACHE_FILE}")
    
    ihsg = ihsg.sort_index()
    ihsg['Daily_Return'] = ihsg['Close'].pct_change()
    ihsg['Goes_Red'] = ihsg['Close'] < ihsg['Close'].shift(1)
    ihsg.index = pd.to_datetime(ihsg.index).tz_localize(None).normalize()
    return ihsg.dropna()

# ==========================================
# 4. ALIGNMENT & BACKTEST ENGINE
# ==========================================
def run_analysis(use_cache=True):
    print("="*60)
    print("MU vs IHSG CORRELATION ENGINE")
    print("="*60)
    
    # 1. Get Football Data
    mu_data = pd.DataFrame()
    if use_cache and os.path.exists(MU_CACHE_FILE):
        print(f"[CACHE] Loading MU history from {MU_CACHE_FILE}")
        mu_data = pd.read_csv(MU_CACHE_FILE, parse_dates=['Date'])
    
    if mu_data.empty:
        # Try Scraper
        mu_data = fetch_mu_history_fbref(years=5)
        
        # Try API if Scraper failed
        if mu_data.empty:
            mu_data = fetch_mu_matches_api(FOOTBALL_API_KEY)
            
        # Fallback to Mock
        if mu_data.empty:
            mu_data = generate_mock_mu_data()
        else:
            mu_data.to_csv(MU_CACHE_FILE, index=False)
            print(f"[SUCCESS] MU history cached to {MU_CACHE_FILE}")

    # 2. Get Stock Data
    ihsg_data = fetch_ihsg_data(years=6, use_cache=use_cache)
    
    # 3. Align & Merge
    print("Aligning match dates to next available trading session...")
    trading_days = ihsg_data.index.unique().sort_values()
    
    def get_next_trading_day(match_date):
        future_days = trading_days[trading_days > match_date]
        return future_days[0] if not future_days.empty else pd.NaT

    mu_data['Next_Trading_Day'] = mu_data['Date'].apply(get_next_trading_day)
    final_df = mu_data.dropna(subset=['Next_Trading_Day']).merge(ihsg_data, left_on='Next_Trading_Day', right_index=True)

    # 4. Statistics
    wins_only = final_df[final_df['MU_Won'] == True]
    total_wins = len(wins_only)
    success_cases = wins_only['Goes_Red'].sum()
    accuracy = (success_cases / total_wins) * 100 if total_wins > 0 else 0
    
    print("\n" + "="*40)
    print("STATISTICAL SUMMARY")
    print("="*40)
    print(f"Total MU Wins Analyzed:  {total_wins}")
    print(f"IHSG Closed Red Next:    {success_cases}")
    print(f"Hypothesis Accuracy:     {accuracy:.2f}%")
    print(f"Avg Return After Win:    {wins_only['Daily_Return'].mean()*100:.4f}%")
    print("="*40)
    
    # 5. Visualize
    sns.set_theme(style="darkgrid")
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    
    # Plot A: Returns Comparison
    avg_ret_win = wins_only['Daily_Return'].mean() * 100
    avg_ret_other = final_df[final_df['MU_Won'] == False]['Daily_Return'].mean() * 100
    
    sns.barplot(x=['After MU Win', 'After Loss/Draw'], y=[avg_ret_win, avg_ret_other], ax=axes[0], palette=['#e74c3c', '#34495e'])
    axes[0].set_title('Average IHSG Daily Return (%)', fontsize=14, fontweight='bold')
    axes[0].axhline(0, color='black', linewidth=1.2)
    
    # Plot B: Cumulative Strategy
    ihsg_data['Strategy_Return'] = 0.0
    win_next_days = wins_only['Next_Trading_Day'].tolist()
    ihsg_data.loc[ihsg_data.index.isin(win_next_days), 'Strategy_Return'] = -ihsg_data['Daily_Return']
    ihsg_data['Cumulative_Return'] = (1 + ihsg_data['Strategy_Return']).cumprod() - 1
    
    axes[1].plot(ihsg_data.index, ihsg_data['Cumulative_Return'] * 100, color='#27ae60', linewidth=2)
    axes[1].fill_between(ihsg_data.index, ihsg_data['Cumulative_Return'] * 100, color='#2ecc71', alpha=0.2)
    axes[1].set_title('Strategy: Short IHSG After MU Win', fontsize=14, fontweight='bold')
    axes[1].set_ylabel('Cumulative Return (%)')
    
    plt.suptitle('Manchester United vs. Indonesian Stock Exchange (IHSG)', fontsize=18, fontweight='bold')
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.show()

if __name__ == "__main__":
    run_analysis()
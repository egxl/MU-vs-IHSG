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

# DATA SOURCE CONFIGURATION
# Set to True to enable "Synthetic generator / Mock Tertiary fallback" if real data retrieval fails
ENABLE_MOCK_FALLBACK = False

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
            
        # Fallback to Mock (Synthetic generator)
        if mu_data.empty:
            if ENABLE_MOCK_FALLBACK:
                mu_data = generate_mock_mu_data()
            else:
                print("\n" + "!"*60)
                print("CRITICAL: No MU match data found from scraper or API.")
                print("Mock fallback is currently DISABLED by default.")
                print("To enable synthetic data for testing, set 'ENABLE_MOCK_FALLBACK = True' in the configuration.")
                print("!"*40 + "\n")
                return
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
    others = final_df[final_df['MU_Won'] == False]
    total_wins = len(wins_only)
    success_cases = wins_only['Goes_Red'].sum()
    accuracy = (success_cases / total_wins) * 100 if total_wins > 0 else 0
    
    avg_ret_win = wins_only['Daily_Return'].mean() * 100 if total_wins > 0 else 0
    avg_ret_other = others['Daily_Return'].mean() * 100 if len(others) > 0 else 0
    
    # Calculate Strategy Return (Short IHSG after MU Win)
    ihsg_data['Strategy_Return'] = 0.0
    win_next_days = final_df[final_df['MU_Won'] == True]['Next_Trading_Day'].unique()
    # If MU wins, we short (profit if IHSG goes red)
    ihsg_data.loc[ihsg_data.index.isin(win_next_days), 'Strategy_Return'] = -ihsg_data.loc[ihsg_data.index.isin(win_next_days), 'Daily_Return']
    ihsg_data['Cumulative_Return'] = (1 + ihsg_data['Strategy_Return']).cumprod() - 1
    
    print("\n" + "="*40)
    print("STATISTICAL SUMMARY")
    print("="*40)
    print(f"Total MU Wins Analyzed:  {total_wins}")
    print(f"IHSG Closed Red Next:    {success_cases}")
    print(f"Hypothesis Accuracy:     {accuracy:.2f}%")
    print(f"Avg Return After Win:    {avg_ret_win:.4f}%")
    print(f"Avg Return After Loss:   {avg_ret_other:.4f}%")
    print("="*40)
    
    # ==========================================
    # 5. SOPHISTICATED VISUALIZATION DASHBOARD
    # ==========================================
    # Set up premium styling with custom theme
    plt.style.use('seaborn-v0_8-whitegrid')
    
    # Custom color palette - sophisticated dark theme
    COLORS = {
        'primary': '#E74C3C',       # Manchester United Red
        'secondary': '#1ABC9C',     # Teal accent
        'background': '#2C3E50',    # Dark slate
        'surface': '#34495E',       # Lighter slate
        'text': '#ECF0F1',          # Off-white
        'win': '#27AE60',           # Green for wins
        'loss': '#E74C3C',          # Red for losses
        'neutral': '#95A5A6',       # Gray
    }
    
    # Create sophisticated 2x2 dashboard
    fig = plt.figure(figsize=(18, 14))
    fig.patch.set_facecolor('#1a1a2e')
    
    # Use GridSpec for advanced layout
    gs = fig.add_gridspec(3, 3, hspace=0.35, wspace=0.3, 
                         left=0.06, right=0.94, top=0.92, bottom=0.05)
    
    # Color helper for text
    def color_text(color='#ECF0F1'):
        return {'color': color, 'fontsize': 11, 'fontweight': 'bold'}
    
    # ------------------------------------------
    # PANEL A: Enhanced Returns Comparison (Top Left)
    # ------------------------------------------
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.set_facecolor('#16213e')
    
    categories = ['After MU Win', 'After Loss/Draw']
    returns = [avg_ret_win, avg_ret_other]
    bar_colors = [COLORS['win'], COLORS['neutral']]
    
    bars = ax1.bar(categories, returns, color=bar_colors, edgecolor='white', 
                   linewidth=1.5, width=0.6, alpha=0.85)
    
    # Add value labels on bars
    for bar, val in zip(bars, returns):
        height = bar.get_height()
        ax1.annotate(f'{val:.3f}%',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 5), textcoords="offset points",
                    ha='center', va='bottom', color='white', fontsize=12, fontweight='bold')
    
    ax1.axhline(0, color='white', linewidth=1, linestyle='--', alpha=0.5)
    ax1.set_title('Average IHSG Daily Return', fontsize=14, fontweight='bold', color='white', pad=15)
    ax1.set_ylabel('Return (%)', color='white', fontsize=10)
    ax1.tick_params(colors='white')
    for spine in ax1.spines.values():
        spine.set_color('white')
        spine.set_alpha(0.3)
    
    # ------------------------------------------
    # PANEL B: Distribution Density Plot (Top Center)
    # ------------------------------------------
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.set_facecolor('#16213e')
    
    win_returns = wins_only['Daily_Return'].dropna() * 100
    other_returns = final_df[final_df['MU_Won'] == False]['Daily_Return'].dropna() * 100
    
    # KDE plots with filled areas
    if len(win_returns) > 3:
        sns.kdeplot(win_returns, ax=ax2, color=COLORS['win'], fill=True, alpha=0.4, 
                   linewidth=2, label='After MU Win')
    if len(other_returns) > 3:
        sns.kdeplot(other_returns, ax=ax2, color=COLORS['neutral'], fill=True, alpha=0.4, 
                   linewidth=2, label='After Loss/Draw')
    
    ax2.axvline(0, color='white', linewidth=1, linestyle='--', alpha=0.5)
    ax2.set_title('Return Distribution Density', fontsize=14, fontweight='bold', color='white', pad=15)
    ax2.set_xlabel('Daily Return (%)', color='white', fontsize=10)
    ax2.set_ylabel('Density', color='white', fontsize=10)
    ax2.legend(facecolor=COLORS['surface'], edgecolor='white', labelcolor='white')
    ax2.tick_params(colors='white')
    for spine in ax2.spines.values():
        spine.set_color('white')
        spine.set_alpha(0.3)
    
    # ------------------------------------------
    # PANEL C: Win Rate Gauge (Top Right)
    # ------------------------------------------
    ax3 = fig.add_subplot(gs[0, 2])
    ax3.set_facecolor('#16213e')
    
    # Create a horizontal bar showing win/red relationship
    win_count = len(wins_only)
    red_count = success_cases
    non_red_count = win_count - red_count
    
    segments = [red_count, non_red_count]
    segment_colors = [COLORS['loss'], COLORS['neutral']]
    
    # Stacked horizontal bar
    left_pos = 0
    for seg, color in zip(segments, segment_colors):
        ax3.barh(0, seg, left=left_pos, color=color, edgecolor='white', linewidth=1, height=0.5)
        left_pos += seg
    
    ax3.set_xlim(0, win_count)
    ax3.set_ylim(-0.5, 0.5)
    ax3.set_title('IHSG Red Days After MU Win', fontsize=14, fontweight='bold', color='white', pad=15)
    ax3.text(win_count/2, 0.3, f'{accuracy:.1f}%', ha='center', va='center', 
             fontsize=24, fontweight='bold', color='white')
    ax3.text(win_count/2, -0.3, f'n={win_count}', ha='center', va='center', 
             fontsize=10, color='white', alpha=0.7)
    ax3.set_yticks([])
    ax3.tick_params(colors='white')
    for spine in ax3.spines.values():
        spine.set_color('white')
        spine.set_alpha(0.3)
    
    # ------------------------------------------
    # PANEL D: Cumulative Strategy Performance (Middle Row - Span 2)
    # ------------------------------------------
    ax4 = fig.add_subplot(gs[1, :2])
    ax4.set_facecolor('#16213e')
    
    # Plot cumulative returns with gradient fill
    ax4.plot(ihsg_data.index, ihsg_data['Cumulative_Return'] * 100, 
             color=COLORS['secondary'], linewidth=2.5, label='Strategy Return', alpha=0.9)
    ax4.fill_between(ihsg_data.index, ihsg_data['Cumulative_Return'] * 100, 
                     color=COLORS['secondary'], alpha=0.15)
    
    # Add benchmark (buy & hold)
    ihsg_data['BuyHold_Return'] = ihsg_data['Daily_Return']
    ihsg_data['Cumulative_BH'] = (1 + ihsg_data['BuyHold_Return']).cumprod() - 1
    ax4.plot(ihsg_data.index, ihsg_data['Cumulative_BH'] * 100, 
             color=COLORS['neutral'], linewidth=1.5, linestyle='--', 
             label='IHSG Buy & Hold', alpha=0.7)
    
    ax4.axhline(0, color='white', linewidth=1, linestyle='-', alpha=0.3)
    ax4.set_title('Cumulative Strategy Performance: Short IHSG After MU Win', 
                  fontsize=14, fontweight='bold', color='white', pad=15)
    ax4.set_ylabel('Cumulative Return (%)', color='white', fontsize=10)
    ax4.legend(facecolor=COLORS['surface'], edgecolor='white', labelcolor='white', loc='upper left')
    ax4.tick_params(colors='white')
    ax4.grid(True, alpha=0.2, color='white')
    for spine in ax4.spines.values():
        spine.set_color('white')
        spine.set_alpha(0.3)
    
    # ------------------------------------------
    # PANEL E: Rolling Correlation (Middle Right)
    # ------------------------------------------
    ax5 = fig.add_subplot(gs[1, 2])
    ax5.set_facecolor('#16213e')
    
    # Calculate rolling correlation (30-day window)
    final_df_sorted = final_df.sort_values('Date').copy()
    final_df_sorted['Rolling_Corr'] = final_df_sorted['MU_Won'].astype(int).rolling(window=10).corr(final_df_sorted['Daily_Return'])
    
    ax5.plot(final_df_sorted['Date'], final_df_sorted['Rolling_Corr'], 
             color=COLORS['primary'], linewidth=2, alpha=0.8)
    ax5.fill_between(final_df_sorted['Date'], final_df_sorted['Rolling_Corr'], 
                     color=COLORS['primary'], alpha=0.2)
    ax5.axhline(0, color='white', linewidth=1, linestyle='--', alpha=0.5)
    ax5.set_title('Rolling Correlation (10-day)', fontsize=14, fontweight='bold', color='white', pad=15)
    ax5.set_ylabel('Correlation', color='white', fontsize=10)
    ax5.tick_params(colors='white')
    ax5.grid(True, alpha=0.2, color='white')
    for spine in ax5.spines.values():
        spine.set_color('white')
        spine.set_alpha(0.3)
    
    # ------------------------------------------
    # PANEL F: Monthly Heatmap (Bottom Row - Span 3)
    # ------------------------------------------
    ax6 = fig.add_subplot(gs[2, :])
    ax6.set_facecolor('#16213e')
    
    # Create monthly aggregation
    final_df_monthly = final_df.copy()
    final_df_monthly['YearMonth'] = final_df_monthly['Date'].dt.to_period('M')
    monthly_pivot = final_df_monthly.pivot_table(
        values='Daily_Return', 
        index=final_df_monthly['YearMonth'].astype(str),
        columns='MU_Won',
        aggfunc='mean'
    ) * 100
    
    # Create heatmap data
    if not monthly_pivot.empty:
        monthly_pivot.columns = ['Loss/Draw', 'MU Win']
        monthly_pivot = monthly_pivot.tail(24)  # Last 24 months
        
        sns.heatmap(monthly_pivot, ax=ax6, cmap='RdYlGn', center=0, annot=True, 
                   fmt='.2f', linewidths=0.5, linecolor='white',
                   cbar_kws={'label': 'Avg Return (%)'},
                   annot_kws={'color': 'white', 'fontsize': 9})
        
        ax6.set_title('Monthly Returns: After MU Win vs Loss/Draw', 
                      fontsize=14, fontweight='bold', color='white', pad=15)
        ax6.set_xlabel('Match Outcome', color='white', fontsize=10)
        ax6.set_ylabel('Month', color='white', fontsize=10)
        ax6.tick_params(colors='white', axis='x', labelrotation=0)
        ax6.tick_params(colors='white', axis='y', labelrotation=0)
        for spine in ax6.spines.values():
            spine.set_color('white')
            spine.set_alpha(0.3)
    
    # ------------------------------------------
    # MAIN TITLE
    # ------------------------------------------
    fig.suptitle('Manchester United vs. Indonesian Stock Exchange (IHSG) Analysis Dashboard', 
                 fontsize=20, fontweight='bold', color='white', y=0.98)
    
    # Add subtitle with key stats
    fig.text(0.5, 0.95, f'Hypothesis Accuracy: {accuracy:.1f}% | Total Matches: {total_wins} | Data Period: {final_df["Date"].min().strftime("%Y")} - {final_df["Date"].max().strftime("%Y")}', 
             ha='center', va='top', fontsize=11, color='#BDC3C7', style='italic')
    
    plt.show()

if __name__ == "__main__":
    run_analysis()
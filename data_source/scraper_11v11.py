import pandas as pd
import os
import re
from datetime import datetime

def parse_local_htm_files(directory="11v11_match_records"):
    all_matches = []
    
    if not os.path.exists(directory):
        print(f"[ERROR] Directory {directory} not found.")
        return None

    # Regex for a single match entry in the joined text
    # It looks for Date, followed by Match, then Result (W|L|D), then Score (\d+-\d+), then Competition
    # We use non-greedy matching (.*?) for Match and Competition.
    match_pattern = re.compile(r"(\d{2} \w{3} \d{4})\s+(.*?)\s+([WLD])\s+(\d+-\d+|v)\s+(.*?)(?=\d{2} \w{3} \d{4}|©|Transfers|$)")

    for filename in os.listdir(directory):
        if filename.endswith(".htm"):
            filepath = os.path.join(directory, filename)
            print(f"Parsing {filename}...")
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    # Join all lines into a single string, replacing newlines with spaces
                    content = " ".join([line.strip() for line in f.readlines()])
                
                # Remove extra spaces
                content = re.sub(r'\s+', ' ', content)
                
                # Find all matches
                found = match_pattern.findall(content)
                
                season_matches = []
                for entry in found:
                    date_str, match_str, result_str, score_str, competition_str = entry
                    
                    # Clean match_str (remove links and extra spaces)
                    match_str = re.sub(r'<.*?>', '', match_str).strip()
                    competition_str = competition_str.strip()
                    
                    try:
                        date_obj = datetime.strptime(date_str, "%d %b %Y")
                        formatted_date = date_obj.strftime("%Y-%m-%d")
                    except ValueError:
                        continue
                        
                    mu_won = result_str == 'W'
                    
                    season_matches.append({
                        'Date': formatted_date,
                        'Match': match_str,
                        'Result': result_str,
                        'Score': score_str,
                        'Competition': competition_str,
                        'MU_Won': mu_won
                    })
                
                print(f"  Found {len(season_matches)} matches.")
                all_matches.extend(season_matches)
                
            except Exception as e:
                print(f"  [ERROR] Failed to parse {filename}: {e}")

    if all_matches:
        df = pd.DataFrame(all_matches)
        # Drop duplicates and sort
        df = df.drop_duplicates(subset=['Date', 'Match']).sort_values('Date')
        
        output_file = "../mu_history_2000_2026.csv"
        df.to_csv(output_file, index=False)
        print(f"\n[SUCCESS] Processed {len(df)} total unique matches and saved to {output_file}")
        
        # Show first few rows for verification
        print("\nSample Data:")
        print(df.head())
        print(df.tail())
        
        return df
    else:
        print("\n[ERROR] No matches were parsed.")
        return None

if __name__ == "__main__":
    parse_local_htm_files()

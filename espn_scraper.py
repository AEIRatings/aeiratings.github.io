import pandas as pd
import os
import requests
import re
from io import StringIO

# --- CONFIGURATION ---
# The target URL for ESPN NFL Standings
ESPN_STANDINGS_URL = "https://www.espn.com/nfl/standings"
# Path to the NFL CSV file relative to the script location
CSV_PATH = 'data/nfl.csv'

# Mapping from a unique part of an ESPN team name to the full name used in nfl.csv.
# This handles subtle differences and helps ensure clean matches.
TEAM_NAME_MAP = {
    'Bills': 'Buffalo Bills', 'Dolphins': 'Miami Dolphins', 'Patriots': 'New England Patriots', 'Jets': 'New York Jets',
    'Ravens': 'Baltimore Ravens', 'Bengals': 'Cincinnati Bengals', 'Browns': 'Cleveland Browns', 'Steelers': 'Pittsburgh Steelers',
    'Texans': 'Houston Texans', 'Colts': 'Indianapolis Colts', 'Jaguars': 'Jacksonville Jaguars', 'Titans': 'Tennessee Titans',
    'Broncos': 'Denver Broncos', 'Chiefs': 'Kansas City Chiefs', 'Raiders': 'Las Vegas Raiders', 'Chargers': 'Los Angeles Chargers',
    'Cowboys': 'Dallas Cowboys', 'Giants': 'New York Giants', 'Eagles': 'Philadelphia Eagles', 'Commanders': 'Washington Commanders',
    'Bears': 'Chicago Bears', 'Lions': 'Detroit Lions', 'Packers': 'Green Bay Packers', 'Vikings': 'Minnesota Vikings',
    'Falcons': 'Atlanta Falcons', 'Panthers': 'Carolina Panthers', 'Saints': 'New Orleans Saints', 'Buccaneers': 'Tampa Bay Buccaneers',
    'Cardinals': 'Arizona Cardinals', 'Rams': 'Los Angeles Rams', '49ers': 'San Francisco 49ers', 'Seahawks': 'Seattle Seahawks',
}

def clean_team_name(team_name):
    """Cleans the team name scraped from ESPN for matching against nfl.csv."""
    # Strip any extra text that might be appended (like a current rank/seed)
    # The 'Team' column often contains HTML/extra text. We look for a keyword match.
    for keyword, full_name in TEAM_NAME_MAP.items():
        if keyword in team_name:
            return full_name
    return team_name # Fallback, likely won't match a team name

def scrape_espn_standings(url, local_teams):
    """
    Fetches NFL standings from ESPN and returns a DataFrame of Team, Wins, and Losses.
    """
    print(f"-> Attempting to scrape standings from {url}...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status() 
    except Exception as e:
        print(f"ERROR: Failed to fetch data. Error detail: {e}")
        return None

    all_standings_data = []

    try:
        # pd.read_html reads tables. ESPN divides standings into multiple tables (one per division).
        tables = pd.read_html(response.text)
    except Exception as e:
        print(f"ERROR: Failed to parse HTML tables: {e}")
        return None
        
    for table in tables:
        # Flatten multi-level columns and strip whitespace/special characters
        table.columns = [''.join(col).strip() for col in table.columns.values]
        
        # Look for the characteristic headers: 'Team', 'W', and 'L' columns 
        # (W/L columns are nested under a 'Record' header in ESPN, often flattening to 'W' and 'L')
        team_cols = [col for col in table.columns if 'Team' in col or 'Name' in col]
        win_cols = [col for col in table.columns if col == 'W']
        loss_cols = [col for col in table.columns if col == 'L']
        
        if team_cols and win_cols and loss_cols:
            df = table[[team_cols[0], win_cols[0], loss_cols[0]]].copy()
            df.columns = ['Team', 'Wins', 'Losses']
            
            # Apply cleaning and map to official team names
            df['Team'] = df['Team'].apply(clean_team_name)
            
            all_standings_data.append(df)
            
    if not all_standings_data:
        print("ERROR: Could not find tables with Team, W, and L data. Check ESPN's page structure.")
        return None
        
    # Combine all scraped tables and filter to only teams present in the local CSV
    all_standings = pd.concat(all_standings_data, ignore_index=True)
    all_standings = all_standings[all_standings['Team'].isin(set(local_teams))]

    return all_standings

def update_nfl_csv(scraped_data):
    """Updates the local nfl.csv with the scraped Wins/Losses data."""
    if not os.path.exists(CSV_PATH):
        print(f"CRITICAL ERROR: Local CSV file not found at {CSV_PATH}")
        return False

    try:
        local_df = pd.read_csv(CSV_PATH)
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to read local CSV: {e}")
        return False
        
    print(f"-> Read local CSV with {len(local_df)} teams.")

    # Convert Wins/Losses to numeric types to ensure successful update/merge
    scraped_data['Wins'] = pd.to_numeric(scraped_data['Wins'], errors='coerce', downcast='integer')
    scraped_data['Losses'] = pd.to_numeric(scraped_data['Losses'], errors='coerce', downcast='integer')
    scraped_data = scraped_data.dropna(subset=['Team', 'Wins', 'Losses'])

    update_df = scraped_data[['Team', 'Wins', 'Losses']].copy()

    # Set 'Team' as index for easy update
    local_df = local_df.set_index('Team')
    update_df = update_df.set_index('Team')

    # Identify the teams present in both sets
    teams_to_update = local_df.index.intersection(update_df.index)
    
    if teams_to_update.empty:
        print("Warning: No matching teams found between scraped data and local CSV. No update performed.")
        return False

    # Update the Wins and Losses columns in the local DataFrame
    local_df.loc[teams_to_update, ['Wins', 'Losses']] = update_df.loc[teams_to_update, ['Wins', 'Losses']]

    # Convert updated columns back to string format required for your existing CSV data
    local_df['Wins'] = local_df['Wins'].astype(float).astype(int).astype(str)
    local_df['Losses'] = local_df['Losses'].astype(float).astype(int).astype(str)
    
    final_df = local_df.reset_index()

    # Write the updated data back to CSV
    try:
        final_df.to_csv(CSV_PATH, index=False)
        print(f"✅ Successfully updated {CSV_PATH} with W-L records for {len(teams_to_update)} teams.")
        return True
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to write to CSV: {e}")
        return False

if __name__ == "__main__":
    
    if os.path.exists(CSV_PATH):
        local_df = pd.read_csv(CSV_PATH)
        local_teams = local_df['Team'].unique()
    else:
        print(f"CRITICAL ERROR: Local CSV file not found at {CSV_PATH}. Cannot proceed.")
        local_teams = []
        
    if local_teams.any():
        standings_data = scrape_espn_standings(ESPN_STANDINGS_URL, local_teams)
        
        if standings_data is not None and not standings_data.empty:
            update_nfl_csv(standings_data)
        else:
            print("Scraping failed or returned no valid standing data after filtering. No changes made.")
            
    print("--- ESPN Standings Scraper Finished ---")

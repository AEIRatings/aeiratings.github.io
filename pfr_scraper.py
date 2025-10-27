import pandas as pd
import os
import re
import requests
from io import StringIO

# --- CONFIGURATION ---
# The URL for the main 2025 NFL Standings page on PFR
NFL_STANDINGS_URL = "https://www.pro-football-reference.com/years/2025/"
# Path to the nfl.csv file. Since the script will likely run from the root 
# of your 'aeiratings.github.io' repository, this path is correct.
CSV_PATH = 'data/nfl.csv'

# Map from PFR abbreviation (Tm) to the full team name used in nfl.csv
TEAM_MAP = {
    'NWE': 'New England Patriots', 'BUF': 'Buffalo Bills', 'MIA': 'Miami Dolphins', 'NYJ': 'New York Jets',
    'BAL': 'Baltimore Ravens', 'CIN': 'Cincinnati Bengals', 'CLE': 'Cleveland Browns', 'PIT': 'Pittsburgh Steelers',
    'HOU': 'Houston Texans', 'IND': 'Indianapolis Colts', 'JAX': 'Jacksonville Jaguars', 'TEN': 'Tennessee Titans',
    'DEN': 'Denver Broncos', 'KAN': 'Kansas City Chiefs', 'LVR': 'Las Vegas Raiders', 'LAC': 'Los Angeles Chargers',
    'DAL': 'Dallas Cowboys', 'NYG': 'New York Giants', 'PHI': 'Philadelphia Eagles', 'WAS': 'Washington Commanders',
    'CHI': 'Chicago Bears', 'DET': 'Detroit Lions', 'GNB': 'Green Bay Packers', 'MIN': 'Minnesota Vikings',
    'ATL': 'Atlanta Falcons', 'CAR': 'Carolina Panthers', 'NOR': 'New Orleans Saints', 'TAM': 'Tampa Bay Buccaneers',
    'ARI': 'Arizona Cardinals', 'LAR': 'Los Angeles Rams', 'SFO': 'San Francisco 49ers', 'SEA': 'Seattle Seahawks',
}

def scrape_pfr_standings(url):
    """
    Fetches raw HTML from PFR, extracts the commented-out tables by ID,
    and returns a combined DataFrame of wins and losses.
    """
    print(f"-> Attempting to scrape standings from {url}...")
    
    # --- FIX: Using a robust User-Agent to bypass 403 Forbidden ---
    headers = {
        # A recent, full browser User-Agent string
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    try:
        # Use requests to fetch raw page content with the new headers
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status() # Raise exception for HTTP errors (like the original 403)
        html_content = response.text
    except Exception as e:
        print(f"ERROR: Failed to fetch data. Error detail: {e}")
        return None

    scraped_tables = {}
    
    # The scraping logic remains the same (searching for commented-out tables)
    for conf_id in ['AFC', 'NFC']:
        # Regex to find the table embedded inside an HTML comment based on its ID
        match = re.search(r'', html_content, re.DOTALL)
        
        if match:
            # Extract the raw table HTML string, removing the comment tags
            table_html = match.group(0).replace('', '')
            try:
                # Use StringIO to let pd.read_html parse the string fragment
                df = pd.read_html(StringIO(table_html))[0]
                
                # Data cleaning steps based on PFR table structure
                # Rename columns and filter out division header rows
                df = df.iloc[1:].rename(columns={'Tm': 'PFR_Tm', 'W': 'Wins', 'L': 'Losses'})
                df = df[['PFR_Tm', 'Wins', 'Losses']]
                df = df[~df['PFR_Tm'].astype(str).str.contains('FC')]
                
                scraped_tables[conf_id] = df
            except Exception as e:
                print(f"Warning: Failed to parse {conf_id} table data in memory: {e}")
                
    if not scraped_tables:
        print("ERROR: No AFC or NFC tables could be successfully parsed from the page source.")
        return None

    # Combine the AFC and NFC tables
    all_standings = pd.concat(scraped_tables.values(), ignore_index=True)
    return all_standings

def update_nfl_csv(scraped_data):
    """Updates the local nfl.csv with the scraped Wins/Losses data."""
    if not os.path.exists(CSV_PATH):
        print(f"CRITICAL ERROR: Local CSV file not found at {CSV_PATH}")
        return

    try:
        local_df = pd.read_csv(CSV_PATH)
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to read local CSV: {e}")
        return
        
    print(f"-> Read local CSV with {len(local_df)} teams.")

    # Map PFR abbreviations to full team names
    scraped_data['Team'] = scraped_data['PFR_Tm'].str.upper().map(TEAM_MAP)
    
    # Convert Wins/Losses to numeric types
    scraped_data['Wins'] = pd.to_numeric(scraped_data['Wins'], errors='coerce', downcast='integer')
    scraped_data['Losses'] = pd.to_numeric(scraped_data['Losses'], errors='coerce', downcast='integer')
    scraped_data = scraped_data.dropna(subset=['Team', 'Wins', 'Losses'])

    update_df = scraped_data[['Team', 'Wins', 'Losses']].copy()

    # Update the local DataFrame
    local_df = local_df.set_index('Team')
    update_df = update_df.set_index('Team')

    # Update only the Wins and Losses columns
    local_df.update(update_df[['Wins', 'Losses']])

    # Convert updated columns back to the expected string format
    local_df['Wins'] = local_df['Wins'].astype(float).astype(int).astype(str)
    local_df['Losses'] = local_df['Losses'].astype(float).astype(int).astype(str)
    
    final_df = local_df.reset_index()

    # Write the updated data back to CSV
    try:
        final_df.to_csv(CSV_PATH, index=False)
        print(f"✅ Successfully updated {CSV_PATH} with W-L records for {len(final_df)} teams.")
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to write to CSV: {e}")

if __name__ == "__main__":
    print("--- Starting PFR Standings Scraper ---")
    
    standings_data = scrape_pfr_standings(NFL_STANDINGS_URL)
    
    if standings_data is not None and not standings_data.empty:
        update_nfl_csv(standings_data)
    else:
        print("Scraping failed or returned no valid standing data. No changes made.")
        
    print("--- PFR Standings Scraper Finished ---")

import pandas as pd
import os
import re
import requests
from io import StringIO

# --- CONFIGURATION ---
# The URL for the main 2025 NFL Standings page on PFR
NFL_STANDINGS_URL = "https://www.pro-football-reference.com/years/2025/index.htm"
# Path to the nfl.csv file relative to where the script is executed
CSV_PATH = 'data/nfl.csv'

# Map from PFR abbreviation (Tm) to the full team name used in nfl.csv
# This map is crucial for matching the scraped data to your existing CSV.
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
    
    try:
        # Use requests to fetch raw page content
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status() # Raise an exception for bad status codes
        html_content = response.text
    except Exception as e:
        print(f"ERROR: Failed to fetch data. Ensure URL is correct: {e}")
        return None

    scraped_tables = {}
    
    # Iterate through both conference tables (IDs are inside comments on PFR pages)
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
                # The first row is typically division headers, so we skip it (iloc[1:])
                df = df.iloc[1:].rename(columns={'Tm': 'PFR_Tm', 'W': 'Wins', 'L': 'Losses'})
                
                # Select essential columns
                df = df[['PFR_Tm', 'Wins', 'Losses']]
                
                # Filter out the remaining header/divider rows that still contain 'FC' in the Tm column
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
        # 1. Read the local data into a DataFrame
        local_df = pd.read_csv(CSV_PATH)
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to read local CSV: {e}")
        return
        
    print(f"-> Read local CSV with {len(local_df)} teams.")

    # 2. Map PFR abbreviations to full team names
    # Create a 'Team' column in the scraped data to match the local CSV
    scraped_data['Team'] = scraped_data['PFR_Tm'].str.upper().map(TEAM_MAP)
    
    # Convert Wins/Losses to proper numeric types for reliable merging/updating
    scraped_data['Wins'] = pd.to_numeric(scraped_data['Wins'], errors='coerce', downcast='integer')
    scraped_data['Losses'] = pd.to_numeric(scraped_data['Losses'], errors='coerce', downcast='integer')
    scraped_data = scraped_data.dropna(subset=['Team', 'Wins', 'Losses'])

    # Select only the relevant columns for updating (Team, Wins, Losses)
    update_df = scraped_data[['Team', 'Wins', 'Losses']].copy()

    # 3. Update the local DataFrame
    # Set 'Team' as index for aligned update
    local_df = local_df.set_index('Team')
    update_df = update_df.set_index('Team')

    # Use the .update() method to only update matching columns/rows, preserving other data like 'Elo'
    # Ensure the columns being updated in the local_df are of the correct type (numeric) if necessary, 
    # then convert back to string as your original file has them as strings.
    local_df.update(update_df[['Wins', 'Losses']])

    # Convert updated columns back to integer then string for consistency with your file structure
    local_df['Wins'] = local_df['Wins'].astype(float).astype(int).astype(str)
    local_df['Losses'] = local_df['Losses'].astype(float).astype(int).astype(str)
    
    # Reset index and save
    final_df = local_df.reset_index()

    # 4. Write the updated data back to CSV
    try:
        final_df.to_csv(CSV_PATH, index=False)
        print(f"✅ Successfully updated {CSV_PATH} with W-L records for {len(final_df)} teams.")
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to write to CSV: {e}")

if __name__ == "__main__":
    print("--- Starting PFR Standings Scraper ---")
    
    # Run the scraping process
    standings_data = scrape_pfr_standings(NFL_STANDINGS_URL)
    
    if standings_data is not None and not standings_data.empty:
        update_nfl_csv(standings_data)
    else:
        print("Scraping failed or returned no valid standing data. No changes made.")
        
    print("--- PFR Standings Scraper Finished ---")

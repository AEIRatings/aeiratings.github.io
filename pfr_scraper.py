import pandas as pd
import os
import re

# --- CONFIGURATION ---
# The URL for the main 2025 NFL Standings page on PFR
NFL_STANDINGS_URL = "https://www.pro-football-reference.com/years/2025/index.htm"
DATA_DIR = 'data'
NFL_CSV_FILE = 'nfl.csv'
CSV_PATH = os.path.join(DATA_DIR, NFL_CSV_FILE)

# Map from PFR abbreviation (Tm) to the full team name used in nfl.csv
# This ensures data integrity when merging.
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
    Fetches and parses the AFC/NFC standings from Pro-Football-Reference.
    It looks for tables with IDs 'AFC' and 'NFC', which are often commented out in the HTML source.
    """
    print(f"-> Attempting to scrape standings from {url}...")
    
    try:
        # Use pandas.read_html to attempt to scrape tables directly
        # The tables are often contained within HTML comments, so we fetch the raw page
        response = pd.io.common.urlopen(url)
        html_content = response.read()
    except Exception as e:
        print(f"ERROR: Failed to fetch data. Ensure URL is correct and network is available: {e}")
        return None

    scraped_tables = {}
    
    # Use regex to find the commented-out tables by ID ('AFC' and 'NFC')
    for conf_id in ['AFC', 'NFC']:
        # This regex looks for the table wrapped inside an HTML comment
        match = re.search(r'', html_content.decode('utf-8'), re.DOTALL)
        
        if match:
            # Clean the table HTML by removing comment tags
            table_html = match.group(0).replace('', '')
            try:
                # Read the clean table HTML into a DataFrame
                df = pd.read_html(table_html)[0]
                
                # Rename columns and remove the division header rows (index 0)
                # The columns are Tm, W, L, T, W-L%...
                df = df.iloc[1:].rename(columns={'Tm': 'PFR_Tm', 'W': 'Wins', 'L': 'Losses'})
                
                # Select and clean relevant columns
                df = df[['PFR_Tm', 'Wins', 'Losses']]
                
                # Filter out Division headers (they contain "FC" in the 'PFR_Tm' column)
                df = df[~df['PFR_Tm'].str.contains('FC')]
                
                scraped_tables[conf_id] = df
            except Exception as e:
                print(f"Warning: Failed to parse {conf_id} table data in memory: {e}")
                
    if not scraped_tables:
        print("ERROR: No AFC or NFC tables could be successfully parsed from Pro-Football-Reference.")
        return None

    # Combine the AFC and NFC tables
    all_standings = pd.concat(scraped_tables.values(), ignore_index=True)
    return all_standings

def update_nfl_csv(scraped_data):
    """Updates the local nfl.csv with the scraped Wins/Losses data."""
    if not os.path.exists(CSV_PATH):
        print(f"CRITICAL ERROR: Local CSV file not found at {CSV_PATH}")
        return

    # 1. Read the local data into a DataFrame
    try:
        local_df = pd.read_csv(CSV_PATH)
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to read local CSV: {e}")
        return
        
    print(f"-> Read local CSV with {len(local_df)} teams.")

    # 2. Map PFR abbreviations to full team names in the scraped data
    scraped_data['Team'] = scraped_data['PFR_Tm'].str.upper().map(TEAM_MAP)
    
    # Convert Wins/Losses to proper numeric types
    scraped_data['Wins'] = pd.to_numeric(scraped_data['Wins'], errors='coerce', downcast='integer')
    scraped_data['Losses'] = pd.to_numeric(scraped_data['Losses'], errors='coerce', downcast='integer')
    scraped_data = scraped_data.dropna(subset=['Team', 'Wins', 'Losses'])

    # Select only the relevant columns for updating (Team, Wins, Losses)
    update_df = scraped_data[['Team', 'Wins', 'Losses']].copy()

    # 3. Update the local DataFrame
    # Set 'Team' as index for easy alignment and update
    local_df = local_df.set_index('Team')
    update_df = update_df.set_index('Team')

    # Use the .update() method to only update matching rows/columns, preserving existing columns like 'Elo' and 'Division'
    local_df.update(update_df[['Wins', 'Losses']])

    # Convert updated columns back to the expected string format
    local_df['Wins'] = local_df['Wins'].astype(int).astype(str)
    local_df['Losses'] = local_df['Losses'].astype(int).astype(str)
    
    # Reset index to bring 'Team' back as a column and save
    final_df = local_df.reset_index()

    # 4. Write the updated data back to CSV
    try:
        # Overwrite the file with the updated data, preserving the structure
        final_df.to_csv(CSV_PATH, index=False)
        print(f"✅ Successfully updated {CSV_PATH} with W-L records for {len(final_df)} teams.")
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to write to CSV: {e}")

if __name__ == "__main__":
    print("--- Starting PFR Standings Scraper ---")
    
    # 1. Scrape data
    standings_data = scrape_pfr_standings(NFL_STANDINGS_URL)
    
    if standings_data is not None and not standings_data.empty:
        # 2. Update local CSV
        update_nfl_csv(standings_data)
    else:
        print("Scraping failed or returned no data. No changes made.")
        
    print("--- PFR Standings Scraper Finished ---")

import requests
import csv
import os

# --- CONFIGURATION (UPDATE THESE WHEN SEASONS CHANGE) ---
# Assuming NFL/CFB are in the 2025 season (Fall/Winter 2025)
CURRENT_SEASON_NFL_CFB = 2025 
# Assuming NBA/CBB are starting their 2025-2026 season (API often uses the ending year)
CURRENT_SEASON_NBA_CBB = 2026 

# Map CSV files to their ESPN API slugs and season year
LEAGUES_CONFIG = {
    'nfl.csv': ('football', 'nfl', CURRENT_SEASON_NFL_CFB),
    'nba.csv': ('basketball', 'nba', CURRENT_SEASON_NBA_CBB),
    'cfb.csv': ('football', 'college-football', CURRENT_SEASON_NFL_CFB),
    'mcbb.csv': ('basketball', 'mens-college-basketball', CURRENT_SEASON_NBA_CBB),
    'wcbb.csv': ('basketball', 'womens-college-basketball', CURRENT_SEASON_NBA_CBB),
}

# --- FILE PATHING ---
# GitHub Actions runs from the repository root, so relative paths are simple
DATA_DIR = 'data'
FIELDNAMES = ['Team', 'Elo', 'Division', 'Wins', 'Losses', 'Notes'] 

# --- FUNCTIONS ---

def get_team_records_from_api(sport, league, year):
    """Fetches win/loss data from the ESPN Standings API."""
    # Use standard ESPN Standings API endpoint
    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/standings?season={year}"
    
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status() 
        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"  ERROR: Failed to fetch API data for {league}. {e}")
        return {}

    api_records = {}
    
    # ESPN Standings structure is nested; iterate through conference/groupings
    entries = []
    standings_data = data.get('children')
    if standings_data:
        for group in standings_data:
            entries.extend(group.get('standings', {}).get('entries', []))
    else:
        # Fallback for leagues without complex groupings
        entries = data.get('standings', {}).get('entries', [])

    for team_entry in entries:
        try:
            team_name = team_entry['team']['displayName']
            stats = team_entry.get("stats", [])
            
            # Extract Wins and Losses
            wins = next(int(s["value"]) for s in stats if s["name"] == "wins")
            losses = next(int(s["value"]) for s in stats if s["name"] == "losses")
            
            # Use lowercase team name for robust matching to the CSV
            api_records[team_name.lower()] = {'Wins': wins, 'Losses': losses}
        except Exception as e:
            # Skip team if its W/L data is malformed or missing
            # print(f"  Warning: Skipping team in API parse. Error: {e}")
            continue
            
    return api_records

def update_csv_file(file_name, api_records):
    """Reads the local CSV, updates Wins/Losses, and overwrites the file."""
    csv_filepath = os.path.join(DATA_DIR, file_name)
    
    try:
        # 1. Read existing CSV data (to preserve Elo and Division)
        with open(csv_filepath, 'r', newline='') as file:
            reader = csv.DictReader(file, fieldnames=FIELDNAMES)
            header = next(reader) # Read header row
            current_teams = list(reader)
            
    except FileNotFoundError:
        print(f"  CRITICAL ERROR: CSV file not found at {csv_filepath}")
        return
    except Exception as e:
        print(f"  CRITICAL ERROR: Could not read CSV file: {e}")
        return

    # 2. Merge new W/L data
    updated_teams = []
    for team_row in current_teams:
        csv_team_name = team_row.get('Team', '').lower() 
        
        if csv_team_name in api_records:
            new_record = api_records[csv_team_name]
            # Update the Wins and Losses columns
            team_row['Wins'] = str(new_record['Wins'])
            team_row['Losses'] = str(new_record['Losses'])
            
        updated_teams.append(team_row)

    # 3. Write updated data back to CSV
    try:
        with open(csv_filepath, 'w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
            # Write the original header back, then the data
            writer.writerow(header)
            writer.writerows(updated_teams)
        print(f"  ✅ Successfully updated {file_name}.")
    except Exception as e:
        print(f"  CRITICAL ERROR: Could not write to CSV file. Error: {e}")

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    
    print("--- Starting AEI Ratings Update Script ---")
    
    for file_name, (sport_slug, league_slug, season_year) in LEAGUES_CONFIG.items():
        print(f"\n--- Processing {league_slug.upper()} ({file_name}) ---")
        
        # 1. Fetch data
        records = get_team_records_from_api(sport_slug, league_slug, season_year)
        
        if records:
            # 2. Update CSV
            update_csv_file(file_name, records)
        else:
            print(f"  Skipping {file_name} due to API error or no records found.")
            
    print("\n--- Update Script Finished ---")

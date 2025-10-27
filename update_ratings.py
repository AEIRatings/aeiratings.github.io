import requests
import csv
import os
from datetime import datetime

# --- CONFIGURATION ---
# Base path is assumed to be the directory containing this script and the 'data' folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')

# Set the current season year. This is crucial for the API call.
# For fall/winter sports (NFL, CFB, NBA, CBB), the season is generally the year it starts.
# Example: 2024-2025 NBA season uses '2025' as the season year in the API.
# You MUST update this when a new season begins.
CURRENT_SEASON_YEAR = 2025 

# Configuration for each league: {file_name: (sport_slug, league_slug)}
LEAGUES_CONFIG = {
    'nfl.csv': ('football', 'nfl'),
    'nba.csv': ('basketball', 'nba'),
    'cfb.csv': ('football', 'college-football'),
    'mcbb.csv': ('basketball', 'mens-college-basketball'),
    'wcbb.csv': ('basketball', 'womens-college-basketball'),
}

# --- FUNCTIONS ---

def get_team_records_from_api(sport, league, year):
    """Fetches win/loss data from the ESPN Standings API."""
    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/standings?season={year}"
    print(f"Fetching data for {league} from: {url}")
    
    try:
        response = requests.get(url)
        response.raise_for_status() # Raise exception for bad status codes
        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"  ERROR: Failed to fetch API data: {e}")
        return {}

    api_records = {}
    try:
        # Navigate the JSON structure to get standings entries
        # Standings structure is often nested, check 'children' for conferences/divisions
        entries = []
        standings_data = data.get('children')
        if standings_data:
            for group in standings_data:
                entries.extend(group.get('standings', {}).get('entries', []))
        else:
            # Fallback for leagues that might not use 'children' (e.g., smaller leagues)
            entries = data.get('standings', {}).get('entries', [])
            
        for team_entry in entries:
            # ESPN's display name is generally the most reliable team name for matching
            team_name = team_entry['team']['displayName']
            stats = team_entry.get("stats", [])
            
            # Extract Wins (W) and Losses (L) from the stats list
            wins = next(int(s["value"]) for s in stats if s["name"] == "wins" and "value" in s)
            losses = next(int(s["value"]) for s in stats if s["name"] == "losses" and "value" in s)
            
            # Normalize team name to lowercase for robust matching against CSV
            api_records[team_name.lower()] = {'Wins': wins, 'Losses': losses}
            
    except Exception as e:
        print(f"  ERROR: Failed to parse API data for {league}. Check API structure. Error: {e}")
        return {}
        
    return api_records

def update_csv_file(file_name, api_records):
    """Reads the local CSV, updates Wins/Losses, and overwrites the file."""
    csv_filepath = os.path.join(DATA_DIR, file_name)
    print(f"  Processing file: {csv_filepath}")
    
    try:
        # Read the entire file content
        with open(csv_filepath, 'r', newline='') as file:
            reader = csv.DictReader(file)
            current_teams = list(reader)
            fieldnames = reader.fieldnames
            
        if not fieldnames:
             print("  ERROR: CSV file is empty or has no headers.")
             return
             
    except FileNotFoundError:
        print(f"  ERROR: CSV file not found at {csv_filepath}")
        return
    except Exception as e:
        print(f"  ERROR: Could not read CSV file: {e}")
        return

    # 2. Merge new data with old data
    updated_teams = []
    missing_count = 0
    for team_row in current_teams:
        csv_team_name = team_row.get('Team', '').lower() # Assuming a 'Team' column exists
        
        if csv_team_name in api_records:
            # Update the Wins and Losses columns
            new_record = api_records[csv_team_name]
            team_row['Wins'] = new_record['Wins']
            team_row['Losses'] = new_record['Losses']
        else:
            missing_count += 1
            # print(f"  WARNING: No API record found for team: {team_row.get('Team')}. Wins/Losses left unchanged.")
            
        updated_teams.append(team_row)

    # 3. Write updated data back to CSV
    try:
        with open(csv_filepath, 'w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(updated_teams)
        
        print(f"  ✅ Successfully updated {len(updated_teams) - missing_count} team records in {file_name}.")
        if missing_count > 0:
            print(f"  ⚠️ Warning: {missing_count} teams were not matched and their W/L was not updated.")

    except Exception as e:
        print(f"  CRITICAL ERROR: Could not write to CSV file. Check permissions. Error: {e}")

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    
    print("--- Starting AEI Ratings Update Script ---")
    print(f"Using Season Year: {CURRENT_SEASON_YEAR}")
    print(f"Local Data Directory: {DATA_DIR}\n")

    # Check for required library
    try:
        import requests
    except ImportError:
        print("\nFATAL ERROR: The 'requests' library is not installed.")
        print("Please run: pip install requests")
        exit(1)

    for file_name, (sport_slug, league_slug) in LEAGUES_CONFIG.items():
        print(f"\n--- Processing {file_name.upper().replace('.CSV', '')} ---")
        
        # 1. Fetch data from ESPN API
        records = get_team_records_from_api(sport_slug, league_slug, CURRENT_SEASON_YEAR)
        
        if records:
            # 2. Update the local CSV file
            update_csv_file(file_name, records)
        else:
            print(f"  Skipping {file_name} due to API error or no records found.")
            
    print("\n--- Update Script Finished ---")
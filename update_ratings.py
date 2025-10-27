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
DATA_DIR = 'data'
FIELDNAMES = ['Team', 'Elo', 'Division', 'Wins', 'Losses', 'Notes'] 

# --- FUNCTIONS ---

def get_team_records_from_api(sport, league, year):
    """Fetches win/loss data from the ESPN Standings API."""
    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/standings?season={year}"
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; AEI-Updater/1.0)'}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        print(f"  [DEBUG] {league}: top-level keys = {list(data.keys())}")
    except requests.exceptions.RequestException as e:
        print(f"  ERROR: Failed to fetch API data for {league}. {e}")
        return {}

    api_records = {}

    # --- ESPN Standings structure is inconsistent between leagues ---
    entries = []

    # --- Newer format (2024+) ---
    if data.get("standings") and data["standings"].get("entries"):
        entries = data["standings"]["entries"]

    # --- Grouped by conferences/divisions (older structure) ---
    elif data.get("children"):
        for group in data["children"]:
            group_entries = (
                group.get("standings", {}).get("entries", [])
                if group.get("standings")
                else []
            )
            entries.extend(group_entries)

    # --- Fallback for some college sports ---
    elif data.get("leagues"):
        for lg in data["leagues"]:
            if "standings" in lg and "entries" in lg["standings"]:
                entries.extend(lg["standings"]["entries"])

    else:
        print(f"  ⚠️ Unexpected JSON format for {league}. Keys: {list(data.keys())}")

    if not entries:
        print(f"  ⚠️ No standings entries found for {league}.")
        return {}

    print(f"  [DEBUG] Found {len(entries)} team entries for {league}")

    # --- Parse team data ---
    for team_entry in entries:
        try:
            team_name = team_entry['team']['displayName']
            stats = team_entry.get("stats", [])
            stat_map = {s["name"]: int(s.get("value", 0)) for s in stats if s.get("name") in ["wins", "losses"]}
            wins = stat_map.get("wins", 0)
            losses = stat_map.get("losses", 0)
            api_records[team_name.lower()] = {'Wins': wins, 'Losses': losses}
        except Exception as e:
            print(f"  Warning: Skipping malformed team entry for {league}: {e}")
            continue

    return api_records


def update_csv_file(file_name, api_records):
    """Reads the local CSV, updates Wins/Losses, and overwrites the file."""
    csv_filepath = os.path.join(DATA_DIR, file_name)
    
    if not os.path.exists(csv_filepath):
        print(f"  ⚠️ Skipping missing file: {csv_filepath}")
        return

    try:
        with open(csv_filepath, 'r', newline='') as file:
            reader = csv.DictReader(file, fieldnames=FIELDNAMES)
            header = next(reader)  # read header
            current_teams = list(reader)
    except Exception as e:
        print(f"  CRITICAL ERROR: Could not read CSV file {csv_filepath}: {e}")
        return

    updated_teams = []
    for team_row in current_teams:
        csv_team_name = team_row.get('Team', '').lower()
        if csv_team_name in api_records:
            new_record = api_records[csv_team_name]
            team_row['Wins'] = str(new_record['Wins'])
            team_row['Losses'] = str(new_record['Losses'])
        updated_teams.append(team_row)

    try:
        with open(csv_filepath, 'w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
            writer.writerow(header)
            writer.writerows(updated_teams)
        print(f"  ✅ Successfully updated {file_name} ({len(api_records)} records).")
    except Exception as e:
        print(f"  CRITICAL ERROR: Could not write to CSV file. Error: {e}")


# --- MAIN EXECUTION ---
if __name__ == "__main__":
    print("--- Starting AEI Ratings Update Script ---")
    
    for file_name, (sport_slug, league_slug, season_year) in LEAGUES_CONFIG.items():
        print(f"\n--- Processing {league_slug.upper()} ({file_name}) ---")
        records = get_team_records_from_api(sport_slug, league_slug, season_year)
        
        if records:
            update_csv_file(file_name, records)
        else:
            print(f"  Skipping {file_name} due to API error or no records found.")
            
    print("\n--- Update Script Finished ---")

import requests
import csv
import unicodedata
from datetime import datetime, timedelta
import pytz  # You may need to run 'pip install pytz'

def load_team_names(filename="data/mcbb.csv"):
    team_names = set()
    try:
        with open(filename, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if row:
                    team = row[0].strip()
                    if team:
                        team_names.add(team)
    except FileNotFoundError:
        print(f"❌ Could not find {filename}.")
    return team_names

def strip_accents(text):
    if not text: return text
    return ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')

def normalize_name(raw_name):
    if not raw_name: return raw_name
    name = unicodedata.normalize('NFC', raw_name)
    name = (name.replace('JosÃ©', 'José').replace('San Jose', 'San José'))
    return name.replace("No. ", "").strip()

def clean_team_name(full_name, valid_team_names):
    if not full_name: return None
    normalized = normalize_name(full_name)
    lower_no_accents = strip_accents(normalized.lower())
    valid_processed = {strip_accents(team.lower()): team for team in valid_team_names}
    return valid_processed.get(lower_no_accents)

def convert_to_pacific_date(utc_string):
    """Converts ESPN UTC string to Pacific Date only."""
    try:
        # ESPN date format is typically '2026-01-25T01:00Z'
        utc_dt = datetime.strptime(utc_string, "%Y-%m-%dT%H:%MZ")
        utc_dt = pytz.utc.localize(utc_dt)
        
        pacific_tz = pytz.timezone('US/Pacific')
        pacific_dt = utc_dt.astimezone(pacific_tz)
        
        # Changed format to only return Year-Month-Day
        return pacific_dt.strftime('%Y-%m-%d') 
    except Exception:
        return utc_string 

def fetch_upcoming_wcbb_games():
    valid_team_names = load_team_names("data/mcbb.csv")
    CSV_FILENAME = "data/mcbb_games.csv"
    all_game_data = []
    seen_games = set()

    for i in range(1, 2):
        target_date = datetime.now() + timedelta(days=i)
        date_str = target_date.strftime('%Y%m%d')
        display_date = target_date.strftime('%Y-%m-%d')

        print(f"[{i}/43] Checking games for {display_date}...")

        BASE_URL = "http://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard"
        url = f"{BASE_URL}?groups=50&dates={date_str}"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f"Error fetching {display_date}: {e}")
            continue

        for event in data.get('events', []):
            comp = event.get('competitions', [{}])[0]
            status = comp.get('status', {}).get('type', {}).get('state')
            
            if status != 'pre':
                continue

            game_time_utc = event.get('date', '') 
            # Convert to Pacific Date here
            game_date_pacific = convert_to_pacific_date(game_time_utc)
            
            competitors = comp.get('competitors', [])
            away_team, home_team = None, None

            for competitor in competitors:
                raw_name = competitor.get('team', {}).get('displayName')
                cleaned_name = clean_team_name(raw_name, valid_team_names)

                if competitor.get('homeAway') == 'away':
                    away_team = cleaned_name
                else:
                    home_team = cleaned_name

            if away_team and home_team:
                game_id = (away_team, home_team, game_date_pacific)
                if game_id not in seen_games:
                    seen_games.add(game_id)
                    all_game_data.append([away_team, home_team, game_date_pacific])

    if all_game_data:
        with open(CSV_FILENAME, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            # Updated header name
            writer.writerow(['away team', 'home team', 'game date (Pacific)'])
            writer.writerows(all_game_data)
        print(f"\n✅ Finished! Saved {len(all_game_data)} total games to {CSV_FILENAME}")
    else:
        print("\nNo upcoming games found for the specified period.")

if __name__ == '__main__':
    fetch_upcoming_wcbb_games()

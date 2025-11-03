import requests
import csv
import unicodedata
from datetime import datetime, timedelta


def load_team_names(filename="cfb.csv"):
    """
    Loads valid college football team names (without nicknames) from a CSV file.
    Returns a set of team names for matching.
    """
    team_names = set()
    try:
        with open(filename, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if row:
                    team = row[0].strip()
                    if team:
                        team_names.add(team)
    except Exception as e:
        print(f"Error loading team names: {e}")
    return team_names


def strip_accents(text):
    """Removes all accent marks from a string (e.g., José -> Jose)."""
    if not text:
        return text
    return ''.join(c for c in unicodedata.normalize('NFD', text)
                   if unicodedata.category(c) != 'Mn')


def normalize_name(raw_name):
    """
    Fixes encoding issues from the ESPN API such as 'San JosÃ©' -> 'San José'
    and ensures consistent Unicode formatting.
    """
    if not raw_name:
        return raw_name

    # Normalize Unicode form
    name = unicodedata.normalize('NFC', raw_name)

    # Fix known encoding glitches
    # ESPN sometimes returns mojibake (mis-decoded UTF-8)
    # e.g., 'San JosÃ© State Spartans' instead of 'San José State Spartans'
    name = (name.replace('JosÃ©', 'José')
                .replace('San Jose', 'San José')
                .replace('Nittany Lions', 'Penn State')  # example of cleanup if desired
            )

    # Remove ranking prefix like "No. 3 "
    name = name.replace("No. ", "").strip()

    return name


def clean_team_name(full_name, valid_team_names):
    """
    Strips nicknames (e.g., 'Georgia Bulldogs' -> 'Georgia') using substring match
    against known team names list. Handles accent-insensitive comparison.
    """
    if not full_name:
        return full_name

    normalized = normalize_name(full_name)
    lower_no_accents = strip_accents(normalized.lower())

    best_match = None
    for team in valid_team_names:
        team_no_accents = strip_accents(team.lower())
        if team_no_accents in lower_no_accents:
            if not best_match or len(team) > len(best_match):
                best_match = team

    return best_match if best_match else normalized


def fetch_and_save_college_football_scores():
    """
    Fetches college football (FBS + FCS) scoreboard data for the previous day
    and saves them into a single deduplicated CSV file.
    """
    valid_team_names = load_team_names("cfb.csv")

    yesterday = datetime.now() - timedelta(days=1)
    date_str = yesterday.strftime('%Y%m%d')
    file_date_str = yesterday.strftime('%Y-%m-%d')

    BASE_URL = "http://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard"
    API_URLS = [
        f"{BASE_URL}?groups=80&dates={date_str}",  # FBS
        f"{BASE_URL}?groups=81&dates={date_str}"   # FCS
    ]

    CSV_FILENAME = "college_football_scores_previous_day.csv"

    all_game_data = []
    seen_games = set()

    print(f"Fetching College Football scores for {file_date_str}...")

    for api_url in API_URLS:
        try:
            print(f" -> Fetching from {api_url}")
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data from {api_url}: {e}")
            continue

        events = data.get('events', [])
        for event in events:
            competitions = event.get('competitions', [])
            if not competitions:
                continue

            comp = competitions[0]
            status = comp.get('status', {}).get('type', {}).get('state')
            if status != 'post':
                continue

            competitors = comp.get('competitors', [])
            away_team_name, home_team_name = None, None
            away_score, home_score = None, None

            for competitor in competitors:
                team_info = competitor.get('team', {})
                team_display_name = team_info.get('displayName')
                team_display_name = normalize_name(team_display_name)
                score = competitor.get('score')

                cleaned_name = clean_team_name(team_display_name, valid_team_names)

                if competitor.get('homeAway') == 'away':
                    away_team_name = cleaned_name
                    away_score = int(score) if score else 0
                elif competitor.get('homeAway') == 'home':
                    home_team_name = cleaned_name
                    home_score = int(score) if score else 0

            if away_team_name and home_team_name:
                game_id = tuple(sorted([away_team_name, home_team_name]))
                if game_id not in seen_games:
                    seen_games.add(game_id)
                    all_game_data.append([
                        away_team_name,
                        home_team_name,
                        away_score,
                        home_score
                    ])

    # Save to CSV
    try:
        with open(CSV_FILENAME, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['away team', 'home team', 'away score', 'home score'])
            writer.writerows(all_game_data)
        print(f"✅ Saved {len(all_game_data)} unique game scores to {CSV_FILENAME}")
    except Exception as e:
        print(f"Error writing to CSV file: {e}")


if __name__ == '__main__':
    fetch_and_save_college_football_scores()

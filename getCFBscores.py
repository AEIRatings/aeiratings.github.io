import requests
import csv
import unicodedata
from datetime import datetime, timedelta

def load_team_names(filename="data/cfb_espn_aliases.csv"):
    """
    Loads the ESPN-display-name -> roster-team-name lookup table (same idea as
    mcbb.csv/wcbb.csv, which store the full ESPN name directly). Each row maps
    one exact ESPN 'displayName' string (e.g. 'Ohio State Buckeyes') to the
    canonical short team name used in data/cfb.csv (e.g. 'Ohio State').
    Returns a dict keyed by the normalized ESPN name for O(1) exact lookup.
    """
    aliases = {}
    try:
        with open(filename, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                espn_name = (row.get('espn_name') or '').strip()
                team = (row.get('team') or '').strip()
                if espn_name and team:
                    aliases[normalize_match_key(espn_name)] = team
    except FileNotFoundError:
        print(f"❌ Could not find {filename}. Make sure the file exists in the data/ folder.")
    except Exception as e:
        print(f"Error loading team aliases from {filename}: {e}")
    return aliases


def strip_accents(text):
    """Removes all accent marks from a string (e.g., José -> Jose)."""
    if not text:
        return text
    return ''.join(c for c in unicodedata.normalize('NFD', text)
                   if unicodedata.category(c) != 'Mn')


def normalize_match_key(name):
    """
    Collapses a team name down to a stable lookup key: lowercased, accents
    stripped, apostrophes/periods removed (so "Ragin' Cajuns" lines up with
    "Ragin Cajuns" and "St. Thomas" lines up with "St Thomas"), whitespace
    collapsed. Used on both sides of the exact-match lookup so minor
    punctuation differences don't cause an otherwise-correct match to miss.
    """
    key = strip_accents(name.lower())
    key = key.replace("'", "").replace(".", "")
    key = " ".join(key.split())
    return key


def normalize_name(raw_name):
    """
    Fixes encoding issues from the ESPN API such as 'San JosÃ©' -> 'San José'
    and ensures consistent Unicode formatting.
    """
    if not raw_name:
        return raw_name

    name = unicodedata.normalize('NFC', raw_name)
    name = (name.replace('JosÃ©', 'José')
                .replace('San Jose', 'San José')
                .replace('Nittany Lions', 'Penn State')
            )
    name = name.replace("No. ", "").strip()
    return name


def clean_team_name(full_name, espn_aliases):
    """
    Resolves an ESPN 'displayName' to the roster's canonical team name using
    only an exact lookup against espn_aliases (built by load_team_names from
    data/cfb_espn_aliases.csv) - the same approach getMCBBscores.py /
    getWCBBscores.py use, where the roster stores the full ESPN name so
    matching is a direct dict lookup instead of a heuristic.

    Deliberately returns None (instead of falling back to a fuzzy/partial
    match) when the name isn't a known alias. This is what actually fixes the
    "Ohio Dominican counted as Ohio" / "Northwestern (IA) counted as
    Northwestern" bug: those schools aren't FBS/FCS teams, so they don't - and
    shouldn't - have an alias entry. Returning None means the game containing
    them is skipped entirely rather than silently credited to the wrong,
    similarly-named FBS/FCS program.
    """
    if not full_name:
        return None

    normalized = normalize_name(full_name)
    return espn_aliases.get(normalize_match_key(normalized))


def fetch_and_save_college_football_scores():
    """
    Fetches college football (FBS + FCS) scoreboard data for the previous day
    and saves them into a single deduplicated CSV file.
    """
    espn_aliases = load_team_names()

    # 1. Determine the date for the data (yesterday)
    yesterday = datetime.now() - timedelta(days=1)
    date_str = yesterday.strftime('%Y%m%d') 
    file_date_str = yesterday.strftime('%Y-%m-%d')

    BASE_URL = "http://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard"
    API_URLS = [
        f"{BASE_URL}?groups=80&dates={date_str}",  # FBS
        f"{BASE_URL}?groups=81&dates={date_str}"   # FCS
    ]

    CSV_FILENAME = "cfb_scores_previous_day.csv"

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
            # FIX: Double-check the actual event date string from the API
            # The API event date format is usually ISO: "2024-12-21T17:00Z"
            event_date_full = event.get('date', '')
            if event_date_full:
                event_date_only = event_date_full.split('T')[0]
                if event_date_only != file_date_str:
                    # Skip games that don't actually match "yesterday"
                    continue

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
                team_display_name = normalize_name(team_info.get('displayName'))
                score = competitor.get('score')
                cleaned_name = clean_team_name(team_display_name, espn_aliases)

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
                    all_game_data.append([away_team_name, home_team_name, away_score, home_score])

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

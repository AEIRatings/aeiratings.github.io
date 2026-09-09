import argparse
import requests
import csv
import unicodedata
from datetime import datetime, timedelta

# NCAA Division I Women's Volleyball on ESPN's public site API.
BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/volleyball/womens-college-volleyball/scoreboard"
SUMMARY_URL = "https://site.api.espn.com/apis/site/v2/sports/volleyball/womens-college-volleyball/summary"
GROUP_ID = 50  # Division I


def load_team_names(filename="data/wvb.csv"):
    """
    Loads valid team names from data/wvb.csv (which stores each team under
    its full ESPN 'displayName', the same convention getWCBBscores.py uses)
    for exact-match lookup.
    """
    team_names = set()
    try:
        with open(filename, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            next(reader, None)  # header
            for row in reader:
                if row:
                    team = row[0].strip()
                    if team:
                        team_names.add(team)
    except FileNotFoundError:
        print(f"❌ Could not find {filename}. Run build_wvb_teams.py first to bootstrap the roster.")
    except Exception as e:
        print(f"Error loading team names from {filename}: {e}")
    return team_names


def strip_accents(text):
    if not text:
        return text
    return ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')


def normalize_name(raw_name):
    if not raw_name:
        return raw_name
    name = unicodedata.normalize('NFC', raw_name)
    name = name.replace('JosÃ©', 'José').replace('San Jose', 'San José')
    return name.replace("No. ", "").strip()


def clean_team_name(full_name, valid_team_names):
    """Exact-match (case/accent-insensitive) lookup against the wvb.csv roster."""
    if not full_name:
        return None
    normalized = normalize_name(full_name)
    lower_no_accents = strip_accents(normalized.lower())
    valid_processed = {strip_accents(team.lower()): team for team in valid_team_names}
    return valid_processed.get(lower_no_accents)


def extract_set_scores(away_competitor, home_competitor):
    """
    Pulls per-set point totals out of ESPN's 'linescores' array, the same
    field ESPN uses for periods/innings in other sports and, for
    set-based sports like volleyball, one entry per set. Returns a list of
    (away_points, home_points) tuples in set order, or None if either
    side has no usable linescores (caller falls back to the summary
    endpoint in that case).
    """
    away_lines = away_competitor.get('linescores') or []
    home_lines = home_competitor.get('linescores') or []
    if not away_lines or not home_lines:
        return None

    sets = []
    for i in range(min(len(away_lines), len(home_lines))):
        a_val = away_lines[i].get('value')
        h_val = home_lines[i].get('value')
        if a_val is None or h_val is None:
            continue
        try:
            sets.append((int(a_val), int(h_val)))
        except (TypeError, ValueError):
            continue

    return sets or None


def fetch_set_scores_from_summary(event_id):
    """
    Fallback for when the scoreboard response doesn't carry per-set
    linescores directly: fetches ESPN's boxscore/summary endpoint for a
    single event and pulls the same linescores off its header competitors.
    """
    url = f"{SUMMARY_URL}?event={event_id}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"  Error fetching summary for event {event_id}: {e}")
        return None

    try:
        competitors = data['header']['competitions'][0]['competitors']
    except (KeyError, IndexError, TypeError):
        return None

    away_c = next((c for c in competitors if c.get('homeAway') == 'away'), None)
    home_c = next((c for c in competitors if c.get('homeAway') == 'home'), None)
    if not away_c or not home_c:
        return None

    return extract_set_scores(away_c, home_c)


def fetch_matches_for_date(date_obj, valid_team_names):
    """
    Fetches finished D1 women's volleyball matches for a single date,
    returning a list of dicts:
      {'match_id', 'away_team', 'home_team', 'sets': [(a1,h1), (a2,h2), ...]}

    Shared by fetch_and_save_wvb_scores (which asks for "yesterday" by
    default) and backfill_wvb.py (which replays a range of dates).
    """
    date_str = date_obj.strftime('%Y%m%d')
    file_date_str = date_obj.strftime('%Y-%m-%d')

    url = f"{BASE_URL}?groups={GROUP_ID}&dates={date_str}&limit=500"

    matches = []
    seen_ids = set()

    try:
        print(f" -> Fetching from {url}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from {url}: {e}")
        return matches

    for event in data.get('events', []):
        competitions = event.get('competitions', [])
        if not competitions:
            continue

        comp = competitions[0]
        status = comp.get('status', {}).get('type', {}).get('state')
        if status != 'post':
            continue

        competitors = comp.get('competitors', [])
        away_c = next((c for c in competitors if c.get('homeAway') == 'away'), None)
        home_c = next((c for c in competitors if c.get('homeAway') == 'home'), None)
        if not away_c or not home_c:
            continue

        away_raw = normalize_name(away_c.get('team', {}).get('displayName'))
        home_raw = normalize_name(home_c.get('team', {}).get('displayName'))
        away_team = clean_team_name(away_raw, valid_team_names)
        home_team = clean_team_name(home_raw, valid_team_names)
        if not away_team or not home_team:
            print(f"  Warning: Could not resolve '{away_raw}' / '{home_raw}' against the wvb.csv roster; skipping.")
            continue

        event_id = event.get('id')
        if event_id in seen_ids:
            continue

        sets = extract_set_scores(away_c, home_c)
        if not sets and event_id:
            sets = fetch_set_scores_from_summary(event_id)

        if not sets:
            print(f"  Warning: No set-by-set scores found for {away_team} @ {home_team} ({file_date_str}); skipping match.")
            continue

        if event_id:
            seen_ids.add(event_id)

        matches.append({
            'match_id': event_id or f"{date_str}-{away_team}-{home_team}",
            'away_team': away_team,
            'home_team': home_team,
            'sets': sets,
        })

    return matches


def save_matches(matches, csv_filename):
    with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['match_id', 'set', 'away team', 'home team', 'away score', 'home score'])
        for match in matches:
            for i, (away_score, home_score) in enumerate(match['sets'], start=1):
                writer.writerow([match['match_id'], i, match['away_team'], match['home_team'], away_score, home_score])
    total_sets = sum(len(m['sets']) for m in matches)
    print(f"✅ Saved {len(matches)} match(es), {total_sets} set(s) to {csv_filename}")


def fetch_and_save_wvb_scores(target_date=None):
    """
    Fetches D1 women's volleyball results (default: yesterday) and saves
    every set of every match into a single long-format CSV, one row per
    set, ready for elo_updater_wvb.py to replay set-by-set.
    """
    valid_team_names = load_team_names()

    day = target_date if target_date else (datetime.now() - timedelta(days=1))
    file_date_str = day.strftime('%Y-%m-%d')

    CSV_FILENAME = "wvb_scores_previous_day.csv"

    print(f"Fetching D1 Women's Volleyball scores for {file_date_str}...")

    matches = fetch_matches_for_date(day, valid_team_names)
    save_matches(matches, CSV_FILENAME)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Fetch D1 women's volleyball set-by-set results for a given day.")
    parser.add_argument('--date', help="Date to fetch, YYYY-MM-DD (defaults to yesterday)")
    args = parser.parse_args()

    target = datetime.strptime(args.date, '%Y-%m-%d') if args.date else None
    fetch_and_save_wvb_scores(target)

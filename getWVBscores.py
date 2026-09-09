import argparse
import requests
import csv
import unicodedata
from datetime import datetime, timedelta

# NCAA Division I Women's Volleyball on ESPN's public site API. Unlike
# basketball/football, this endpoint doesn't need a `groups=` filter - the
# womens-college-volleyball league on ESPN's site API is D1-only already.
BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/volleyball/womens-college-volleyball/scoreboard"
SUMMARY_URL = "https://site.api.espn.com/apis/site/v2/sports/volleyball/womens-college-volleyball/summary"


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


# Every character seen in the wild standing in for an apostrophe/okina in a
# school name (e.g. "Hawai'i" vs "Hawaiʻi" vs "Hawai’i") - the ESPN
# scoreboard and the ESPN teams endpoint don't reliably agree on which one
# they use for the same school, so matching has to be blind to all of them.
_APOSTROPHE_CHARS = ["'", "’", "ʻ", "ʼ", "`"]


def normalize_match_key(name):
    """
    Collapses a team name down to a stable lookup key: lowercased, accents
    stripped, every apostrophe/okina variant and periods removed (so
    "Hawai'i" lines up with "Hawaiʻi" and "St. Thomas" lines up with
    "St Thomas"), whitespace collapsed. Used on both sides of the
    exact-match lookup so punctuation/glyph differences alone can't cause
    an otherwise-correct match to miss.
    """
    key = strip_accents(name.lower())
    for ch in _APOSTROPHE_CHARS:
        key = key.replace(ch, "")
    key = key.replace(".", "")
    key = " ".join(key.split())
    return key


def clean_team_name(full_name, valid_team_names):
    """Exact-match (case/accent/punctuation-insensitive) lookup against the wvb.csv roster."""
    if not full_name:
        return None
    normalized = normalize_name(full_name)
    key = normalize_match_key(normalized)
    valid_processed = {normalize_match_key(team): team for team in valid_team_names}
    return valid_processed.get(key)


def extract_set_scores(away_competitor, home_competitor):
    """
    Pulls per-set point totals out of ESPN's 'linescores' array (confirmed
    present directly on the scoreboard response for volleyball, each entry
    carrying an explicit 'period' number, e.g.
    {"value": 25.0, "period": 1}). Sets are matched up by that 'period'
    number rather than by list position/length, so a missing or
    out-of-order entry on one side can't silently misalign set N for one
    team with set N+1 for the other. Returns a list of
    (away_points, home_points) tuples in set order, or None if there's no
    usable overlap (caller falls back to the summary endpoint in that
    case).
    """
    def scores_by_period(lines):
        by_period = {}
        for entry in (lines or []):
            period = entry.get('period')
            value = entry.get('value')
            if period is None or value is None:
                continue
            try:
                by_period[int(period)] = int(value)
            except (TypeError, ValueError):
                continue
        return by_period

    away_by_period = scores_by_period(away_competitor.get('linescores'))
    home_by_period = scores_by_period(home_competitor.get('linescores'))

    common_periods = sorted(set(away_by_period) & set(home_by_period))
    sets = [(away_by_period[p], home_by_period[p]) for p in common_periods]

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

    url = f"{BASE_URL}?dates={date_str}&limit=500"

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
        status_type = comp.get('status', {}).get('type', {})
        # Checking `completed` rather than `state == 'post'` matters here:
        # a suspended/postponed match (e.g. weather-suspended outdoor
        # matches) reports state 'post' with completed=False and only a
        # partial set or two recorded - state alone would wrongly treat
        # that partial, unfinished match as a final result.
        if not status_type.get('completed'):
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
            unresolved = []
            if not away_team:
                unresolved.append(f"away='{away_raw}'")
            if not home_team:
                unresolved.append(f"home='{home_raw}'")
            print(f"  Warning: Could not resolve {' and '.join(unresolved)} against the wvb.csv roster; skipping match.")
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
            # Raw ESPN UTC kickoff time (e.g. '2026-09-09T18:00Z'). Lets
            # downstream consumers order matches chronologically within a
            # day - early-season tournaments routinely have a team play 2-3
            # matches in one day, and each of those matches has to be
            # applied in the order it was actually played, not scoreboard
            # order, so a team's rating going into its 2pm match reflects
            # what happened in its 10am match.
            'start_time': event.get('date', ''),
        })

    # Chronological order within the day, for readability and so any
    # consumer that just reads matches top-to-bottom (rather than
    # re-sorting) still gets the right order.
    matches.sort(key=lambda m: (not m['start_time'], m['start_time']))

    return matches


def save_matches(matches, csv_filename):
    with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['match_id', 'start_time', 'set', 'away team', 'home team', 'away score', 'home score'])
        for match in matches:
            for i, (away_score, home_score) in enumerate(match['sets'], start=1):
                writer.writerow([match['match_id'], match['start_time'], i, match['away_team'], match['home_team'],
                                  away_score, home_score])
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

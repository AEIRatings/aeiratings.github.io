"""
Shared ESPN fetching and team-name matching for the leagues that use the
catch-up Elo pipeline: men's (mcbb) and women's (wcbb) college basketball,
the NBA and the NHL.

Used by get<LEAGUE>scores.py (completed games), getMCBBscoresn.py /
getWCBBscoresn.py (upcoming games) and backfill_elo.py.
"""
import csv
import unicodedata
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests

# espn_path is the sport/league part of the ESPN scoreboard URL. groups=50
# limits college scoreboards to Division I games.
LEAGUES = {
    'mcbb': {
        'ratings_file': 'data/mcbb.csv',
        'espn_path': 'basketball/mens-college-basketball',
        'query': 'groups=50&',
    },
    'wcbb': {
        'ratings_file': 'data/wcbb.csv',
        'espn_path': 'basketball/womens-college-basketball',
        'query': 'groups=50&',
    },
    'nba': {
        'ratings_file': 'data/nba.csv',
        'espn_path': 'basketball/nba',
        'query': '',
    },
    'nhl': {
        'ratings_file': 'data/nhl.csv',
        'espn_path': 'hockey/nhl',
        'query': '',
    },
}

# ESPN season types: 1 preseason, 2 regular season, 3 postseason. Preseason
# and exhibition games never count toward the ratings.
PRESEASON = 1

# ESPN display names that differ from the names in data/<league>.csv.
# Keys are ESPN names, values are our canonical names (which the logos use).
ESPN_ALIASES = {
    'mcbb': {
        'LSU New Orleans Privateers': 'New Orleans Privateers',
        'St. Thomas Tommies': 'St. Thomas-Minnesota Tommies',
    },
    'wcbb': {
        'LSU New Orleans Privateers': 'New Orleans Privateers',
        'St. Thomas Tommies': 'St. Thomas-Minnesota Tommies',
        'East Tennessee State Buccaneers': 'East Tennessee State Bucs',
        'Massachusetts Minutewomen': 'Massachusetts Minutemen',
        'Missouri State Lady Bears': 'Missouri State Bears',
    },
    'nba': {
        'LA Clippers': 'Los Angeles Clippers',
    },
    'nhl': {},
}

# Last day of the season we look ahead to for upcoming games (covers the
# NCAA tournament finals in early April).
SEASON_END = datetime(2027, 4, 10)


def scoreboard_url(league, date):
    base = f"http://site.api.espn.com/apis/site/v2/sports/{LEAGUES[league]['espn_path']}/scoreboard"
    # limit raises ESPN's default page size.
    return f"{base}?{LEAGUES[league]['query']}limit=1000&dates={date.strftime('%Y%m%d')}"


def strip_accents(text):
    if not text:
        return text
    return ''.join(c for c in unicodedata.normalize('NFD', text)
                   if unicodedata.category(c) != 'Mn')


def _key(name):
    return strip_accents(name.lower()).strip()


def normalize_name(raw_name):
    """Fixes ESPN encoding quirks such as 'San JosÃ©' and 'No. 5 ' prefixes."""
    if not raw_name:
        return raw_name
    name = unicodedata.normalize('NFC', raw_name)
    name = name.replace('JosÃ©', 'José').replace('San Jose', 'San José')
    return name.replace('No. ', '').strip()


def load_name_lookup(league):
    """
    Returns {normalized key: canonical team name} for every team in the
    league's ratings file, plus the ESPN aliases for that league.
    """
    lookup = {}
    with open(LEAGUES[league]['ratings_file'], newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader, None)  # header
        for row in reader:
            if row and row[0].strip():
                lookup[_key(row[0])] = row[0].strip()
    for espn_name, ours in ESPN_ALIASES[league].items():
        if _key(ours) in lookup:
            lookup[_key(espn_name)] = lookup[_key(ours)]
    return lookup


def clean_team_name(raw_name, lookup):
    """Exact (case/accent-insensitive) match to a Division I team, else None."""
    if not raw_name:
        return None
    return lookup.get(_key(normalize_name(raw_name)))


def pacific_date(utc_string, fallback_day):
    """ESPN start time like '2026-11-13T00:00Z' -> Pacific 'YYYY-MM-DD'."""
    try:
        dt = datetime.strptime(utc_string, '%Y-%m-%dT%H:%MZ').replace(tzinfo=timezone.utc)
        return dt.astimezone(ZoneInfo('America/Los_Angeles')).strftime('%Y-%m-%d')
    except Exception:
        return fallback_day.strftime('%Y-%m-%d')


def fetch_events(league, date):
    """Raw ESPN events for one date ([] on any network error)."""
    url = scoreboard_url(league, date)
    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        return response.json().get('events', [])
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None


def _teams(event, lookup):
    comp = (event.get('competitions') or [{}])[0]
    away = home = None
    away_score = home_score = None
    for competitor in comp.get('competitors', []):
        name = clean_team_name(competitor.get('team', {}).get('displayName'), lookup)
        score = competitor.get('score')
        score = int(score) if score not in (None, '') else None
        if competitor.get('homeAway') == 'away':
            away, away_score = name, score
        else:
            home, home_score = name, score
    state = comp.get('status', {}).get('type', {}).get('state')
    return state, away, home, away_score, home_score


def fetch_final_games(league, date, lookup, seen_ids=None):
    """
    Completed regular-season or postseason games on one date between two
    teams in our ratings file (Division I only for college), as
    [(event_id, away, home, away_score, home_score), ...].
    Returns None if ESPN could not be reached, so callers can stop instead of
    silently skipping a day.
    """
    events = fetch_events(league, date)
    if events is None:
        return None
    games = []
    for event in events:
        event_id = event.get('id')
        if seen_ids is not None and event_id in seen_ids:
            continue
        if (event.get('season') or {}).get('type') == PRESEASON:
            continue
        state, away, home, a_score, h_score = _teams(event, lookup)
        if state != 'post' or not away or not home or a_score is None or h_score is None:
            continue
        if seen_ids is not None:
            seen_ids.add(event_id)
        games.append((event_id, away, home, a_score, h_score))
    return games


def fetch_upcoming_games(league, start, end, lookup):
    """
    Not-yet-started Division I games from start through end (inclusive), as
    [(away, home, 'YYYY-MM-DD'), ...] where the date is the tip-off date in
    US Pacific time (what the predictions pages compare against).
    """
    games, seen = [], set()
    day = start
    while day.date() <= end.date():
        events = fetch_events(league, day) or []
        for event in events:
            state, away, home, _, _ = _teams(event, lookup)
            if state != 'pre' or not away or not home:
                continue
            if event.get('id') in seen:
                continue
            seen.add(event.get('id'))
            games.append((away, home, pacific_date(event.get('date'), day)))
        day += timedelta(days=1)
    return games

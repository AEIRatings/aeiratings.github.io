import requests
import csv
from datetime import datetime, timedelta
import pytz

from getWVBscores import BASE_URL, GROUP_ID, load_team_names, normalize_name, clean_team_name


def convert_to_pacific_date(utc_string):
    """Converts ESPN UTC string to Pacific Date only."""
    try:
        utc_dt = datetime.strptime(utc_string, "%Y-%m-%dT%H:%MZ")
        utc_dt = pytz.utc.localize(utc_dt)
        pacific_tz = pytz.timezone('US/Pacific')
        pacific_dt = utc_dt.astimezone(pacific_tz)
        return pacific_dt.strftime('%Y-%m-%d')
    except Exception:
        return utc_string


def fetch_upcoming_wvb_games():
    valid_team_names = load_team_names("data/wvb.csv")
    CSV_FILENAME = "data/wvb_games.csv"
    all_game_data = []
    seen_games = set()

    # D1 women's volleyball runs roughly late August through the National
    # Championship in mid-December, so 120 days ahead comfortably covers
    # the rest of a season no matter when this is run.
    DAYS_AHEAD = 120

    for i in range(0, DAYS_AHEAD):
        target_date = datetime.now() + timedelta(days=i)
        date_str = target_date.strftime('%Y%m%d')
        display_date = target_date.strftime('%Y-%m-%d')

        print(f"[{i}/{DAYS_AHEAD}] Checking games for {display_date}...")

        url = f"{BASE_URL}?groups={GROUP_ID}&dates={date_str}&limit=500"

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
            game_date_pacific = convert_to_pacific_date(game_time_utc)

            competitors = comp.get('competitors', [])
            away_team, home_team = None, None

            for competitor in competitors:
                raw_name = normalize_name(competitor.get('team', {}).get('displayName'))
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

    with open(CSV_FILENAME, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['away team', 'home team', 'game date (Pacific)'])
        writer.writerows(all_game_data)

    if all_game_data:
        print(f"\n✅ Finished! Saved {len(all_game_data)} total games to {CSV_FILENAME}")
    else:
        print("\nNo upcoming games found for the specified period.")


if __name__ == '__main__':
    fetch_upcoming_wvb_games()

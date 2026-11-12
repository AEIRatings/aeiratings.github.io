"""
Writes every upcoming Division I wcbb game from today through the end of the
season to data/wcbb_games.csv, for the predictions page.
"""
import csv
from datetime import datetime

from espn_common import SEASON_END, fetch_upcoming_games, load_name_lookup

CSV_FILENAME = 'data/wcbb_games.csv'

if __name__ == '__main__':
    games = fetch_upcoming_games('wcbb', datetime.now(), SEASON_END, load_name_lookup('wcbb'))
    with open(CSV_FILENAME, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['away team', 'home team', 'game date (Pacific)'])
        writer.writerows(games)
    print(f"Saved {len(games)} upcoming game(s) to {CSV_FILENAME}")

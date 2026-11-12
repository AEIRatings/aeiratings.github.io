"""
Writes every upcoming Division I mcbb game from today through the end of the
season to data/mcbb_games.csv, for the predictions page.
"""
import csv
from datetime import datetime

from cbb_common import SEASON_END, fetch_upcoming_games, load_name_lookup

CSV_FILENAME = 'data/mcbb_games.csv'

if __name__ == '__main__':
    games = fetch_upcoming_games('mcbb', datetime.now(), SEASON_END, load_name_lookup('mcbb'))
    with open(CSV_FILENAME, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['away team', 'home team', 'game date (Pacific)'])
        writer.writerows(games)
    print(f"Saved {len(games)} upcoming game(s) to {CSV_FILENAME}")

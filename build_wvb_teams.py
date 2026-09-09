"""
One-time/manual bootstrap for the NCAA Women's Volleyball roster.

Fetches the full Division I women's volleyball team list from ESPN's site
API and writes data/wvb_preseason.csv (a fixed Elo=1000 baseline used by
backfill_wvb.py) plus data/wvb.csv (the live ratings file the daily
pipeline reads/writes), unless data/wvb.csv already exists - in which
case it's left untouched so a re-run can't clobber ratings that have
already played out. Run this once via the "Bootstrap WVB Teams" workflow
(or locally) before the daily scores/elo workflow is enabled.
"""

import csv
import os
import requests

TEAMS_URL = "https://site.api.espn.com/apis/site/v2/sports/volleyball/womens-college-volleyball/teams"
GROUP_ID = 50  # Division I
PRESEASON_FILE = "data/wvb_preseason.csv"
RATINGS_FILE = "data/wvb.csv"
STARTING_ELO = 1000
MAX_PAGES = 20  # safety cap; ESPN paginates ~50 teams/page and D1 WVB has ~330 teams


def fetch_all_teams():
    teams = []
    seen = set()
    page = 1

    while page <= MAX_PAGES:
        url = f"{TEAMS_URL}?groups={GROUP_ID}&limit=500&page={page}"
        try:
            print(f" -> Fetching {url}")
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching teams page {page}: {e}")
            break

        page_teams = []
        for sport in data.get('sports', []):
            for league in sport.get('leagues', []):
                for entry in league.get('teams', []):
                    team = entry.get('team', {})
                    name = team.get('displayName')
                    if name and name not in seen:
                        seen.add(name)
                        page_teams.append(name)

        if not page_teams:
            break

        teams.extend(page_teams)
        page += 1

    return sorted(teams)


def write_roster(teams):
    os.makedirs('data', exist_ok=True)

    if not teams:
        print("No teams fetched from ESPN; aborting without touching existing files.")
        return

    with open(PRESEASON_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Team', 'Elo', 'Conference', 'Notes', 'RatingUpdated'])
        for team in teams:
            writer.writerow([team, STARTING_ELO, '', '', 'FALSE'])
    print(f"Wrote {len(teams)} teams to {PRESEASON_FILE}")

    if os.path.exists(RATINGS_FILE):
        print(f"{RATINGS_FILE} already exists - leaving current ratings untouched. "
              f"Delete it first if you want to reset every team back to the fresh preseason baseline.")
        return

    with open(RATINGS_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Team', 'Elo', 'Conference', 'Notes', 'RatingUpdated'])
        for team in teams:
            writer.writerow([team, STARTING_ELO, '', '', 'FALSE'])
    print(f"Wrote {len(teams)} teams to {RATINGS_FILE}")


if __name__ == '__main__':
    fetch_all_teams_result = fetch_all_teams()
    write_roster(fetch_all_teams_result)

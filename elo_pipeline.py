"""
Shared score-fetching and Elo-updating steps for mcbb, wcbb, nba and nhl.

The daily job no longer assumes it ran yesterday. data/<league>_last_update.txt
records the last date whose games are already in the ratings, and each run
replays every day after it through yesterday, in order. A missed or failed run
is caught up next time, and a re-run never counts the same day twice.
"""
import csv
import os
from datetime import datetime, timedelta

import pandas as pd

from espn_common import load_name_lookup, fetch_final_games, LEAGUES

DATE_FMT = '%Y-%m-%d'


def state_file(league):
    return f'data/{league}_last_update.txt'


def scores_file(league):
    return f'{league}_scores_previous_day.csv'


def through_file(league):
    return f'{league}_scores_through.txt'


def read_last_update(league):
    with open(state_file(league), encoding='utf-8') as f:
        return datetime.strptime(f.read().strip(), DATE_FMT)


def calculate_new_elo(AElo, HElo, ascore, hscore):
    """AEI Elo update (same formula as the other leagues). Returns (away, home)."""
    if ascore > hscore:
        ex = 1 / (1 + 10 ** ((HElo - AElo) / 400))
    else:
        ex = 1 / (1 + 10 ** ((AElo - HElo) / 400))

    diff = ascore - hscore
    sign = 1 if diff > 0 else -1 if diff < 0 else 0
    act = abs(diff + 1) ** 0.42 * sign

    gap_sign = 1 if HElo - AElo > 0 else -1 if HElo - AElo < 0 else 0
    AElo_new = (AElo + 4 * (act / (ex + 0.1))) * abs(HElo - AElo) ** (gap_sign / 1000)
    HElo_new = HElo - (AElo_new - AElo)
    return AElo_new, HElo_new


def fetch_scores(league, end_date=None):
    """
    Fetches every completed game after the last update through end_date
    (default: yesterday) and writes them, in date order, to
    <league>_scores_previous_day.csv. Writes the last date actually fetched
    to <league>_scores_through.txt.
    """
    lookup = load_name_lookup(league)
    start = read_last_update(league) + timedelta(days=1)
    end = end_date or (datetime.now() - timedelta(days=1))
    end = datetime(end.year, end.month, end.day)

    rows, seen, through = [], set(), start - timedelta(days=1)
    day = start
    while day <= end:
        games = fetch_final_games(league, day, lookup, seen)
        if games is None:
            print(f"Stopping at {day:%Y-%m-%d}; it will be retried on the next run.")
            break
        for event_id, away, home, a_score, h_score in games:
            rows.append([day.strftime(DATE_FMT), event_id, away, home, a_score, h_score])
        print(f"{day:%Y-%m-%d}: {len(games)} game(s)")
        through = day
        day += timedelta(days=1)

    with open(scores_file(league), 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['date', 'event id', 'away team', 'home team', 'away score', 'home score'])
        writer.writerows(rows)
    with open(through_file(league), 'w', encoding='utf-8') as f:
        f.write(through.strftime(DATE_FMT))
    print(f"Saved {len(rows)} game(s) from {start:%Y-%m-%d} through {through:%Y-%m-%d} to {scores_file(league)}")


def update_ratings(league):
    """Applies the fetched games to data/<league>.csv and advances the state file."""
    ratings_file = LEAGUES[league]['ratings_file']
    if not os.path.exists(through_file(league)):
        print(f"{through_file(league)} not found; run the score fetch first.")
        return
    with open(through_file(league), encoding='utf-8') as f:
        through = datetime.strptime(f.read().strip(), DATE_FMT)
    if through <= read_last_update(league):
        print("No new days to apply.")
        return

    ratings_df = pd.read_csv(ratings_file)
    ratings_df['Elo'] = pd.to_numeric(ratings_df['Elo'], errors='coerce')
    ratings = ratings_df.set_index('Team')['Elo'].to_dict()
    scores = pd.read_csv(scores_file(league), dtype={'date': str})

    updated = set()
    for _, row in scores.iterrows():
        away, home = row['away team'], row['home team']
        if away not in ratings or home not in ratings:
            print(f"Warning: {away} vs {home} has a team missing from {ratings_file}; skipped.")
            continue
        ratings[away], ratings[home] = calculate_new_elo(
            ratings[away], ratings[home], int(row['away score']), int(row['home score']))
        updated.update([away, home])

    ratings_df['Elo'] = ratings_df['Team'].map(ratings)
    ratings_df['RatingUpdated'] = ratings_df['Team'].isin(updated)
    ratings_df.to_csv(ratings_file, index=False)
    with open(state_file(league), 'w', encoding='utf-8') as f:
        f.write(through.strftime(DATE_FMT) + '\n')

    print(f"Applied {len(scores)} game(s) through {through:%Y-%m-%d}; {len(updated)} team(s) updated.")

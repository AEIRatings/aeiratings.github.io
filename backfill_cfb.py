import argparse
from datetime import datetime, timedelta

import pandas as pd

from getCFBscores import load_team_names, fetch_games_for_date
from elo_updater_cfb import calculate_new_elo


def backfill(start_date_str, end_date_str, baseline_file, output_file):
    """
    Replays every CFB game from start_date_str through end_date_str
    (inclusive, 'YYYY-MM-DD') in chronological order on top of the ratings
    in baseline_file, using the same ESPN fetch/alias-matching logic as the
    daily job, and writes the resulting ratings to output_file.

    Games are applied day-by-day (not all at once) because each day's Elo
    calculation depends on the ratings produced by the previous day.
    """
    ratings_df = pd.read_csv(baseline_file)
    ratings_df['Elo'] = pd.to_numeric(ratings_df['Elo'], errors='coerce')
    current_ratings = ratings_df.set_index('Team')['Elo'].to_dict()

    espn_aliases = load_team_names()

    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

    last_day_updated_teams = set()
    total_games = 0

    day = start_date
    while day <= end_date:
        file_date_str = day.strftime('%Y-%m-%d')
        games = fetch_games_for_date(day, espn_aliases)

        day_updated_teams = set()
        for away_team, home_team, away_score, home_score in games:
            if away_team not in current_ratings or home_team not in current_ratings:
                missing = away_team if away_team not in current_ratings else home_team
                print(f"  Warning: '{missing}' not found in ratings. Skipping {away_team} vs {home_team}.")
                continue

            AElo = current_ratings[away_team]
            HElo = current_ratings[home_team]
            AElo_new, HElo_new = calculate_new_elo(AElo, HElo, away_score, home_score)
            current_ratings[away_team] = AElo_new
            current_ratings[home_team] = HElo_new
            day_updated_teams.add(away_team)
            day_updated_teams.add(home_team)

        print(f"{file_date_str}: {len(games)} game(s), {len(day_updated_teams)} team(s) updated")
        total_games += len(games)
        last_day_updated_teams = day_updated_teams
        day += timedelta(days=1)

    ratings_df = ratings_df.set_index('Team')
    ratings_df['Elo'] = ratings_df.index.map(current_ratings)
    ratings_df = ratings_df.reset_index()
    ratings_df['RatingUpdated'] = ratings_df['Team'].apply(lambda t: t in last_day_updated_teams)
    ratings_df.to_csv(output_file, index=False)

    print(f"\nDone. Replayed {total_games} total game(s) from {start_date_str} through {end_date_str}.")
    print(f"Saved final ratings to '{output_file}'.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Replay CFB games day-by-day from a preseason baseline to rebuild Elo ratings."
    )
    parser.add_argument('--start', required=True, help="First date to replay, YYYY-MM-DD (inclusive)")
    parser.add_argument('--end', required=True, help="Last date to replay, YYYY-MM-DD (inclusive)")
    parser.add_argument('--baseline', default='data/cfb_preseason.csv', help="Starting ratings CSV")
    parser.add_argument('--output', default='data/cfb.csv', help="File to write the final ratings to")
    args = parser.parse_args()

    backfill(args.start, args.end, args.baseline, args.output)

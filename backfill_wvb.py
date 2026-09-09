import argparse
from datetime import datetime, timedelta

import pandas as pd

from getWVBscores import fetch_matches_for_date
from elo_updater_wvb import calculate_new_elo


def backfill(start_date_str, end_date_str, baseline_file, output_file):
    """
    Replays every WVB match from start_date_str through end_date_str
    (inclusive, 'YYYY-MM-DD') in chronological order on top of the ratings
    in baseline_file, applying each match set-by-set exactly like the
    daily job (elo_updater_wvb.process_matches), and writes the resulting
    ratings to output_file.

    Days are applied in order (each day's starting ratings are whatever
    the previous day left behind), and within a day each match is applied
    set-by-set (each set's starting ratings are whatever the previous set
    in that same match left behind).
    """
    ratings_df = pd.read_csv(baseline_file)
    ratings_df['Elo'] = pd.to_numeric(ratings_df['Elo'], errors='coerce')
    current_ratings = ratings_df.set_index('Team')['Elo'].to_dict()
    valid_team_names = set(current_ratings.keys())

    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

    last_day_updated_teams = set()
    total_matches = 0
    total_sets = 0

    day = start_date
    while day <= end_date:
        file_date_str = day.strftime('%Y-%m-%d')
        matches = fetch_matches_for_date(day, valid_team_names)

        day_updated_teams = set()
        for match in matches:
            away_team = match['away_team']
            home_team = match['home_team']

            if away_team not in current_ratings or home_team not in current_ratings:
                missing = away_team if away_team not in current_ratings else home_team
                print(f"  Warning: '{missing}' not found in ratings. Skipping {away_team} @ {home_team}.")
                continue

            for away_score, home_score in match['sets']:
                AElo = current_ratings[away_team]
                HElo = current_ratings[home_team]
                AElo_new, HElo_new = calculate_new_elo(AElo, HElo, away_score, home_score)
                current_ratings[away_team] = AElo_new
                current_ratings[home_team] = HElo_new
                total_sets += 1

            day_updated_teams.add(away_team)
            day_updated_teams.add(home_team)
            total_matches += 1

        print(f"{file_date_str}: {len(matches)} match(es), {len(day_updated_teams)} team(s) updated")
        last_day_updated_teams = day_updated_teams
        day += timedelta(days=1)

    ratings_df = ratings_df.set_index('Team')
    ratings_df['Elo'] = ratings_df.index.map(current_ratings)
    ratings_df = ratings_df.reset_index()
    ratings_df['RatingUpdated'] = ratings_df['Team'].apply(lambda t: t in last_day_updated_teams)
    ratings_df.to_csv(output_file, index=False)

    print(f"\nDone. Replayed {total_matches} match(es), {total_sets} set(s) total from {start_date_str} through {end_date_str}.")
    print(f"Saved final ratings to '{output_file}'.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Replay WVB matches day-by-day, set-by-set, from a preseason baseline to rebuild Elo ratings."
    )
    parser.add_argument('--start', required=True, help="First date to replay, YYYY-MM-DD (inclusive)")
    parser.add_argument('--end', required=True, help="Last date to replay, YYYY-MM-DD (inclusive)")
    parser.add_argument('--baseline', default='data/wvb_preseason.csv', help="Starting ratings CSV")
    parser.add_argument('--output', default='data/wvb.csv', help="File to write the final ratings to")
    args = parser.parse_args()

    backfill(args.start, args.end, args.baseline, args.output)

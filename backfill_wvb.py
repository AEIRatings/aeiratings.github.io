import argparse
from datetime import datetime, timedelta

import pandas as pd

from getWVBscores import fetch_matches_for_date
from elo_updater_wvb import calculate_new_elo, STARTING_ELO


def backfill(start_date_str, end_date_str, baseline_file, output_file):
    """
    Replays every WVB match from start_date_str through end_date_str
    (inclusive, 'YYYY-MM-DD') in chronological order on top of the ratings
    in baseline_file, applying each match set-by-set exactly like the
    daily job (elo_updater_wvb.process_matches), and writes the resulting
    ratings to output_file.

    Days are applied in order (each day's starting ratings are whatever
    the previous day left behind). Within a day, matches are applied in
    chronological start-time order - not fetch order - since a team can
    play more than one match on the same day (early-season tournaments
    routinely have teams playing 2-3 matches in a single day), and each
    set's starting ratings must reflect every set of every earlier match
    that team has already played that day, not just earlier sets of the
    same match.
    """
    ratings_df = pd.read_csv(baseline_file)
    ratings_df['Elo'] = pd.to_numeric(ratings_df['Elo'], errors='coerce')
    current_ratings = ratings_df.set_index('Team')['Elo'].to_dict()
    valid_team_names = set(current_ratings.keys())

    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

    last_day_updated_teams = set()
    new_teams_registered = set()
    total_matches = 0
    total_sets = 0

    day = start_date
    while day <= end_date:
        file_date_str = day.strftime('%Y-%m-%d')
        matches = fetch_matches_for_date(day, valid_team_names)
        # fetch_matches_for_date already returns matches sorted by
        # start_time, but re-sort defensively here too since correctness
        # of same-day ordering is what this whole loop depends on.
        matches.sort(key=lambda m: (not m.get('start_time'), m.get('start_time') or ''))

        day_updated_teams = set()
        for match in matches:
            away_team = match['away_team']
            home_team = match['home_team']

            # A team not yet in current_ratings is a real D1 program that
            # just isn't registered yet (this endpoint is D1-only), e.g. a
            # school that started sponsoring volleyball mid-cycle - not a
            # bad match. Register it at the standard starting Elo instead
            # of skipping every match it plays for the rest of the backfill.
            for team in (away_team, home_team):
                if team not in current_ratings:
                    current_ratings[team] = STARTING_ELO
                    new_teams_registered.add(team)
                    print(f"  Note: '{team}' isn't in the baseline yet - registering it at the starting "
                          f"Elo of {STARTING_ELO}.")

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

    if new_teams_registered:
        other_columns = [c for c in ratings_df.columns if c not in ('Team', 'Elo')]
        new_rows = pd.DataFrame([
            {'Team': team, 'Elo': current_ratings[team], **{c: '' for c in other_columns}}
            for team in sorted(new_teams_registered)
        ])
        ratings_df = pd.concat([ratings_df, new_rows], ignore_index=True)

    ratings_df['RatingUpdated'] = ratings_df['Team'].apply(lambda t: t in last_day_updated_teams)
    ratings_df.to_csv(output_file, index=False)

    print(f"\nDone. Replayed {total_matches} match(es), {total_sets} set(s) total from {start_date_str} through {end_date_str}.")
    print(f"Saved final ratings to '{output_file}'.")
    if new_teams_registered:
        print(f"Registered {len(new_teams_registered)} new team(s) not in the baseline: "
              f"{', '.join(sorted(new_teams_registered))}")


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

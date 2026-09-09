import pandas as pd
import numpy as np

# Define the constants/files
RATINGS_FILE = 'data/wvb.csv'
SCORES_FILE = 'wvb_scores_previous_day.csv'
OUTPUT_FILE = 'data/wvb.csv'


def calculate_new_elo(AElo, HElo, ascore, hscore):
    """
    Calculates the new Elo ratings for the Away and Home teams based on the
    same modified-Elo formula used by every other AEIRatings sport (see
    elo_updater_cfb.py). It is generic over any pair of "away score" /
    "home score" values, which is what lets volleyball reuse it once per
    set instead of once per match (see process_matches below).

    Args:
        AElo (float): Current Elo rating of the Away Team.
        HElo (float): Current Elo rating of the Home Team.
        ascore (int): Away team's points in this set.
        hscore (int): Home team's points in this set.

    Returns:
        tuple: (New Elo rating for Away Team, New Elo rating for Home Team)
    """

    # 1. Expected Score for Away Team (ex)
    if (ascore > hscore):
        ex = 1 / (1 + 10 ** ((HElo - AElo) / 400))
    else:
        ex = 1 / (1 + 10 ** ((AElo - HElo) / 400))

    # 2. Actual Score Modifier (act)
    act = abs((ascore - hscore) + 1) ** 0.42 * (1 if ascore - hscore > 0 else -1 if ascore - hscore < 0 else 0)

    # 3. New Rating Adjustment for Away Team (nra / AElo_new)
    AElo_new = (AElo + 4 * (act / (ex + 0.1))) * abs(HElo - AElo) ** (
        (1 if HElo - AElo > 0 else -1 if HElo - AElo < 0 else 0) / 1000
    )

    # 4. New Rating for Home Team (nrh / HElo_new) - Zero-sum change
    HElo_new = HElo - (AElo_new - AElo)

    return AElo_new, HElo_new


def process_matches():
    """
    Reads existing Elo ratings and set-by-set match results, then replays
    each match one set at a time: the ratings entering set 2 are whatever
    set 1 just produced, the ratings entering set 3 are whatever set 2 just
    produced, and so on until the match's last set is applied.

    Matches are applied in chronological (start_time) order, not file/
    scoreboard order, because a team can play more than one match on the
    same day (very common in early-season tournaments - pool play routinely
    has a team playing 2-3 matches in a single day). If that team's 10am
    match isn't applied before its 2pm match, the 2pm match would be scored
    against a stale rating.
    """
    try:
        # Load current Elo ratings
        ratings_df = pd.read_csv(RATINGS_FILE)
        ratings_df['Elo'] = pd.to_numeric(ratings_df['Elo'], errors='coerce')
        current_ratings = ratings_df.set_index('Team')['Elo'].to_dict()

        # Load set-by-set scores (long format: one row per set)
        scores_df = pd.read_csv(SCORES_FILE)

    except FileNotFoundError:
        print(f"Error: Required file not found. Please ensure both '{RATINGS_FILE}' and '{SCORES_FILE}' are available.")
        return
    except KeyError:
        print(f"Error: The input files are missing required columns. Check if '{RATINGS_FILE}' has 'Team' and 'Elo', "
              f"and '{SCORES_FILE}' has 'match_id', 'set', 'away team', 'home team', 'away score', and 'home score'.")
        return
    except Exception as e:
        print(f"An unexpected error occurred during file loading: {e}")
        return

    if scores_df.empty:
        print("No sets to process today.")
        ratings_df['RatingUpdated'] = False
        ratings_df.to_csv(OUTPUT_FILE, index=False)
        return

    updated_teams = set()
    matches_processed = 0
    sets_processed = 0

    if 'start_time' not in scores_df.columns:
        scores_df['start_time'] = ''
    scores_df['start_time'] = scores_df['start_time'].fillna('')

    # Build one (start_time, match_id, sorted_sets) tuple per match, then
    # sort the matches themselves by start_time - missing/unparseable
    # timestamps sort last (via the `not start_time` key) rather than
    # first, since '' < any real ISO timestamp string would otherwise put
    # them first. Within each match, sets are explicitly re-sorted so set 1
    # is always applied before set 2, etc.
    match_groups = []
    for match_id, match_sets in scores_df.groupby('match_id', sort=False):
        match_sets = match_sets.sort_values('set')
        start_time = match_sets.iloc[0]['start_time'] or ''
        match_groups.append((start_time, match_id, match_sets))

    match_groups.sort(key=lambda g: (not g[0], g[0]))

    for start_time, match_id, match_sets in match_groups:
        away_team = match_sets.iloc[0]['away team']
        home_team = match_sets.iloc[0]['home team']

        if away_team not in current_ratings or home_team not in current_ratings:
            missing = away_team if away_team not in current_ratings else home_team
            print(f"Warning: Team '{missing}' not found in '{RATINGS_FILE}'. Skipping match {match_id} "
                  f"({away_team} @ {home_team}).")
            continue

        trajectory = [(0, current_ratings[away_team], current_ratings[home_team])]
        applied_any_set = False

        for _, row in match_sets.iterrows():
            set_num = row['set']
            try:
                away_score = int(row['away score'])
                home_score = int(row['home score'])
            except (ValueError, TypeError):
                print(f"  Skipping set {set_num} of match {match_id}: scores are not valid numbers.")
                continue

            # Ratings read here reflect every set already applied earlier in
            # this same loop - this is the "run set 1, update, run set 2,
            # update again" behavior the model is built around.
            AElo = current_ratings[away_team]
            HElo = current_ratings[home_team]
            AElo_new, HElo_new = calculate_new_elo(AElo, HElo, away_score, home_score)

            current_ratings[away_team] = AElo_new
            current_ratings[home_team] = HElo_new
            trajectory.append((set_num, AElo_new, HElo_new))
            sets_processed += 1
            applied_any_set = True

        if not applied_any_set:
            continue

        updated_teams.add(away_team)
        updated_teams.add(home_team)
        matches_processed += 1

        when = f" ({start_time})" if start_time else ""
        print(f"Match {match_id}{when}: {away_team} @ {home_team} - {len(trajectory) - 1} set(s) applied sequentially")
        for set_num, a, h in trajectory:
            label = "start" if set_num == 0 else f"after set {int(set_num)}"
            print(f"    {label}: {away_team}={a:.2f}, {home_team}={h:.2f}")

    # After processing every match, prepare the final output DataFrame
    ratings_df = ratings_df.set_index('Team')
    ratings_df['Elo'] = ratings_df.index.map(current_ratings)
    ratings_df = ratings_df.reset_index()
    ratings_df['RatingUpdated'] = ratings_df['Team'].apply(lambda team: team in updated_teams)

    ratings_df.to_csv(OUTPUT_FILE, index=False)

    print(f"\nSuccessfully calculated new Elo ratings and saved to '{OUTPUT_FILE}'.")
    print(f"Processed {matches_processed} match(es), {sets_processed} set(s) total. "
          f"Updated ratings for {len(updated_teams)} team(s) that played.")


if __name__ == '__main__':
    process_matches()

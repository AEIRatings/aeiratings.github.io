"""
Applies the games in nhl_scores_previous_day.csv to data/nhl.csv and
advances data/nhl_last_update.txt. See elo_pipeline.py.
"""
from elo_pipeline import calculate_new_elo, update_ratings  # noqa: F401

if __name__ == '__main__':
    update_ratings('nhl')

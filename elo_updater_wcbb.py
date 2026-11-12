"""
Applies the games in wcbb_scores_previous_day.csv to data/wcbb.csv and
advances data/wcbb_last_update.txt. See elo_pipeline.py.
"""
from elo_pipeline import calculate_new_elo, update_ratings  # noqa: F401

if __name__ == '__main__':
    update_ratings('wcbb')

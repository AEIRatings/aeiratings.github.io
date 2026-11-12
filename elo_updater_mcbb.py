"""
Applies the games in mcbb_scores_previous_day.csv to data/mcbb.csv and
advances data/mcbb_last_update.txt. See cbb_elo.py.
"""
from cbb_elo import calculate_new_elo, update_ratings  # noqa: F401

if __name__ == '__main__':
    update_ratings('mcbb')

"""
Fetches every completed wcbb game since data/wcbb_last_update.txt through
yesterday into wcbb_scores_previous_day.csv. See cbb_elo.py.
"""
from cbb_elo import fetch_scores

if __name__ == '__main__':
    fetch_scores('wcbb')

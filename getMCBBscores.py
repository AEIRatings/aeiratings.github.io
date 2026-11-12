"""
Fetches every completed mcbb game since data/mcbb_last_update.txt through
yesterday into mcbb_scores_previous_day.csv. See cbb_elo.py.
"""
from cbb_elo import fetch_scores

if __name__ == '__main__':
    fetch_scores('mcbb')

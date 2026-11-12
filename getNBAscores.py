"""
Fetches every completed NBA game since data/nba_last_update.txt through
yesterday into nba_scores_previous_day.csv. See elo_pipeline.py.
"""
from elo_pipeline import fetch_scores

if __name__ == '__main__':
    fetch_scores('nba')

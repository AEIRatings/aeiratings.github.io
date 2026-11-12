"""
Fetches every completed wcbb game since data/wcbb_last_update.txt through
yesterday into wcbb_scores_previous_day.csv. See elo_pipeline.py.
"""
from elo_pipeline import fetch_scores

if __name__ == '__main__':
    fetch_scores('wcbb')

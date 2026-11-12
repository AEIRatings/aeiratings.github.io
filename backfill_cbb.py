"""
Rebuilds data/<league>.csv for mcbb or wcbb by replaying every game from
--start through --end (inclusive) on top of the preseason ratings in
data/<league>_preseason.csv, using the same code as the daily job.

    python backfill_cbb.py --league mcbb --start 2026-11-01 --end 2026-11-11
"""
import argparse
import shutil
from datetime import datetime, timedelta

from cbb_common import LEAGUES
from cbb_elo import DATE_FMT, fetch_scores, state_file, update_ratings

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--league', required=True, choices=sorted(LEAGUES))
    parser.add_argument('--start', required=True, help='First date to replay, YYYY-MM-DD')
    parser.add_argument('--end', help='Last date to replay, YYYY-MM-DD (default: yesterday)')
    args = parser.parse_args()

    start = datetime.strptime(args.start, DATE_FMT)
    end = datetime.strptime(args.end, DATE_FMT) if args.end else None

    shutil.copyfile(f'data/{args.league}_preseason.csv', LEAGUES[args.league]['ratings_file'])
    with open(state_file(args.league), 'w', encoding='utf-8') as f:
        f.write((start - timedelta(days=1)).strftime(DATE_FMT) + '\n')

    fetch_scores(args.league, end)
    update_ratings(args.league)

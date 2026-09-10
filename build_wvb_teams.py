"""
Validates and enriches the NCAA Women's Volleyball roster against
data/wcbb.csv (women's basketball).

This does NOT rebuild the roster from wcbb.csv's own team-name strings -
an earlier version of this script tried that and it was wrong: wcbb.csv
often uses a gender-specific or differently-abbreviated mascot for the
same school ("Penn State Lady Lions" vs volleyball's actual "Penn State
Nittany Lions", "Wyoming Cowgirls" vs "Wyoming Cowboys", "McNeese Cowgirls"
vs "McNeese Cowboys"), so swapping in wcbb.csv's name would have broken
future exact-name matching against ESPN's real volleyball data for every
one of those schools.

What it actually does, using data/wvb.csv's EXISTING team names (each one
either bootstrapped from ESPN's volleyball teams endpoint or seen in a
real scored match) as the source of truth for spelling:

1. DROPS any team that both (a) fails a conservative cross-check against
   wcbb.csv - same location-prefix matching getWVBscores.py's
   is_known_d1_school() uses, requiring the shared prefix to cover at
   least 2 words or the entirety of the shorter name (a single shared
   word like "Central" is not enough - too many unrelated schools share
   one) - and (b) is not on the small explicit-exception allowlist for
   real D1 programs wcbb.csv just doesn't happen to carry (e.g. West
   Florida, Savannah State, The Citadel - none of them sponsor D1 women's
   basketball). This is what actually removes the junk: ESPN teams-feed
   artifacts like "TBD TBD" and "Seattle University null", and schools
   that plain aren't D1 (Centenary, Montreat, Northeastern State, Rust,
   Seattle Pacific, Tuskegee, Wiley, Bowie State, Edward Waters, St.
   Francis Brooklyn - the last one dropped its whole athletics department
   in 2023).
2. BACKFILLS the Conference column from the matched wcbb.csv row wherever
   that cross-check succeeds, without touching Team, Elo, Notes, or
   RatingUpdated for any surviving row.

New schools that aren't in data/wvb.csv yet at all are intentionally left
alone here - getWVBscores.py's own auto-registration path (also
cross-checked against wcbb.csv) already adds those correctly, using
whatever name ESPN's volleyball feed actually reports for them, the first
time they show up in a real match. Seeding them here from wcbb.csv's name
would risk the exact same naming mismatch problem this script exists to
avoid.
"""

import csv
import os

from getWVBscores import load_wcbb_roster, normalize_match_key

RATINGS_FILE = "data/wvb.csv"
PRESEASON_FILE = "data/wvb_preseason.csv"
STARTING_ELO = 1000

# Confirmed non-D1 (or, for the first two, genuine ESPN-teams-feed
# garbage) after manual research - these fail the automated cross-check
# for the right reason, so they're dropped outright.
MANUAL_DROP = {
    "TBD TBD",
    "Seattle University null",
    "Centenary Gentlemen",
    "Montreat Cavaliers",
    "Northeastern State RiverHawks",
    "Rust Bearcats",
    "Seattle Pacific Falcons",
    "Tuskegee Golden Tigers",
    "Wiley Wildcats",
    "Bowie State Bulldogs",
    "Edward Waters Tigers",
    "St. Francis Brooklyn Terriers",  # dropped its entire athletics dept. in 2023
}

# Real D1 volleyball programs where the automated prefix cross-check
# can't confidently match data/wcbb.csv, either because wcbb.csv uses a
# gendered/differently-abbreviated mascot for the same school ("Georgia
# Lady Bulldogs" vs volleyball's "Georgia Bulldogs", "Wyoming Cowgirls"
# vs "Wyoming Cowboys"), a legacy location prefix ("New Orleans
# Privateers" vs "LSU New Orleans Privateers"), or isn't on wcbb.csv at
# all (West Florida, Savannah State, The Citadel - none sponsor D1
# women's basketball). Manually verified against data/wcbb.csv and
# independent confirmation of D1 status; empty string means "real D1
# program, but no conference available from wcbb.csv."
MANUAL_CONFERENCE = {
    "Georgia Bulldogs": "SEC",
    "Grambling Tigers": "SWAC",
    "Hampton Pirates": "CAA",
    "LSU New Orleans Privateers": "Southland",
    "McNeese Cowboys": "Southland",
    "Montana Grizzlies": "Big Sky",
    "Savannah State Tigers": "",
    "St. Thomas Tommies": "Summit",
    "Tennessee Volunteers": "SEC",
    "The Citadel Bulldogs": "",
    "UNLV Rebels": "Mountain West",
    "West Florida Argonauts": "",
    "Wyoming Cowboys": "Mountain West",
}


def match_wcbb_conference(team, wcbb_teams):
    """
    Returns the Conference of the wcbb.csv row that shares at least a
    2-word (or full-length) prefix with `team`, or None if there's no
    confident match. See the module docstring for why the threshold is
    2 words, not 1.
    """
    team_words = normalize_match_key(team).split()
    for wcbb_team, conference in wcbb_teams:
        wcbb_words = normalize_match_key(wcbb_team).split()
        common = 0
        for a, b in zip(team_words, wcbb_words):
            if a == b:
                common += 1
            else:
                break
        if common >= 2 or common == min(len(team_words), len(wcbb_words)):
            return conference
    return None


def load_wcbb_teams_with_conference(filename="data/wcbb.csv"):
    teams = []
    with open(filename, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            team = (row.get('Team') or '').strip()
            conference = (row.get('Conference') or '').strip()
            if team:
                teams.append((team, conference))
    return teams


def clean_roster(rows, wcbb_teams):
    kept = []
    dropped = []
    unresolved = []

    for row in rows:
        team = row['Team']

        if team in MANUAL_DROP:
            dropped.append(team)
            continue

        if team in MANUAL_CONFERENCE:
            conference = MANUAL_CONFERENCE[team]
            if conference:
                row['Conference'] = conference
            kept.append(row)
            continue

        conference = match_wcbb_conference(team, wcbb_teams)
        if conference is None:
            # The automated cross-check failed and this isn't a team
            # this script's maintainer has already researched - keep it
            # (Conference left unchanged) rather than guess, and flag it
            # so a human can add it to MANUAL_DROP or MANUAL_CONFERENCE.
            unresolved.append(team)
            kept.append(row)
            continue

        row['Conference'] = conference
        kept.append(row)

    return kept, dropped, unresolved


def write_csv(filename, rows, fieldnames):
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    if not os.path.exists(RATINGS_FILE):
        print(f"{RATINGS_FILE} doesn't exist yet - nothing to validate. "
              f"Run getWVBscores.py / getWVBscoresn.py first to start populating it.")
        return

    with open(RATINGS_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = [row for row in reader if row.get('Team', '').strip()]

    wcbb_teams = load_wcbb_teams_with_conference()
    kept, dropped, unresolved = clean_roster(rows, wcbb_teams)

    write_csv(RATINGS_FILE, kept, fieldnames)
    print(f"Kept {len(kept)} team(s) in {RATINGS_FILE}.")
    if dropped:
        print(f"Dropped {len(dropped)} team(s) that didn't cross-check as real D1 programs:")
        for team in dropped:
            print(f"  - {team}")
    if unresolved:
        print(f"\nWarning: {len(unresolved)} team(s) didn't cross-check against wcbb.csv and aren't in "
              f"MANUAL_DROP or MANUAL_CONFERENCE - kept as-is with Conference unchanged, but worth a "
              f"manual look (add each to one or the other in build_wvb_teams.py):")
        for team in unresolved:
            print(f"  - {team}")

    preseason_rows = [
        {'Team': row['Team'], 'Elo': STARTING_ELO, 'Conference': row.get('Conference', ''),
         'Notes': '', 'RatingUpdated': 'FALSE'}
        for row in kept
    ]
    write_csv(PRESEASON_FILE, preseason_rows, fieldnames)
    print(f"Wrote {len(preseason_rows)} team(s) to {PRESEASON_FILE} (Elo reset to {STARTING_ELO}).")


if __name__ == '__main__':
    main()

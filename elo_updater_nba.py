import pandas as pd
import numpy as np

# Define the constants/files
RATINGS_FILE = 'data/nba.csv'
SCORES_FILE = 'nba_scores_previous_day.csv'
OUTPUT_FILE = 'data/nba.csv'

def calculate_new_elo(AElo, HElo, ascore, hscore):
    """
    Calculates the new Elo ratings for the Away and Home teams based on the 
    provided set of formulas.

    Args:
        AElo (float): Current Elo rating of the Away Team.
        HElo (float): Current Elo rating of the Home Team.
        ascore (int): Score of the Away Team.
        hscore (int): Score of the Home Team.

    Returns:
        tuple: (New Elo rating for Away Team, New Elo rating for Home Team)
    """

    # 1. Expected Score for Away Team (ex)
    # ex = 1 / (1+ 10 ** ((AElo - HElo)/400))
    # Using np.power is robust for potential large exponents
    ex = 1 / (1+ 10 ** ((AElo - HElo)/400))

    # 2. Actual Score Modifier (act)
    # act = abs((ascore - hscore) + 1) ** 0.42 * (sign(ascore - hscore))
    act = abs((ascore - hscore) + 1) ** 0.42 * (1 if ascore - hscore > 0 else -1 if ascore - hscore < 0 else 0)

    # 3. New Rating Adjustment for Away Team (nra / AElo_new)
    # The second term is |HElo - AElo| ^ (sign(HElo - AElo) / 1000)
    AElo_new = (AElo + 4 * (act / (ex + 0.1))) * abs(HElo - AElo) ** ( (1 if HElo - AElo > 0 else -1 if HElo - AElo < 0 else 0) / 1000 )

    # 4. New Rating for Home Team (nrh / HElo_new) - Zero-sum change
    # nrh = HElo - (nra - AElo)
    # The change in AElo is AElo_new - AElo. This change is subtracted from HElo.
    HElo_new = HElo - (AElo_new-AElo)

    return AElo_new, HElo_new

def process_games():
    """
    Reads existing Elo ratings and game results, calculates new ratings,
    and outputs a CSV with the updated ratings.
    """
    try:
        # Load initial Elo ratings
        ratings_df = pd.read_csv(RATINGS_FILE)
        # Convert the rating column to numeric, coercing non-numeric values
        ratings_df['Rating'] = pd.to_numeric(ratings_df['Rating'], errors='coerce')
        # Create a dictionary for quick lookup: {Team: Rating}
        current_ratings = ratings_df.set_index('Team')['Rating'].to_dict()

        # Load game scores
        scores_df = pd.read_csv(SCORES_FILE)

    except FileNotFoundError as e:
        print(f"Error: Required file not found. Please ensure both '{RATINGS_FILE}' and '{SCORES_FILE}' are available.")
        return
    except KeyError as e:
        print(f"Error: The input files are missing required columns. Check if '{RATINGS_FILE}' has 'Team' and 'Rating', and '{SCORES_FILE}' has 'AwayTeam', 'HomeTeam', 'AwayScore', and 'HomeScore'.")
        return
    except Exception as e:
        print(f"An unexpected error occurred during file loading: {e}")
        return

    # Use a set to track which teams actually played a game and had their rating updated
    updated_teams = set()

    # Iterate through each game and calculate new ratings
    for index, row in scores_df.iterrows():
        away_team = row['AwayTeam']
        home_team = row['HomeTeam']
        
        # Ensure scores are integers
        try:
            # We use .item() to safely get scalar value from the cell
            away_score = int(row['AwayScore'])
            home_score = int(row['HomeScore'])
        except ValueError:
            print(f"Skipping game {index}: Scores for {away_team} vs {home_team} are not valid numbers.")
            continue
        
        # Look up current Elo ratings and skip game if team is missing
        try:
            AElo = current_ratings[away_team]
            HElo = current_ratings[home_team]
        except KeyError as e:
            print(f"Warning: Team {e} not found in '{RATINGS_FILE}'. Skipping game {away_team} vs {home_team}.")
            continue
            
        # Perform calculation
        AElo_new, HElo_new = calculate_new_elo(AElo, HElo, away_score, home_score)
        
        # Update ratings dictionary with the new values
        current_ratings[away_team] = AElo_new
        current_ratings[home_team] = HElo_new
        updated_teams.add(away_team)
        updated_teams.add(home_team)

    # After processing all games, prepare the final output DataFrame
    
    # Update the original ratings DataFrame with the new ratings
    ratings_df = ratings_df.set_index('Team')
    
    # Overwrite the 'Rating' column using the updated dictionary
    ratings_df['Rating'] = ratings_df.index.map(current_ratings)
    
    # Reset index and add a flag for updated teams
    ratings_df = ratings_df.reset_index()
    ratings_df['RatingUpdated'] = ratings_df['Team'].apply(lambda team: team in updated_teams)
    
    # Save the final DataFrame to a new CSV file
    ratings_df.to_csv(OUTPUT_FILE, index=False)
    
    print(f"Successfully calculated new Elo ratings and saved to '{OUTPUT_FILE}'.")
    print(f"Updated ratings for {len(updated_teams)} teams that played in the recorded games.")

# Execute the main function

process_games()

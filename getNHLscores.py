import requests
import csv
from datetime import datetime, timedelta

def fetch_and_save_scores():
    """
    Fetches scoreboard data for the previous day from the ESPN API 
    and saves the results to a CSV file named 'nba_scores_previous_day.csv'.
    """
    
    # 1. Determine the date for the data (yesterday)
    yesterday = datetime.now() - timedelta(days=1)
    # The API uses the YYYYMMDD format for the 'dates' parameter.
    date_str = yesterday.strftime('%Y%m%d') 
    file_date_str = yesterday.strftime('%Y-%m-%d') # For print message clarity

    # 2. Define the API endpoint
    BASE_URL = "http://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard"
    API_URL = f"{BASE_URL}?dates={date_str}"
    
    # 3. Define the static CSV filename as requested
    CSV_FILENAME = "nhl_scores_previous_day.csv"
    
    print(f"Fetching NHL scores for: {file_date_str} from {API_URL}")

    try:
        # 4. Make the API request
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from ESPN API: {e}")
        return

    # List to store processed game data
    game_data = []

    # The scoreboard data is typically found in the 'events' key
    events = data.get('events', [])
    
    if not events:
        print(f"No events found for {file_date_str} or the API returned no data.")
        # Create an empty file with just the header if no data is found
        with open(CSV_FILENAME, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['away team', 'home team', 'away score', 'home score'])
        print(f"Created CSV file with header: {CSV_FILENAME}")
        return

    # 5. Process the events
    for event in events:
        # Each event usually has one competition
        competitions = event.get('competitions', [])
        
        if not competitions:
            continue

        competition = competitions[0]
        competitors = competition.get('competitors', [])
        
        # Ensure the game is final before recording 
        # State 'post' means the game is finished.
        if competition.get('status', {}).get('type', {}).get('state') != 'post':
            print(f"Skipping event {event.get('name')}: Game status is not 'final'.")
            continue
        
        # Parse competitor data
        away_team_name, away_score = None, None
        home_team_name, home_score = None, None

        for competitor in competitors:
            team_info = competitor.get('team', {})
            score = competitor.get('score')
            
            # The 'homeAway' key distinguishes the teams
            if competitor.get('homeAway') == 'away':
                away_team_name = team_info.get('displayName')
                # Scores are returned as strings, convert to int for CSV
                away_score = int(score) if score is not None else 0 
            elif competitor.get('homeAway') == 'home':
                home_team_name = team_info.get('displayName')
                home_score = int(score) if score is not None else 0

        # 6. Store the data in the required format
        if all([away_team_name, home_team_name, away_score is not None, home_score is not None]):
            game_data.append([
                away_team_name,
                home_team_name,
                away_score,
                home_score
            ])
            
    # 7. Write the data to the CSV file
    try:
        with open(CSV_FILENAME, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write header: away team, home team, away score, home score
            writer.writerow(['away team', 'home team', 'away score', 'home score'])
            
            # Write data rows
            writer.writerows(game_data)
            
        print(f"Successfully saved {len(game_data)} game scores to {CSV_FILENAME}")
        
    except Exception as e:
        print(f"Error writing to CSV file: {e}")


if __name__ == '__main__':
    fetch_and_save_scores()

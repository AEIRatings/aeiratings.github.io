import csv
from bs4 import BeautifulSoup
import os

# --- Helper Functions for Data Merging ---

def read_existing_data(filename="data/nba.csv"):
    """Reads the current nba.csv file to preserve Elo and other columns."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return list(reader)
    except FileNotFoundError:
        print(f"Warning: The existing file '{filename}' was not found. Returning empty data.")
        return []

def normalize_team_name(team_name):
    """Standardize team name for lookup."""
    return team_name.strip()

def merge_data(scraped_data, existing_data):
    """
    Merges scraped wins/losses into existing data, keeping Elo/Division/Notes.
    """
    # Create a lookup map from the scraped data using the team name
    scraped_map = {normalize_team_name(item['team']): {'wins': item['wins'], 'losses': item['losses']} for item in scraped_data}
    
    merged_data = []
    
    for row in existing_data:
        team_name_key = normalize_team_name(row['Team'])
        scraped_record = scraped_map.get(team_name_key)
        
        # If we have a scraped record, update Wins and Losses in the existing row
        if scraped_record:
            row['Wins'] = scraped_record['wins']
            row['Losses'] = scraped_record['losses']
        
        merged_data.append(row)
        
    return merged_data

def write_to_csv(data, filename="data/nba.csv"):
    """
    Writes the merged data back to the nba.csv file.
    """
    if not data:
        print("No data found to write to CSV.")
        return

    # Use the expected fieldnames to maintain the correct CSV structure
    fieldnames = ['Team', 'Elo', 'Wins', 'Losses', 'Division', 'Notes'] 

    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        
        print(f"\nSuccessfully updated CSV file: {filename}")
        
    except IOError as e:
        print(f"An error occurred during CSV writing: {e}")

# --- End Helper Functions for Data Merging ---


def scrape_nba_standings(html_content):
    """
    Scrapes NBA team standings (team, wins, losses) from HTML content
    and returns a list of dictionaries.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    all_standings_data = []

    # Target IDs for the conference standings tables on basketball-reference.com
    target_ids = ['confs_standings_E', 'confs_standings_W']
    
    print(f"Searching for tables with IDs in content: {', '.join(target_ids)}")

    for table_id in target_ids:
        table = soup.find('table', id=table_id)
        
        # Basketball-Reference often hides tables in an HTML comment inside a div, 
        # so we also check the commented-out structure.
        if not table:
            from bs4 import Comment
            comment_wrapper = soup.find('div', id=f'all_{table_id}')
            if comment_wrapper:
                comment = comment_wrapper.find(string=lambda text: isinstance(text, Comment))
                if comment:
                    comment_soup = BeautifulSoup(comment, 'html.parser')
                    table = comment_soup.find('table', id=table_id)

        if not table:
            print(f"Warning: Could not find standings table with ID '{table_id}'")
            continue

        for row in table.find('tbody').find_all('tr'):
            # Filter for actual team rows which should have a 'wins' column
            wins_cell = row.find('td', {'data-stat': 'wins'})
            if not wins_cell:
                continue

            team_element = row.find('th', {'data-stat': 'team_name'})
            # Clean up the team name
            team_name = team_element.text.strip().split('(')[0].strip() if team_element else None
            
            if not team_name:
                continue

            wins = wins_cell.text.strip().replace('—', '0')
            losses_cell = row.find('td', {'data-stat': 'losses'})
            losses = losses_cell.text.strip().replace('—', '0') if losses_cell else '0'
            
            all_standings_data.append({
                'team': team_name, 
                'wins': wins, 
                'losses': losses
            })

    return all_standings_data

# Main execution block for the GitHub Action
if __name__ == "__main__":
    html_input_file = "nba2026.html" 
    csv_output_file = "data/nba.csv"

    print(f"Reading HTML content from: {html_input_file}")
    
    try:
        with open(html_input_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except FileNotFoundError:
        print(f"Error: HTML file not found at {html_input_file}. Cannot scrape.")
        exit(1)
    except Exception as e:
        print(f"An error occurred while reading the file: {e}")
        exit(1)
        
    # 1. Scrape the raw W/L data
    scraped_wl_data = scrape_nba_standings(html_content)
    
    if scraped_wl_data:
        # 2. Read the existing CSV
        existing_full_data = read_existing_data(filename=csv_output_file)
        
        # 3. Merge the new W/L data
        merged_data = merge_data(scraped_wl_data, existing_full_data)
        
        # 4. Write the merged data back to the CSV
        write_to_csv(merged_data, filename=csv_output_file)
    else:
        print("Could not scrape any W/L data. Aborting update.")

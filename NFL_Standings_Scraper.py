import csv
from bs4 import BeautifulSoup

# --- New Helper Functions for Data Merging ---

def read_existing_data(filename="data/nfl.csv"):
    """Reads the current nfl.csv file to preserve Elo and other columns."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return list(reader)
    except FileNotFoundError:
        print(f"Error: The existing file '{filename}' was not found. Cannot merge data.")
        return []

def merge_data(scraped_data, existing_data):
    """
    Merges scraped wins/losses into existing data, keeping Elo/Division/Notes.
    """
    # Create a lookup map from the scraped data for quick access
    # Uses the 'team' key from scraping to map to the full data's 'Team' key
    scraped_map = {item['team']: {'wins': item['wins'], 'losses': item['losses']} for item in scraped_data}
    
    merged_data = []
    
    for row in existing_data:
        team_name = row['Team']
        scraped_record = scraped_map.get(team_name)
        
        # If we have a scraped record, update Wins and Losses in the existing row
        if scraped_record:
            row['Wins'] = scraped_record['wins']
            row['Losses'] = scraped_record['losses']
        
        merged_data.append(row)
        
    return merged_data
    
# --- End New Helper Functions ---


def extract_standings(filename="nfl2025.html"):
    """
    Reads the HTML file and scrapes team, wins, and losses from 
    the AFC and NFC standings tables.
    """
    try:
        # Open and read the HTML file
        with open(filename, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except FileNotFoundError as e:
        print(f"Error: The file '{filename}' was not found. {e}")
        return []

    print(f"Parsing content from {filename}...")
    soup = BeautifulSoup(html_content, 'html.parser')
    all_teams_data = []

    # Target IDs for AFC and NFC standings tables on pro-football-reference.com
    target_ids = ["all_AFC", "all_NFC"]

    for div_id in target_ids:
        div_wrapper = soup.find('div', {'id': div_id, 'class': 'table_wrapper'})
        if not div_wrapper:
            continue

        table = div_wrapper.find('table', class_='stats_table')
        if not table:
            continue

        for row in table.find('tbody').find_all('tr'):
            if 'onecell' in row.get('class', []):
                continue

            team_cell = row.find('th', {'data-stat': 'team'})
            if team_cell:
                team_name = team_cell.get_text(strip=True)
            else:
                continue

            wins_cell = row.find('td', {'data-stat': 'wins'})
            losses_cell = row.find('td', {'data-stat': 'losses'})

            wins = wins_cell.get_text(strip=True) if wins_cell else '0'
            losses = losses_cell.get_text(strip=True) if losses_cell else '0'

            all_teams_data.append({
                'team': team_name,
                'wins': wins,
                'losses': losses
            })

    return all_teams_data


def write_to_csv(data, filename="data/nfl.csv"):
    """
    Writes the merged data back to the nfl.csv file.
    """
    if not data:
        print("No data found to write to CSV.")
        return

    fieldnames = list(data[0].keys())

    try:
        # Open the file and write the new data
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        
        print(f"\nSuccessfully updated CSV file: {filename}")
        
    except IOError as e:
        print(f"An error occurred during CSV writing: {e}")

if __name__ == "__main__":
    # The scraped HTML file name is hardcoded here for the GitHub Action to target
    scraped_html_file = "nfl2025.html" 

    # 1. Scrape the raw W/L data from the downloaded HTML file
    scraped_wl_data = extract_standings(filename=scraped_html_file)
    
    if scraped_wl_data:
        # 2. Read the existing CSV to preserve Elo, Division, etc.
        existing_full_data = read_existing_data(filename="data/nfl.csv")
        
        if existing_full_data:
            # 3. Merge the new W/L into the full data
            merged_data = merge_data(scraped_wl_data, existing_full_data)
            
            # 4. Write the merged data back to data/nfl.csv
            write_to_csv(merged_data, filename="data/nfl.csv")
        else:
            print("Could not read existing data for merging. Aborting update.")

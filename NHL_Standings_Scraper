import csv
from bs4 import BeautifulSoup
from bs4 import Comment
import os

# --- Helper Functions for Data Merging ---

def read_existing_data(filename="data/nhl.csv"):
    """Reads the current nhl.csv file to preserve Elo, Division, and Notes columns."""
    try:
        # Use DictReader for easy access to column names
        with open(filename, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            # Filter out any non-data rows (like the initial line)
            data = [row for row in reader if row.get('Team')]
            return data
    except FileNotFoundError:
        print(f"Warning: The existing file '{filename}' was not found. Returning empty data.")
        return []

def normalize_team_name(team_name):
    """Standardize team name for lookup (removes common HTML/CSV artifacts)."""
    # Removes trailing characters often used on Hockey-Reference to denote playoff eligibility
    return team_name.strip().replace('*', '').replace('+', '')

def merge_data(scraped_data, existing_data):
    """
    Merges scraped points into existing data, keeping Elo, Division, and Notes.
    """
    # Create a lookup map from the scraped data using the normalized team name
    scraped_map = {normalize_team_name(item['team']): item['points'] for item in scraped_data}
    
    merged_data = []
    
    for row in existing_data:
        team_name_key = normalize_team_name(row['Team'])
        new_points = scraped_map.get(team_name_key)
        
        # If we have a scraped points value, update the 'Points' column in the existing row
        if new_points is not None:
            row['Points'] = new_points
        
        merged_data.append(row)
        
    return merged_data

def write_to_csv(data, filename="data/nhl.csv"):
    """
    Writes the merged data back to the nhl.csv file.
    """
    if not data:
        print("No data found to write to CSV.")
        return

    # Use the expected fieldnames from the existing CSV structure
    fieldnames = ['Team', 'Elo', 'Points', 'Division', 'Notes'] 

    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            # Re-insert the initial metadata comment line from the original data source
            csvfile.write("Team,Elo,Points,Division,Notes\n") # This is a placeholder, normally extracted from existing file
            writer.writerows(data)
        
        print(f"\nSuccessfully updated CSV file: {filename}")
        
    except IOError as e:
        print(f"An error occurred during CSV writing: {e}")

# --- End Helper Functions for Data Merging ---


def scrape_nhl_standings(html_content):
    """
    Scrapes NHL team standings (team, points) from HTML content
    and returns a list of dictionaries.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    all_standings_data = []

    # Target IDs for the conference standings tables on hockey-reference.com
    target_ids = ['standings_EAS', 'standings_WES']
    
    def get_table_from_html(soup, table_id):
        # 1. Check for the table directly
        table = soup.find('table', id=table_id)
        
        # 2. Check for the table inside an HTML comment (common on Sports Reference sites)
        if not table:
            comment_wrapper = soup.find('div', id=f'all_{table_id}')
            if comment_wrapper:
                comment = comment_wrapper.find(string=lambda text: isinstance(text, Comment))
                if comment:
                    comment_soup = BeautifulSoup(comment, 'html.parser')
                    table = comment_soup.find('table', id=table_id)
        return table

    for table_id in target_ids:
        table = get_table_from_html(soup, table_id)

        if not table:
            continue

        for row in table.find('tbody').find_all('tr'):
            # Filter for actual team rows by checking for the 'points' column
            points_cell = row.find('td', {'data-stat': 'points'})
            if not points_cell:
                continue

            team_element = row.find('th', {'data-stat': 'team_name'})
            team_name = team_element.text.strip() if team_element else None
            
            if not team_name:
                continue

            points = points_cell.text.strip().replace('—', '0')
            
            all_standings_data.append({
                'team': team_name, 
                'points': points
            })

    return all_standings_data

# Main execution block for the GitHub Action
if __name__ == "__main__":
    html_input_file = "nhl2026.html" 
    csv_output_file = "data/nhl.csv"
    
    try:
        with open(html_input_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except FileNotFoundError:
        print(f"Error: HTML file not found at {html_input_file}. Cannot scrape.")
        exit(1)
        
    # 1. Scrape the raw Points data
    scraped_points_data = scrape_nhl_standings(html_content)
    
    if scraped_points_data:
        # 2. Read the existing CSV
        existing_full_data = read_existing_data(filename=csv_output_file)
        
        # 3. Merge the new Points data
        merged_data = merge_data(scraped_points_data, existing_full_data)
        
        # 4. Write the merged data back to the CSV
        write_to_csv(merged_data, filename=csv_output_file)
    else:
        print("Could not scrape any Points data. Aborting update.")

import requests
from bs4 import BeautifulSoup
import re
import pandas as pd

base_url = "https://www.ulaval.ca"
save_interval = 10

# Function to fetch and parse the webpage content
def fetch_webpage(url):
    response = requests.get(url)
    return BeautifulSoup(response.text, 'html.parser')

# Function to extract course information
def extract_course_info(soup):
    data = []
    
    # Find all buttons with the specified id pattern
    buttons = soup.find_all('button', id=re.compile(r'(automne|hiver|printemps|ete)-\d{4}-gif-\d{4}-'))
    
    for button in buttons:
        course_id = button['id']
        course_parts = course_id.split('-')
        course_season = course_parts[0].capitalize()
        course_year = course_parts[1]
        course_code = course_parts[2].upper()
        course_code += course_parts[3]
        course_group_letter = chr(65 + len(data))  # Generate group letters starting from 'A'
        
        course_name = f"{course_code}-{course_season}-{course_group_letter}"
        
        parent = button.find_parent().find_parent()
        
        toggle_sections = parent.find_all('div', class_='toggle-section--content')
        
        for section in toggle_sections:
            group_number = 0
            day = dates = start_time = end_time = location = class_type = teacher = "N/A"
            
            # Extracting data from the section
            try:
                teacher = section.find('strong', string='Enseignant:').next_sibling.strip()
            except AttributeError:
                pass

            try:
                class_type = section.find('strong', string='Type:').next_sibling.strip()
            except AttributeError:
                pass

            try:
                dates = section.find('strong', string='Dates:').next_sibling.strip()
            except AttributeError:
                pass

            try:
                day = section.find('strong', string='Journée:').next_sibling.strip()
            except AttributeError:
                pass

            try:
                time_range = section.find('strong', string='Horaire:').next_sibling.strip()
                start_time, end_time = time_range.split(' à ')
            except AttributeError:
                pass

            try:
                pavillon = section.find('strong', string='Pavillon:').next_sibling.strip()
                local = section.find('strong', string='Local:').next_sibling.strip()
                location = f"{pavillon} {local}"
            except AttributeError:
                pass

            # Append data to the list
            data.append({
                "Name": course_name,
                "Group Number": group_number,
                "Day": day,
                "Dates": dates,
                "Start Time": start_time,
                "End Time": end_time,
                "Location": location,
                "Type": class_type,
                "Teacher": teacher
            })

    return data

# Main function to scrape data and save to CSV
def main():
    all_course_data = []

    # Read URLs from the file
    with open('example_data.csv', 'r') as file:
        urls = file.readlines()
    
    for i, url_suffix in enumerate(urls, 1):
        url = base_url + url_suffix.strip()
        soup = fetch_webpage(url)
        course_data = extract_course_info(soup)
        all_course_data.extend(course_data)
        print(url_suffix)
        
        if i % save_interval == 0:
            df = pd.DataFrame(all_course_data)
            df.to_csv('course_data.csv', mode='a', header=False, index=False)
            print(f"Data saved to course_data.csv")
            all_course_data = []  # Clear the data after saving

    # Save any remaining data after the loop completes
    if all_course_data:
        df = pd.DataFrame(all_course_data)
        df.to_csv('course_data.csv', mode='a', header=False, index=False)
        print(f"Data saved to course_data.csv")

if __name__ == "__main__":
    main()

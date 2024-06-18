import requests
from bs4 import BeautifulSoup
import csv

# Base URL for the initial link
base_url = "https://www.ulaval.ca"

# Read the links from the programmes_ulaval.txt file
with open('cours_ulaval.txt', 'r') as file:
    programme_links = [line.strip() for line in file.readlines()]

# Function to extract course details
def extract_course_details(url):
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract course name
        name = soup.find('h1', class_='fe--titre').get_text(strip=True)
        
        # Extract sections
        sections = []
        section_wrappers = soup.find_all('div', class_='toggle-section--content-wrapper')
        for section_wrapper in section_wrappers:
            section_data = {}
            section_data['Name'] = name
            
            # Safely extract each piece of data
            nrc_el = section_wrapper.find('span', class_='section-cours--nrc-el')
            section_data['Group Number'] = nrc_el.get_text(strip=True) if nrc_el else 'N/A'
            
            day_el = section_wrapper.find('li', class_='section-cours--etiquette', string=lambda x: x and 'Journée:' in x)
            section_data['Day'] = day_el.find_next_sibling().get_text(strip=True) if day_el else 'N/A'
            
            dates_el = section_wrapper.find('li', class_='section-cours--etiquette', string=lambda x: x and 'Dates:' in x)
            section_data['Dates'] = dates_el.find_next_sibling().get_text(strip=True) if dates_el else 'N/A'
            
            schedule_el = section_wrapper.find('li', class_='section-cours--etiquette', string=lambda x: x and 'Horaire:' in x)
            if schedule_el:
                times = schedule_el.find_next_sibling().get_text(strip=True).split(' à ')
                section_data['Start Time'] = times[0] if len(times) > 0 else 'N/A'
                section_data['End Time'] = times[1] if len(times) > 1 else 'N/A'
            else:
                section_data['Start Time'] = 'N/A'
                section_data['End Time'] = 'N/A'
            
            location_el = section_wrapper.find('li', class_='section-cours--etiquette', string=lambda x: x and 'Pavillon:' in x)
            section_data['Location'] = location_el.find_next_sibling().get_text(strip=True) if location_el else 'N/A'
            
            type_el = section_wrapper.find('li', class_='section-cours--etiquette', string=lambda x: x and 'Type:' in x)
            section_data['Type'] = type_el.find_next_sibling().get_text(strip=True) if type_el else 'N/A'
            
            teacher_el = section_wrapper.find('li', class_='section-cours--etiquette', string=lambda x: x and 'Enseignant:' in x)
            section_data['Teacher'] = teacher_el.find_next_sibling().get_text(strip=True) if teacher_el else 'N/A'
            
            sections.append(section_data)
        
        return sections
    else:
        print(f"Failed to retrieve page: {url}")
        return []

# File to save the course details
output_file = 'data_ulaval.csv'

# Open the CSV file for writing
with open(output_file, 'w', newline='') as csvfile:
    fieldnames = ['Name', 'Group Number', 'Day', 'Dates', 'Start Time', 'End Time', 'Location', 'Type', 'Teacher']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    # Loop through each programme link
    for idx, programme_link in enumerate(programme_links):
        # Construct the full URL for the current programme
        url = base_url + programme_link
        
        # Extract course details
        course_details = extract_course_details(url)
        
        # Write the details to the CSV file
        for course_detail in course_details:
            writer.writerow(course_detail)
        
        # Save progress every 10 iterations
        if (idx + 1) % 10 == 0:
            csvfile.flush()
            print(f"Progress saved after {idx + 1} iterations.")

print("Scraping completed and course details saved to ulaval_cours.csv")

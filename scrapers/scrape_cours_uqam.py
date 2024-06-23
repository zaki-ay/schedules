import requests
from bs4 import BeautifulSoup
import pandas as pd
import csv

# Function to read the class sigles from a CSV file
def read_class_sigles(file_path):
    with open(file_path, 'r') as file:
        sigles = [line.strip() for line in file.readlines()]
    return sigles

# Function to scrape class information for a given sigle
def scrape_class_info(sigle):
    url = f'https://etudier.uqam.ca/cours?sigle={sigle}'
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    data = []
    data.extend(extract_semester_info(soup, 'groupes_wrapper20241', sigle, 'Winter'))
    data.extend(extract_semester_info(soup, 'groupes_wrapper20242', sigle, 'Summer'))
    data.extend(extract_semester_info(soup, 'groupes_wrapper20243', sigle, 'Fall'))
    
    return data

# Function to extract semester information
def extract_semester_info(soup, div_id, sigle, semester):
    div = soup.find(id=div_id)
    if not div or "Ce cours n'est pas offert lors de ce trimestre." in div.text:
        return []

    classes = div.find_all('div', class_='groupe')
    extracted_data = []

    for i, class_div in enumerate(classes):
        name = f"{sigle}-{semester}-{'ABCDEFGHIJKLMNOPQRSTUVWXYZ'[i]}"

        # Extract group number
        no_groupe = class_div.find('h3', class_='no_groupe')
        if no_groupe:
            group_number = no_groupe.text.strip().split(' ')[1]
        else:
            no_groupe = class_div.find('h3', text=lambda t: 'Groupe' in t)
            group_number = no_groupe.text.strip().split(' ')[1]

        # Extract schedule details
        schedule_table = class_div.find('h3', text='Horaire et lieu').find_next('table')
        rows = schedule_table.find_all('tr')[1:]  # Skip the header row

        # Extract teacher's name
        teacher = class_div.find('h3', text='Enseignant').find_next('li').text.strip()

        for row in rows:
            day = row.find_all('td')[0].text.strip()
            dates = row.find_all('td')[1].text.strip().replace('\n', ' ')
            time_range = row.find_all('td')[2].text.strip().replace('\n', ' ')
            start_time, end_time = parse_time_range(time_range)
            location = row.find_all('td')[3].text.strip()
            class_type = row.find_all('td')[4].text.strip()

            extracted_data.append({
                'Name': name,
                'Group Number': group_number,
                'Day': day,
                'Dates': dates,
                'Start Time': start_time,
                'End Time': end_time,
                'Location': location,
                'Type': class_type,
                'Teacher': teacher
            })

    return extracted_data

# Function to parse the time range
def parse_time_range(time_range):
    time_range = time_range.replace('\xa0', ' ')
    time_parts = time_range.split(' à ')
    if len(time_parts) == 2:
        start_time = time_parts[0].replace('De ', '').strip()
        end_time = time_parts[1].strip()
        return start_time, end_time
    return '', ''  # Return empty strings if the format is unexpected

# Main function to read sigles, scrape data, and save to CSV
def main():
    input_file = 'cours.txt'
    output_file = 'data_uqam.csv'
    save_every_n = 3  # Number of iterations after which data is saved to CSV
    
    sigles = read_class_sigles(input_file)
    all_data = []

    for index, sigle in enumerate(sigles):
        class_info = scrape_class_info(sigle)
        all_data.extend(class_info)
        print(sigle)

        # Save to file every N iterations
        if (index + 1) % save_every_n == 0:
            df = pd.DataFrame(all_data)
            df.to_csv(output_file, index=False, mode='a', header=not index)  # Append mode, write header only for the first batch

    # Save any remaining data not yet written to file
    if all_data:
        df = pd.DataFrame(all_data)
        df.to_csv(output_file, index=False, mode='a', header=False)  # Append mode, no header

if __name__ == "__main__":
    main()

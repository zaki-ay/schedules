import requests
from bs4 import BeautifulSoup

# Base URL for the initial link
base_url = "https://www.ulaval.ca"

# Read the links from the programmes_ulaval.txt file
with open('programmes_ulaval.txt', 'r') as file:
    programme_links = [line.strip() for line in file.readlines()]

# List to store the course links
course_links = []

# Define the number of iterations after which the file should be saved
save_interval = 5  # You can adjust this value as needed

# Function to save links to a file
def save_to_file(filename, links):
    with open(filename, 'w') as file:
        for link in links:
            file.write(f"{link}\n")

# Loop through each programme link
for idx, programme_link in enumerate(programme_links):
    # Construct the full URL for the current programme
    url = base_url + programme_link
    
    # Send a GET request to the programme page
    response = requests.get(url)
    
    # Check if the request was successful
    if response.status_code == 200:
        # Parse the page content
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all <a> tags with class name "carte-accessible--lien"
        a_tags = soup.find_all('a', class_='carte-accessible--lien')

        # Extract the href attribute from each <a> tag and add it to the list
        for a_tag in a_tags:
            course_links.append(a_tag.get('href'))
            #print(a_tag.get('href'))
    else:
        print(f"Failed to retrieve page: {url}")
    
    # Save to file every N iterations
    if (idx + 1) % save_interval == 0:
        save_to_file('cours_ulaval.txt', course_links)
        print(f"Progress saved after {idx + 1} iterations.")

# Save any remaining links after the loop completes
save_to_file('cours_ulaval.txt', course_links)
print("Scraping completed and course links saved to cours_ulaval.txt")

import requests
from bs4 import BeautifulSoup

# Base URL with page number placeholder
base_url = "https://www.ulaval.ca/etudes/programmes?page={}"

# List to store href links
href_links = []

# Loop through all 75 pages
for page_number in range(76):
    # Construct the full URL for the current page
    url = base_url.format(page_number)
    
    # Send a GET request to the page
    response = requests.get(url)
    
    # Check if the request was successful
    if response.status_code == 200:
        # Parse the page content
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all <a> tags with class name "programme-etudes"
        a_tags = soup.find_all('a', class_='programme-etudes')
        
        # Extract the href attribute from each <a> tag and add it to the list
        for a_tag in a_tags:
            href_links.append(a_tag.get('href'))
            print(a_tag.get('href'))
    else:
        print(f"Failed to retrieve page {page_number}")

# Save the href links to a text file
with open('programmes_ulaval.txt', 'w') as file:
    for link in href_links:
        file.write(f"{link}\n")

print("Scraping completed and links saved to programmes_ulaval.txt")

import requests
from bs4 import BeautifulSoup

def scrape_data_sigle(url):
    try:
        # Sending HTTP request to the URL
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Parsing the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')

        # Finding the element with ID 'bloc-cours'        
        if soup:
            # Extracting all elements with data-sigle attribute within 'bloc-cours'
            courses = soup.find_all(attrs={"data-sigle": True})
            print(courses)
            return [course['data-sigle'] for course in courses]
        else:
            print(f"No 'bloc-cours' found in {url}")
            return []

    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return []

def read_urls_and_scrape(file_path, output_file_path, n):
    with open(file_path, 'r') as file:
        urls = file.readlines()

    all_data = {}
    for index, url in enumerate(urls):
        url = url.strip()
        if url:  # ensuring the URL is not empty
            data_sigles = scrape_data_sigle(url)
            all_data[url] = data_sigles
            # Write to file every N iterations
            if (index + 1) % n == 0:
                write_to_file(output_file_path, all_data)
                all_data = {}  # Resetting dictionary after writing

    # Writing any remaining data if the total count is not perfectly divisible by N
    if all_data:
        write_to_file(output_file_path, all_data)

def write_to_file(output_file_path, data):
    with open(output_file_path, 'a') as file:  # 'a' mode for appending to the file
        for url, sigles in data.items():
            file.write(f"{url}: {sigles}\n")

file_path = './static/data/liste_programmes.txt'  # Update with the path to your file
output_file_path = './static/data/raw_liste_cours.txt'  # Path to output file
N = 10  # Number of iterations after which to write to the file
read_urls_and_scrape(file_path, output_file_path, N)

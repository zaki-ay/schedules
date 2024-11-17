import json

def text_to_json(input_file, output_file):
    # Read the text file
    with open(input_file, 'r') as file:
        lines = file.readlines()
    
    # Process the content: strip newlines and extra spaces
    data = [line.strip() for line in lines]
    
    # Write the list to a JSON file
    with open(output_file, 'w') as json_file:
        json.dump(data, json_file, indent=4)

# Specify the input and output file paths
input_file = 'liste_cours.txt'
output_file = 'cours_uqam.json'

# Convert text to JSON
text_to_json(input_file, output_file)

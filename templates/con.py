import json

# Define the input and output file paths
input_file = 'cours_uqam.txt'
output_file = 'cours_uqam.json'

# Read the class names from the text file
with open(input_file, 'r') as file:
    class_names = file.read().splitlines()

# Remove duplicates by converting to a set and back to a list
unique_class_names = list(set(class_names))

# Write the unique class names to a JSON file
with open(output_file, 'w') as file:
    json.dump(unique_class_names, file, indent=4)

print(f'Class names have been successfully converted to {output_file}')

import pandas as pd
import sqlite3

# File paths
csv_file_path = '../static/data_unique.csv'
db_file_path = '../static/database_unique.db'

# Define table schema (if needed, use sqlite3 for creating tables explicitly)
columns = ['Name', 'Group_Number', 'Day', 'Dates', 'Start_Time', 'End_Time', 'Location', 'Type', 'Teacher']

# Open SQLite connection
connection = sqlite3.connect(db_file_path)

# Process CSV in chunks
chunksize = 1000
for chunk in pd.read_csv(
    csv_file_path,
    sep=',',  # Adjust delimiter if needed
    header=None,  # CSV has no header
    names=columns,
    chunksize=chunksize,
):
    chunk.to_sql('tasks_table', connection, if_exists='append', index=False)

# Close connection
connection.close()
print("CSV successfully converted to SQLite database!")

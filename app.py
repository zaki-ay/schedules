from flask import Flask, request, jsonify, render_template
import sqlite3
import getpass
from functools import lru_cache

app = Flask(__name__)

BASE_USER = getpass.getuser()

# Database helper functions
def get_db_connection():
    conn = sqlite3.connect(f'./static/database.db')
    conn.row_factory = sqlite3.Row
    return conn

def close_db_connection(conn):
    if conn:
        conn.close()

class Task:
    def __init__(self, name, day_times):
        self.name = name
        self.day_times = day_times  # day_times is a list of (day, start_time, end_time) tuples

    def overlaps_with(self, other_task):
        for day1, start1, end1 in self.day_times:
            for day2, start2, end2 in other_task.day_times:
                if day1 == day2 and not (end1 <= start2 or start1 >= end2):
                    return True
        return False

    def __repr__(self):
        return f"Task({self.name}, {self.day_times})"

def _convert_to_minutes(time_str):
    if not time_str:
        return -1
    try:
        hours, minutes = map(int, time_str.split('h'))
        return hours * 60 + minutes
    except ValueError:
        print(f"Warning: Invalid time format '{time_str}'. Expected format like '10h30'.")
        return -1

@lru_cache(maxsize=None)
def read_tasks_from_db(season):
    tasks = {}
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Use a LIKE clause to filter tasks by season (case-insensitive)
    query = """
        SELECT Name, Day, Start_Time, End_Time
        FROM tasks_table
        WHERE LOWER(Name) LIKE ?
    """
    # Format the season with wildcards
    cursor.execute(query, (f"%{season.lower()}%",))
    
    rows = cursor.fetchall()
    for row in rows:
        key = row['Name']
        day_time = (row['Day'], _convert_to_minutes(row['Start_Time']), _convert_to_minutes(row['End_Time']))
        if key in tasks:
            tasks[key].append(day_time)
        else:
            tasks[key] = [day_time]

    close_db_connection(conn)
    return [Task(name, day_times) for name, day_times in tasks.items()]

def find_possible_schedules(tasks):
    tasks = sorted(tasks, key=lambda x: x.day_times[0][1])  # Sort tasks by start time of the first timeslot
    results = set()  # Use a set to store unique schedules
    schedule = []
    included_sigles = set()  # Set to track included sigles in the current schedule

    def backtrack(index):
        if all(not schedule[i].overlaps_with(schedule[j]) for i in range(len(schedule)) for j in range(i + 1, len(schedule))):
            results.add(tuple(sorted(task.name for task in schedule)))

        for i in range(index, len(tasks)):
            sigle = tasks[i].name.split('-')[0]  # Extract the sigle part of the task name
            if all(not task.overlaps_with(tasks[i]) for task in schedule) and sigle not in included_sigles:
                schedule.append(tasks[i])
                included_sigles.add(sigle)
                backtrack(i + 1)
                schedule.pop()
                included_sigles.remove(sigle)

    backtrack(0)
    return [list(sch) for sch in results]  # Convert set of tuples to list of lists

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/schedule', methods=['GET', 'POST'])
def create_schedule():
    if request.method == 'POST':
        sigles = request.form['sigles'].split(',')
        season = request.form['season']
        min_length = len(sigles)

        tasks = read_tasks_from_db(season)
        tasks = [task for task in tasks if any(sigle.upper() in task.name for sigle in sigles)]        
        possible_schedules = find_possible_schedules(tasks)

        ret_schedules = []
        for schedule in possible_schedules:
            if len(schedule) >= min_length:
                ret_schedules.append(schedule)

        return jsonify({'schedules': ret_schedules})
    else:
        return index()

@app.route('/class_details', methods=['GET'])
def get_class_details():
    class_name = request.args.get('class_name')
    if not class_name:
        return jsonify({'error': 'Class name is required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Query the database for the specific class name
    query = """
        SELECT Name, Day, Group_Number, Dates, Start_Time, End_Time, Location, Type, Teacher
        FROM tasks_table
        WHERE Name = ?
    """
    cursor.execute(query, (class_name,))
    rows = cursor.fetchall()

    close_db_connection(conn)

    # Check if the class was found
    if not rows:
        return jsonify({'error': 'Class not found'}), 404

    # Format the class details
    class_details = []
    for row in rows:
        class_details.append({
            'name': row['Name'],
            'day': row['Day'],
            'group': row['Group_Number'],
            'dates': row['Dates'],
            'start_time': row['Start_Time'],
            'end_time': row['End_Time'],
            'location': row['Location'],
            'type': row['Type'],
            'teacher': row['Teacher']
        })

    return jsonify({'class_details': class_details})

if __name__ == '__main__':
    app.run()

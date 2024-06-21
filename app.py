from flask import Flask, request, jsonify, render_template
import csv

app = Flask(__name__)

class Task:
    def __init__(self, name, day_times):
        self.name = name
        self.day_times = day_times  # day_times is a list of (day, start_time, end_time) tuples

    def overlaps_with(self, other_task):
        # Check for overlap in timeslots
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

def read_tasks_from_file(season):
    #file_path = f'{season}.csv'
    file_path = '/home/zicozico/sched/data_uqam.csv'
    tasks = {}
    with open(file_path, 'r') as file:
        reader = csv.DictReader(file)
        for line in reader:
            key = line['Name']
            class_split = key.split('-')
            if len(class_split) == 3:
                if class_split[1].lower() == season:
                    day_time = (line['Day'], _convert_to_minutes(line['Start Time']), _convert_to_minutes(line['End Time']))
                    if key in tasks:
                        tasks[key].append(day_time)
                    else:
                        tasks[key] = [day_time]
    # Convert to Task instances
    return [Task(name, day_times) for name, day_times in tasks.items()]

def find_possible_schedules(tasks):
    tasks = sorted(tasks, key=lambda x: x.day_times[0][1])  # Sort tasks by start time of the first timeslot
    results = set()  # Use a set to store unique schedules
    schedule = []
    included_sigles = set()  # Set to track included sigles in the current schedule

    def backtrack(index):
        # Check the current schedule for overlaps and unique sigles
        if all(not schedule[i].overlaps_with(schedule[j]) for i in range(len(schedule)) for j in range(i + 1, len(schedule))):
            results.add(tuple(sorted(task.name for task in schedule)))

        for i in range(index, len(tasks)):
            sigle = tasks[i].name.split('-')[0]  # Extract the sigle part of the task name
            if all(not task.overlaps_with(tasks[i]) for task in schedule) and sigle not in included_sigles:
                schedule.append(tasks[i])
                included_sigles.add(sigle)  # Add this sigle to the set of included sigles
                backtrack(i + 1)
                schedule.pop()
                included_sigles.remove(sigle)  # Remove the sigle when backtracking

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
        min_length = len(sigles) #int(request.form['min_length']) #len(sigles)
        #file_path = f'{season}.csv'
        #file_path = '/home/zicozico/sched/data_uqam.csv'

        tasks = read_tasks_from_file(season)
        tasks = [task for task in tasks if any(sigle in task.name for sigle in sigles)]
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

    #season = class_name.split('-')[1].lower()
    #file_path = f'{season}.csv'
    file_path = '/home/zicozico/sched/data_uqam.csv'

    class_details = []

    with open(file_path, 'r') as file:
        reader = csv.DictReader(file)
        for line in reader:
            if line['Name'] == class_name:
                details = {
                    'name': line['Name'],
                    'day': line['Day'],
                    'group': line['Group Number'],
                    'dates': line['Dates'],
                    'start_time': line['Start Time'],
                    'end_time': line['End Time'],
                    'location': line['Location'],
                    'type': line['Type'],
                    'teacher': line['Teacher']
                }
                class_details.append(details)

    if not class_details:
        return jsonify({'error': 'Class not found'}), 404

    return jsonify({'class_details': class_details})

if __name__ == '__main__':
    app.run()

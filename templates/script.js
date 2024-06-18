document.getElementById('scheduleForm').addEventListener('submit', function(event) {
    event.preventDefault();
    const formData = new FormData(event.target);
    fetch('/schedule', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        window.schedules = data.schedules;
        window.currentScheduleIndex = 0;
        if (window.schedules.length > 0) {
            fetchAndDisplaySchedule(0);
        } else {
            alert('No schedules found.');
        }
    });
});

document.getElementById('prevSchedule').addEventListener('click', function() {
    if (window.currentScheduleIndex > 0) {
        window.currentScheduleIndex--;
        fetchAndDisplaySchedule(window.currentScheduleIndex);
    }
});

document.getElementById('nextSchedule').addEventListener('click', function() {
    if (window.currentScheduleIndex < window.schedules.length - 1) {
        window.currentScheduleIndex++;
        fetchAndDisplaySchedule(window.currentScheduleIndex);
    }
});

function fetchAndDisplaySchedule(index) {
    const schedule = window.schedules[index];
    Promise.all(schedule.map(className => fetch(`/class_details?class_name=${className}`).then(res => res.json())))
    .then(classDetailsArray => {
        displaySchedule(classDetailsArray.map(res => res.class_details).flat());
    });
}

function displaySchedule(classes) {
    const calendarTableBody = document.querySelector('#calendarTable tbody');
    calendarTableBody.innerHTML = '';

    // Create time slots from 8:00 to 22:00
    const startHour = 8;
    const endHour = 22;
    for (let hour = startHour; hour < endHour; hour++) {
        const row = document.createElement('tr');
        for (let day = 0; day < 8; day++) {
            const cell = document.createElement('td');
            if (day === 0) {
                cell.textContent = `${hour}:00 - ${hour + 1}:00`;
            }
            row.appendChild(cell);
        }
        calendarTableBody.appendChild(row);
    }

    // Fill in class details
    classes.forEach(classDetail => {
        const dayIndex = {
            'Lundi': 1,
            'Mardi': 2,
            'Mercredi': 3,
            'Jeudi': 4,
            'Vendredi': 5,
            'Samedi': 6,
            'Dimanche': 7
        }[classDetail.day];

        const startHour = parseInt(classDetail.start_time.split('h')[0]);
        const endHour = parseInt(classDetail.end_time.split('h')[0]);
        for (let hour = startHour; hour < endHour; hour++) {
            const cell = calendarTableBody.children[hour - 8].children[dayIndex];
            cell.textContent = `${classDetail.name} (${classDetail.teacher})`;
        }
    });
}

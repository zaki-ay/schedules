 document.addEventListener('DOMContentLoaded', function() {
    const calendarTableBody = document.querySelector('#calendarTable tbody');
    const blurMask = document.getElementById('blurMask');
    const rows = 28; // 28 half-hour increments from 8:00 AM to 10:00 PM
    const columns = 6;

    let currentHour = 8; // Start at 8:00 AM
    for (let i = 0; i < rows; i++) {
        const row = document.createElement('tr');
        for (let j = 0; j < columns; j++) {
            const cell = document.createElement('td');
            if (j === 0) { // First column: Time column
                let time = `${currentHour}:${i % 2 === 0 ? '00' : '30'}`;
                cell.textContent = time;
                if (i % 2 === 1) { // Increment the hour every two iterations (every full hour)
                    currentHour++;
                }
            }
            row.appendChild(cell);
        }
        calendarTableBody.appendChild(row);
    }

    document.getElementById('scheduleForm').addEventListener('submit', function(event) {
        event.preventDefault();
        blurMask.classList.add('active');
        const formData = new FormData(event.target);
        const sigles = formData.get('sigles').split(',').map(s => s.trim()).filter(s => s);
        displayClassList(sigles);

        fetch('/schedule', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data && data.schedules) {
                window.schedules = data.schedules;
                window.currentScheduleIndex = 0;
                updateScheduleDisplay();
                fetchAndDisplaySchedule(window.currentScheduleIndex).finally(() => {
                    blurMask.classList.remove('active');
                });
            } else {
                blurMask.classList.remove('active');
                console.error('No schedules returned:', data);
            }
        })
        .catch(error => {
            blurMask.classList.remove('active');
            console.error('Error fetching schedules:', error);
        });

        // Clear the input form after submission
        //event.target.reset();
    });

    document.getElementById('prevSchedule').addEventListener('click', function() {
        blurMask.classList.add('active');
        if (window.currentScheduleIndex > 0) {
            window.currentScheduleIndex--;
            updateScheduleDisplay();
            fetchAndDisplaySchedule(window.currentScheduleIndex).finally(() => {
                blurMask.classList.remove('active');
            });
        } else {
            blurMask.classList.remove('active');
        }
    });

    document.getElementById('nextSchedule').addEventListener('click', function() {
        blurMask.classList.add('active');
        if (window.currentScheduleIndex < window.schedules.length - 1) {
            window.currentScheduleIndex++;
            updateScheduleDisplay();
            fetchAndDisplaySchedule(window.currentScheduleIndex).finally(() => {
                blurMask.classList.remove('active');
            });
        } else {
            blurMask.classList.remove('active');
        }
    });

    function displayClassList(classes) {
        const classList = document.getElementById('classList');
        classList.innerHTML = ''; // Clear previous list
        const siglesInput = document.getElementById('sigles'); // Get the input field

        classes.forEach((className, index) => {
            const listItem = document.createElement('li');
            listItem.textContent = className;
            const removeButton = document.createElement('button');
            removeButton.textContent = 'X';
            removeButton.className = 'remove-btn';
            removeButton.onclick = function() {
                blurMask.classList.add('active'); // Show the blur mask
                classes.splice(index, 1); // Remove class from array
                displayClassList(classes); // Update display
                siglesInput.value = classes.join(','); // Update the input field with remaining classes

                // Create a FormData object and submit the updated list
                const formData = new FormData(document.getElementById('scheduleForm'));
                formData.set('sigles', classes.join(',')); // Update the formData sigles field
                fetch('/schedule', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    if (data && data.schedules) {
                        window.schedules = data.schedules;
                        window.currentScheduleIndex = 0;
                        updateScheduleDisplay();
                        fetchAndDisplaySchedule(window.currentScheduleIndex).finally(() => {
                            blurMask.classList.remove('active');
                        });
                    } else {
                        blurMask.classList.remove('active');
                        console.error('No schedules returned:', data);
                    }
                })
                .catch(error => {
                    blurMask.classList.remove('active');
                    console.error('Error fetching schedules:', error);
                });
            };
            listItem.appendChild(removeButton);
            classList.appendChild(listItem);
        });
    }

    function updateScheduleDisplay() {
        document.getElementById('scheduleIndex').textContent = `${window.currentScheduleIndex + 1}/${window.schedules.length}`;
    }

    function fetchAndDisplaySchedule(index) {
        const schedule = window.schedules[index];
        return Promise.all(schedule.map(className => fetch(`/class_details?class_name=${className}`)
            .then(res => res.json())
            .then(res => res.class_details)))
        .then(classDetailsArray => {
            displaySchedule(classDetailsArray.flat());
        })
        .catch(error => {
            console.error('Error fetching class details:', error);
        });
    }

    function displaySchedule(classes) {
        const calendarTableBody = document.querySelector('#calendarTable tbody');
        calendarTableBody.innerHTML = '';

        // Create time slots from 8:00 to 22:00, in half-hour increments
        const startHour = 8;
        const endHour = 22;
        let rowCounter = 0; // To track rows for half-hour increments
        for (let hour = startHour; hour < endHour; hour++) {
            for (let half = 0; half < 2; half++) { // Two iterations per hour: 0 for the hour, 1 for the half hour
                const row = document.createElement('tr');
                for (let day = 0; day < 6; day++) {
                    const cell = document.createElement('td');
                    if (day === 0) { // First column for the time label
                        const minutes = half === 0 ? "00" : "30";
                        cell.textContent = `${hour}:${minutes}`;
                    }
                    row.appendChild(cell);
                }
                calendarTableBody.appendChild(row);
            }
            rowCounter++;
        }

        // Fill in class details and add tooltips
        classes.forEach(classDetail => {
            const dayIndex = {
                'Lundi': 1,
                'Mardi': 2,
                'Mercredi': 3,
                'Jeudi': 4,
                'Vendredi': 5
            }[classDetail.day];

            const className = classDetail.name.split('-')[0];
            const startTime = parseInt(classDetail.start_time.split('h')[0]);
            const endTime = parseInt(classDetail.end_time.split('h')[0]);
            const startMinute = parseInt(classDetail.start_time.split('h')[1] || "00");
            const endMinute = parseInt(classDetail.end_time.split('h')[1] || "00");

            // Determine the start and end rows based on time
            let startRow = (startTime - startHour) * 2;
            if (startMinute >= 30) startRow++;
            let endRow = (endTime - startHour) * 2;
            if (endMinute > 0) endRow++;

            const classColor = getClassColor(className, classDetail.type);

            for (let row = startRow; row < endRow; row++) {
                if (calendarTableBody.children[row]) {
                    const cell = calendarTableBody.children[row].children[dayIndex];
                    cell.textContent = `${className} - Groupe ${classDetail.group}`;
                    cell.title = `Cours: ${className}\nEnseignant: ${classDetail.teacher}\nJour: ${classDetail.day}\nHeure: ${classDetail.start_time} - ${classDetail.end_time}\nGroupe: ${classDetail.group}\nLocal: ${classDetail.location}\nType: ${classDetail.type}\nDates: ${classDetail.dates}`;
                    cell.classList.add('class-info');
                    cell.style.backgroundColor = classColor;
                }
            }
        });
    }

    function getClassColor(className, classType) {
        // Check if the color for this class has already been generated
        if (!window.classColors) {
            window.classColors = {};
        }
        if (!window.classColors[className]) {
            // Generate a random color
            let color = '#' + (Math.floor(Math.random() * 127 + 128).toString(16).padStart(2, '0')) +
                (Math.floor(Math.random() * 127 + 128).toString(16).padStart(2, '0')) +
                (Math.floor(Math.random() * 127 + 128).toString(16).padStart(2, '0'));
            window.classColors[className] = color;
        }

        // Convert the hex color to RGB
        let rgb = hexToRgb(window.classColors[className]);

        // Adjust the color based on class type
        if (classType === 'Cours magistral') {
            rgb = adjustColorBrightness(rgb, 0); // Slightly darker for Cours magistral
        } else if (classType === 'Atelier') {
            rgb = adjustColorBrightness(rgb, 10); // Slightly lighter for Labo
        }

        return rgbToHex(rgb);
    }

    // Helper function to convert hex color to RGB
    function hexToRgb(hex) {
        let bigint = parseInt(hex.slice(1), 16);
        let r = (bigint >> 16) & 255;
        let g = (bigint >> 8) & 255;
        let b = bigint & 255;
        return { r, g, b };
    }

    // Helper function to convert RGB color to hex
    function rgbToHex(rgb) {
        return `#${((1 << 24) + (rgb.r << 16) + (rgb.g << 8) + rgb.b).toString(16).slice(1)}`;
    }

    // Helper function to adjust color brightness
    function adjustColorBrightness(rgb, percent) {
        let r = Math.round(rgb.r * (1 + percent / 100));
        let g = Math.round(rgb.g * (1 + percent / 100));
        let b = Math.round(rgb.b * (1 + percent / 100));

        // Ensure the values are within the valid range [0, 255]
        r = Math.min(255, Math.max(0, r));
        g = Math.min(255, Math.max(0, g));
        b = Math.min(255, Math.max(0, b));

        return { r, g, b };
    }
  });
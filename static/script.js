let classNames = [];
$(document).ready(function() {
    $.getJSON('/static/data/cours_uqam.json', function(data) {
        classNames = data;
    });
    const maxSuggestions = 10;
    $('#sigles').autocomplete({
        source: function(request, response) {
            // Split the request term by commas and trim the spaces
            const terms = request.term.split(',').map(term => term.trim());
            // Get the last term to autocomplete
            const lastTerm = terms[terms.length - 1].toUpperCase();
            const matches = $.grep(classNames, function(className) {
                return className.startsWith(lastTerm);
            }).slice(0, maxSuggestions); // Limit the number of suggestions to maxSuggestions
            response(matches);
        },
        minLength: function() {
            const value = $('#sigles').val();
            // Calculate minLength based on field content length minus the number of commas
            const commaCount = (value.match(/,/g) || []).length;
            return 2 + value.length - commaCount;
        },
        focus: function() {
            // Prevent value inserted on focus
            return false;
        },
        select: function(event, ui) {
            const terms = this.value.split(',').map(term => term.trim());
            // Remove the current input
            terms.pop();
            // Add the selected item
            terms.push(ui.item.value);
            // Update the input with the new terms without adding a comma or space
            this.value = terms.join(',');
            return false;
        }
    });
    // Trigger the autocomplete when typing
    $('#sigles').on('input', function() {
        $(this).autocomplete("search");
    });
});

document.addEventListener('DOMContentLoaded', function() {
    clearCalendar();

    document.getElementById('scheduleForm').addEventListener('submit', async function(event) {
        event.preventDefault();
        const formData = new FormData(event.target);
        const sigles = formData.get('sigles').split(',').map(s => s.trim()).filter(s => s);
        if (sigles.length === 0) return;
        blurMask.classList.add('active');
        displayClassList(sigles);
        try {
            const response = await fetch('/schedule', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            if (data && data.schedules) {
                window.schedules = data.schedules;
                window.currentScheduleIndex = 0;
                updateScheduleDisplay();
                await fetchAndDisplaySchedule(window.currentScheduleIndex);
            } else {
                //console.error('No schedules returned:', data);
            }
        } catch (error) {
            //console.error('Error fetching schedules:', error);
            alert("Aucun horaire n'a été trouvé!")
            clearCalendar();
            
        } finally {
            blurMask.classList.remove('active');
        }
    });
    document.getElementById('prevSchedule').addEventListener('click', async function() {
        blurMask.classList.add('active');
        if (window.currentScheduleIndex > 0) {
            window.currentScheduleIndex--;
            updateScheduleDisplay();
            try {
                await fetchAndDisplaySchedule(window.currentScheduleIndex);
            } finally {
                blurMask.classList.remove('active');
            }
        } else {
            blurMask.classList.remove('active');
        }
    });
    document.getElementById('nextSchedule').addEventListener('click', async function() {
        blurMask.classList.add('active');
        if (window.currentScheduleIndex < window.schedules.length - 1) {
            window.currentScheduleIndex++;
            updateScheduleDisplay();
            try {
                await fetchAndDisplaySchedule(window.currentScheduleIndex);
            } finally {
                blurMask.classList.remove('active');
            }
        } else {
            blurMask.classList.remove('active');
        }
    });

    function clearCalendar() {
        const calendarTableBody = document.querySelector('#calendarTable tbody');
        calendarTableBody.innerHTML = '';
        const startHour = 9; // Start at 9:00 AM
        const endHour = 22; // End at 10:00 PM
        const rows = (endHour - startHour) * 2; // Two rows per hour
        const columns = 6; // 6 columns (Time + Weekdays)
        let currentHour = startHour;
        for (let i = 0; i < rows; i++) {
            const row = document.createElement('tr');
            for (let j = 0; j < columns; j++) {
                const cell = document.createElement('td');
                if (j === 0) { // First column: Time column
                    const time = `${currentHour.toString().padStart(2, '0')}:${i % 2 === 0 ? '00' : '30'}`;
                    cell.textContent = time;
                    if (i % 2 === 1) { // Increment the hour every two iterations (every full hour)
                        currentHour++;
                    }
                }
                row.appendChild(cell);
            }
            calendarTableBody.appendChild(row);
        }
        window.schedules = [];
        window.currentScheduleIndex = 0;
        document.getElementById("scheduleIndex").innerHTML = "1/1";
    }

    function displayClassList(classes) {
        const classList = document.getElementById('classList');
        classList.innerHTML = '';
        const siglesInput = document.getElementById('sigles');
        classes.forEach((className, index) => {
            const listItem = document.createElement('li');
            listItem.textContent = className.toUpperCase();
            const removeButton = document.createElement('button');
            removeButton.textContent = 'X';
            removeButton.className = 'remove-btn';
            removeButton.onclick = function() {
                blurMask.classList.add('active');
                classes.splice(index, 1);
                displayClassList(classes);
                siglesInput.value = classes.join(',');
                const formData = new FormData(document.getElementById('scheduleForm'));
                formData.set('sigles', classes.join(','));
                if (classes.length == 0) {
                    clearCalendar();
                    
                    blurMask.classList.remove('active');
                    return;
                }
                fetch('/schedule', {
                    method: 'POST',
                    body: formData
                }).then(response => response.json()).then(data => {
                    if (data && data.schedules) {
                        window.schedules = data.schedules;
                        window.currentScheduleIndex = 0;
                        updateScheduleDisplay();
                        fetchAndDisplaySchedule(window.currentScheduleIndex).finally(() => {
                            blurMask.classList.remove('active');
                        });
                    } else {
                        blurMask.classList.remove('active');
                        //console.error('No schedules returned:', data);
                    }
                }).catch(error => {
                    blurMask.classList.remove('active');
                    alert("Aucun horaire n'a été trouvé!")
                    clearCalendar();
                    
                    //console.error('Error fetching schedules:', error);
                });
            };
            listItem.appendChild(removeButton);
            classList.appendChild(listItem);
        });
    }

    function updateScheduleDisplay() {
        document.getElementById('scheduleIndex').textContent = `${window.currentScheduleIndex + 1}/${window.schedules.length}`;
    }
    async function fetchAndDisplaySchedule(index) {
        const schedule = window.schedules[index];
        try {
            const classDetailsArray = await Promise.all(schedule.map(async className => {
                const res = await fetch(`/class_details?class_name=${className}`);
                const data = await res.json();
                return data.class_details;
            }));
            displaySchedule(classDetailsArray.flat());
        } catch (error) {
            alert("Aucun horaire n'a été trouvé!")
            clearCalendar();
            
            //console.error('Error fetching class details:', error);
        }
    }

    function displaySchedule(classes) {
        const calendarTableBody = document.querySelector('#calendarTable tbody');
        const fragment = document.createDocumentFragment();
        const startHour = 9;
        const endHour = 22;
        const rows = (endHour - startHour) * 2; // Two rows per hour
        const columns = 6; // Time + 5 weekdays
        for (let i = 0; i < rows; i++) {
            const row = document.createElement('tr');
            for (let j = 0; j < columns; j++) {
                const cell = document.createElement('td');
                if (j === 0) { // Time column
                    const hour = Math.floor(i / 2) + startHour;
                    const minute = i % 2 === 0 ? '00' : '30';
                    cell.textContent = `${hour.toString().padStart(2, '0')}:${minute}`;
                }
                row.appendChild(cell);
            }
            fragment.appendChild(row);
        }
        calendarTableBody.innerHTML = '';
        calendarTableBody.appendChild(fragment);
        classes.forEach(classDetail => {
            const dayIndex = {
                'Lundi': 1,
                'Mardi': 2,
                'Mercredi': 3,
                'Jeudi': 4,
                'Vendredi': 5
            } [classDetail.day];
            const className = classDetail.name.split('-')[0];
            const startTime = parseInt(classDetail.start_time.split('h')[0]);
            const endTime = parseInt(classDetail.end_time.split('h')[0]);
            const startMinute = parseInt(classDetail.start_time.split('h')[1] || "00");
            const endMinute = parseInt(classDetail.end_time.split('h')[1] || "00");
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
        if (!window.classColors) {
            window.classColors = {};
        }
        if (!window.classColors[className]) {
            let color = '#' + (Math.floor(Math.random() * 127 + 128).toString(16).padStart(2, '0')) + (Math.floor(Math.random() * 127 + 128).toString(16).padStart(2, '0')) + (Math.floor(Math.random() * 127 + 128).toString(16).padStart(2, '0'));
            window.classColors[className] = color;
        }
        let rgb = hexToRgb(window.classColors[className]);
        if (classType === 'Cours magistral') {
            rgb = adjustColorBrightness(rgb, 0);
        } else if (classType === 'Atelier') {
            rgb = adjustColorBrightness(rgb, 10);
        }
        return rgbToHex(rgb);
    }

    function hexToRgb(hex) {
        let bigint = parseInt(hex.slice(1), 16);
        let r = (bigint >> 16) & 255;
        let g = (bigint >> 8) & 255;
        let b = bigint & 255;
        return {
            r,
            g,
            b
        };
    }

    function rgbToHex(rgb) {
        return `#${((1 << 24) + (rgb.r << 16) + (rgb.g << 8) + rgb.b).toString(16).slice(1)}`;
    }

    function adjustColorBrightness(rgb, percent) {
        let r = Math.round(rgb.r * (1 + percent / 100));
        let g = Math.round(rgb.g * (1 + percent / 100));
        let b = Math.round(rgb.b * (1 + percent / 100));
        r = Math.min(255, Math.max(0, r));
        g = Math.min(255, Math.max(0, g));
        b = Math.min(255, Math.max(0, b));
        return {
            r,
            g,
            b
        };
    }
});
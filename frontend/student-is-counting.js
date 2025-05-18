document.addEventListener('DOMContentLoaded', function() {
    const studentIsCountingTableBody = document.getElementById('student-is-counting-table-body');
    const pageTitleElement = document.querySelector('h1'); // Assuming the main h1 is for the student's name/note
    const subTitleElement = document.querySelector('h2'); // The h2 "Name is Counting"

    let fetchedClassDetails = []; // Store fetched details for dynamic updates
    let currentStudentNoteForDisplay = ''; // Store the note of the current student
    if (!studentIsCountingTableBody || !pageTitleElement || !subTitleElement) {
        console.error('Required HTML elements (table body or title) not found!');
        if (studentIsCountingTableBody) {
            studentIsCountingTableBody.innerHTML = `<tr><td colspan="3" style="color: red; text-align: center;">Page structure error.</td></tr>`;
        }
        return;
    }

    const urlParams = new URLSearchParams(window.location.search);
    const studentCode = urlParams.get('code'); // Changed from note to code
    const day = urlParams.get('day');

    if (!studentCode) {
        pageTitleElement.textContent = 'Error';
        subTitleElement.textContent = 'Student Code Missing';
        studentIsCountingTableBody.innerHTML = `<tr><td colspan="3" style="color: red; text-align: center;">No student code provided in the URL.</td></tr>`;
        return;
    }
    if (!day || !['1', '2', '3'].includes(day)) {
        pageTitleElement.textContent = `Student Code: ${studentCode}`;
        subTitleElement.textContent = 'Error: Day Parameter Invalid';
        studentIsCountingTableBody.innerHTML = `<tr><td colspan="3" style="color: red; text-align: center;">Day parameter is missing or invalid (must be 1, 2, or 3).</td></tr>`;
        return;
    }

    const dayNames = { '1': 'Monday', '2': 'Tuesday', '3': 'Wednesday' };
    pageTitleElement.textContent = `Student Code: ${studentCode}`; // Initial title

    fetch(`/api/student/counting-details?code=${encodeURIComponent(studentCode)}&day=${encodeURIComponent(day)}`)
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { throw new Error(err.error || `HTTP error! status: ${response.status}`) });
            }
            return response.json();
        })
        .then(apiResponse => {
            currentStudentNoteForDisplay = apiResponse.student_note || studentCode; // Use note if available, else code
            fetchedClassDetails = apiResponse.counting_details; // Store for later use
            // Update titles with the fetched note
            pageTitleElement.textContent = `Student: ${currentStudentNoteForDisplay}`;
            subTitleElement.textContent = `Manage Class Counted by ${currentStudentNoteForDisplay} for ${dayNames[day]}`;
            renderCountingDetailsTable(fetchedClassDetails);
        })
        .catch(error => {
            console.error('Error fetching student counting details:', error);
            studentIsCountingTableBody.innerHTML = `<tr><td colspan="3" style="color: red; text-align: center;">Error loading details: ${error.message}</td></tr>`;
        });

    function renderCountingDetailsTable(details) {
        studentIsCountingTableBody.innerHTML = ''; // Clear existing rows

        if (!details || details.length === 0) {
            studentIsCountingTableBody.innerHTML = `<tr><td colspan="3" style="text-align: center;">This student's class is not assigned to count any classes on ${dayNames[day]}.</td></tr>`;
            return;
        }

        details.forEach(item => {
            const row = studentIsCountingTableBody.insertRow();

            row.insertCell().textContent = item.class_name;
            
            const countsCell = row.insertCell();
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.checked = item.is_counted_by_current_student;
            checkbox.dataset.className = item.class_name; // Store class name for the event handler
            checkbox.addEventListener('change', handleCountingChange);
            countsCell.appendChild(checkbox);
            
            const isCountedByCell = row.insertCell();
            const notesToDisplayElements = [];

            // Add the current student's note in bold if they count this class
            if (item.is_counted_by_current_student) {
                const liCurrentStudent = document.createElement('li');
                const strongTag = document.createElement('strong');
                strongTag.textContent = currentStudentNoteForDisplay; // Use the fetched note
                liCurrentStudent.appendChild(strongTag);
                notesToDisplayElements.push(liCurrentStudent);
            }

            // Add other students' notes
            if (item.also_counted_by_notes && item.also_counted_by_notes.length > 0) {
                item.also_counted_by_notes.forEach(note => {
                    const li = document.createElement('li');
                    li.textContent = note;
                    notesToDisplayElements.push(li);
                });
            }

            if (notesToDisplayElements.length > 0) {
                const ul = document.createElement('ul');
                ul.style.margin = '0';
                ul.style.paddingLeft = '15px';
                notesToDisplayElements.forEach(el => ul.appendChild(el));
                isCountedByCell.appendChild(ul);
            } else {
                isCountedByCell.textContent = 'N/A';
            }
        });
    }

    function handleCountingChange(event) {
        const checkbox = event.target;
        const className = checkbox.dataset.className;
        const isCounting = checkbox.checked;
        const studentCodeForAPI = urlParams.get('code'); // Get student code for the API call

        fetch('/api/student/update-counting-class', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                student_code: studentCodeForAPI, // Send student_code
                class_name: className,
                is_counting: isCounting
            }),
        })
        .then(response => response.json().then(data => ({ ok: response.ok, data })))
        .then(({ok, data}) => {
            if (ok && data.success) {
                console.log(data.message); // Or a more user-friendly notification
                
                // Update the "Is Counted By" cell for the changed row
                const row = checkbox.closest('tr');
                if (row) {
                    const isCountedByCell = row.cells[2]; // Assuming 0: Class, 1: Counts (checkbox), 2: Is Counted By
                    if (isCountedByCell) {
                        isCountedByCell.innerHTML = ''; // Clear current content

                        const itemDetails = fetchedClassDetails.find(d => d.class_name === className);
                        const notesToDisplayElements = [];

                        // Add current student's note (bolded) if they are now counting this class
                        if (isCounting) { // Use the new state of the checkbox
                            const liCurrentStudent = document.createElement('li');
                            const strongTag = document.createElement('strong');
                            strongTag.textContent = currentStudentNoteForDisplay; // Use stored note for display
                            liCurrentStudent.appendChild(strongTag);
                            notesToDisplayElements.push(liCurrentStudent);
                        }

                        // Add other students' notes (these don't change from this action)
                        if (itemDetails && itemDetails.also_counted_by_notes && itemDetails.also_counted_by_notes.length > 0) {
                            itemDetails.also_counted_by_notes.forEach(note => {
                                const li = document.createElement('li');
                                li.textContent = note;
                                notesToDisplayElements.push(li);
                            });
                        }
                        renderNotesListInCell(isCountedByCell, notesToDisplayElements);
                    }
                }
            } else {
                alert(`Error updating counting status: ${data.error || 'Unknown error'}`);
                checkbox.checked = !isCounting; // Revert checkbox on error
            }
        })
        .catch(error => {
            console.error('Error updating counting status:', error);
            alert(`Failed to update: ${error.message}`);
            checkbox.checked = !isCounting; // Revert checkbox on error
        });
    }

    // Helper function to render the list of notes in the "Is Counted By" cell
    function renderNotesListInCell(cell, notesElements) {
        if (notesElements.length > 0) {
            const ul = document.createElement('ul');
            ul.style.margin = '0';
            ul.style.paddingLeft = '15px';
            notesElements.forEach(el => ul.appendChild(el));
            cell.appendChild(ul);
        } else {
            cell.textContent = 'N/A';
        }
    }
});
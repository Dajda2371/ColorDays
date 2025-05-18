document.addEventListener('DOMContentLoaded', function() {
    const studentsTableBody = document.getElementById('students-table-body');

    if (!studentsTableBody) {
        console.error('Students table body not found!');
        return;
    }

    loadStudents();

    // Get the 'day' parameter from the current URL if it exists
    const urlParams = new URLSearchParams(window.location.search);
    const dayFromUrl = urlParams.get('day');
    const classFromUrl = urlParams.get('class'); // Get the 'class' parameter

    function loadStudents() {
        fetch('/api/students')
            .then(response => {
                if (!response.ok) {
                    return response.json().then(err => { throw new Error(err.error || `HTTP error! status: ${response.status}`) });
                }
                return response.json();
            })
            .then(students => {
                let studentsToRender = students;
                if (classFromUrl) {
                    studentsToRender = students.filter(student => student.class === classFromUrl);
                    // Optionally, update a subtitle or heading to indicate filtering
                    const pageHeading = document.querySelector('h1');
                    if (pageHeading) {
                        pageHeading.textContent = `Students for Class: ${classFromUrl}`;
                    }
                }
                renderStudentsTable(studentsToRender);
            })
            .catch(error => {
                console.error('Error fetching students:', error);
                studentsTableBody.innerHTML = `<tr><td colspan="5" style="color: red; text-align: center;">Error loading students: ${error.message}</td></tr>`;
            });
    }

    function renderStudentsTable(students) {
        studentsTableBody.innerHTML = ''; // Clear existing rows

        if (students.length === 0) {
            let noStudentsMessage = 'No student configurations found.';
            if (classFromUrl) {
                noStudentsMessage = `No student configurations found for class ${classFromUrl}.`;
            }
            studentsTableBody.innerHTML = `<tr><td colspan="5" style="text-align: center;">${noStudentsMessage}</td></tr>`;
            return;
        }

        students.forEach(student => {
            const row = studentsTableBody.insertRow();

            row.insertCell().textContent = student.code;
            row.insertCell().textContent = student.class; // Add the student's class
            row.insertCell().textContent = student.note;
            
            // 'counting_classes' is expected to be an array from the backend
            const countingClassesCell = row.insertCell();
            countingClassesCell.textContent = student.counting_classes && student.counting_classes.length > 0 
                                            ? student.counting_classes.join(', ') 
                                            : 'N/A';

            const actionsCell = row.insertCell();
            
            const editButton = document.createElement('a');
            let editHref = `student-is-counting.html?code=${encodeURIComponent(student.code)}`;
            if (dayFromUrl) { // If 'day' was in the URL of students.html, pass it along
                editHref += `&day=${encodeURIComponent(dayFromUrl)}`;
            }
            editButton.href = editHref;
            editButton.textContent = 'Edit Classes';
            editButton.className = 'button class-button'; // Apply class-button style
            actionsCell.appendChild(editButton);

            actionsCell.appendChild(document.createTextNode(' ')); // For spacing

            const removeButton = document.createElement('button');
            removeButton.textContent = 'Remove';
            removeButton.className = 'button class-button button-danger'; // Apply class-button and keep button-danger
            removeButton.addEventListener('click', () => removeStudent(student.code, student.note, student.class)); // Pass code, note, and class for confirmation
            actionsCell.appendChild(removeButton);
        });
    }

    function removeStudent(studentCode, studentNote, studentClass) {
        if (!confirm(`Are you sure you want to remove the student configuration:\nCode: ${studentCode}\nClass: ${studentClass}\nNote: ${studentNote || '(No note)'}?`)) {
            return;
        }

        fetch('/api/students/remove', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code: studentCode }) // Send the student's code
        })
        .then(response => response.json().then(data => ({ ok: response.ok, data })))
        .then(({ ok, data }) => {
            if (ok && data.success) {
                alert(data.message || 'Student configuration removed successfully.');
                loadStudents(); // Reload the table
            } else {
                alert(`Error removing student configuration: ${data.error || 'Unknown error'}`);
            }
        })
        .catch(error => {
            console.error('Error removing student configuration:', error);
            alert(`Failed to remove student configuration: ${error.message}`);
        });
    }

    // Make this function globally accessible for the inline onclick
    window.addStudentConfiguration = function() {
        let studentClassToAdd;

        if (classFromUrl) {
            studentClassToAdd = classFromUrl;
            console.log(`Adding student configuration for class from URL: ${studentClassToAdd}`);
        } else {
            studentClassToAdd = prompt("Enter the student's class (e.g., 9.A):");
            if (studentClassToAdd === null || studentClassToAdd.trim() === "") {
                alert("Class cannot be empty. Operation cancelled.");
                return;
            }
            studentClassToAdd = studentClassToAdd.trim();
        }
        const note = prompt("Enter a note for this student configuration:");
        if (note === null) { // Allow empty note, but not if cancelled
            alert("Operation cancelled.");
            return;
        }

        fetch('/api/students/add', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                class: studentClassToAdd,
                note: note // Note can be empty string
            }),
        })
        .then(response => response.json().then(data => ({ ok: response.ok, data })))
        .then(({ok, data}) => {
            if (ok && data.success) {
                alert(data.message || 'Student configuration added successfully.');
                loadStudents(); // Reload the table to show the new student
            } else {
                alert(`Error adding student configuration: ${data.error || 'Unknown error'}`);
            }
        })
        .catch(error => {
            console.error('Error adding student configuration:', error);
            alert(`Failed to add student configuration: ${error.message}`);
        });
    }
});
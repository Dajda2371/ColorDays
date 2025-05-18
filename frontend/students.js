document.addEventListener('DOMContentLoaded', function() {
    const studentsTableBody = document.getElementById('students-table-body');

    if (!studentsTableBody) {
        console.error('Students table body not found!');
        return;
    }

    loadStudents();

    function loadStudents() {
        fetch('/api/students')
            .then(response => {
                if (!response.ok) {
                    return response.json().then(err => { throw new Error(err.error || `HTTP error! status: ${response.status}`) });
                }
                return response.json();
            })
            .then(students => {
                renderStudentsTable(students);
            })
            .catch(error => {
                console.error('Error fetching students:', error);
                studentsTableBody.innerHTML = `<tr><td colspan="5" style="color: red; text-align: center;">Error loading students: ${error.message}</td></tr>`;
            });
    }

    function renderStudentsTable(students) {
        studentsTableBody.innerHTML = ''; // Clear existing rows

        if (students.length === 0) {
            studentsTableBody.innerHTML = '<tr><td colspan="5" style="text-align: center;">No student configurations found.</td></tr>';
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
            editButton.href = `student-is-counting.html?note=${encodeURIComponent(student.note)}`;
            editButton.textContent = 'Edit Classes';
            editButton.className = 'button'; // Add a class for styling if needed
            actionsCell.appendChild(editButton);

            actionsCell.appendChild(document.createTextNode(' ')); // For spacing

            const removeButton = document.createElement('button');
            removeButton.textContent = 'Remove';
            removeButton.className = 'button-danger'; // Add a class for styling if needed
            removeButton.addEventListener('click', () => removeStudent(student.class)); // student.class is the identifier
            actionsCell.appendChild(removeButton);
        });
    }

    function removeStudent(studentClassIdentifier) {
        if (!confirm(`Are you sure you want to remove the student configuration for class "${studentClassIdentifier}"?`)) {
            return;
        }

        fetch('/api/students/remove', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ class: studentClassIdentifier })
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
        const studentClass = prompt("Enter the student's class (e.g., 9.A):");
        if (studentClass === null || studentClass.trim() === "") {
            alert("Class cannot be empty. Operation cancelled.");
            return;
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
                class: studentClass.trim(),
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
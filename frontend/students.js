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

    // Set these to match your backend config
    const DOMAIN = "barevnedny.davidbenes.cz";
    const PORT = 8000;

    // Function to render students (add QR Code button)
    function renderStudentsTable(students) {
      const tbody = document.getElementById('students-table-body');
      tbody.innerHTML = '';
      students.forEach(student => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td>${student.code}</td>
          <td>${student.class}</td>
          <td>${student.note}</td>
          <td>${(student.counting_classes || []).join(', ')}</td>
          <td>
          <button class="class-button" onclick="window.location.href='classes.html?class=${encodeURIComponent(student.class)}'">Edit Classes</button>
            <button class="class-button" onclick="showQrCode('${student.code}')">QR Code</button>
            <button class="class-button" onclick="removeStudent('${student.code}', '${student.note?.replace(/'/g, "\\'") || ''}', '${student.class}')">Remove</button>
          </td>
        `;
        tbody.appendChild(tr);
      });
    }

    // Show QR code modal
    window.showQrCode = function(code) {
      const url = `http://${DOMAIN}:${PORT}/login.html?code=${encodeURIComponent(code)}`;
      document.getElementById('qrModal').style.display = 'flex';
      document.getElementById('qrUrl').textContent = code;
      document.getElementById('qrcode').innerHTML = '';
      new QRCode(document.getElementById('qrcode'), {
        text: url,
        width: 220,
        height: 220,
      });
    };

    // Close modal
    document.getElementById('closeQrModal').onclick = function() {
      document.getElementById('qrModal').style.display = 'none';
    };

    // Optional: close modal when clicking outside the QR code box
    document.getElementById('qrModal').onclick = function(e) {
      if (e.target === this) this.style.display = 'none';
    };

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
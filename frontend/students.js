document.addEventListener('DOMContentLoaded', function () {
    const studentsTableBody = document.getElementById('students-table-body');

    if (!studentsTableBody) {
        console.error('Students table body not found!');
        return;
    }

    // Remove the hardcoded DOMAIN and PORT
    // const DOMAIN = "barevnedny.davidbenes.cz";
    // const PORT = 8000;

    let DOMAIN = '';
    let PORT = '';

    // Fetch DOMAIN and PORT from backend config
    function fetchDomainAndPort() {
        return fetch('/api/data/config')
            .then(res => res.json())
            .then(config => {
                DOMAIN = config.DOMAIN || window.location.hostname;
                PORT = config.PORT || window.location.port || 80;
            })
            .catch(() => {
                // fallback to current location if API fails
                DOMAIN = window.location.hostname;
                PORT = window.location.port || 80;
            });
    }

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

    // Call fetchDomainAndPort before loading students
    fetchDomainAndPort().then(() => {
        loadStudents();
    });

    // Function to render students (add QR Code button)
    function renderStudentsTable(students) {
        window.lastStudentsList = students;
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
            <button class="class-button" onclick="window.location.href='student-is-counting.html?code=${encodeURIComponent(student.code)}&day=${encodeURIComponent(dayFromUrl || '')}&class=${encodeURIComponent(classFromUrl || '')}'">Edit Classes</button>
            <button class="class-button" onclick="showQrCode('${student.code}')">QR Code</button>
            <button class="class-button" onclick="removeStudent('${student.code}', '${student.note?.replace(/'/g, "\\'") || ''}', '${student.class}')">Remove</button>
          </td>
        `;
            tbody.appendChild(tr);
        });
    }

    // Show QR code modal
    window.showQrCode = function (code) {
        // Find the student object by code (assuming you have access to the students array)
        const student = (window.lastStudentsList || []).find(s => s.code === code);
        document.getElementById('qrNote').textContent = student && student.note ? student.note : '';
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
    document.getElementById('closeQrModal').onclick = function () {
        document.getElementById('qrModal').style.display = 'none';
    };

    // Optional: close modal when clicking outside the QR code box
    document.getElementById('qrModal').onclick = function (e) {
        if (e.target === this) this.style.display = 'none';
    };

    // Make functions globally accessible
    window.removeStudent = function (studentCode, studentNote, studentClass) {
        if (!confirm(`Are you sure you want to remove the student configuration:\nCode: ${studentCode}\nClass: ${studentClass}\nNote: ${studentNote || '(No note)'}?`)) {
            return;
        }

        fetch(`/api/students?code=${encodeURIComponent(studentCode)}`, {
            method: 'DELETE',
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
    };

    window.handleAddStudentRow = function () {
        const tbody = document.getElementById('students-table-body');
        if (document.getElementById('addStudentRow')) return;

        const addRow = document.createElement('tr');
        addRow.id = 'addStudentRow';

        let classValue = '';
        if (classFromUrl) {
            classValue = classFromUrl;
        }

        addRow.innerHTML = `
            <td style="color: grey; font-style: italic;">Auto-generated</td>
            <td><input type="text" id="newStudentClass" placeholder="Class (e.g. 9.A)" value="${classValue}" /></td>
            <td><input type="text" id="newStudentNote" placeholder="Note" /></td>
            <td>-</td>
            <td>
                <button class="class-button" onclick="saveNewStudent()">Save</button>
                <button class="class-button" onclick="cancelAddStudent()">Cancel</button>
            </td>
        `;
        // Insert as first row or append? Append usually.
        // If we want it at the top: tbody.insertBefore(addRow, tbody.firstChild);
        // But table usually appends.
        tbody.appendChild(addRow);

        // Focus the input
        if (classValue) {
            document.getElementById('newStudentNote').focus();
        } else {
            document.getElementById('newStudentClass').focus();
        }
    };

    window.cancelAddStudent = function () {
        const row = document.getElementById('addStudentRow');
        if (row) row.remove();
    };

    window.saveNewStudent = function () {
        const classInput = document.getElementById('newStudentClass');
        const noteInput = document.getElementById('newStudentNote');

        const className = classInput.value.trim();
        const note = noteInput.value.trim();

        if (!className) {
            alert("Class name is required.");
            return;
        }

        fetch('/api/students', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                class: className,
                note: note
            }),
        })
            .then(response => response.json().then(data => ({ ok: response.ok, data })))
            .then(({ ok, data }) => {
                if (ok && data.success) {
                    // Remove row and reload
                    cancelAddStudent();
                    loadStudents();
                    console.log(data.message);
                } else {
                    alert(`Error adding student configuration: ${data.error || 'Unknown error'}`);
                }
            })
            .catch(error => {
                console.error('Error adding student configuration:', error);
                alert(`Failed to add student configuration: ${error.message}`);
            });
    };

    // Alias for backward compatibility if needed, though we will change HTML
    window.addStudentConfiguration = window.handleAddStudentRow;
});
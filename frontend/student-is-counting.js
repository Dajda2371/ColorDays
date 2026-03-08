
// --- NAVBAR LOGIC ADDED ---
const logoutButton = document.getElementById('logoutButton');
const languageToggle = document.getElementById('languageToggle');
const toggleCs = document.getElementById('toggleCs');
const toggleEn = document.getElementById('toggleEn');

let translations = {};
let currentLanguage = 'en';

async function handleLogout() {
    try {
        const response = await fetch('/logout', {
            method: 'POST',
            credentials: 'include'
        });
        if (response.ok) {
            window.location.href = '/login.html';
        } else {
            alert((translations.logoutFailedAlert?.[currentLanguage] || 'Logout failed'));
        }
    } catch (error) {
        alert((translations.logoutErrorAlert?.[currentLanguage] || 'An error occurred during logout.'));
    }
}

if (logoutButton) {
    logoutButton.addEventListener('click', handleLogout);
}

async function fetchTranslations() {
    try {
        const response = await fetch('/api/translations');
        if (!response.ok) return;
        translations = await response.json();
        applyTranslations();
    } catch (error) {
        console.error('Error fetching translations:', error);
    }
}

function applyTranslations() {
    document.querySelectorAll('[data-translate-key]').forEach(element => {
        const key = element.getAttribute('data-translate-key');
        const text = translations[key]?.[currentLanguage] || translations[key]?.['en'];
        if (text) {
            if (element.tagName === 'INPUT') {
                element.placeholder = text;
            } else {
                element.textContent = text;
            }
        }
    });
}

function displayLoggedInUser() {
    const cookies = document.cookie.split('; ');
    const usernameCookie = cookies.find(row => row.startsWith('ColorDaysUser='));
    const usernameTextSpan = document.getElementById('usernameText');
    if (usernameCookie && usernameTextSpan) {
        const username = usernameCookie.split('=')[1];
        usernameTextSpan.textContent = decodeURIComponent(username);
    } else if (usernameTextSpan) {
        usernameTextSpan.textContent = translations.usernameNotLoggedIn?.[currentLanguage] || (translations.usernameNotLoggedIn?.[currentLanguage] || 'Not Logged In');
    }
}

function getCookie(name) {
    const nameEQ = name + "=";
    const ca = document.cookie.split(';');
    for (let i = 0; i < ca.length; i++) {
        let c = ca[i];
        while (c.charAt(0) === ' ') c = c.substring(1, c.length);
        if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length, c.length);
    }
    return null;
}

async function setLanguagePreference(lang) {
    try {
        const response = await fetch('/api/language/set', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ language: lang }),
            credentials: 'include'
        });
        if (response.ok) {
            currentLanguage = lang;
            applyTranslations(); window.location.reload(); window.location.reload();
            displayLoggedInUser();
        }
    } catch (error) {
        console.error('Error setting language:', error);
    }
}

function setToggleState(lang) {
    if (toggleCs && toggleEn) {
        if (lang === 'cs') {
            toggleCs.classList.add('active');
            toggleEn.classList.remove('active');
        } else {
            toggleEn.classList.add('active');
            toggleCs.classList.remove('active');
        }
    }
}

if (languageToggle) {
    languageToggle.addEventListener('click', (event) => {
        const target = event.target;
        if (target.tagName === 'SPAN' && target.dataset.lang) {
            const selectedLang = target.dataset.lang;
            setLanguagePreference(selectedLang);
            setToggleState(selectedLang);
        }
    });
}
// --- END NAVBAR LOGIC ---

document.addEventListener('DOMContentLoaded', function () {

    // Navbar Initialization
    currentLanguage = getCookie("language") || 'en';
    fetchTranslations().then(() => {
        setToggleState(currentLanguage);
        displayLoggedInUser();
    });

    const studentIsCountingTableBody = document.getElementById('student-is-counting-table-body');
    const pageTitleElement = document.getElementById('pageTitle');

    let fetchedClassDetails = []; // Store fetched details for dynamic updates
    let currentStudentNoteForDisplay = ''; // Store the note of the current student
    if (!studentIsCountingTableBody || !pageTitleElement) {
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
        pageTitleElement.textContent = (translations.errorStudentCodeMissing?.[currentLanguage] || 'Error: Student Code Missing');
        studentIsCountingTableBody.innerHTML = `<tr><td colspan="3" style="color: red; text-align: center;">No student code provided in the URL.</td></tr>`;
        return;
    }
    if (!day || !['1', '2', '3'].includes(day)) {
        pageTitleElement.textContent = (translations.errorDayParameterInvalid?.[currentLanguage] || 'Error: Day Parameter Invalid');
        studentIsCountingTableBody.innerHTML = `<tr><td colspan="3" style="color: red; text-align: center;">Day parameter is missing or invalid (must be 1, 2, or 3).</td></tr>`;
        return;
    }

    const dayNames = { '1': 'Monday', '2': 'Tuesday', '3': 'Wednesday' };
    pageTitleElement.textContent = dayNames[day]; // Initial title

    function loadStudentDetails() {
        if (!document.hidden || !window.hasLoadedStudentDetails) {
            fetch(`/api/student/counting-details?code=${encodeURIComponent(studentCode)}&day=${encodeURIComponent(day)}`)
                .then(response => {
                    if (!response.ok) {
                        return response.json().then(err => { throw new Error(err.error || `HTTP error! status: ${response.status}`) });
                    }
                    return response.json();
                })
                .then(apiResponse => {
                    window.hasLoadedStudentDetails = true;
                    currentStudentNoteForDisplay = apiResponse.student_note || studentCode; // Use note if available, else code
                    fetchedClassDetails = apiResponse.counting_details; // Store for later use
                    const studentClass = apiResponse.student_class; // Get the student's main class

                    // Update titles with the fetched note
                    // Update title with the day (instead of student note)
                    pageTitleElement.textContent = dayNames[day];

                    // Update the "Back to Students" button
                    const backBtn = document.getElementById('backButton');
                    if (backBtn && !backBtn.onclick) { // only set onclick once
                        const prevClass = urlParams.get('class');
                        const targetClass = prevClass || studentClass;
                        let newHref = 'students.html';
                        if (targetClass || day) {
                            newHref += '?';
                            const params = new URLSearchParams();
                            if (targetClass) params.set('class', targetClass);
                            if (day) params.set('day', day);
                            newHref += params.toString();
                        }
                        backBtn.onclick = function () { window.location.href = newHref; };
                    }
                    renderCountingDetailsTable(fetchedClassDetails);
                })
                .catch(error => {
                    console.error('Error fetching student counting details:', error);
                    studentIsCountingTableBody.innerHTML = `<tr><td colspan="3" style="color: red; text-align: center;">Error loading details: ${error.message}</td></tr>`;
                });
        }
    }

    loadStudentDetails();

    // Fetch refresh interval and setup auto-refresh
    fetch('/api/config/refresh_intervals')
        .then(res => res.json())
        .then(intervals => {
            const interval = intervals['student-is-counting.html'];
            if (interval && interval > 0) {
                setInterval(() => {
                    if (document.hidden) return;
                    if (document.activeElement.tagName === 'INPUT') return;
                    loadStudentDetails();
                }, interval);
            }
        })
        .catch(err => console.error("Error fetching refresh intervals:", err));

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
            countsCell.className = 'narrow-col';
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
                isCountedByCell.textContent = (translations.naText?.[currentLanguage] || 'N/A');
            }
        });
    }

    function handleCountingChange(event) {
        const checkbox = event.target;
        const className = checkbox.dataset.className;
        const isCounting = checkbox.checked;
        const studentCodeForAPI = urlParams.get('code'); // Get student code for the API call

        fetch('/api/student/counting-class', {
            method: 'PUT',
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
            .then(({ ok, data }) => {
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
            cell.textContent = (translations.naText?.[currentLanguage] || 'N/A');
        }
    }
});

function goBackToStudents() {
    const urlParams = new URLSearchParams(window.location.search);
    const dayFromUrl = urlParams.get('day');
    const classFromUrl = urlParams.get('class');

    let url = 'students.html';
    if (classFromUrl) {
        url += '?class=' + encodeURIComponent(classFromUrl);
    }
    if (dayFromUrl) {
        url += (classFromUrl ? '&' : '?') + 'day=' + encodeURIComponent(dayFromUrl);
    }
    window.location.href = url;
}

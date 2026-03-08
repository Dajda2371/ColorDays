// --- Global variable to store the current class name ---
let currentClassName = null;
let currentDayIdentifier = null; // Added to store the day

// --- Wait for the DOM to be fully loaded ---
document.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);
    currentClassName = urlParams.get('class'); // Store class name globally
    currentDayIdentifier = urlParams.get('day'); // Store day globally

    if (!currentClassName || !currentDayIdentifier) {
        alert((translations.noClassSelectedAlert?.[currentLanguage] || "No class selected. Redirecting to the menu."));
        window.location.href = 'menu.html'; // Redirect if no class
        return; // Stop further execution
    }

    // Update the heading with the class name
    const classNameElement = document.getElementById('className');
    const classTeacherElement = document.getElementById('classTeacher');
    if (classNameElement) {
        // Find if we have translations loaded somewhere, else fallback correctly
        let dayKey = '';
        const dayLower = currentDayIdentifier.toLowerCase();
        if (dayLower === 'monday' || dayLower === '1') dayKey = 'dayMonday';
        else if (dayLower === 'tuesday' || dayLower === '2') dayKey = 'dayTuesday';
        else if (dayLower === 'wednesday' || dayLower === '3') dayKey = 'dayWednesday';

        let dayDisplay = currentDayIdentifier.charAt(0).toUpperCase() + currentDayIdentifier.slice(1);

        if (dayKey) {
            classNameElement.innerHTML = `${decodeURIComponent(currentClassName)} | <span data-translate-key="${dayKey}">${dayDisplay}</span>`;
        } else {
            classNameElement.textContent = `${decodeURIComponent(currentClassName)} | ${dayDisplay}`;
        }
        classNameElement.removeAttribute('data-translate-key');
    } else {
        console.error("Element with ID 'className' not found.");
    }

    const markAsDoneBtn = document.getElementById('markAsDoneButton');
    const lockBtn = document.getElementById('lockButton');

    if (markAsDoneBtn) {
        markAsDoneBtn.addEventListener('click', () => handleStateChange('done'));
    }
    if (lockBtn) {
        lockBtn.addEventListener('click', () => handleStateChange('locked'));
    }

    // Role check for Lock button
    fetch('/api/auth/me')
        .then(res => res.json())
        .then(data => {
            if (data.role === 'administrator' || data.role === 'teacher') {
                if (lockBtn) lockBtn.style.display = 'inline-block';
            }
        })
        .catch(err => console.error("Error fetching user info:", err));

    // Fetch class teacher
    fetch('/api/classes')
        .then(response => response.json())
        .then(classes => {
            const currentClassInfo = classes.find(c => c.class === decodeURIComponent(currentClassName));
            if (currentClassInfo && classTeacherElement) {
                classTeacherElement.textContent = currentClassInfo.teacher || '';
            }
        })
        .catch(error => console.error("Error fetching class details:", error));

    // Create the buttons immediately (they don't depend on fetched counts)
    createButtons();

    // Fetch initial data for the table
    fetchData();

    // Call localization and header loading logic
    currentLanguage = getCookie("language") || 'en';
    fetchTranslations().then(() => {
        setToggleState(currentLanguage);
        displayLoggedInUser();

        // Fetch refresh interval and setup auto-refresh
        fetch('/api/config/refresh_intervals')
            .then(res => res.json())
            .then(intervals => {
                const interval = intervals['index.html'];
                if (interval && interval > 0) {
                    setInterval(() => {
                        if (document.hidden) return;
                        if (document.activeElement.tagName === 'INPUT' || document.activeElement.tagName === 'TEXTAREA') return;
                        fetchData();
                    }, interval);
                }
            })
            .catch(err => console.error("Error fetching refresh intervals:", err));
    });
});

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


let currentClassState = '';

// --- Fetch data from the backend ---
async function fetchData() {
    if (!currentClassName || !currentDayIdentifier) {
        console.error("Cannot fetch data, className or dayIdentifier is not set.");
        return;
    }

    console.log(`Fetching data for class: ${currentClassName}, day: ${currentDayIdentifier}`);
    try {
        // Construct the correct API URL including the day
        const apiUrl = `/api/counts?class=${encodeURIComponent(currentClassName)}&day=${encodeURIComponent(currentDayIdentifier)}`;
        const response = await fetch(apiUrl);

        if (!response.ok) {
            // Handle HTTP errors (like 404, 500)
            throw new Error(`HTTP error! Status: ${response.status}`);
        }

        const dataResponse = await response.json(); // Parse the JSON response
        console.log("Data received from backend:", dataResponse);

        const data = dataResponse.counts;
        currentClassState = dataResponse.state || '';

        // Update the UI elements
        updateTable(data);
        updateTotals(data);
        updateUIState();

    } catch (error) {
        console.error("Error fetching data:", error);
        resetTableAndTotals();
    }
}

async function handleStateChange(newState) {
    if (currentClassState === 'locked' && newState === 'locked') {
        // Special case: Unlock (which is the lock button in locked state)
        // should return the state to 'done'
        newState = 'done';
    } else if (currentClassState === newState) {
        // Normal toggle: if clicking an active state button again, reset to empty
        newState = '';
    }

    try {
        const response = await fetch('/api/counts/state', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                className: decodeURIComponent(currentClassName),
                day: currentDayIdentifier,
                state: newState
            })
        });

        if (response.ok) {
            fetchData(); // Refresh everything
        } else {
            const err = await response.json();
            alert((translations.stateUpdateFailedAlert?.[currentLanguage] || "Failed to update state: ") + (err.detail || ''));
        }
    } catch (error) {
        console.error("Error updating state:", error);
        alert((translations.stateUpdateFailedAlert?.[currentLanguage] || "Error updating state."));
    }
}

function updateUIState() {
    const markDoneBtn = document.getElementById('markAsDoneButton');
    const lockBtn = document.getElementById('lockButton');
    const allCountButtons = document.querySelectorAll('.btn-count');

    if (!markDoneBtn) return;

    // Reset common styles/states
    markDoneBtn.classList.remove('disabled');
    if (lockBtn) lockBtn.classList.remove('disabled');
    allCountButtons.forEach(btn => btn.classList.remove('disabled'));

    if (currentClassState === 'done') {
        allCountButtons.forEach(btn => btn.classList.add('disabled'));

        // Mark as Done becomes EDIT, enabled, green
        markDoneBtn.setAttribute('data-translate-key', 'editButtonText');
        markDoneBtn.style.backgroundColor = '#d4edda';
        markDoneBtn.style.color = '#155724';
        markDoneBtn.classList.remove('disabled');

        if (lockBtn) {
            // Lock stays LOCK, enabled, red
            lockBtn.setAttribute('data-translate-key', 'lockButtonText');
            lockBtn.classList.remove('disabled');
            lockBtn.style.backgroundColor = '#f8d7da';
            lockBtn.style.color = '#721c24';
            lockBtn.style.pointerEvents = 'auto'; // ensure clickable
            lockBtn.style.opacity = '1';
        }

    } else if (currentClassState === 'locked') {
        allCountButtons.forEach(btn => btn.classList.add('disabled'));

        // Mark as Done becomes EDIT, disabled, green
        markDoneBtn.setAttribute('data-translate-key', 'editButtonText');
        markDoneBtn.classList.add('disabled');
        markDoneBtn.style.backgroundColor = '#d4edda';
        markDoneBtn.style.color = '#155724';

        if (lockBtn) {
            // Lock becomes UNLOCK, enabled, red
            lockBtn.setAttribute('data-translate-key', 'unlockButtonText');
            lockBtn.classList.remove('disabled');
            lockBtn.style.backgroundColor = '#f8d7da';
            lockBtn.style.color = '#721c24';
            lockBtn.style.pointerEvents = 'auto'; // ensure clickable
            lockBtn.style.opacity = '1';
        }
    } else {
        // State EMPTY
        allCountButtons.forEach(btn => btn.classList.remove('disabled'));

        // Mark as Done stays MARK AS DONE, enabled, blue/default
        markDoneBtn.setAttribute('data-translate-key', 'markAsDoneButtonText');
        markDoneBtn.style.backgroundColor = '';
        markDoneBtn.style.color = '';
        markDoneBtn.classList.remove('disabled');

        if (lockBtn) {
            // Lock button stays LOCK, but is DISABLED
            lockBtn.setAttribute('data-translate-key', 'lockButtonText');
            lockBtn.classList.add('disabled');
            lockBtn.style.backgroundColor = '';
            lockBtn.style.color = '';
            lockBtn.style.pointerEvents = 'none';
            lockBtn.style.opacity = '0.5';
        }
    }

    // Refresh translations for the dynamically updated keys
    applyTranslations();
}

// --- Update the table cells with fetched data ---
function updateTable(data) {
    console.log("Updating table...");
    // 1. Reset all count cells to 0 first
    for (let i = 0; i <= 6; i++) {
        const studentCell = document.getElementById(`student${i}`);
        const teacherCell = document.getElementById(`teacher${i}`);
        if (studentCell) studentCell.textContent = '0';
        if (teacherCell) teacherCell.textContent = '0';
    }

    // 2. Fill in counts from the fetched data array
    if (Array.isArray(data)) {
        data.forEach(item => {
            // Construct the ID of the cell to update
            const cellId = `${item.type}${item.points}`; // e.g., "student3", "teacher5"
            const cell = document.getElementById(cellId);
            if (cell) {
                cell.textContent = item.count; // Update the cell content
            } else {
                console.warn(`Cell with ID ${cellId} not found in the HTML!`);
            }
        });
    } else {
        console.error("Data received for table update is not an array:", data);
    }
    console.log("Table update complete.");
}

// --- Calculate and update total counts ---
function updateTotals(data) {
    // Update console log to reflect weighted calculation
    console.log("Updating totals (with teacher points doubled)...");
    let studentScoreTotal = 0; // Use a name that reflects score, not just count
    let teacherScoreTotal = 0; // Use a name that reflects score, not just count
    let studentCountTotal = 0;
    let teacherCountTotal = 0;

    if (Array.isArray(data)) {
        data.forEach(item => {
            // item has { type: 'student'/'teacher', points: number, count: number }
            if (item.type === 'student') {
                // Student score = points * count
                studentScoreTotal += item.points * item.count;
                studentCountTotal += item.count;
            } else if (item.type === 'teacher') {
                // Teacher score = points * count * 2 (doubled)
                teacherScoreTotal += item.points * item.count * 2;
                teacherCountTotal += item.count;
            }
        });
    } else {
        console.error("Data received for totals update is not an array:", data);
    }

    const studentTotalCell = document.getElementById('studentTotal');
    const teacherTotalCell = document.getElementById('teacherTotal');
    const studentCountCell = document.getElementById('studentCount');
    const teacherCountCell = document.getElementById('teacherCount');

    // Update the footer cells with the calculated SCORES
    if (studentTotalCell) studentTotalCell.textContent = studentScoreTotal;
    if (teacherTotalCell) teacherTotalCell.textContent = teacherScoreTotal;
    if (studentCountCell) studentCountCell.textContent = studentCountTotal;
    if (teacherCountCell) teacherCountCell.textContent = teacherCountTotal;

    // Update console log
    console.log("Totals update complete (weighted):", { studentScoreTotal, teacherScoreTotal });
}

// --- Reset table and totals (e.g., on error) ---
function resetTableAndTotals() {
    console.warn("Resetting table and totals to 0.");
    for (let i = 0; i <= 6; i++) {
        const studentCell = document.getElementById(`student${i}`);
        const teacherCell = document.getElementById(`teacher${i}`);
        if (studentCell) studentCell.textContent = '0';
        if (teacherCell) teacherCell.textContent = '0';
    }
    const studentTotalCell = document.getElementById('studentTotal');
    const teacherTotalCell = document.getElementById('teacherTotal');
    const studentCountCell = document.getElementById('studentCount');
    const teacherCountCell = document.getElementById('teacherCount');
    if (studentTotalCell) studentTotalCell.textContent = '0';
    if (teacherTotalCell) teacherTotalCell.textContent = '0';
    if (studentCountCell) studentCountCell.textContent = '0';
    if (teacherCountCell) teacherCountCell.textContent = '0';
}


// --- Create increment and decrement buttons ---
function createButtons() {
    console.log("Creating buttons...");
    const studentButtonsDiv = document.getElementById('studentButtons');
    const teacherButtonsDiv = document.getElementById('teacherButtons');

    if (!studentButtonsDiv || !teacherButtonsDiv) {
        console.error("Button container divs not found!");
        return;
    }

    // Clear any existing buttons first
    studentButtonsDiv.innerHTML = '';
    teacherButtonsDiv.innerHTML = '';

    // Helper to create a button group
    function createButtonGroup(div, type, points) {
        const wrapper = document.createElement('div');
        wrapper.className = 'point-control-group';

        // Increment Button
        const incButton = document.createElement('button');
        incButton.textContent = `+${points}`;
        incButton.className = 'btn-count btn-add';
        incButton.onclick = () => handleCountChange('increment', type, points);

        // Decrement Button
        const decButton = document.createElement('button');
        decButton.textContent = `-${points}`;
        decButton.className = 'btn-count btn-remove';
        decButton.onclick = () => handleCountChange('decrement', type, points);

        wrapper.appendChild(incButton);
        wrapper.appendChild(decButton);
        div.appendChild(wrapper);
    }

    // Loop through points 0 to 6
    for (let points = 0; points <= 6; points++) {
        createButtonGroup(studentButtonsDiv, 'student', points);
        createButtonGroup(teacherButtonsDiv, 'teacher', points);
    }

    console.log("Button creation complete.");
}

// --- Handle increment/decrement button clicks ---
async function handleCountChange(action, type, points) {
    if (!currentClassName || !currentDayIdentifier) {
        console.error("Cannot change count, className or dayIdentifier is not set.");
        alert((translations.classContextLostAlert?.[currentLanguage] || "Error: Class context lost. Please refresh or go back to menu."));
        return;
    }

    const apiUrl = `/api/${action}`; // action is 'increment' or 'decrement'
    const payload = {
        class: currentClassName,
        type: type,
        value: points,
        day: currentDayIdentifier
    };

    console.log(`Sending ${action} request to ${apiUrl} with payload:`, payload);

    try {
        const response = await fetch(apiUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                // 'Credentials': 'include' // Often handled by browser for same-origin, or add if needed
            },
            body: JSON.stringify(payload),
        });

        // Check for specific "already zero" error on decrement
        if (action === 'decrement' && response.status === 400) {
            const errorData = await response.json().catch(() => ({})); // Try to parse error message
            console.warn(`Cannot decrement: ${errorData.message || errorData.error || 'Count is already zero.'}`);
            // Optionally provide subtle feedback to the user
            // e.g., briefly flash the button red
            return; // Stop processing, don't refetch data
        }

        if (!response.ok) {
            // Handle other errors
            const errorData = await response.json().catch(() => ({ error: 'Failed to parse error response from server.' }));
            throw new Error(`HTTP error! Status: ${response.status} - ${errorData.error || errorData.message || 'Unknown server error'}`);
        }

        // If the request was successful (200 OK)
        const result = await response.json();
        console.log(`${action} successful:`, result);

        // Refresh the data from the server to show the updated state
        fetchData();

    } catch (error) {
        console.error(`Error during ${action}:`, error);
        const actionTranslation = action === 'increment'
            ? (translations.failedToIncrementAlert?.[currentLanguage] || 'Failed to increment count.')
            : (translations.failedToDecrementAlert?.[currentLanguage] || 'Failed to decrement count.');
        alert(`${actionTranslation} ${error.message}`);
    }
}

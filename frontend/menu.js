const dynamicClassList = document.getElementById('dynamicClassList');
const logoutButton = document.getElementById('logoutButton');
const classesButton = document.getElementById('classesButton');
const configButton = document.getElementById('configButton');
const leaderboardButton = document.getElementById('leaderboardButton');
const changePasswordBtn = document.getElementById('changePasswordBtn');
const languageToggle = document.getElementById('languageToggle');
const toggleCs = document.getElementById('toggleCs');
const toggleEn = document.getElementById('toggleEn');
// No need to get configButton unless you add specific JS logic for it
let currentDataVersion = -1;

// --- Localization ---
let translations = {};
let currentLanguage = 'cs'; // Default language

// --- Logout Functionality (Keep this as is) ---
async function handleLogout() {
    const confirmation = confirm(translations.logoutConfirmation?.[currentLanguage] || "Are you sure you want to log out?");
    if (!confirmation) return;

    console.log("Attempting logout...");
    try {
        const response = await fetch('/logout', {
            method: 'POST',
            credentials: 'include' // Important for sending/receiving cookies
        });

        if (response.ok) {
            console.log("Logout successful on server. Redirecting to login.");
            // Redirect to login page after successful logout
            window.location.href = '/login.html';
        } else {
            // Try to parse error message if available
            const result = await response.json().catch(() => ({})); // Default to empty object if JSON fails
            console.error('Logout request failed:', response.status, result.error || (translations.unknownErrorText?.[currentLanguage] || 'Unknown server error'));
            alert(`Logout failed: ${result.error || (translations.serverErrorText?.[currentLanguage] || 'Server error')}`);
        }
    } catch (error) {
        console.error('Error during logout fetch:', error);
        alert((translations.logoutErrorAlert?.[currentLanguage] || 'An error occurred during logout. Please check your connection.'));
    }
}

logoutButton.addEventListener('click', handleLogout);
// --- END Logout Functionality ---

// --- Localization Functions ---
async function fetchTranslations() {
    try {
        console.log("Attempting to fetch translations from /api/translations...");
        const response = await fetch('/api/translations'); // Fetch from the new backend endpoint
        if (!response.ok) {
            console.error('Failed to load translations:', response.status);
            return;
        }
        console.log("Translations fetched successfully. Parsing JSON...");
        translations = await response.json();
        applyTranslations(); // Apply translations once fetched
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

// --- Function to fetch and display classes ---
async function loadAndDisplayClasses() {
    // Only show loading message if the list is currently empty
    if (!dynamicClassList.innerHTML.trim()) {
        const loadingMessage = translations.loadingClassesText?.[currentLanguage] || translations.loadingClassesText?.['en'] || 'Loading classes...'; 
        dynamicClassList.innerHTML = `<p>${loadingMessage}</p>`;
    }

    // Update currentDataVersion whenever we fetch the classes
    try {
        const versionResponse = await fetch('/api/data/version');
        if (versionResponse.ok) {
            const versionData = await versionResponse.json();
            currentDataVersion = versionData.version;
        }
    } catch (e) {
        console.warn("Failed to fetch data version during full reload:", e);
    }

    const studentCode = getCookie("SQLAuthUserStudent");
    let allClasses = [];
    let currentStudentData = null; // To store the specific student's record
    let relevantClassesForDisplay = []; // Classes to be grouped and shown
    let errorMessage = null;

    let smartSortingEnabled = false;
    try {
        const configResponse = await fetch('/api/config/public');
        if (configResponse.ok) {
            const configData = await configResponse.json();
            smartSortingEnabled = configData.smart_sorting === "true";
        }
    } catch (e) {
        console.warn("Failed to fetch public config", e);
    }

    try {
        // Step 1: Fetch all class data (contains counts1/2/3 flags)
        const allClassesResponse = await fetch('/api/classes', { credentials: 'include' });
        if (!allClassesResponse.ok) {
            const errorData = await allClassesResponse.json().catch(() => ({ error: "Failed to fetch base class data" }));
            throw new Error(errorData.error || `HTTP error! status: ${allClassesResponse.status}`);
        }
        allClasses = await allClassesResponse.json();

        if (studentCode) {
            console.log("Student session detected. Fetching specific classes for student code:", studentCode);
            const studentsResponse = await fetch('/api/students', { credentials: 'include' });
            if (!studentsResponse.ok) {
                const errorData = await studentsResponse.json().catch(() => ({ error: "Failed to fetch student data" }));
                // Don't throw, but log and potentially fall back or show error for student-specific list
                console.error("Failed to fetch student data:", errorData.error || `HTTP error! status: ${studentsResponse.status}`);
                errorMessage = (translations.errorSpecificClassAssignments?.[currentLanguage] || "Could not load your specific class assignments. Showing all available classes.");
                // For students, if their data fails to load, they should ideally see nothing or a specific error.
                // Falling back to "all classes" might be confusing if they are meant to see a restricted list.
                // Let's ensure they see an error and an empty list if their specific data isn't available.
                relevantClassesForDisplay = [];
            } else {
                const allStudents = await studentsResponse.json();
                currentStudentData = allStudents.find(s => s.code === studentCode);

                if (currentStudentData) {
                    console.log("Student data loaded:", currentStudentData);
                    // relevantClassesForDisplay will be determined later based on visible days and student's counting_classes
                } else {
                    console.warn("Current student data not found or no counting_classes. Student code:", studentCode);
                    errorMessage = (translations.errorAssignedClasses?.[currentLanguage] || "Could not load your assigned classes. You may not be assigned to any.");
                    // If student record not found, they shouldn't see any classes.
                    currentStudentData = null; // Ensure it's null
                    relevantClassesForDisplay = []; // Student sees no classes if their specific list is empty/not found
                }
            }
        } else {
            // Not a student, or student cookie not found, use all classes
            console.log("No student session. Fetching all classes.");
            relevantClassesForDisplay = [...allClasses];
        }
    } catch (error) {
        console.error('Error loading classes:', error);
        errorMessage = `${(translations.errorLoadingClassesSuffix?.[currentLanguage] || "Error loading classes: {error}. Please try again later or contact support.").replace("{error}", error.message)}`;
        relevantClassesForDisplay = []; // Clear classes on major error
    }

    // Create a DocumentFragment to build the new content off-screen
    const fragment = document.createDocumentFragment();

    if (errorMessage) {
        const errorPara = document.createElement('p');
        errorPara.style.color = 'red';
        errorPara.textContent = errorMessage;
        fragment.appendChild(errorPara);
    }

    const days = [
        { nameKey: "dayMonday", defaultName: "Monday", iscountedbyFlag: "iscountedby1" },
        { nameKey: "dayTuesday", defaultName: "Tuesday", iscountedbyFlag: "iscountedby2" },
        { nameKey: "dayWednesday", defaultName: "Wednesday", iscountedbyFlag: "iscountedby3" }
    ];

    let contentRendered = false;

    if (studentCode && currentStudentData) {
        // --- Student Logic ---
        const studentMainClass = currentStudentData.class;
        const studentPersonalCountingList = new Set(currentStudentData.counting_classes || []);
        console.log(`Student Main Class: ${studentMainClass}, Personally Counts:`, studentPersonalCountingList);

        if (!studentMainClass) {
            if (!errorMessage) errorMessage = (translations.errorMainClassNotSet?.[currentLanguage] || "Your main class is not set. Cannot determine days to display.");
            const errorPara = document.createElement('p');
            errorPara.style.color = 'red';
            errorPara.textContent = errorMessage;
            fragment.appendChild(errorPara);
            dynamicClassList.replaceChildren(fragment);
            return;
        }

        days.forEach(day => {
            // Check if the student's main class is responsible for counting ANY class on this day
            const dayDisplayName = translations[day.nameKey]?.[currentLanguage] || translations[day.nameKey]?.['en'] || day.defaultName; // Added English fallback
            const isDayVisibleForStudent = allClasses.some(cls => cls[day.iscountedbyFlag] === studentMainClass);
            console.log(`Day: ${dayDisplayName}, iscountedbyFlag: ${day.iscountedbyFlag}, Student Main Class: ${studentMainClass}, Is Visible: ${isDayVisibleForStudent}`);

            if (isDayVisibleForStudent) {
                // Get the classes this student is personally assigned to count
                const classesStudentCounts = Array.from(studentPersonalCountingList);

                if (classesStudentCounts.length > 0) {
                    contentRendered = true;
                    const daySectionDiv = document.createElement('div');
                    daySectionDiv.className = 'day-section';
                    daySectionDiv.innerHTML = `<h2>${dayDisplayName}</h2>`;

                    const studentClassesToDisplay = allClasses.filter(cls => classesStudentCounts.includes(cls.class));
                    const stateKey = `state${day.iscountedbyFlag.slice(-1)}`;

                    // Smart Sorting Logic
                    const classRegex = /^\d+\.[A-Za-z]+$/;
                    const allMatch = studentClassesToDisplay.length > 0 && studentClassesToDisplay.every(cls => classRegex.test(cls.class));
                    const useSmartSorting = smartSortingEnabled && allMatch;

                    if (useSmartSorting) {
                        const grouped = {};
                        studentClassesToDisplay.forEach(cls => {
                            const numberPart = cls.class.split('.')[0];
                            if (!grouped[numberPart]) grouped[numberPart] = [];
                            grouped[numberPart].push(cls);
                        });

                        const sortedGroupKeys = Object.keys(grouped).sort((a, b) => parseInt(a) - parseInt(b));

                        sortedGroupKeys.forEach(key => {
                            const groupDiv = document.createElement('div');
                            groupDiv.style.marginBottom = "10px";

                            grouped[key].sort((a, b) => a.class.localeCompare(b.class));

                            grouped[key].forEach(cls => {
                                const link = document.createElement('a');
                                link.href = `index.html?class=${encodeURIComponent(cls.class)}&day=${day.defaultName.toLowerCase()}`;
                                link.textContent = cls.class;
                                link.className = 'class-button';

                                const stateValue = cls[stateKey];
                                if (stateValue === 'done') link.classList.add('class-button-done');
                                else if (stateValue === 'locked') link.classList.add('class-button-locked');

                                const overrideKey = 'override_' + day.defaultName.toLowerCase();
                                if (cls[overrideKey]) {
                                    link.classList.add('class-button-locked');
                                    link.style.pointerEvents = 'none';
                                    link.style.opacity = '0.5';
                                    link.removeAttribute('href');
                                    link.title = 'Overridden by Admin';
                                }

                                groupDiv.appendChild(link);
                            });
                            daySectionDiv.appendChild(groupDiv);
                        });
                    } else {
                        const ul = document.createElement('ul');
                        ul.className = 'classList';
                        studentClassesToDisplay.sort((a, b) => a.class.localeCompare(b.class)).forEach(cls => {
                            const listItem = document.createElement('li');
                            const link = document.createElement('a');
                            link.href = `index.html?class=${encodeURIComponent(cls.class)}&day=${day.defaultName.toLowerCase()}`;
                            link.textContent = cls.class;

                            const stateValue = cls[stateKey];
                            if (stateValue === 'done') link.classList.add('class-button-done');
                            else if (stateValue === 'locked') link.classList.add('class-button-locked');

                            const overrideKey = 'override_' + day.defaultName.toLowerCase();
                            if (cls[overrideKey]) {
                                link.classList.add('class-button-locked');
                                link.style.pointerEvents = 'none';
                                link.style.opacity = '0.5';
                                link.removeAttribute('href');
                                link.title = 'Overridden by Admin';
                            }

                            listItem.appendChild(link);
                            ul.appendChild(listItem);
                        });
                        daySectionDiv.appendChild(ul);
                    }
                    fragment.appendChild(daySectionDiv);
                }
            }
        });
        if (!contentRendered && !errorMessage) {
            const noClassesPara = document.createElement('p');
            noClassesPara.textContent = translations.noClassesToCountStudentText?.[currentLanguage] || translations.noClassesToCountStudentText?.['en'] || 'You have no classes to count...';
            fragment.appendChild(noClassesPara);
        }

    } else if (!studentCode) {
        // --- Admin/Teacher Logic ---
        // Admins/Teachers see all classes under every day

        // Smart Sorting Logic
        const classRegex = /^\d+\.[A-Za-z]+$/;
        const allMatch = allClasses.every(cls => classRegex.test(cls.class));
        const useSmartSorting = smartSortingEnabled && allMatch;

        days.forEach(day => {
            contentRendered = true; // A day section will always be rendered
            const dayDisplayName = translations[day.nameKey]?.[currentLanguage] || translations[day.nameKey]?.['en'] || day.defaultName; // Added English fallback
            const daySectionDiv = document.createElement('div');
            daySectionDiv.className = 'day-section';
            daySectionDiv.innerHTML = `<h2>${dayDisplayName}</h2>`;

            const stateKey = `state${day.iscountedbyFlag.slice(-1)}`;

            if (useSmartSorting) {
                const grouped = {};
                allClasses.forEach(cls => {
                    const numberPart = cls.class.split('.')[0];
                    if (!grouped[numberPart]) grouped[numberPart] = [];
                    grouped[numberPart].push(cls);
                });

                const sortedGroupKeys = Object.keys(grouped).sort((a, b) => parseInt(a) - parseInt(b));

                sortedGroupKeys.forEach(key => {
                    const groupDiv = document.createElement('div');
                    groupDiv.style.marginBottom = "10px";

                    grouped[key].sort((a, b) => a.class.localeCompare(b.class));

                    grouped[key].forEach(cls => {
                        const link = document.createElement('a');
                        link.href = `index.html?class=${encodeURIComponent(cls.class)}&day=${day.defaultName.toLowerCase()}`;
                        link.textContent = cls.class;
                        link.className = 'class-button';

                        const stateValue = cls[stateKey];
                        if (stateValue === 'done') link.classList.add('class-button-done');
                        else if (stateValue === 'locked') link.classList.add('class-button-locked');

                        const overrideKey = 'override_' + day.defaultName.toLowerCase();
                        if (cls[overrideKey]) {
                            link.classList.add('class-button-locked');
                            link.style.pointerEvents = 'none';
                            link.style.opacity = '0.5';
                            link.removeAttribute('href');
                            link.title = 'Overridden by Admin';
                        }

                        groupDiv.appendChild(link);
                    });
                    daySectionDiv.appendChild(groupDiv);
                });
            } else {
                const ul = document.createElement('ul');
                ul.className = 'classList';
                // Display ALL classes from allClasses
                allClasses.sort((a, b) => a.class.localeCompare(b.class)).forEach(cls => {
                    const listItem = document.createElement('li');
                    const link = document.createElement('a');
                    link.href = `index.html?class=${encodeURIComponent(cls.class)}&day=${day.defaultName.toLowerCase()}`;
                    link.textContent = cls.class;

                    const stateValue = cls[stateKey];
                    if (stateValue === 'done') link.classList.add('class-button-done');
                    else if (stateValue === 'locked') link.classList.add('class-button-locked');

                    const overrideKey = 'override_' + day.defaultName.toLowerCase();
                    if (cls[overrideKey]) {
                        link.classList.add('class-button-locked');
                        link.style.pointerEvents = 'none';
                        link.style.opacity = '0.5';
                        link.removeAttribute('href');
                        link.title = 'Overridden by Admin';
                    }

                    listItem.appendChild(link);
                    ul.appendChild(listItem);
                });
                daySectionDiv.appendChild(ul);
            }
            fragment.appendChild(daySectionDiv);
        });
    }

    // Final check if nothing was rendered and no specific error message was already set for students
    if (!contentRendered && !errorMessage && !fragment.hasChildNodes()) {
        const lastResortPara = document.createElement('p');
        lastResortPara.textContent = translations.noClassesScheduledAdminText?.[currentLanguage] || translations.noClassesScheduledAdminText?.['en'] || 'No classes are scheduled...';
        fragment.appendChild(lastResortPara);
    }

    dynamicClassList.replaceChildren(fragment);
}

// --- Function to display logged-in username ---
function displayLoggedInUser() {
    const cookies = document.cookie.split('; ');
    const usernameCookie = cookies.find(row => row.startsWith('ColorDaysUser='));
    const usernameTextSpan = document.getElementById('usernameText');

    if (usernameCookie) {
        const username = usernameCookie.split('=')[1];
        usernameTextSpan.textContent = decodeURIComponent(username);
    } else { // This branch is for when the ColorDaysUser cookie is missing
        usernameTextSpan.textContent = translations.usernameNotLoggedIn?.[currentLanguage] || (translations.usernameNotLoggedIn?.[currentLanguage] || 'Not Logged In');
    }
}

// Helper function to get a specific cookie by name
function getCookie(name) {
    const nameEQ = name + "=";
    const ca = document.cookie.split(';');
    for (let i = 0; i < ca.length; i++) {
        let c = ca[i];
        while (c.charAt(0) === ' ') c = c.substring(1, c.length); // trim leading spaces
        if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length, c.length); // Return cookie value
    }
    return null; // Cookie not found
}

// --- Function to manage visibility of header buttons based on role ---
async function manageButtonVisibility() {
    console.log("--- manageButtonVisibility ---");
    const isStudent = getCookie("SQLAuthUserStudent") !== null;

    if (isStudent) {
        console.log("Student session detected. Keeping Classes, Config, Leaderboard and Change Password buttons hidden.");
        // They are already hidden by default in HTML (style="display: none;")
        return;
    }

    // Teachers/Admins reach here. Show the basic teacher buttons.
    console.log("Non-student session. Showing Classes, Leaderboard and Change Password buttons (initially).");
    if (classesButton) classesButton.style.display = 'inline-block';
    if (leaderboardButton) leaderboardButton.style.display = 'inline-block';
    
    // Check user info to see if we should show Change Password
    try {
        const meResponse = await fetch('/api/auth/me', { credentials: 'include' });
        if (meResponse.ok) {
            const meData = await meResponse.json();
            if (meData.is_oauth_user) {
                console.log("User is authenticated via Google OAuth. Hiding Change Password button.");
                if (changePasswordBtn) changePasswordBtn.style.display = 'none';
            } else {
                console.log("User is a regular user. Showing Change Password button.");
                if (changePasswordBtn) changePasswordBtn.style.display = 'inline-block';
            }
        } else {
             // Fallback if /api/auth/me fails
             if (changePasswordBtn) changePasswordBtn.style.display = 'inline-block';
        }
    } catch (error) {
        console.error("Error fetching user info for button visibility:", error);
        if (changePasswordBtn) changePasswordBtn.style.display = 'inline-block';
    }

    // Now check specifically for Config (only for administrators)
    try {
        const response = await fetch('/api/users', { credentials: 'include' });
        if (response.ok) {
            console.log("User is an admin. Showing Config button.");
            if (configButton) configButton.style.display = 'inline-block';
            const overridesButton = document.getElementById('overridesButton');
            if (overridesButton) overridesButton.style.display = 'inline-block';
        } else {
            console.log("User is not an admin. Config button remains hidden.");
            if (configButton) configButton.style.display = 'none';
            const overridesButton = document.getElementById('overridesButton');
            if (overridesButton) overridesButton.style.display = 'none';
        }
    } catch (error) {
        console.error("Error checking admin status:", error);
    }
    console.log("--- End manageButtonVisibility ---");
}




// --- Function to set language preference via backend ---
async function setLanguagePreference(lang) {
    console.log(`Setting language preference to: ${lang}`);
    try {
        const response = await fetch('/api/language/set', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ language: lang }),
            credentials: 'include' // Important for the server to set cookies for this origin
        });

        const result = await response.json();
        if (response.ok) {
            console.log(`Language successfully set to ${lang} via backend. Server message: ${result.message}`);
            const alertMessage = (translations.languageUpdateSuccessAlert?.[lang] || "Language preference updated to {lang}. You might need to reload the page for changes to take full effect.")
                .replace("{lang}", lang === 'cs' ? 'Čeština' : 'English');
            // alert(alertMessage); // Removed alert, page updates visually
            currentLanguage = lang; // Update current language
            applyTranslations(); // Re-apply translations to the page
            // Reload dynamic content that needs re-translation
            loadAndDisplayClasses();
            displayLoggedInUser();
        } else {
            console.error('Failed to set language preference:', response.status, result.error || (translations.unknownErrorText?.[currentLanguage] || 'Unknown server error'));
            alert((translations.languageUpdateFailedAlert?.[currentLanguage] || translations.languageUpdateFailedAlert?.['en'] || "Failed to set language: {error}").replace("{error}", result.error || (translations.serverErrorText?.[currentLanguage] || 'Server error'))); // Added English fallback
        }
    } catch (error) {
        console.error('Error during setLanguagePreference fetch:', error);
        alert(translations.languageUpdateErrorAlert?.[currentLanguage] || translations.languageUpdateErrorAlert?.['en'] || 'An error occurred while setting language preference. Please check your connection.'); // Added English fallback
    }
}

// --- Function to set the visual state of the language toggle ---
function setToggleState(lang) {
    if (toggleCs && toggleEn) {
        if (lang === 'cs') {
            toggleCs.classList.add('active');
            toggleEn.classList.remove('active');
        } else if (lang === 'en') {
            toggleEn.classList.add('active');
            toggleCs.classList.remove('active');
        } else {
            // Default to English if cookie is missing or invalid
            toggleEn.classList.add('active');
            toggleCs.classList.remove('active');
        }
    }
}

// Add event listeners for language toggle sides
if (languageToggle) {
    languageToggle.addEventListener('click', (event) => {
        const target = event.target;
        if (target.tagName === 'SPAN' && target.dataset.lang) {
            const selectedLang = target.dataset.lang;
            setLanguagePreference(selectedLang); // Call backend to set cookie
            setToggleState(selectedLang); // Update UI immediately
        }
    });
}

// Load classes when the page loads
document.addEventListener('DOMContentLoaded', () => {
    // Set currentLanguage from cookie first, so it's available for all subsequent calls
    currentLanguage = getCookie("language") || 'cs';

    // Check for forced password change
    if (getCookie("ChangePasswordVerificationNotNeeded")) {
        window.location.href = '/change-password.html';
        return;
    }

    fetchTranslations().then(() => { // Fetch translations first
        // applyTranslations has been called by fetchTranslations and used the currentLanguage set above.
        setToggleState(currentLanguage);
        loadAndDisplayClasses();
        displayLoggedInUser();
        manageButtonVisibility();

        // Fetch refresh interval and setup auto-refresh
        fetch('/api/config/refresh_intervals')
            .then(res => res.json())
            .then(intervals => {
                const interval = intervals['menu.html'];
                if (interval && interval > 0) {
                    setInterval(async () => {
                        try {
                            const response = await fetch('/api/data/version');
                            if (response.ok) {
                                const data = await response.json();
                                if (data.version !== currentDataVersion) {
                                    console.log(`Data version changed from ${currentDataVersion} to ${data.version}. Refreshing classes.`);
                                    loadAndDisplayClasses();
                                }
                            }
                        } catch (error) {
                            console.error("Error checking for data updates:", error);
                        }
                    }, interval);
                }
            })
            .catch(err => console.error("Error fetching refresh intervals:", err));
    });
});
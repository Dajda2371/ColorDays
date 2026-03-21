
// --- NAVBAR LOGIC ADDED ---
const logoutButton = document.getElementById('logoutButton');
const languageToggle = document.getElementById('languageToggle');
const toggleCs = document.getElementById('toggleCs');
const toggleEn = document.getElementById('toggleEn');

let translations = {};
let currentLanguage = 'cs';

async function handleLogout() {
    const confirmation = confirm(translations.logoutConfirmation?.[currentLanguage] || "Are you sure you want to log out?");
    if (!confirmation) return;

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
            applyTranslations(); window.location.reload();
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

// Wait for the HTML document to be fully loaded before running the script
document.addEventListener('DOMContentLoaded', (event) => {
    // Language Initialization
    currentLanguage = getCookie("language") || 'cs';
    fetchTranslations().then(() => {
        setToggleState(currentLanguage);
        displayLoggedInUser();
    });

    console.log("DOM fully loaded. Checking for cookie..."); // Log: DOM ready
    // --- Check for the password change cookie on page load ---
    const cookieName = "ChangePasswordVerificationNotNeeded";
    console.log("Current document.cookie:", document.cookie); // Log the raw cookie string

    // Try a simpler check first:
    if (document.cookie.indexOf(cookieName + '=') !== -1) {
        console.log("Cookie check PASSED."); // Add this log
        console.log(`Cookie '${cookieName}' found. Hiding old password field.`);
        const oldPasswordDiv = document.getElementById('oldPasswordContainer');
        const backButton = document.getElementById('backButton');
        if (oldPasswordDiv) {
            console.log("Found element #oldPasswordContainer. Setting display to none."); // Log: Element found
            oldPasswordDiv.style.display = 'none';
        } else {
            console.error("ERROR: Could not find element with ID 'oldPasswordContainer'!"); // Log: Element NOT found
        }
        if (backButton) {
            backButton.style.display = 'none';
        }
    }
    // --- End cookie check ---

    // Assuming the form ID in change-password.html is 'changePasswordForm'
    const changePasswordForm = document.getElementById('changePasswordForm');
    // Get references to the input fields
    const oldPasswordInput = document.getElementById('old_password'); // Added reference for old password
    const newPasswordInput = document.getElementById('new_password'); // Corrected ID based on HTML
    // Assuming the error message div ID is 'errorMessage'
    const errorMessageDiv = document.getElementById('error-message'); // Corrected ID based on HTML

    // Only add the submit listener *after* the DOM is loaded
    if (changePasswordForm) {
        changePasswordForm.addEventListener('submit', async function (event) {
            event.preventDefault(); // Prevent default form submission

            // Read values from the input fields
            const oldPassword = oldPasswordInput.value; // Read the old password
            const newPassword = newPasswordInput.value;
            // Since we are sending the old password, we need verification
            const verificationNeeded = true;

            // Clear previous error messages
            errorMessageDiv.textContent = '';

            const cookies = document.cookie.split('; ');
            const usernameCookie = cookies.find(row => row.startsWith('ColorDaysUser='));
            const currentUsername = usernameCookie ? decodeURIComponent(usernameCookie.split('=')[1]) : '';

            try {
                const response = await fetch('/api/auth/change', { // Send request to the backend endpoint
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        // Body should be outside the headers object
                    },
                    // Send old password, new password, and verification flag
                    body: JSON.stringify({ username: currentUsername, old_password: oldPassword, new_password: newPassword }),
                });

                const result = await response.json(); // Parse the JSON response from the server

                if (response.ok && result.success) {
                    // Password change successful
                    console.log('Password change successful!');
                    // Redirect to the main application page
                    window.location.href = 'menu.html'; // Redirect to menu.html in the same directory
                } else {
                    // Login failed - display error message from server
                    console.error('Password change failed:', result.message);
                    errorMessageDiv.textContent = result.message || (translations.invalidPasswordError?.[currentLanguage] || 'Invalid password.');
                }

            } catch (error) {
                // Handle network errors or issues reaching the server
                console.error('Change password request failed:', error);
                errorMessageDiv.textContent = (translations.changePasswordRequestFailed?.[currentLanguage] || 'Change password request failed. Please check your connection or contact support.');
            }
        });
    } else {
        console.error("Could not find the change password form element!");
    }
}); // End of DOMContentLoaded listener
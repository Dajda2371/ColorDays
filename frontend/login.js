
// --- LANGUAGE LOGIC ADDED ---
const languageToggle = document.getElementById('languageToggle');
const toggleCs = document.getElementById('toggleCs');
const toggleEn = document.getElementById('toggleEn');

let translations = {};
let currentLanguage = 'en';

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

    // Translate Google button if it exists
    const googleBtn = document.querySelector('.google-btn');
    if (googleBtn) {
        const span = googleBtn.querySelector('span');
        if (span) {
            span.textContent = translations.googleLoginBtnText?.[currentLanguage] || translations.googleLoginBtnText?.['en'] || "Login with Google";
        }
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
// --- END LANGUAGE LOGIC ---

document.addEventListener('DOMContentLoaded', function () {

    // Language Initialization
    currentLanguage = getCookie("language") || 'en';
    fetchTranslations().then(() => {
        setToggleState(currentLanguage);
    });

    const teacherLoginForm = document.getElementById('loginForm'); // Teacher login form
    const studentLoginForm = document.getElementById('studentLoginForm'); // Student login form
    const errorMessageDiv = document.getElementById('error-message');

    // Function to display error messages
    function displayError(message) {
        errorMessageDiv.textContent = message;
        errorMessageDiv.style.display = 'block'; // Make sure it's visible
    }

    // Function to clear error messages
    function clearError() {
        errorMessageDiv.textContent = '';
        errorMessageDiv.style.display = 'none';
    }

    // --- Teacher Login Logic ---
    if (teacherLoginForm) {
        teacherLoginForm.addEventListener('submit', function (event) {
            event.preventDefault(); // Prevent default form submission
            clearError(); // Clear previous errors

            const username = teacherLoginForm.username.value;
            const password = teacherLoginForm.password.value;

            fetchWithCredentials('/login', { username, password }, 'Teacher');
        });
    }

    // --- Student Login Logic ---
    if (studentLoginForm) {
        studentLoginForm.addEventListener('submit', function (event) {
            event.preventDefault(); // Prevent default form submission
            clearError(); // Clear previous errors

            const code = studentLoginForm.code.value;

            if (!code) {
                displayError((translations.enterStudentCodeError?.[currentLanguage] || 'Please enter your student code.'));
                return;
            }

            fetchWithCredentials('/login/student', { code }, 'Student');
        });
    }

    // --- Generic Fetch Function for Login ---
    function fetchWithCredentials(endpoint, bodyPayload, userType) {
        fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(bodyPayload),
            credentials: 'include' // Crucial for sending and receiving cookies
        })
            .then(response => {
                if (!response.ok) {
                    // Attempt to parse error from JSON body, then throw
                    return response.json().then(errData => {
                        const error = new Error(errData.error || `HTTP error! status: ${response.status}`);
                        error.data = errData; // Attach full error data if needed
                        throw error;
                    }).catch(() => {
                        // If response.json() fails (e.g., not JSON), throw a generic error
                        throw new Error(`${userType} login failed. Server returned status: ${response.status}`);
                    });
                }
                return response.json(); // Assuming success response is JSON
            })
            .then(data => {
                if (data.success) {
                    console.log(`${userType} login successful:`, data);
                    window.location.href = '/menu.html'; // Redirect on success
                } else {
                    displayError(data.error || `${userType}${translations.loginFailedTryAgainError?.[currentLanguage] || " login failed. Please try again."}`);
                }
            })
            .catch(error => {
                console.error(`${userType} login error:`, error);
                const serverErrorMessage = error.data ? error.data.error : null;
                displayError(serverErrorMessage || error.message || `${translations.unexpectedLoginError?.[currentLanguage] || "An unexpected error occurred during "}${userType.toLowerCase()} login.`);
            });
    }

    // --- Auto-login with code from URL parameter ---
    const urlParams = new URLSearchParams(window.location.search);
    const codeParam = urlParams.get('code');
    const errorParam = urlParams.get('error');

    if (errorParam === 'invalid_domain') {
        alert((translations.invalidGoogleDomainAlert?.[currentLanguage] || 'Tato e-mailová doména není pro Google přihlášení povolena.'));
    }

    if (codeParam) {
        console.log('Auto-login: Code parameter detected:', codeParam);
        // Fill in the student code field
        if (studentLoginForm && studentLoginForm.code) {
            studentLoginForm.code.value = codeParam;
        }
        // Automatically attempt login
        clearError();
        fetchWithCredentials('/login/student', { code: codeParam }, 'Student');
    }
});
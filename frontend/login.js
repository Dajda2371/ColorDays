document.addEventListener('DOMContentLoaded', function () {
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
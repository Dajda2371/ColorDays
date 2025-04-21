const loginForm = document.getElementById('loginForm');
const usernameInput = document.getElementById('username');
const oldPasswordInput = document.getElementById('old_password');
const newPasswordInput = document.getElementById('new_password');
const errorMessageDiv = document.getElementById('error-message');

changePasswordForm.addEventListener('submit', async function(event) {
    event.preventDefault(); // Prevent default form submission

    const username = usernameInput.value;
    const oldPassword = oldPasswordInput.value;
    const newPassword = passwordInput.value;
    const verificationNeeded = true; // Set to true if verification is needed

    // Clear previous error messages
    errorMessageDiv.textContent = '';

    try {
        const response = await fetch('/api/auth/change', { // Send request to the backend endpoint
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                body: JSON.stringify({ username, oldPassword: oldPassword, newPassword: newPassword, verificationNeeded: verificationNeeded })
            },
            body: JSON.stringify({ username: username, oldPassword: oldPassword, newPassword: newPassword, verificationNeeded: verificationNeeded }), // Send data as JSON
        });

        const result = await response.json(); // Parse the JSON response from the server

        if (response.ok && result.success) {
            // Login successful
            console.log('Password change successful!');
            // Redirect to the main application page
            window.location.href = 'menu.html'; // Redirect to menu.html in the same directory
        } else {
            // Login failed - display error message from server
            console.error('Password change failed:', result.message);
            errorMessageDiv.textContent = result.message || 'Invalid password.';
        }

    } catch (error) {
        // Handle network errors or issues reaching the server
        console.error('Change password request failed:', error);
        errorMessageDiv.textContent = 'Change password request failed. Please check your connection or contact support.';
    }
});
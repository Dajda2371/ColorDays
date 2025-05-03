// Assuming the form ID in change-password.html is 'changePasswordForm'
const changePasswordForm = document.getElementById('changePasswordForm');
// Get references to the input fields
const oldPasswordInput = document.getElementById('old_password'); // Added reference for old password
const newPasswordInput = document.getElementById('new_password'); // Corrected ID based on HTML
// Assuming the error message div ID is 'errorMessage'
const errorMessageDiv = document.getElementById('error-message'); // Corrected ID based on HTML

changePasswordForm.addEventListener('submit', async function(event) {
    event.preventDefault(); // Prevent default form submission

    // Read values from the input fields
    const oldPassword = oldPasswordInput.value; // Read the old password
    const newPassword = newPasswordInput.value;
    // Since we are sending the old password, we need verification
    const verificationNeeded = true;

    // Clear previous error messages
    errorMessageDiv.textContent = '';

    try {
        const response = await fetch('/api/auth/change', { // Send request to the backend endpoint
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                // Body should be outside the headers object
            },
            // Send old password, new password, and verification flag
            body: JSON.stringify({ oldPassword: oldPassword, newPassword: newPassword, verificationNeeded: verificationNeeded }),
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
            errorMessageDiv.textContent = result.message || 'Invalid password.';
        }

    } catch (error) {
        // Handle network errors or issues reaching the server
        console.error('Change password request failed:', error);
        errorMessageDiv.textContent = 'Change password request failed. Please check your connection or contact support.';
    }
});
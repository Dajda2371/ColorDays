// Assuming the form ID in change-password.html is 'changePasswordForm'
const changePasswordForm = document.getElementById('changePasswordForm');
// Assuming the new password input ID is 'newPassword'
const newPasswordInput = document.getElementById('newPassword');
// Assuming the error message div ID is 'errorMessage'
const errorMessageDiv = document.getElementById('errorMessage');

changePasswordForm.addEventListener('submit', async function(event) {
    event.preventDefault(); // Prevent default form submission

    // We only need the new password in the forced change flow
    const newPassword = newPasswordInput.value;
    // const verificationNeeded = false; // Set to false for the forced change flow

    // Clear previous error messages
    errorMessageDiv.textContent = '';

    try {
        const response = await fetch('/api/auth/change', { // Send request to the backend endpoint
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                // Body should be outside the headers object
            },
            // Send only the new password and verificationNeeded flag
            body: JSON.stringify({ newPassword: newPassword, verificationNeeded: verificationNeeded }),
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
        } // Make sure the IDs match your HTML ('newPassword', 'errorMessage', 'changePasswordForm')

    } catch (error) {
        // Handle network errors or issues reaching the server
        console.error('Change password request failed:', error);
        errorMessageDiv.textContent = 'Change password request failed. Please check your connection or contact support.';
    }
});
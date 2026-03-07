// Wait for the HTML document to be fully loaded before running the script
document.addEventListener('DOMContentLoaded', (event) => {
    console.log("DOM fully loaded. Checking for cookie..."); // Log: DOM ready
    // --- Check for the password change cookie on page load ---
    const cookieName = "ChangePasswordVerificationNotNeeded";
    console.log("Current document.cookie:", document.cookie); // Log the raw cookie string

    // Try a simpler check first:
    if (document.cookie.indexOf(cookieName + '=') !== -1) {
        console.log("Cookie check PASSED."); // Add this log
        console.log(`Cookie '${cookieName}' found. Hiding old password field.`);
        const oldPasswordDiv = document.getElementById('oldPasswordContainer');
        if (oldPasswordDiv) {
            console.log("Found element #oldPasswordContainer. Setting display to none."); // Log: Element found
            oldPasswordDiv.style.display = 'none';
        } else {
            console.error("ERROR: Could not find element with ID 'oldPasswordContainer'!"); // Log: Element NOT found
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
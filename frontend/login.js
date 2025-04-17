const loginForm = document.getElementById('loginForm');
const usernameInput = document.getElementById('username');
const passwordInput = document.getElementById('password');
const errorMessageDiv = document.getElementById('error-message');

loginForm.addEventListener('submit', async function(event) {
    event.preventDefault(); // Prevent default form submission

    const username = usernameInput.value;
    const password = passwordInput.value;

    // Clear previous error messages
    errorMessageDiv.textContent = '';

    try {
        const response = await fetch('/login', { // Send request to the backend endpoint
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username: username, password: password }), // Send data as JSON
        });

        const result = await response.json(); // Parse the JSON response from the server

        if (response.ok && result.success) {
            // Login successful
            console.log('Login successful!');
            // Redirect to the main application page
            window.location.href = 'menu.html'; // Redirect to index.html in the same directory
        } else {
            // Login failed - display error message from server
            console.error('Login failed:', result.message);
            errorMessageDiv.textContent = result.message || 'Invalid username or password.';
        }

    } catch (error) {
        // Handle network errors or issues reaching the server
        console.error('Login request failed:', error);
        errorMessageDiv.textContent = 'Login request failed. Please check your connection or contact support.';
    }
});
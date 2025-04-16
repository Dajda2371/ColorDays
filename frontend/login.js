// login.js

// --- VERY IMPORTANT ---
// This is a MOCK login for demonstration only.
// Storing credentials directly in JavaScript is INSECURE.
// Real applications MUST validate credentials on a server.
const validUsername = 'admin';
const validPassword = 'password123'; // Never do this in production!

const loginForm = document.getElementById('loginForm');
const usernameInput = document.getElementById('username');
const passwordInput = document.getElementById('password');
const errorMessageDiv = document.getElementById('error-message');

loginForm.addEventListener('submit', function(event) {
    event.preventDefault(); // Prevent the default form submission

    const enteredUsername = usernameInput.value;
    const enteredPassword = passwordInput.value;

    // Clear previous error messages
    errorMessageDiv.textContent = '';

    // Simulate checking credentials (INSECURE - for demo only)
    if (enteredUsername === validUsername && enteredPassword === validPassword) {
        // Login successful
        console.log('Login successful!');
        // Redirect to the main page
        window.location.href = 'index.html';
    } else {
        // Login failed
        console.log('Login failed!');
        errorMessageDiv.textContent = 'Invalid username or password.';
    }
});

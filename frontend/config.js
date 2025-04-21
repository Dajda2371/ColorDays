let users = {};

async function fetchUsers() {
  const res = await fetch('/list_users');
  const users = await res.json();
  const userList = document.getElementById('userList');
  userList.innerHTML = '';
  users.forEach(user => {
    const li = document.createElement('li');
    li.textContent = user;
    userList.appendChild(li);
  });
}
  
function renderUsers() {
  const tbody = document.getElementById("userTableBody");
  tbody.innerHTML = "";

  Object.entries(users).forEach(([username, info]) => {
    const tr = document.createElement("tr");

    let status;

    if (!info.password) {
      status = "not set";
    } else if (info.password === "_NULL_") {
      status = "not set";
    } else {
      status = "set";
    }

    tr.innerHTML = `
      <td>${username}</td>
      <td>${status}</td>
      <td>
        ${
          status === "not set" || /^[a-zA-Z0-9]{10}$/.test(info.password)
            ? `<button onclick="setPassword('${username}')">Set Password</button>`
            : `<button onclick="resetPassword('${username}')">Reset Password</button>`
        }
        ${
          username !== "admin"
            ? `<button onclick="removeUser('${username}')">Remove</button>`
            : ""
        }
      </td>
    `;

    tbody.appendChild(tr);
  });
}

async function loadUsers() {
  const res = await fetch("/api/users");
  const data = await res.json();
  users = {};
  data.forEach(user => {
    users[user.username] = { password: user.password };
  });
  renderUsers();
}

async function addUser() {
  const username = prompt("Enter new username:");
  // Basic validation for username
  if (!username) { // Check if prompt was cancelled or empty
    alert("Username cannot be empty.");
    return;
  }
  // Check if username already exists (using the locally loaded 'users' object)
  // Note: This check is based on the last 'loadUsers' call, might be slightly stale.
  if (users[username]) {
    alert("Username already exists locally. Refresh if needed."); // Clarified message
    return;
  }

  // const password = null; // Set password to null initially

  try { // Added try...catch for fetch errors
    const res = await fetch("/add_user", { // Target the correct endpoint
      method: "POST",
      headers: { "Content-Type": "application/json" },
      // --- MODIFIED: Include password in the body ---
      body: JSON.stringify({ username, password: null }) // Send null password
      // --- END MODIFIED ---
    });

    // Improved response handling
    if (res.ok) {
      let successMessage = "User added successfully!";
      try {
        const result = await res.json(); // Attempt to parse success response
        if (result && result.message) {
          successMessage = result.message;
        }
      } catch (e) { /* Ignore if response not JSON */ }
      alert(successMessage);
      loadUsers(); // Refresh the user list on success
    } else {
      // Attempt to get error message from backend
      let errorMessage = "Failed to add user";
      try {
        const errorData = await res.json();
        if (errorData && errorData.error) {
          errorMessage = `Failed to add user: ${errorData.error}`;
        }
      } catch (e) { /* Ignore if response not JSON */ }
      alert(errorMessage + ` (Status: ${res.status})`);
    }
  } catch (error) {
      console.error("Network or other error adding user:", error);
      alert("An error occurred while trying to add the user. Check the console.");
  }
}

async function removeUser(username) {
  if (!confirm(`Remove user ${username}?`)) return;
  const res = await fetch("/api/users/remove", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username })
  });
  if (res.ok) loadUsers();
  else alert("Failed to remove user");
}

function generatePassword(length = 10) {
  const chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
  return Array.from({ length }, () => chars[Math.floor(Math.random() * chars.length)]).join("");
}

async function resetPassword(username) {
  const newPassword = generatePassword();
  const res = await fetch("/api/users/reset", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, new_password: newPassword })
  });
  if (res.ok) loadUsers();
  else alert("Failed to reset password");
}
  
async function changePassword() {
  const username = document.getElementById('changeUsername').value.trim();
  const password = document.getElementById('changePassword').value;

  if (!username || !password) return alert("Username and new password required.");

  const res = await fetch('/change_password', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  });

  const data = await res.json();
  alert(data.message);
}

// Load user list on page load
loadUsers();
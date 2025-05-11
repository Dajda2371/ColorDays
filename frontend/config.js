let users = {};
let currentClasses = []; // For storing class data

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
    } else if (info.password === "not_set") {
      status = "not set";
    } else if (info.password === "set") {
      status = "set";
    } else if (info.password === "google_auth_user") {
        status = "Google Auth";
    } else {
      status = info.password;
    }

    tr.innerHTML = `
      <td>${username}</td>
      <td>${status}</td>
      <td>
        ${
          status === "not set" && status !== "Google Auth" // || /^[a-zA-Z0-9]{10}$/.test(info.password)
            ? `<button onclick="setPassword('${username}')">Set Password</button>`
            : status === "Google Auth"
              ? ``
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

async function setPassword(username) {
  const newPassword = generatePassword();
  const res = await fetch("/api/users/set", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, new_password: newPassword })
  });
  if (res.ok) loadUsers();
  else alert("Failed to reset password");
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

// --- Class Management Functions ---

function renderClasses() {
  const tbody = document.getElementById("classTableBody");
  tbody.innerHTML = ""; // Clear existing rows

  currentClasses.forEach(cls => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${cls.class}</td>
      <td>${cls.teacher}</td>
      <td>
        <input type="checkbox" ${cls.counts1 === 'T' ? 'checked' : ''} onchange="updateClassCount('${cls.class}', 'counts1', this.checked)" />
        <input type="checkbox" ${cls.couts2 === 'T' ? 'checked' : ''} onchange="updateClassCount('${cls.class}', 'couts2', this.checked)" /> 
        <input type="checkbox" ${cls.couts3 === 'T' ? 'checked' : ''} onchange="updateClassCount('${cls.class}', 'couts3', this.checked)" />
      </td>
      <td>
        <button onclick="promptRemoveClass('${cls.class}')">Remove</button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

async function loadClasses() {
  try {
    const res = await fetch("/api/classes");
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({ error: "Failed to fetch classes" }));
      throw new Error(errorData.error || `HTTP error! status: ${res.status}`);
    }
    currentClasses = await res.json();
    renderClasses();
  } catch (error) {
    console.error("Error loading classes:", error);
    alert(`Error loading classes: ${error.message}`);
    // Optionally clear the table or show an error message in the table
    document.getElementById("classTableBody").innerHTML = '<tr><td colspan="4">Error loading classes.</td></tr>';
  }
}

async function addClass() {
  const className = prompt("Enter new class name (e.g., 2.A):");
  if (!className) return; // User cancelled or entered empty

  const teacher = prompt("Enter teacher's name for class " + className + ":");
  if (!teacher) return; // User cancelled or entered empty

  // For simplicity, new classes default to all counts 'F'
  const newClassData = {
    class: className.trim(),
    teacher: teacher.trim(),
    counts1: 'F',
    couts2: 'F', // Ensure key matches backend/SQL ('couts2')
    couts3: 'F'  // Ensure key matches backend/SQL ('couts3')
  };

  try {
    const res = await fetch("/api/classes/add", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(newClassData)
    });

    const result = await res.json();
    if (res.ok) {
      alert(result.message || "Class added successfully!");
      loadClasses(); // Refresh the class list
    } else {
      alert(`Failed to add class: ${result.error || `Server error (Status: ${res.status})`}`);
    }
  } catch (error) {
    console.error("Error adding class:", error);
    alert("An error occurred while trying to add the class. Check the console.");
  }
}

async function promptRemoveClass(className) {
  if (!confirm(`Are you sure you want to remove class "${className}"?`)) return;

  try {
    const res = await fetch("/api/classes/remove", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ class: className })
    });

    const result = await res.json();
    if (res.ok) {
      alert(result.message || "Class removed successfully!");
      loadClasses(); // Refresh the class list
    } else {
      alert(`Failed to remove class: ${result.error || `Server error (Status: ${res.status})`}`);
    }
  } catch (error) {
    console.error("Error removing class:", error);
    alert("An error occurred while trying to remove the class. Check the console.");
  }
}

async function updateClassCount(className, countField, isChecked) {
  const value = isChecked ? 'T' : 'F';
  console.log(`Updating class: ${className}, field: ${countField}, new value: ${value}`);

  try {
    const res = await fetch("/api/classes/update_counts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ class: className, countField: countField, value: value })
    });

    const result = await res.json();
    if (res.ok) {
      // Update local store to reflect change immediately
      const classToUpdate = currentClasses.find(c => c.class === className);
      if (classToUpdate) {
        classToUpdate[countField] = value;
      }
      // No need to re-render the whole table if only one checkbox changed,
      // but if you prefer full consistency or server might do more, uncomment loadClasses()
      // renderClasses(); // Or just let the checkbox state be the source of truth visually
      console.log(result.message || "Class count updated successfully on server.");
    } else {
      alert(`Failed to update class count: ${result.error || `Server error (Status: ${res.status})`}`);
      // On error, reload classes to ensure UI consistency with the server state
      loadClasses();
    }
  } catch (error) {
    console.error("Error updating class count:", error);
    alert("An error occurred while trying to update the class count. Check the console.");
    // On error, reload classes to ensure UI consistency
    loadClasses();
  }
}

// Load user list on page load
loadUsers();
loadClasses(); // Load class list on page load
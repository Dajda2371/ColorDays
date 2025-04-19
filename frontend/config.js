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

    const status = !info.password
      ? "not set"
      : /^[a-zA-Z0-9]{10}$/.test(info.password)
      ? info.password
      : "set";

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
  if (!username || users[username]) {
    alert("Invalid or existing username.");
    return;
  }
  const res = await fetch("/api/users", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username })
  });
  if (res.ok) loadUsers();
  else alert("Failed to add user");
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
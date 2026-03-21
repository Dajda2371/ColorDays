
// --- NAVBAR LOGIC ADDED ---
const logoutButton = document.getElementById('logoutButton');
const languageToggle = document.getElementById('languageToggle');
const toggleCs = document.getElementById('toggleCs');
const toggleEn = document.getElementById('toggleEn');

let translations = {};
let currentLanguage = 'cs';

async function handleLogout() {
    const confirmation = confirm(translations.logoutConfirmation?.[currentLanguage] || "Are you sure you want to log out?");
    if (!confirmation) return;

    try {
        const response = await fetch('/logout', {
            method: 'POST',
            credentials: 'include'
        });
        if (response.ok) {
            window.location.href = '/login.html';
        } else {
            alert((translations.logoutFailedAlert?.[currentLanguage] || 'Logout failed'));
        }
    } catch (error) {
        alert((translations.logoutErrorAlert?.[currentLanguage] || 'An error occurred during logout.'));
    }
}

if (logoutButton) {
    logoutButton.addEventListener('click', handleLogout);
}

async function fetchTranslations() {
    try {
        const response = await fetch('/api/translations');
        if (!response.ok) return;
        translations = await response.json();
        applyTranslations();
    } catch (error) {
        console.error('Error fetching translations:', error);
    }
}

function applyTranslations() {
    document.querySelectorAll('[data-translate-key]').forEach(element => {
        const key = element.getAttribute('data-translate-key');
        const text = translations[key]?.[currentLanguage] || translations[key]?.['en'];
        if (text) {
            if (element.tagName === 'INPUT') {
                element.placeholder = text;
            } else {
                element.textContent = text;
            }
        }
    });
}

function displayLoggedInUser() {
    const cookies = document.cookie.split('; ');
    const usernameCookie = cookies.find(row => row.startsWith('ColorDaysUser='));
    const usernameTextSpan = document.getElementById('usernameText');
    if (usernameCookie && usernameTextSpan) {
        const username = usernameCookie.split('=')[1];
        usernameTextSpan.textContent = decodeURIComponent(username);
    } else if (usernameTextSpan) {
        usernameTextSpan.textContent = translations.usernameNotLoggedIn?.[currentLanguage] || (translations.usernameNotLoggedIn?.[currentLanguage] || 'Not Logged In');
    }
}

function getCookie(name) {
    const nameEQ = name + "=";
    const ca = document.cookie.split(';');
    for (let i = 0; i < ca.length; i++) {
        let c = ca[i];
        while (c.charAt(0) === ' ') c = c.substring(1, c.length);
        if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length, c.length);
    }
    return null;
}

async function setLanguagePreference(lang) {
    try {
        const response = await fetch('/api/language/set', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ language: lang }),
            credentials: 'include'
        });
        if (response.ok) {
            currentLanguage = lang;
            applyTranslations(); window.location.reload(); window.location.reload();
            displayLoggedInUser();
        }
    } catch (error) {
        console.error('Error setting language:', error);
    }
}

function setToggleState(lang) {
    if (toggleCs && toggleEn) {
        if (lang === 'cs') {
            toggleCs.classList.add('active');
            toggleEn.classList.remove('active');
        } else {
            toggleEn.classList.add('active');
            toggleCs.classList.remove('active');
        }
    }
}

if (languageToggle) {
    languageToggle.addEventListener('click', (event) => {
        const target = event.target;
        if (target.tagName === 'SPAN' && target.dataset.lang) {
            const selectedLang = target.dataset.lang;
            setLanguagePreference(selectedLang);
            setToggleState(selectedLang);
        }
    });
}
// --- END NAVBAR LOGIC ---

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
  
  const cookies = document.cookie.split('; ');
  const usernameCookie = cookies.find(row => row.startsWith('ColorDaysUser='));
  let currentUser = usernameCookie ? decodeURIComponent(usernameCookie.split('=')[1]) : null;

  Object.entries(users).forEach(([username, info]) => {
    const tr = document.createElement("tr");

    let status;

    if (!info.password) {
      status = (translations.notSetStatus?.[currentLanguage] || "not set");
    } else if (info.password === "not_set") {
      status = (translations.notSetStatus?.[currentLanguage] || "not set");
    } else if (info.password === (translations.setStatus?.[currentLanguage] || "set")) {
      status = (translations.setStatus?.[currentLanguage] || "set");
    } else if (info.password === "google_auth_user") {
      status = (translations.googleAuthStatus?.[currentLanguage] || "Google Auth");
    } else {
      status = info.password;
    }

    let roleSelectHtml = '';
    if (username === 'admin' || username === currentUser) {
        roleSelectHtml = `<select disabled><option>${info.role || 'teacher'}</option></select>`;
    } else {
        roleSelectHtml = `
            <select onchange="changeRole('${username}', this.value)">
                <option value="teacher" ${info.role === 'teacher' ? 'selected' : ''}>Teacher</option>
                <option value="admin" ${info.role === 'admin' ? 'selected' : ''}>Admin</option>
            </select>
        `;
    }

    tr.innerHTML = `
      <td>${username}</td>
      <td>${status}</td>
      <td>${roleSelectHtml}</td>
      <td>
        ${status === (translations.notSetStatus?.[currentLanguage] || "not set") && status !== (translations.googleAuthStatus?.[currentLanguage] || "Google Auth") // || /^[a-zA-Z0-9]{10}$/.test(info.password)
        ? `<button onclick="setPassword('${username}')">${translations.setPasswordBtnText?.[currentLanguage] || 'Set Password'}</button>`
        : status === (translations.googleAuthStatus?.[currentLanguage] || "Google Auth")
          ? ``
          : `<button onclick="resetPassword('${username}')">${translations.resetPasswordBtnText?.[currentLanguage] || 'Reset Password'}</button>`
      }
        ${username !== "admin"
        ? `<button onclick="removeUser('${username}')">${translations.removeBtnText?.[currentLanguage] || 'Remove'}</button>`
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
    users[user.username] = { password: user.password, role: user.role };
  });
  renderUsers();
}

async function addUser() {
  const username = prompt((translations.enterNewUsernamePrompt?.[currentLanguage] || "Enter new username:"));
  // Basic validation for username
  if (!username) { // Check if prompt was cancelled or empty
    alert((translations.usernameEmptyError?.[currentLanguage] || "Username cannot be empty."));
    return;
  }
  // Check if username already exists (using the locally loaded 'users' object)
  // Note: This check is based on the last 'loadUsers' call, might be slightly stale.
  if (users[username]) {
    alert((translations.usernameExistsError?.[currentLanguage] || "Username already exists locally. Refresh if needed.")); // Clarified message
    return;
  }

  // const password = null; // Set password to null initially

  try { // Added try...catch for fetch errors
    const res = await fetch("/api/users", { // Target the correct endpoint
      method: "POST",
      headers: { "Content-Type": "application/json" },
      // --- MODIFIED: Include password in the body ---
      body: JSON.stringify({ username, password: null }) // Send null password
      // --- END MODIFIED ---
    });

    // Improved response handling
    if (res.ok) {
      let successMessage = (translations.userAddedSuccess?.[currentLanguage] || "User added successfully!");
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
      let errorMessage = (translations.failedAddUser?.[currentLanguage] || "Failed to add user");
      try {
        const errorData = await res.json();
        if (errorData && errorData.error) {
          errorMessage = `${translations.failedAddUserPrefix?.[currentLanguage] || "Failed to add user: "}${errorData.error}`;
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
  if (!confirm(`${translations.confirmRemoveUser?.[currentLanguage] || "Remove user "}${username}?`)) return;
  const res = await fetch(`/api/users?username=${encodeURIComponent(username)}`, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" }
  });
  if (res.ok) loadUsers();
  else alert((translations.failedRemoveUser?.[currentLanguage] || "Failed to remove user"));
}

function generatePassword(length = 10) {
  const chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
  return Array.from({ length }, () => chars[Math.floor(Math.random() * chars.length)]).join("");
}

async function setPassword(username) {
  const newPassword = generatePassword();
  const res = await fetch("/api/users", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, new_password: newPassword })
  });
  if (res.ok) loadUsers();
  else alert((translations.failedResetPassword?.[currentLanguage] || "Failed to reset password"));
}

async function resetPassword(username) {
  const newPassword = generatePassword();
  const res = await fetch("/api/users", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, new_password: newPassword })
  });
  if (res.ok) loadUsers();
  else alert((translations.failedResetPassword?.[currentLanguage] || "Failed to reset password"));
}

async function changePassword() {
  const username = document.getElementById('changeUsername').value.trim();
  const password = document.getElementById('changePassword').value;

  if (!username || !password) return alert((translations.usernamePasswordRequired?.[currentLanguage] || "Username and new password required."));

  const res = await fetch('/change_password', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  });

  const data = await res.json();
  alert(data.message);
}

async function changeRole(username, newRole) {
  if (!confirm(`Are you sure you want to change role for ${username} to ${newRole}?`)) {
    loadUsers(); // revert select UI if cancelled
    return;
  }
  
  try {
    const res = await fetch("/api/users/role", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, role: newRole })
    });
    const result = await res.json();
    if (res.ok && result.success) {
      loadUsers();
    } else {
      alert(result.detail || result.error || "Failed to update role");
      loadUsers();
    }
  } catch (err) {
    console.error(err);
    alert("Error updating role");
    loadUsers();
  }
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
      <td class="narrow-col">
        <div style="display: flex; justify-content: center; align-items: center; white-space: nowrap;">
          <input type="checkbox" ${cls.counts1 === 'T' ? 'checked' : ''} onchange="updateClassCount('${cls.class}', 'counts1', this.checked)" />
          <input type="checkbox" ${cls.counts2 === 'T' ? 'checked' : ''} onchange="updateClassCount('${cls.class}', 'counts2', this.checked)" />
          <input type="checkbox" ${cls.counts3 === 'T' ? 'checked' : ''} onchange="updateClassCount('${cls.class}', 'counts3', this.checked)" />
        </div>
      </td>
      <td>
        <button onclick="promptRemoveClass('${cls.class}')">Remove</button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function handleAddClassRow() {
  const tbody = document.getElementById("classTableBody");
  // Check if adding row already exists
  if (document.getElementById("addClassRow")) return;

  const addRow = document.createElement("tr");
  addRow.id = "addClassRow";
  addRow.innerHTML = `
      <td><input type="text" id="newClassName" placeholder="${translations.newClassPlaceholder?.[currentLanguage] || 'New Class (e.g. 1.A)'}" /></td>
      <td><input type="text" id="newClassTeacher" placeholder="${translations.teacherNamePlaceholder?.[currentLanguage] || 'Teacher Name'}" /></td>
      <td class="narrow-col">
        <!-- Counts are always F initially, saved on click later if needed, but here we just create class -->
        <div style="display: flex; justify-content: center; align-items: center; white-space: nowrap;">
          <input type="checkbox" disabled />
          <input type="checkbox" disabled />
          <input type="checkbox" disabled />
        </div>
      </td>
      <td>
        <button onclick="saveNewClass()">Save</button>
        <button onclick="cancelAddClass()">Cancel</button>
      </td>
    `;
  tbody.appendChild(addRow);
}

function cancelAddClass() {
  const row = document.getElementById("addClassRow");
  if (row) row.remove();
}


function prefillClasses() {
  if (!confirm((translations.confirmScrapeClasses?.[currentLanguage] || "Are you sure you want to scrape classes from the school website? This will add any new classes found."))) return;

  // Find the button if clicked, or just do general logic
  // Since we call this from onclick in HTML, we don't necessarily have the event object passed automatically unless we pass it.
  // Let's assume we find it by text or just show global loading.
  // Simpler: Just allow it to run.

  fetch("/api/classes/prefill", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({})
  })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        alert(data.message);
        loadClasses();
      } else {
        alert("Error: " + (data.error || "Unknown error"));
      }
    })
    .catch(err => {
      console.error(err);
      alert("Error contacting server.");
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
    // Show error in a non-blocking way if possible, or keep alert if critical for now.
    // Ideally we'd have a status div.
    console.log(`Error loading classes: ${error.message}`);
    // Optionally clear the table or show an error message in the table
    document.getElementById("classTableBody").innerHTML = '<tr><td colspan="4">Error loading classes.</td></tr>';
  }
}

async function saveNewClass() {
  const nameInput = document.getElementById("newClassName");
  const teacherInput = document.getElementById("newClassTeacher");

  const className = nameInput.value.trim();
  const teacher = teacherInput.value.trim();

  if (!className) {
    alert((translations.pleaseEnterClassName?.[currentLanguage] || "Please enter a class name."));
    return;
  }
  // Allow empty teacher

  // For simplicity, new classes default to all counts 'F'
  const newClassData = {
    class: className,
    teacher: teacher,
    counts1: 'F',
    counts2: 'F', // Ensure key matches backend/SQL ('counts2')
    counts3: 'F'  // Ensure key matches backend/SQL ('counts3')
  };

  try {
    const res = await fetch("/api/classes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(newClassData)
    });

    const data = await res.json();

    if (res.ok && data.success) {
      // Clear inputs
      // nameInput.value = ""; // No need to clear, row is removed
      // teacherInput.value = ""; // No need to clear, row is removed

      // Remove the add row and reload
      cancelAddClass();
      loadClasses();

      // No success alert as requested
      console.log(data.message);
    } else {
      alert("Error: " + (data.error || data.detail || "Failed to add class"));
    }
  } catch (error) {
    console.error("Error adding class:", error);
    alert("Error adding class. See console for details.");
  }
}

// Kept for backward compatibility if onclick still points to addClass
const addClass = handleAddClassRow;

async function promptRemoveClass(className) {
  if (!confirm(`${translations.confirmRemoveClass?.[currentLanguage] || "Are you sure you want to remove class "}"${className}"?`)) return;

  try {
    const res = await fetch(`/api/classes?class=${encodeURIComponent(className)}`, {
      method: "DELETE",
      headers: { "Content-Type": "application/json" }
    });

    const data = await res.json();

    if (res.ok && data.success) {
      loadClasses();
      console.log(data.message);
    } else {
      alert("Error: " + (data.error || data.detail || "Failed to remove class"));
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
    const res = await fetch("/api/classes/counts", {
      method: "PUT",
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

// --- Debounce Utility ---
function debounce(func, delay) {
  let timeout;
  return function (...args) {
    const context = this;
    clearTimeout(timeout);
    timeout = setTimeout(() => func.apply(context, args), delay);
  };
}

// Create a debounced version of saveGoogleOauth
// Saves will be triggered 1 second after the last change.
const debouncedSaveGoogleOauth = debounce(saveGoogleOauth, 1000);

// --- Oauth Management Functions ---

async function loadOauthConfig() {
  try {
    // Adjust the path if your frontend and backend are served differently
    // Assuming config.html is in /frontend/ and config.json is in /backend/data/
    const response = await fetch('api/data/config');
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const config = await response.json();

    // Populate Google OAuth settings
    const googleOauthCheckbox = document.getElementById('googleOauth');
    if (googleOauthCheckbox) {
      // The JSON stores "true" as a string, so we compare it.
      googleOauthCheckbox.checked = config.oauth_eneabled === "true";
      googleOauthCheckbox.addEventListener('change', debouncedSaveGoogleOauth); // Auto-save on change
    }

    const googleOauthTableBody = document.getElementById('googleOauthTableBody');
    if (googleOauthTableBody) {
      // Clear existing rows (if any, though HTML is now empty)
      googleOauthTableBody.innerHTML = '';

      if (config.allowed_oauth_domains && Array.isArray(config.allowed_oauth_domains)) {
        config.allowed_oauth_domains.forEach((domain, index) => {
          const row = googleOauthTableBody.insertRow();

          const domainCell = row.insertCell();
          const domainInput = document.createElement('input');
          domainInput.type = 'text';
          domainInput.id = `domain-${index}`; // Unique ID for each domain input
          domainInput.value = domain;
          domainInput.placeholder = 'domain.com';
          domainInput.addEventListener('blur', debouncedSaveGoogleOauth); // Auto-save on blur
          domainCell.appendChild(domainInput);

          const actionsCell = row.insertCell();
          const removeButton = document.createElement('button');
          removeButton.textContent = 'remove';
          removeButton.onclick = function () {
            row.remove(); // Removes the current row from the table
            debouncedSaveGoogleOauth(); // Auto-save after removal
          };
          actionsCell.appendChild(removeButton);
        });
      }
    }
  } catch (error) {
    console.error('Failed to load OAuth configuration:', error);
    // Optionally display an error message to the user in the UI
    const googleOauthTableBody = document.getElementById('googleOauthTableBody');
    if (googleOauthTableBody) {
      googleOauthTableBody.innerHTML = '<tr><td colspan="2">Error loading OAuth config.</td></tr>';
    }
  }
}

function addGoogleOauthDomain() {
  const domainName = prompt((translations.enterNewDomainPrompt?.[currentLanguage] || "Enter the new allowed domain (e.g., example.com):"));
  if (domainName && domainName.trim() !== "") {
    const googleOauthTableBody = document.getElementById('googleOauthTableBody');
    if (googleOauthTableBody) {
      const row = googleOauthTableBody.insertRow();

      const domainCell = row.insertCell();
      const domainInput = document.createElement('input');
      domainInput.type = 'text';
      // No need for a unique ID if we select all inputs by type later
      domainInput.value = domainName.trim();
      domainInput.addEventListener('blur', debouncedSaveGoogleOauth); // Auto-save on blur for new inputs
      domainInput.placeholder = 'domain.com';
      domainCell.appendChild(domainInput);

      const actionsCell = row.insertCell();
      const removeButton = document.createElement('button');
      removeButton.textContent = 'remove';
      removeButton.onclick = function () {
        row.remove(); // Removes the current row from the table
        debouncedSaveGoogleOauth(); // Auto-save after removal
      };
      actionsCell.appendChild(removeButton);
      debouncedSaveGoogleOauth(); // Auto-save after adding a new domain row
    }
  } else if (domainName !== null) { // User pressed OK but field was empty
    alert((translations.domainEmptyError?.[currentLanguage] || "Domain name cannot be empty."));
  }
}

async function saveGoogleOauth() {
  const googleOauthCheckbox = document.getElementById('googleOauth');
  const isEnabled = googleOauthCheckbox ? googleOauthCheckbox.checked : false;

  const googleOauthTableBody = document.getElementById('googleOauthTableBody');
  const domains = [];
  if (googleOauthTableBody) {
    const rows = googleOauthTableBody.getElementsByTagName('tr');
    for (let i = 0; i < rows.length; i++) {
      const inputElement = rows[i].querySelector('input[type="text"]');
      if (inputElement && inputElement.value.trim() !== "") {
        domains.push(inputElement.value.trim());
      }
    }
  }

  const oauthConfigData = {
    oauth_eneabled: isEnabled.toString(), // Server expects "true" or "false" as string
    allowed_oauth_domains: domains
  };
  console.log("Auto-saving Google OAuth settings:", oauthConfigData); // For debugging

  try {
    const response = await fetch('/api/data/save/config', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(oauthConfigData),
    });

    const result = await response.json();
    if (response.ok) {
      //alert(result.message || 'OAuth settings saved successfully!');
    } else {
      alert(`Error saving OAuth settings: ${result.error || 'Unknown server error'}`);
    }
  } catch (error) {
    console.error('Failed to save OAuth settings:', error);
    alert('Failed to save OAuth settings. Check console for details.');
  }
}

// --- Initialization ---

document.addEventListener("DOMContentLoaded", () => {

    // Navbar Initialization
    currentLanguage = getCookie("language") || 'cs';
    fetchTranslations().then(() => {
        setToggleState(currentLanguage);
        displayLoggedInUser();
    });

  loadUsers();
  loadClasses();
  loadOauthConfig();
});

// Make functions available globally for HTML onclick attributes
window.renderClasses = renderClasses;
window.handleAddClassRow = handleAddClassRow;
window.cancelAddClass = cancelAddClass;
window.prefillClasses = prefillClasses;
window.loadClasses = loadClasses;
window.saveNewClass = saveNewClass;
window.promptRemoveClass = promptRemoveClass;
window.addClass = handleAddClassRow; // Alias for backward compatibility
window.changePassword = changePassword;
window.addUser = addUser;
window.removeUser = removeUser;
window.setPassword = setPassword;
window.resetPassword = resetPassword;
window.changeRole = changeRole;
window.addGoogleOauthDomain = addGoogleOauthDomain;
window.saveGoogleOauth = saveGoogleOauth;
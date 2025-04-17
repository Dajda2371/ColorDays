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
  
  async function addUser() {
    const username = document.getElementById('newUsername').value.trim();
    const password = document.getElementById('newPassword').value;
  
    if (!username || !password) return alert("Username and password required.");
  
    const res = await fetch('/add_user', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
  
    const data = await res.json();
    alert(data.message);
    fetchUsers();
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
  
  async function removeUser() {
    const username = document.getElementById('removeUsername').value.trim();
  
    if (!username) return alert("Username required.");
    if (username === 'admin') return alert("Admin account cannot be removed.");
  
    const res = await fetch('/remove_user', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username })
    });
  
    const data = await res.json();
    alert(data.message);
    fetchUsers();
  }
  
  // Load user list on page load
  fetchUsers();
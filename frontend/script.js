const studentCounts = Array(7).fill(0);
const teacherCounts = Array(7).fill(0);

const tableBody = document.getElementById('counterTable');
const studentButtons = document.getElementById('studentButtons');
const teacherButtons = document.getElementById('teacherButtons');
const studentTotal = document.getElementById('studentTotal');
const teacherTotal = document.getElementById('teacherTotal');

let dataLoaded = false;
let hasUserInteracted = false;

function updateTable() {
  tableBody.innerHTML = '';
  for (let i = 0; i <= 6; i++) {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td>${i}</td>
      <td>${studentCounts[i]}</td>
      <td>${teacherCounts[i]}</td>
    `;
    tableBody.appendChild(row);
  }

    // Calculate total points for Students
  const studentTotalPoints = studentCounts.reduce((sum, count, i) => sum + count * i, 0);

    // Calculate total points for Teachers (multiplied by 2)
  const teacherTotalPoints = teacherCounts.reduce((sum, count, i) => sum + count * i * 2, 0);

  studentTotal.textContent = studentTotalPoints;
  teacherTotal.textContent = teacherTotalPoints;
}

function createButtons(container, countsArray, updateFn) {
  for (let i = 0; i <= 6; i++) {
    const button = document.createElement('button');
    button.textContent = `+${i}`;
    button.addEventListener('click', () => {
      countsArray[i]++;
      updateFn();
      if (dataLoaded) {
        hasUserInteracted = true; // mark actual interaction
        saveSQLToServer();
      }
    });
    container.appendChild(button);
  }
}

function saveSQLToServer() {
  if (!dataLoaded || !hasUserInteracted) return; // don't save too early

  console.log("Saving to server:", studentCounts, teacherCounts);
  fetch('/save-sql', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ studentCounts, teacherCounts })
  }).catch(err => console.error("Save failed:", err));
}

function loadSQLFromServer() {
  fetch('/load-sql')
    .then(res => res.json())
    .then(data => {
      console.log("Loaded from server:", data); // Debug output

      for (let i = 0; i <= 6; i++) {
        studentCounts[i] = data.studentCounts[i] || 0;
        teacherCounts[i] = data.teacherCounts[i] || 0;
      }

      updateTable();
      dataLoaded = true; // Now allow save on user action
    })
    .catch(err => {
      console.error("Load failed:", err);
      dataLoaded = true; // Still allow future saves
    });
}

document.addEventListener('DOMContentLoaded', () => {
  createButtons(studentButtons, studentCounts, updateTable);
  createButtons(teacherButtons, teacherCounts, updateTable);
  loadSQLFromServer();
});
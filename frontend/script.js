const studentCounts = [0, 0, 0, 0, 0, 0];
const teacherCounts = [0, 0, 0, 0, 0, 0];

const tableBody = document.getElementById('counterTable');
const studentButtons = document.getElementById('studentButtons');
const teacherButtons = document.getElementById('teacherButtons');
const studentTotal = document.getElementById('studentTotal');
const teacherTotal = document.getElementById('teacherTotal');

function updateTable() {
  tableBody.innerHTML = '';
  for (let i = 0; i < 6; i++) {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td>${i + 1}</td>
      <td>${studentCounts[i]}</td>
      <td>${teacherCounts[i]}</td>
    `;
    tableBody.appendChild(row);
  }

  // Calculate total points for Students
  const studentTotalPoints = studentCounts.reduce((total, count, index) => total + (count * (index + 1)), 0);

  // Calculate total points for Teachers (multiplied by 2)
  const teacherTotalPoints = teacherCounts.reduce((total, count, index) => total + (count * (index + 1) * 2), 0);

  studentTotal.textContent = studentTotalPoints;
  teacherTotal.textContent = teacherTotalPoints;
}

function createButtons(container, countsArray, updateFn) {
  for (let i = 1; i <= 6; i++) {
    const button = document.createElement('button');
    button.textContent = `+${i}`;
    button.addEventListener('click', () => {
      countsArray[i - 1]++;
      updateFn();
    });
    container.appendChild(button);
  }
}

// Create buttons and set up table
createButtons(studentButtons, studentCounts, updateTable);
createButtons(teacherButtons, teacherCounts, updateTable);
updateTable();
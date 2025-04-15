const counts = [0, 0, 0, 0, 0, 0];
const tableBody = document.getElementById('counterTable');
const buttonsContainer = document.getElementById('buttonsContainer');

function updateTable() {
  tableBody.innerHTML = '';
  counts.forEach((count, index) => {
    const row = document.createElement('tr');
    row.innerHTML = `<td>${index + 1}</td><td>${count}</td>`;
    tableBody.appendChild(row);
  });
}

function createButtons() {
  for (let i = 1; i <= 6; i++) {
    const button = document.createElement('button');
    button.textContent = `+${i}`;
    button.addEventListener('click', () => {
      counts[i - 1]++;
      updateTable();
    });
    buttonsContainer.appendChild(button);
  }
}

createButtons();
updateTable();
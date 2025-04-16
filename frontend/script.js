const studentCounts = Array(7).fill(0);
const teacherCounts = Array(7).fill(0);

const tableBody = document.getElementById('counterTable');
const studentButtons = document.getElementById('studentButtons');
const teacherButtons = document.getElementById('teacherButtons');
const studentTotal = document.getElementById('studentTotal');
const teacherTotal = document.getElementById('teacherTotal');

let dataLoaded = false;
let hasUserInteracted = false;

// --- Helper function to handle fetch responses and check for auth errors ---
async function handleFetchResponse(response) {
  if (!response.ok) {
    // Check if the error is specifically an Unauthorized error
    if (response.status === 401) {
      console.error("Authentication required. Redirecting to login page.");
      // Redirect the user to the login page
      window.location.href = '/login.html';
      // Throw an error to stop further processing in the calling function
      throw new Error('Unauthorized');
    } else {
      // Handle other HTTP errors (e.g., 404, 500)
      const errorText = await response.text(); // Try to get error text from server
      console.error(`HTTP error ${response.status}: ${errorText}`);
      throw new Error(`HTTP error ${response.status}`);
    }
  }

  // If response is OK, try to parse JSON, handling potential empty responses
  try {
      const contentType = response.headers.get("content-type");
      if (contentType && contentType.indexOf("application/json") !== -1) {
          return await response.json(); // Parse JSON if content type is correct
      } else {
          // Handle non-JSON responses if necessary, or just return null/undefined
          console.log("Response was OK but not JSON.");
          return null; // Or handle as appropriate for your API (e.g., for /save-sql)
      }
  } catch (jsonError) {
      console.error("Failed to parse JSON response:", jsonError);
      throw new Error("Invalid JSON response from server");
  }
}
// --- End Helper Function ---


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

  const studentTotalPoints = studentCounts.reduce((sum, count, i) => sum + count * i, 0);
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
        hasUserInteracted = true;
        saveSQLToServer(); // Call the async save function
      }
    });
    container.appendChild(button);
  }
}

// --- Modified saveSQLToServer to use the helper ---
async function saveSQLToServer() {
  // Don't save if data hasn't loaded or user hasn't clicked anything yet
  if (!dataLoaded || !hasUserInteracted) return;

  console.log("Attempting to save counts..."); // Log save attempt

  try {
    const response = await fetch('/save-sql', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ studentCounts, teacherCounts })
    });
    // Use the helper to check response and handle errors (including 401)
    await handleFetchResponse(response);
    console.log("Counts saved successfully (response OK).");
    // Optionally reset hasUserInteracted if you only want to save changes since last save
    // hasUserInteracted = false;
  } catch (error) {
    // Errors (network, 401, other HTTP, JSON parse) are caught here
    // The helper function already logged details and handled 401 redirect
    console.error("Save operation failed:", error.message);
    // Decide how to handle save failures - maybe notify the user?
  }
}

// --- Modified loadSQLFromServer to use the helper ---
async function loadSQLFromServer() {
  console.log("Attempting to load counts...");
  try {
    const response = await fetch('/load-sql');
    // Use the helper to check response and handle errors (including 401)
    const data = await handleFetchResponse(response);

    // Only process data if it was successfully parsed (handleFetchResponse returns null/data)
    if (data && data.studentCounts && data.teacherCounts) {
      for (let i = 0; i <= 6; i++) {
        // Use nullish coalescing for safety, although parse_sql should return arrays
        studentCounts[i] = data.studentCounts[i] ?? 0;
        teacherCounts[i] = data.teacherCounts[i] ?? 0;
      }
      updateTable();
      console.log("Counts loaded successfully.");
    } else if (data === null) {
        // Handle cases where response was OK but not JSON or empty
        console.log("Load response OK, but no JSON data received.");
        updateTable(); // Update table even with default zeros
    } else {
        // This case might occur if handleFetchResponse logic changes or data is unexpected
        console.warn("Load response OK, but data format was unexpected:", data);
        updateTable(); // Update table with defaults
    }

    dataLoaded = true; // Mark data as loaded (or attempted to load)

  } catch (error) {
    // Errors (network, 401, other HTTP, JSON parse) are caught here
    // The helper function already logged details and handled 401 redirect
    console.error("Load operation failed:", error.message);
    // Even on failure, mark as loaded to prevent potential retry loops
    // and allow UI interaction (saving might still fail later if auth is the issue)
    dataLoaded = true;
    updateTable(); // Ensure table shows initial state (zeros) on load failure
  }
}

// --- DOMContentLoaded remains the same, calls the async load function ---
document.addEventListener('DOMContentLoaded', () => {
  createButtons(studentButtons, studentCounts, updateTable);
  createButtons(teacherButtons, teacherCounts, updateTable);
  loadSQLFromServer(); // Call the async function to load initial data
});

// --- Global variable to store the current class name ---
let currentClassName = null;
let currentDayIdentifier = null; // Added to store the day

// --- Wait for the DOM to be fully loaded ---
document.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);
    currentClassName = urlParams.get('class'); // Store class name globally
    currentDayIdentifier = urlParams.get('day'); // Store day globally

    if (!currentClassName || !currentDayIdentifier) {
        alert("No class selected. Redirecting to the menu.");
        window.location.href = 'menu.html'; // Redirect if no class
        return; // Stop further execution
    }

    // Update the heading with the class name
    const classNameElement = document.getElementById('className');
    if (classNameElement) {
        classNameElement.textContent = `Class: ${decodeURIComponent(currentClassName)} - Day: ${currentDayIdentifier.charAt(0).toUpperCase() + currentDayIdentifier.slice(1)}`;
    } else {
        console.error("Element with ID 'className' not found.");
    }

    // Create the buttons immediately (they don't depend on fetched counts)
    createButtons();

    // Fetch initial data for the table
    fetchData();
});

// --- Fetch data from the backend ---
async function fetchData() {
    if (!currentClassName || !currentDayIdentifier) {
        console.error("Cannot fetch data, className or dayIdentifier is not set.");
        return;
    }

    console.log(`Fetching data for class: ${currentClassName}, day: ${currentDayIdentifier}`);
    try {
        // Construct the correct API URL including the day
        const apiUrl = `/api/counts?class=${encodeURIComponent(currentClassName)}&day=${encodeURIComponent(currentDayIdentifier)}`;
        const response = await fetch(apiUrl);

        if (!response.ok) {
            // Handle HTTP errors (like 404, 500)
            throw new Error(`HTTP error! Status: ${response.status}`);
        }

        const data = await response.json(); // Parse the JSON response (expecting a list)
        console.log("Data received from backend:", data);

        // Update the UI elements
        updateTable(data);
        updateTotals(data);

    } catch (error) {
        console.error("Error fetching data:", error);
        // Optionally display an error message to the user on the page
        // e.g., document.getElementById('errorMessage').textContent = "Failed to load data.";
        // Reset table/totals to 0 or show error state?
        resetTableAndTotals(); // Example: reset to 0 on error
    }
}

// --- Update the table cells with fetched data ---
function updateTable(data) {
    console.log("Updating table...");
    // 1. Reset all count cells to 0 first
    for (let i = 0; i <= 6; i++) {
        const studentCell = document.getElementById(`student${i}`);
        const teacherCell = document.getElementById(`teacher${i}`);
        if (studentCell) studentCell.textContent = '0';
        if (teacherCell) teacherCell.textContent = '0';
    }

    // 2. Fill in counts from the fetched data array
    if (Array.isArray(data)) {
        data.forEach(item => {
            // Construct the ID of the cell to update
            const cellId = `${item.type}${item.points}`; // e.g., "student3", "teacher5"
            const cell = document.getElementById(cellId);
            if (cell) {
                cell.textContent = item.count; // Update the cell content
            } else {
                console.warn(`Cell with ID ${cellId} not found in the HTML!`);
            }
        });
    } else {
        console.error("Data received for table update is not an array:", data);
    }
     console.log("Table update complete.");
}

// --- Calculate and update total counts ---
function updateTotals(data) {
  // Update console log to reflect weighted calculation
  console.log("Updating totals (with teacher points doubled)...");
  let studentScoreTotal = 0; // Use a name that reflects score, not just count
  let teacherScoreTotal = 0; // Use a name that reflects score, not just count

  if (Array.isArray(data)) {
      data.forEach(item => {
          // item has { type: 'student'/'teacher', points: number, count: number }
          if (item.type === 'student') {
              // Student score = points * count
              studentScoreTotal += item.points * item.count;
          } else if (item.type === 'teacher') {
              // Teacher score = points * count * 2 (doubled)
              teacherScoreTotal += item.points * item.count * 2;
          }
      });
  } else {
       console.error("Data received for totals update is not an array:", data);
  }

  const studentTotalCell = document.getElementById('studentTotal');
  const teacherTotalCell = document.getElementById('teacherTotal');

  // Update the footer cells with the calculated SCORES
  if (studentTotalCell) studentTotalCell.textContent = studentScoreTotal;
  if (teacherTotalCell) teacherTotalCell.textContent = teacherScoreTotal;

  // Update console log
  console.log("Totals update complete (weighted):", { studentScoreTotal, teacherScoreTotal });
}

// --- Reset table and totals (e.g., on error) ---
function resetTableAndTotals() {
    console.warn("Resetting table and totals to 0.");
     for (let i = 0; i <= 6; i++) {
        const studentCell = document.getElementById(`student${i}`);
        const teacherCell = document.getElementById(`teacher${i}`);
        if (studentCell) studentCell.textContent = '0';
        if (teacherCell) teacherCell.textContent = '0';
    }
    const studentTotalCell = document.getElementById('studentTotal');
    const teacherTotalCell = document.getElementById('teacherTotal');
    if (studentTotalCell) studentTotalCell.textContent = '0';
    if (teacherTotalCell) teacherTotalCell.textContent = '0';
}


// --- Create increment and decrement buttons ---
function createButtons() {
    console.log("Creating buttons...");
    const studentButtonsDiv = document.getElementById('studentButtons');
    const teacherButtonsDiv = document.getElementById('teacherButtons');

    if (!studentButtonsDiv || !teacherButtonsDiv) {
        console.error("Button container divs not found!");
        return;
    }

    // Clear any existing buttons first
    studentButtonsDiv.innerHTML = '';
    teacherButtonsDiv.innerHTML = '';

    // Loop through points 0 to 6
    for (let points = 0; points <= 6; points++) {
        // --- Student Buttons ---
        const sIncButton = document.createElement('button');
        sIncButton.textContent = `+${points}`;
        sIncButton.onclick = () => handleCountChange('increment', 'student', points);
        studentButtonsDiv.appendChild(sIncButton);

        const sDecButton = document.createElement('button');
        sDecButton.textContent = `-${points}`;
        sDecButton.onclick = () => handleCountChange('decrement', 'student', points);
        studentButtonsDiv.appendChild(sDecButton);

        // Add a space or break for readability if desired
        // studentButtonsDiv.appendChild(document.createTextNode(' '));

        // --- Teacher Buttons ---
        const tIncButton = document.createElement('button');
        tIncButton.textContent = `+${points}`;
        tIncButton.onclick = () => handleCountChange('increment', 'teacher', points);
        teacherButtonsDiv.appendChild(tIncButton);

        const tDecButton = document.createElement('button');
        tDecButton.textContent = `-${points}`;
        tDecButton.onclick = () => handleCountChange('decrement', 'teacher', points);
        teacherButtonsDiv.appendChild(tDecButton);

        // Add a space or break for readability if desired
        // teacherButtonsDiv.appendChild(document.createTextNode(' '));
    }
    console.log("Button creation complete.");
}

// --- Handle increment/decrement button clicks ---
async function handleCountChange(action, type, points) {
    if (!currentClassName || !currentDayIdentifier) {
        console.error("Cannot change count, className or dayIdentifier is not set.");
        alert("Error: Class context lost. Please refresh or go back to menu.");
        return;
    }

    const apiUrl = `/api/${action}`; // action is 'increment' or 'decrement'
    const payload = {
        className: currentClassName,
        type: type,
        points: points,
        day: currentDayIdentifier // Include the day identifier in the payload
    };

    console.log(`Sending ${action} request to ${apiUrl} with payload:`, payload);

    try {
        const response = await fetch(apiUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                // 'Credentials': 'include' // Often handled by browser for same-origin, or add if needed
            },
            body: JSON.stringify(payload),
        });

        // Check for specific "already zero" error on decrement
        if (action === 'decrement' && response.status === 400) {
             const errorData = await response.json().catch(() => ({})); // Try to parse error message
             console.warn(`Cannot decrement: ${errorData.message || errorData.error || 'Count is already zero.'}`);
             // Optionally provide subtle feedback to the user
             // e.g., briefly flash the button red
             return; // Stop processing, don't refetch data
        }

        if (!response.ok) {
            // Handle other errors
            const errorData = await response.json().catch(() => ({ error: 'Failed to parse error response from server.' }));
            throw new Error(`HTTP error! Status: ${response.status} - ${errorData.error || errorData.message || 'Unknown server error'}`);
        }

        // If the request was successful (200 OK)
        const result = await response.json();
        console.log(`${action} successful:`, result);

        // Refresh the data from the server to show the updated state
        fetchData();

    } catch (error) {
        console.error(`Error during ${action}:`, error);
        alert(`Failed to ${action} count. ${error.message}`); // Inform the user
    }
}

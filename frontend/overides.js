document.addEventListener('DOMContentLoaded', async () => {
    // Check if user is admin
    const isAdmin = await verifyAdmin();
    if (!isAdmin) {
        alert("You must be an admin to view this page.");
        window.location.href = 'menu.html';
        return;
    }

    await loadData();
});

async function verifyAdmin() {
    try {
        const response = await fetch('/api/users', { credentials: 'include' });
        return response.ok;
    } catch {
        return false;
    }
}

const days = ['monday', 'tuesday', 'wednesday'];
let classData = [];
let overridesData = {};

async function loadData() {
    try {
        const classesResponse = await fetch('/api/classes', { credentials: 'include' });
        if (!classesResponse.ok) throw new Error("Failed to load classes");
        classData = await classesResponse.json();

        const overridesResponse = await fetch('/api/overrides', { credentials: 'include' });
        if (overridesResponse.ok) {
            overridesData = await overridesResponse.json();
        } else {
            overridesData = {};
        }

        renderTables();
        document.getElementById('saveButton').style.display = 'block';
        document.getElementById('saveButton').addEventListener('click', saveOverrides);
    } catch (error) {
        document.getElementById('tablesContainer').innerHTML = `<p style="color:red">Error: ${error.message}</p>`;
    }
}

function renderTables() {
    const container = document.getElementById('tablesContainer');
    container.innerHTML = '';
    
    // Sort classes naturally
    const sortedClasses = [...classData].sort((a, b) => {
        const aNum = parseInt(a.class.split('.')[0] || 0);
        const bNum = parseInt(b.class.split('.')[0] || 0);
        if (aNum !== bNum) return aNum - bNum;
        return a.class.localeCompare(b.class);
    });

    days.forEach(day => {
        const h2 = document.createElement('h2');
        h2.className = 'day-heading';
        h2.textContent = day.charAt(0).toUpperCase() + day.slice(1);
        container.appendChild(h2);

        const table = document.createElement('table');
        table.className = 'override-table';
        
        const thead = document.createElement('thead');
        thead.innerHTML = `
            <tr>
                <th>Class Name</th>
                <th>Override</th>
                <th>Student points</th>
                <th>Number of students</th>
                <th>teacher points</th>
                <th>number of teachers</th>
            </tr>
        `;
        table.appendChild(thead);

        const tbody = document.createElement('tbody');
        sortedClasses.forEach(cls => {
            const tr = document.createElement('tr');
            
            const currentOverride = overridesData[cls.class]?.[day] || { checkbox: false, student_points: '', number_of_students: '', teacher_points: '', number_of_teachers: '' };
            
            // "Override" checkbox by default unchecked
            tr.innerHTML = `
                <td>${cls.class}</td>
                <td><input type="checkbox" data-class="${cls.class}" data-day="${day}" data-field="checkbox" ${currentOverride.checkbox ? 'checked' : ''}></td>
                <td><input type="number" data-class="${cls.class}" data-day="${day}" data-field="student_points" value="${currentOverride.student_points === undefined ? '' : currentOverride.student_points}"></td>
                <td><input type="number" data-class="${cls.class}" data-day="${day}" data-field="number_of_students" value="${currentOverride.number_of_students === undefined ? '' : currentOverride.number_of_students}"></td>
                <td><input type="number" data-class="${cls.class}" data-day="${day}" data-field="teacher_points" value="${currentOverride.teacher_points === undefined ? '' : currentOverride.teacher_points}"></td>
                <td><input type="number" data-class="${cls.class}" data-day="${day}" data-field="number_of_teachers" value="${currentOverride.number_of_teachers === undefined ? '' : currentOverride.number_of_teachers}"></td>
            `;
            tbody.appendChild(tr);
        });
        
        table.appendChild(tbody);
        container.appendChild(table);
    });
}

async function saveOverrides() {
    const btn = document.getElementById('saveButton');
    btn.disabled = true;
    btn.textContent = 'Saving...';
    
    // Build new overrides object
    const newOverrides = {};
    
    const checkboxes = document.querySelectorAll('input[type="checkbox"]');
    const numberInputs = document.querySelectorAll('input[type="number"]');
    
    // initialize structure
    classData.forEach(cls => {
        newOverrides[cls.class] = { monday: {}, tuesday: {}, wednesday: {} };
    });
    
    checkboxes.forEach(cb => {
        const cls = cb.getAttribute('data-class');
        const day = cb.getAttribute('data-day');
        newOverrides[cls][day].checkbox = cb.checked;
    });
    
    numberInputs.forEach(input => {
        const cls = input.getAttribute('data-class');
        const day = input.getAttribute('data-day');
        const field = input.getAttribute('data-field');
        newOverrides[cls][day][field] = input.value;
    });
    
    try {
        const res = await fetch('/api/overrides', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ overrides: newOverrides }),
            credentials: 'include'
        });
        
        if (res.ok) {
            alert('Overrides saved successfully!');
        } else {
            const err = await res.json();
            alert('Failed to save: ' + (err.detail || err.error || 'Unknown error'));
        }
    } catch (error) {
        alert('Exception: ' + error.message);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Save Overrides';
    }
}

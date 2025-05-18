document.addEventListener('DOMContentLoaded', function() {
    const mondaySection = document.getElementById('monday-classes');
    const tuesdaySection = document.getElementById('tuesday-classes');
    const wednesdaySection = document.getElementById('wednesday-classes');
    const classCountingTbody = document.getElementById('class-counting-tbody');

    if (!mondaySection || !tuesdaySection || !wednesdaySection) {
        console.error('One or more day sections are missing from the HTML.');
        return;
    }

    if (!classCountingTbody) {
        console.error('The class counting table body is missing from the HTML.');
        return;
    }

    fetch('/api/classes')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(classes => {
            if (!classes || classes.length === 0) {
                const noClassesMsgP = document.createElement('p');
                noClassesMsgP.textContent = 'No classes available to display.';
                mondaySection.appendChild(noClassesMsgP.cloneNode(true));
                tuesdaySection.appendChild(noClassesMsgP.cloneNode(true));
                wednesdaySection.appendChild(noClassesMsgP.cloneNode(true));

                const noDataRow = classCountingTbody.insertRow();
                const cell = noDataRow.insertCell();
                cell.colSpan = 4; // Span across all columns
                cell.textContent = 'No class counting data available.';
                cell.style.textAlign = 'center';
            }
            classes.forEach(cls => {
                // cls.class is the class name, e.g., '1.A'
                // cls.counts1, cls.counts2, cls.counts3 are 'T' or 'F'

                if (cls.counts1 === 'T') {
                    const button = createClassButton(cls.class);
                    mondaySection.appendChild(button);
                }
                if (cls.counts2 === 'T') {
                    const button = createClassButton(cls.class);
                    tuesdaySection.appendChild(button);
                }
                if (cls.counts3 === 'T') {
                    const button = createClassButton(cls.class);
                    wednesdaySection.appendChild(button);
                }

                // Populate the "Class Counting List" table
                const row = classCountingTbody.insertRow();

                const cellClass = row.insertCell();
                cellClass.textContent = cls.class;

                const cellIsCountedBy1 = row.insertCell();
                cellIsCountedBy1.textContent = cls.iscountedby1 === '_NULL_' ? 'N/A' : cls.iscountedby1;

                const cellIsCountedBy2 = row.insertCell();
                cellIsCountedBy2.textContent = cls.iscountedby2 === '_NULL_' ? 'N/A' : cls.iscountedby2;

                const cellIsCountedBy3 = row.insertCell();
                cellIsCountedBy3.textContent = cls.iscountedby3 === '_NULL_' ? 'N/A' : cls.iscountedby3;

                // Style N/A cells if desired
                [cellIsCountedBy1, cellIsCountedBy2, cellIsCountedBy3].forEach(cell => {
                    if (cell.textContent === 'N/A') {
                        cell.style.color = '#777'; // Lighter text for N/A
                    }
                });
            });
        })
        .catch(error => {
            console.error('Error fetching or processing class data:', error);
            const errorPara = document.createElement('p');
            errorPara.textContent = 'Failed to load class buttons. Please check the console for errors.';
            errorPara.style.color = 'red';
            // Insert error before the "Back to Class Selection" link
            const backLink = document.querySelector('p > a[href="menu.html"]');
            if (backLink) {
                backLink.parentElement.insertAdjacentElement('beforebegin', errorPara);
            } else {
                document.body.appendChild(errorPara);
            }
        });

    function createClassButton(className) {
        const link = document.createElement('a');
        // Link to students.html with class name as a query parameter
        link.href = `students.html?class=${encodeURIComponent(className)}`;
        link.textContent = className;
        link.className = 'button class-button'; // Use 'button' or a custom class for styling
        // You can add more specific styling via style.css for '.class-button'
        return link;
    }
});
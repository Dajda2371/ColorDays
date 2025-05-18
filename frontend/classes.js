document.addEventListener('DOMContentLoaded', function() {
    const mondaySection = document.getElementById('monday-classes');
    const tuesdaySection = document.getElementById('tuesday-classes');
    const wednesdaySection = document.getElementById('wednesday-classes');

    if (!mondaySection || !tuesdaySection || !wednesdaySection) {
        console.error('One or more day sections are missing from the HTML.');
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
                const noClassesMsg = document.createElement('p');
                noClassesMsg.textContent = 'No classes available to display.';
                // Append to a general area or the first section if appropriate
                mondaySection.appendChild(noClassesMsg.cloneNode(true));
                tuesdaySection.appendChild(noClassesMsg.cloneNode(true));
                wednesdaySection.appendChild(noClassesMsg.cloneNode(true));
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
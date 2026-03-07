document.addEventListener('DOMContentLoaded', function () {
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

    // Fetch both classes and config concurrently
    Promise.all([
        fetch('/api/classes').then(response => {
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status} for /api/classes`);
            return response.json();
        }),
        fetch('/api/data/config').then(response => { // Fetch server configuration
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status} for /api/data/config`);
            return response.json();
        })
    ])
        .then(([classes, config]) => { // Destructure the results from Promise.all
            // Convert the config string to a boolean for easier use
            // If config.can_students_count_their_own_class is "false", then canStudentsCountOwnClass will be false.
            // If it's "true" (or anything else, or missing), it defaults to true (allowing self-count).
            const canStudentsCountOwnClass = config.can_students_count_their_own_class !== "false";
            console.log("Can students count their own class:", canStudentsCountOwnClass, "(raw config value:", config.can_students_count_their_own_class, ")");

            // --- Auto Assign Logic ---
            const splitEvenlyBtn = document.getElementById('split-evenly-btn');
            const splitRandomlyBtn = document.getElementById('split-randomly-btn');
            const clearAssignmentsBtn = document.getElementById('clear-assignments-btn');

            if (splitEvenlyBtn && splitRandomlyBtn && clearAssignmentsBtn) {
                splitEvenlyBtn.addEventListener('click', () => {
                    if (!confirm((translations.confirmSplitEvenly?.[currentLanguage] || "Are you sure you want to split counting duties evenly? This will overwrite existing assignments."))) return;

                    const updates = [];
                    ['1', '2', '3'].forEach(day => {
                        // Ensure classes are sorted alphabetically by class name
                        classes.sort((a, b) => a.class.localeCompare(b.class, undefined, { numeric: true, sensitivity: 'base' }));

                        const countingClasses = classes.filter(c => c[`counts${day}`] === 'T').map(c => c.class).sort();
                        if (countingClasses.length === 0) return;

                        classes.forEach((cls, index) => {
                            // "Split Evenly" only affects the classes that are counting
                            if (countingClasses.includes(cls.class)) {
                                let counterName;
                                const idx = countingClasses.indexOf(cls.class);
                                // Cycle: shift left by 1 (or count by previous)
                                const counterIdx = (idx - 1 + countingClasses.length) % countingClasses.length;
                                counterName = countingClasses[counterIdx];

                                if (!canStudentsCountOwnClass && countingClasses.length === 1 && counterName === cls.class) {
                                    counterName = '_NULL_';
                                }

                                updates.push({
                                    class: cls.class,
                                    dayIdentifier: day,
                                    value: counterName
                                });
                            } else {
                                // Generate the rest: distribute non-counting classes evenly based on their position
                                const counterIdx = index % countingClasses.length;
                                const counterName = countingClasses[counterIdx];

                                updates.push({
                                    class: cls.class,
                                    dayIdentifier: day,
                                    value: counterName
                                });
                            }
                        });
                    });
                    sendBatchUpdates(updates);
                });

                splitRandomlyBtn.addEventListener('click', () => {
                    if (!confirm((translations.confirmSplitRandomly?.[currentLanguage] || "Are you sure you want to split counting duties randomly? This will overwrite existing assignments."))) return;

                    const updates = [];
                    ['1', '2', '3'].forEach(day => {
                        const countingClasses = classes.filter(c => c[`counts${day}`] === 'T').map(c => c.class);
                        if (countingClasses.length === 0) return;

                        const totalTargets = classes.length;
                        const baseCount = Math.floor(totalTargets / countingClasses.length);
                        const remainder = totalTargets % countingClasses.length;

                        // Create a pool of counters
                        let counterPool = [];

                        // Fill base counts
                        countingClasses.forEach(c => {
                            for (let i = 0; i < baseCount; i++) counterPool.push(c);
                        });

                        // Fill remainder randomly
                        // Shuffle countingClasses first to pick random ones for the remainder slots
                        const shuffledForRemainder = [...countingClasses].sort(() => Math.random() - 0.5);
                        for (let i = 0; i < remainder; i++) {
                            counterPool.push(shuffledForRemainder[i]);
                        }

                        // Shuffle the entire pool to distribute counters randomly
                        counterPool.sort(() => Math.random() - 0.5);

                        // Assign counters to classes
                        const initialAssignments = classes.map((cls, index) => ({
                            cls: cls,
                            counter: counterPool[index]
                        }));

                        // Resolve conflicts (classes counting themselves) if needed
                        if (!canStudentsCountOwnClass) {
                            for (let i = 0; i < initialAssignments.length; i++) {
                                if (initialAssignments[i].cls.class === initialAssignments[i].counter) {
                                    // Conflict found. Try to swap with another assignment.
                                    let swapped = false;
                                    // Try to find a suitable swap partner j
                                    // Randomized start index for swapping to avoid patterns
                                    const startIndex = Math.floor(Math.random() * initialAssignments.length);

                                    for (let k = 0; k < initialAssignments.length; k++) {
                                        const j = (startIndex + k) % initialAssignments.length;
                                        if (i === j) continue;

                                        const counterAtI = initialAssignments[i].counter;
                                        const counterAtJ = initialAssignments[j].counter;
                                        const targetI = initialAssignments[i].cls.class;
                                        const targetJ = initialAssignments[j].cls.class;

                                        // Valid swap condition:
                                        // 1. The counter from j (counterAtJ) must not be targetI
                                        // 2. The counter from i (counterAtI) must not be targetJ
                                        if (counterAtJ !== targetI && counterAtI !== targetJ) {
                                            initialAssignments[i].counter = counterAtJ;
                                            initialAssignments[j].counter = counterAtI;
                                            swapped = true;
                                            break;
                                        }
                                    }

                                    if (!swapped) {
                                        // If we simply cannot resolve the conflict (e.g., only 1 counting class exists and it's this one),
                                        // assign _NULL_
                                        initialAssignments[i].counter = '_NULL_';
                                    }
                                }
                            }
                        }

                        // Add final assignments to updates
                        initialAssignments.forEach(assignment => {
                            updates.push({
                                class: assignment.cls.class,
                                dayIdentifier: day,
                                value: assignment.counter
                            });
                        });
                    });
                    sendBatchUpdates(updates);
                });

                clearAssignmentsBtn.addEventListener('click', () => {
                    if (!confirm((translations.confirmClearAll?.[currentLanguage] || "Are you sure you want to CLEAR ALL counting assignments? This cannot be undone."))) return;

                    // Show loading state
                    clearAssignmentsBtn.disabled = true;
                    if (splitEvenlyBtn) splitEvenlyBtn.disabled = true;
                    if (splitRandomlyBtn) splitRandomlyBtn.disabled = true;

                    fetch('/api/classes/assignments', {
                        method: 'DELETE'
                    })
                        .then(res => res.json())
                        .then(data => {
                            if (data.success) {
                                alert((translations.successText?.[currentLanguage] || "Success: ") + data.message);
                                window.location.reload();
                            } else {
                                alert((translations.errorText?.[currentLanguage] || "Error: ") + (data.error || data.message || (translations.unknownErrorText?.[currentLanguage] || "Unknown error")));
                            }
                        })
                        .catch(err => {
                            console.error(err);
                            alert((translations.errorClearingAssignmentsText?.[currentLanguage] || "Error clearing assignments: ") + err.message);
                        })
                        .finally(() => {
                            if (clearAssignmentsBtn) clearAssignmentsBtn.disabled = false;
                            if (splitEvenlyBtn) splitEvenlyBtn.disabled = false;
                            if (splitRandomlyBtn) splitRandomlyBtn.disabled = false;
                        });
                });
            }

            function sendBatchUpdates(updates) {
                if (updates.length === 0) {
                    alert((translations.noUpdatesToApply?.[currentLanguage] || "No updates to apply (maybe no classes are set to count?)."));
                    return;
                }

                // Show loading state
                if (splitEvenlyBtn) splitEvenlyBtn.disabled = true;
                if (splitRandomlyBtn) splitRandomlyBtn.disabled = true;
                if (clearAssignmentsBtn) clearAssignmentsBtn.disabled = true;

                fetch('/api/classes/iscountedby/batch', {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ updates: updates })
                })
                    .then(res => res.json())
                    .then(data => {
                        if (data.success) {
                            alert((translations.successText?.[currentLanguage] || "Success: ") + data.message);
                            window.location.reload();
                        } else {
                            alert((translations.errorText?.[currentLanguage] || "Error: ") + (data.error || data.message || (translations.unknownErrorText?.[currentLanguage] || "Unknown error")));
                        }
                    })
                    .catch(err => {
                        console.error(err);
                        alert((translations.errorSendingUpdatesText?.[currentLanguage] || "Error sending updates: ") + err.message);
                    })
                    .finally(() => {
                        if (splitEvenlyBtn) splitEvenlyBtn.disabled = false;
                        if (splitRandomlyBtn) splitRandomlyBtn.disabled = false;
                        if (clearAssignmentsBtn) clearAssignmentsBtn.disabled = false;
                    });
            }
            // --- End Auto Assign Logic ---


            // Prepare lists of classes that count for each day
            const mondayCountingClasses = classes.filter(c => c.counts1 === 'T').map(c => c.class);
            const tuesdayCountingClasses = classes.filter(c => c.counts2 === 'T').map(c => c.class);
            const wednesdayCountingClasses = classes.filter(c => c.counts3 === 'T').map(c => c.class);

            if (!classes || classes.length === 0) {
                const noClassesMsgP = document.createElement('p');
                noClassesMsgP.textContent = (translations.noClassesAvailableText?.[currentLanguage] || 'No classes available to display.');
                mondaySection.appendChild(noClassesMsgP.cloneNode(true));
                tuesdaySection.appendChild(noClassesMsgP.cloneNode(true));
                wednesdaySection.appendChild(noClassesMsgP.cloneNode(true));

                const noDataRow = classCountingTbody.insertRow();
                const cell = noDataRow.insertCell();
                cell.colSpan = 4; // Span across all columns
                cell.textContent = (translations.noClassCountingDataText?.[currentLanguage] || 'No class counting data available.');
                cell.style.textAlign = 'center';

                // Add "Prefill Classes" button
                const prefillContainer = document.createElement('div');
                prefillContainer.style.textAlign = 'center';
                prefillContainer.style.marginTop = '2rem';

                const prefillButton = document.createElement('button');
                prefillButton.textContent = (translations.prefillClassesBtnText?.[currentLanguage] || 'Prefill Classes from Website');
                prefillButton.className = 'button'; // Re-use existing button class
                prefillButton.style.backgroundColor = '#4CAF50'; // Green color to indicate action

                prefillButton.onclick = function () {
                    prefillButton.disabled = true;
                    prefillButton.textContent = (translations.scrapingText?.[currentLanguage] || 'Scraping...');

                    fetch('/api/classes/prefill', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({})
                    })
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                alert(data.message);
                                window.location.reload();
                            } else {
                                alert('Error: ' + (data.error || 'Unknown error'));
                                prefillButton.disabled = false;
                                prefillButton.textContent = (translations.prefillClassesBtnText?.[currentLanguage] || 'Prefill Classes from Website');
                            }
                        })
                        .catch(err => {
                            console.error(err);
                            alert('Error contacting server.');
                            prefillButton.disabled = false;
                            prefillButton.textContent = (translations.prefillClassesBtnText?.[currentLanguage] || 'Prefill Classes from Website');
                        });
                };

                prefillContainer.appendChild(prefillButton);
                document.querySelector('body > section').insertAdjacentElement('afterend', prefillContainer);
            }
            classes.forEach(cls => {
                // cls.class is the class name, e.g., '1.A'
                // cls.counts1, cls.counts2, cls.counts3 are 'T' or 'F'

                if (cls.counts1 === 'T') {
                    const button = createClassButton(cls.class, '1'); // Pass day identifier 1 for Monday
                    mondaySection.appendChild(button);
                }
                if (cls.counts2 === 'T') {
                    const button = createClassButton(cls.class, '2'); // Pass day identifier 2 for Tuesday
                    tuesdaySection.appendChild(button);
                }
                if (cls.counts3 === 'T') {
                    const button = createClassButton(cls.class, '3'); // Pass day identifier 3 for Wednesday
                    wednesdaySection.appendChild(button);
                }

                // Populate the "Class Counting List" table
                const row = classCountingTbody.insertRow();

                const cellClass = row.insertCell();
                cellClass.textContent = cls.class;

                const cellIsCountedBy1 = row.insertCell();
                cellIsCountedBy1.appendChild(createCountingDropdown(mondayCountingClasses, cls.iscountedby1, cls.class, '1', canStudentsCountOwnClass));

                const cellIsCountedBy2 = row.insertCell();
                cellIsCountedBy2.appendChild(createCountingDropdown(tuesdayCountingClasses, cls.iscountedby2, cls.class, '2', canStudentsCountOwnClass));

                const cellIsCountedBy3 = row.insertCell();
                cellIsCountedBy3.appendChild(createCountingDropdown(wednesdayCountingClasses, cls.iscountedby3, cls.class, '3', canStudentsCountOwnClass));
            });
        })
        .catch(error => {
            console.error('Error fetching or processing class data:', error);
            const errorPara = document.createElement('p');
            errorPara.textContent = (translations.failedLoadClassButtons?.[currentLanguage] || 'Failed to load class buttons. Please check the console for errors.');
            errorPara.style.color = 'red';
            // Insert error before the "Back to Class Selection" link
            const backLink = document.querySelector('p > a[href="menu.html"]');
            if (backLink) {
                backLink.parentElement.insertAdjacentElement('beforebegin', errorPara);
            } else {
                document.body.appendChild(errorPara);
            }
        });

    function createClassButton(className, dayIdentifier) {
        const link = document.createElement('a');
        // Link to students.html with class name as a query parameter
        link.href = `students.html?class=${encodeURIComponent(className)}&day=${dayIdentifier}`;
        link.textContent = className;
        link.className = 'button class-button'; // Use 'button' or a custom class for styling
        // You can add more specific styling via style.css for '.class-button'
        return link;
    }

    function createCountingDropdown(availableClasses, selectedValue, classIdentifier, dayIdentifier, canStudentsCountOwnClass) {
        const select = document.createElement('select');
        select.dataset.class = classIdentifier; // e.g., '1.A'
        select.dataset.day = dayIdentifier;     // e.g., '1' for Monday, '2' for Tuesday
        // Add a class for potential styling
        select.classList.add('counting-dropdown');

        // N/A Option
        const naOption = document.createElement('option');
        naOption.value = '_NULL_';
        naOption.textContent = (translations.naText?.[currentLanguage] || 'N/A');
        select.appendChild(naOption);

        // Options for counting classes
        availableClasses.forEach(countingClass => {
            const option = document.createElement('option');
            option.value = countingClass;
            option.textContent = countingClass;

            // If students cannot count their own class AND this option is for the class itself
            if (!canStudentsCountOwnClass && countingClass === classIdentifier) {
                option.disabled = true;
                option.title = "This class cannot be set to count itself based on server configuration.";
            }
            select.appendChild(option);
        });

        // Set the selected value
        // If selectedValue is not among the options (e.g. old data or not a counting class),
        // it will default to the first option (N/A) or remain unselected based on browser.
        // Explicitly setting to _NULL_ if it's not a valid class option ensures N/A is picked.
        if (availableClasses.includes(selectedValue) || selectedValue === '_NULL_') {
            select.value = selectedValue;
        } else {
            select.value = '_NULL_'; // Default to N/A if current value is invalid/not in list
        }

        // Add event listener to save changes
        select.addEventListener('change', function () {
            const changedClass = this.dataset.class;
            const changedDayIdentifier = this.dataset.day;
            const newValue = this.value;

            // console.log(`Change detected: Class ${changedClass}, Day ${changedDayIdentifier}, New Value: ${newValue}`);

            fetch('/api/classes/iscountedby', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    class: changedClass,
                    dayIdentifier: changedDayIdentifier, // '1', '2', or '3'
                    value: newValue
                }),
            })
                .then(response => {
                    if (!response.ok) {
                        return response.json().then(err => { throw new Error(err.error || `HTTP error! status: ${response.status}`) });
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.success) {
                        console.log(data.message);
                        // Optionally, provide user feedback (e.g., a small temporary "Saved!" message)
                    } else {
                        // This case should ideally be caught by the !response.ok check above
                        console.error('Failed to save:', data.error || 'Unknown error');
                        alert(`${translations.errorSavingChange?.[currentLanguage] || 'Error saving change: '}${data.error || (translations.unknownErrorText?.[currentLanguage] || 'Unknown error')}`);
                    }
                })
                .catch(error => {
                    console.error('Error updating class counting value:', error);
                    alert(`${translations.errorUpdating?.[currentLanguage] || 'Error updating: '}${error.message}`);
                });
        });

        return select;
    }
});
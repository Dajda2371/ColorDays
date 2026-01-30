const fetch = require('node-fetch');

async function test() {
    try {
        const classesRes = await fetch('http://localhost:8000/api/classes');
        const classes = await classesRes.json();
        
        // Mock Config
        const canStudentsCountOwnClass = false; // Based on user config

        ['1'].forEach(day => { // Test day 1
            console.log(`Testing Day ${day}...`);
            const countingClasses = classes.filter(c => c[`counts${day}`] === 'T').map(c => c.class).sort();
            console.log('Counting Classes:', countingClasses);
            
            if (countingClasses.length === 0) return;

            classes.forEach((cls, index) => {
                let val;
                if (countingClasses.includes(cls.class)) {
                     const idx = countingClasses.indexOf(cls.class);
                     const counterIdx = (idx - 1 + countingClasses.length) % countingClasses.length;
                     val = countingClasses[counterIdx];
                     // Self count check
                     if (!canStudentsCountOwnClass && countingClasses.length === 1 && val === cls.class) {
                         val = '_NULL_';
                     }
                } else {
                     const counterIdx = index % countingClasses.length;
                     val = countingClasses[counterIdx];
                }
                console.log(`${cls.class} (Index ${index}) -> ${val}`);
            });
        });

    } catch (e) {
        console.error(e);
    }
}

test();

const fs = require('fs');

const files = [
    './frontend/leaderboard.js',
    './frontend/config.js',
    './frontend/change-password.js',
    './frontend/classes.js',
    './frontend/students.js',
    './frontend/student-is-counting.js'
];

files.forEach(file => {
    try {
        const content = fs.readFileSync(file, 'utf8');
        if (content.indexOf("document.querySelectorAll('[data-translate-key]')") !== -1) {
            console.log(file + ": Ok");
        } else {
             console.log(file + ": Fails");
        }
    } catch(e) { }
});

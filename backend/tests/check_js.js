const fs = require('fs');

const files = [
    './frontend/classes.js',
    './frontend/students.js',
    './frontend/student-is-counting.js',
    './frontend/config.js',
    './frontend/change-password.js',
    './frontend/leaderboard.js',
    './frontend/script.js',
    './frontend/menu.js'
];

files.forEach(file => {
    try {
        const content = fs.readFileSync(file, 'utf8');
        const matches = content.match(/document\.querySelectorAll\('\[data-translate-key\]'\)/g);
        console.log(`${file}: applyTranslations: ${matches ? matches.length : 0}`);
        const setLangMatches = content.match(/setLanguagePreference/g);
        console.log(`${file}: setLangMatches: ${setLangMatches ? setLangMatches.length : 0}`);
        
    } catch(e) {
        // ignore
    }
});

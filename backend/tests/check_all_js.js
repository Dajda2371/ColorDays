const fs = require('fs');

const files = [
    './frontend/classes.js',
    './frontend/students.js',
    './frontend/student-is-counting.js',
    './frontend/config.js',
    './frontend/change-password.js',
    './frontend/login.js',
    './frontend/script.js',
    './frontend/leaderboard.js',
    './frontend/menu.js'
];

files.forEach(file => {
    try {
        const content = fs.readFileSync(file, 'utf8');
        const hasTransDef = content.includes('let translations = {};') || content.includes('let translations ');
        const hasApply = content.includes('function applyTranslations()');
        const hasSetLang = content.includes('function setLanguagePreference');
        const err = (hasTransDef && hasApply && hasSetLang) ? "OK" : "MISSING LOGIC";
        console.log(`${file}: ${err} (trans: ${hasTransDef}, apply: ${hasApply}, setLang: ${hasSetLang})`);
    } catch(e) {
        console.log(e.message);
    }
});

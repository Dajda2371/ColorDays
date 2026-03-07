const leaderboardTable = document.getElementById('leaderboardTable');
const logoutButton = document.getElementById('logoutButton');
const languageToggle = document.getElementById('languageToggle');
const toggleCs = document.getElementById('toggleCs');
const toggleEn = document.getElementById('toggleEn');

// --- Localization ---
let translations = {};
let currentLanguage = 'en'; // Default language

// --- Logout Functionality ---
async function handleLogout() {
    console.log("Attempting logout...");
    try {
        const response = await fetch('/logout', {
            method: 'POST',
            credentials: 'include'
        });

        if (response.ok) {
            console.log("Logout successful on server. Redirecting to login.");
            window.location.href = '/login.html';
        } else {
            const result = await response.json().catch(() => ({}));
            console.error('Logout request failed:', response.status, result.error || 'Unknown server error');
            alert(`Logout failed: ${result.error || 'Server error'}`);
        }
    } catch (error) {
        console.error('Error during logout fetch:', error);
        alert('An error occurred during logout. Please check your connection.');
    }
}

if (logoutButton) {
    logoutButton.addEventListener('click', handleLogout);
}

// --- Localization Functions ---
async function fetchTranslations() {
    try {
        console.log("Attempting to fetch translations from /api/translations...");
        const response = await fetch('/api/translations');
        if (!response.ok) {
            console.error('Failed to load translations:', response.status);
            return;
        }
        console.log("Translations fetched successfully.");
        translations = await response.json();
        applyTranslations();
    } catch (error) {
        console.error('Error fetching translations:', error);
    }
}

function applyTranslations() {
    console.log(`Applying translations for language: ${currentLanguage}`);
    document.querySelectorAll('[data-translate-key]').forEach(element => {
        const key = element.getAttribute('data-translate-key');
        if (translations[key] && translations[key][currentLanguage]) {
            element.textContent = translations[key][currentLanguage];
        } else if (translations[key] && translations[key]['en']) {
            element.textContent = translations[key]['en'];
        }
    });
}

// --- Function to fetch and display leaderboard ---
async function loadLeaderboard() {
    const loadingMessage = translations.loadingLeaderboardText?.[currentLanguage] || translations.loadingLeaderboardText?.['en'] || 'Loading leaderboard...';
    leaderboardTable.innerHTML = `<tr><td colspan="4">${loadingMessage}</td></tr>`;

    try {
        const response = await fetch('/api/leaderboard', { credentials: 'include' });
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ error: "Failed to fetch leaderboard data" }));
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }
        const leaderboardData = await response.json();

        leaderboardTable.innerHTML = ''; // Clear loading message

        if (leaderboardData.length === 0) {
            leaderboardTable.innerHTML = `<tr><td colspan="4">${translations.noDataText?.[currentLanguage] || 'No data available'}</td></tr>`;
            return;
        }

        leaderboardData.forEach((entry, index) => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${index + 1}</td>
                <td>${entry.class}</td>
                <td>${entry.percentage}</td>
                <td>${entry.score}</td>
            `;
            leaderboardTable.appendChild(row);
        });

    } catch (error) {
        console.error('Error loading leaderboard:', error);
        leaderboardTable.innerHTML = `<tr><td colspan="4" style="color:red;">Error loading leaderboard: ${error.message}</td></tr>`;
    }
}

// --- Function to display logged-in username ---
function displayLoggedInUser() {
    const cookies = document.cookie.split('; ');
    const usernameCookie = cookies.find(row => row.startsWith('ColorDaysUser='));
    const usernameTextSpan = document.getElementById('usernameText');

    if (usernameCookie) {
        const username = usernameCookie.split('=')[1];
        usernameTextSpan.textContent = decodeURIComponent(username);
    } else {
        usernameTextSpan.textContent = translations.usernameNotLoggedIn?.[currentLanguage] || 'Not Logged In';
    }
}

// Helper function to get cookie
function getCookie(name) {
    const nameEQ = name + "=";
    const ca = document.cookie.split(';');
    for (let i = 0; i < ca.length; i++) {
        let c = ca[i];
        while (c.charAt(0) === ' ') c = c.substring(1, c.length);
        if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length, c.length);
    }
    return null;
}

// --- Language Functions ---
async function setLanguagePreference(lang) {
    console.log(`Setting language preference to: ${lang}`);
    try {
        const response = await fetch('/api/language/set', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ language: lang }),
            credentials: 'include'
        });

        if (response.ok) {
            currentLanguage = lang;
            applyTranslations();
            loadLeaderboard(); // Reload data
            displayLoggedInUser();
        } else {
            console.error('Failed to set language preference:', response.status);
        }
    } catch (error) {
        console.error('Error during setLanguagePreference fetch:', error);
    }
}

function setToggleState(lang) {
    if (toggleCs && toggleEn) {
        if (lang === 'cs') {
            toggleCs.classList.add('active');
            toggleEn.classList.remove('active');
        } else if (lang === 'en') {
            toggleEn.classList.add('active');
            toggleCs.classList.remove('active');
        } else {
            toggleEn.classList.add('active');
            toggleCs.classList.remove('active');
        }
    }
}

if (languageToggle) {
    languageToggle.addEventListener('click', (event) => {
        const target = event.target;
        if (target.tagName === 'SPAN' && target.dataset.lang) {
            const selectedLang = target.dataset.lang;
            setLanguagePreference(selectedLang);
            setToggleState(selectedLang);
        }
    });
}

// Load on start
document.addEventListener('DOMContentLoaded', () => {
    currentLanguage = getCookie("language") || 'en';

    fetchTranslations().then(() => {
        setToggleState(currentLanguage);
        loadLeaderboard();
        displayLoggedInUser();
    });
});

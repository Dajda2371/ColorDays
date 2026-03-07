import os

def replace_in_file(path, replacements):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        for old_str, new_str in replacements:
            content = content.replace(old_str, new_str)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
    except Exception as e:
        print(f"Error in {path}: {e}")

repl_index_html = [
    ('<title>Color Days Counter</title>', '<title data-translate-key="mainHeading">Color Days Counter</title>'),
    ('<h1 id="className" class="mb-5px">Loading...</h1>', '<h1 id="className" class="mb-5px" data-translate-key="loadingText">Loading...</h1>'),
    ('<th>Points</th>', '<th data-translate-key="pointsHeader">Points</th>'),
    ('<th>Students</th>', '<th data-translate-key="studentsHeader">Students</th>'),
    ('<th>Teachers</th>', '<th data-translate-key="teachersHeader">Teachers</th>'),
    ('<strong>Total People</strong>', '<strong data-translate-key="totalPeopleText">Total People</strong>'),
    ('<strong>Total Points</strong>', '<strong data-translate-key="totalPointsText">Total Points</strong>'),
    ('<h3>Student Buttons</h3>', '<h3 data-translate-key="studentButtonsHeading">Student Buttons</h3>'),
    ('<h3>Teacher Buttons</h3>', '<h3 data-translate-key="teacherButtonsHeading">Teacher Buttons</h3>'),
    ('<a href="menu.html" style="display:none;">Back to Class Selection</a>', '<a href="menu.html" style="display:none;" data-translate-key="backToClassSelectionText">Back to Class Selection</a>'),
    ('loading ...', 'loading ...<!-- data-translate-key="loadingLowerText" handled via JS -->')
]

repl_script_js = [
    ('"No class selected. Redirecting to the menu."', '(translations.noClassSelectedAlert?.[currentLanguage] || "No class selected. Redirecting to the menu.")'),
    ("'Logout failed'", "(translations.logoutFailedAlert?.[currentLanguage] || 'Logout failed')"),
    ("'An error occurred during logout.'", "(translations.logoutErrorAlert?.[currentLanguage] || 'An error occurred during logout.')"),
    ("'Not Logged In'", "(translations.usernameNotLoggedIn?.[currentLanguage] || 'Not Logged In')"),
    ('"Error: Class context lost. Please refresh or go back to menu."', '(translations.classContextLostAlert?.[currentLanguage] || "Error: Class context lost. Please refresh or go back to menu.")'),
]

repl_leaderboard_html = [
    ('<td colspan="4">Loading...</td>', '<td colspan="4" data-translate-key="loadingText">Loading...</td>'),
    ('<title>Color Days - Leaderboard</title>', '<title data-translate-key="leaderboardButtonText">Color Days - Leaderboard</title>'),
]

repl_leaderboard_js = [
    ("'Loading leaderboard...'", "(translations.loadingLeaderboardText?.[currentLanguage] || 'Loading leaderboard...')"),
    ("'No data available'", "(translations.noDataText?.[currentLanguage] || 'No data available')"),
    ("'Not Logged In'", "(translations.usernameNotLoggedIn?.[currentLanguage] || 'Not Logged In')"),
]

repl_login_html = [
    ('<h1>Login to Color Days Counter</h1>', '<h1 data-translate-key="loginHeading">Login to Color Days Counter</h1>'),
    ('<h2>Login as Student</h2>', '<h2 data-translate-key="loginAsStudent">Login as Student</h2>'),
    ('<label for="code">Code:</label>', '<label for="code" data-translate-key="codeLabel">Code:</label>'),
    ('<button type="submit" class="btn-primary">Login</button>', '<button type="submit" class="btn-primary" data-translate-key="loginButton">Login</button>'),
    ('<h2>Login as Teacher</h2>', '<h2 data-translate-key="loginAsTeacher">Login as Teacher</h2>'),
    ('<button onclick="window.location.href=\'/login/google\'" class="btn-google">Login with Google</button>', '<button onclick="window.location.href=\'/login/google\'" class="btn-google" data-translate-key="loginWithGoogle">Login with Google</button>'),
    ('<p class="text-separator">or</p>', '<p class="text-separator" data-translate-key="orText">or</p>'),
    ('<label for="username">Username:</label>', '<label for="username" data-translate-key="usernameLabel">Username:</label>'),
    ('<label for="password">Password:</label>', '<label for="password" data-translate-key="passwordLabel">Password:</label>'),
    ('<title>Login - Color Days</title>', '<title data-translate-key="loginTitle">Login - Color Days</title>'),
]

repl_login_js = [
    ("'Please enter your student code.'", "(translations.enterStudentCodeError?.[currentLanguage] || 'Please enter your student code.')"),
    ('` login failed. Server returned status: ${response.status}`', '`${translations.loginFailedStatusError?.[currentLanguage] || " login failed. Server returned status: "}${response.status}`'),
    ('`${userType} login failed. Please try again.`', '`${userType}${translations.loginFailedTryAgainError?.[currentLanguage] || " login failed. Please try again."}`'),
    ('`An unexpected error occurred during ${userType.toLowerCase()} login.`', '`${translations.unexpectedLoginError?.[currentLanguage] || "An unexpected error occurred during "}${userType.toLowerCase()} login.`'),
    ("'Tato e-mailová doména není pro Google přihlášení povolena.'", "(translations.invalidGoogleDomainAlert?.[currentLanguage] || 'Tato e-mailová doména není pro Google přihlášení povolena.')"),
]

repl_menu_html = [
    ('<title>Color Days - Menu</title>', '<title data-translate-key="menuTitle">Color Days - Menu</title>'),
]

repl_menu_js = [
    ("'Logout failed'", "(translations.logoutFailedAlert?.[currentLanguage] || 'Logout failed')"),
    ("'An error occurred during logout. Please check your connection.'", "(translations.logoutErrorAlert?.[currentLanguage] || 'An error occurred during logout. Please check your connection.')"),
    ("'Not Logged In'", "(translations.usernameNotLoggedIn?.[currentLanguage] || 'Not Logged In')"),
]

repl_classes_html = [
    ('<title>Classes</title>', '<title data-translate-key="classesTitle">Classes</title>'),
    ('<h2>Days</h2>', '<h2 data-translate-key="daysHeading">Days</h2>'),
    ('<h2>Class Counting List</h2>', '<h2 data-translate-key="classCountingListHeading">Class Counting List</h2>'),
    ('<button id="split-evenly-btn" class="button">Split Evenly</button>', '<button id="split-evenly-btn" class="button" data-translate-key="splitEvenlyBtnText">Split Evenly</button>'),
    ('<button id="split-randomly-btn" class="button">Split Randomly</button>', '<button id="split-randomly-btn" class="button" data-translate-key="splitRandomlyBtnText">Split Randomly</button>'),
    ('<button id="clear-assignments-btn" class="button" class="btn-danger">Clear All</button>', '<button id="clear-assignments-btn" class="button btn-danger" data-translate-key="clearAllBtnText">Clear All</button>'),
    ('<h3>Monday</h3>', '<h3 data-translate-key="mondayHeader">Monday</h3>'),
    ('<h3>Tuesday</h3>', '<h3 data-translate-key="tuesdayHeader">Tuesday</h3>'),
    ('<h3>Wednesday</h3>', '<h3 data-translate-key="wednesdayHeader">Wednesday</h3>'),
    ('<th>Class</th>', '<th data-translate-key="classHeader">Class</th>'),
    ('<th>Monday</th>', '<th data-translate-key="mondayHeader">Monday</th>'),
    ('<th>Tuesday</th>', '<th data-translate-key="tuesdayHeader">Tuesday</th>'),
    ('<th>Wednesday</th>', '<th data-translate-key="wednesdayHeader">Wednesday</th>'),
]

repl_classes_js = [
    ('"Are you sure you want to split counting duties evenly? This will overwrite existing assignments."', '(translations.confirmSplitEvenly?.[currentLanguage] || "Are you sure you want to split counting duties evenly? This will overwrite existing assignments.")'),
    ('"Are you sure you want to split counting duties randomly? This will overwrite existing assignments."', '(translations.confirmSplitRandomly?.[currentLanguage] || "Are you sure you want to split counting duties randomly? This will overwrite existing assignments.")'),
    ('"Are you sure you want to CLEAR ALL counting assignments? This cannot be undone."', '(translations.confirmClearAll?.[currentLanguage] || "Are you sure you want to CLEAR ALL counting assignments? This cannot be undone.")'),
    ('"No updates to apply (maybe no classes are set to count?)."', '(translations.noUpdatesToApply?.[currentLanguage] || "No updates to apply (maybe no classes are set to count?).")'),
    ("'No classes available to display.'", "(translations.noClassesAvailableText?.[currentLanguage] || 'No classes available to display.')"),
    ("'No class counting data available.'", "(translations.noClassCountingDataText?.[currentLanguage] || 'No class counting data available.')"),
    ("'Prefill Classes from Website'", "(translations.prefillClassesBtnText?.[currentLanguage] || 'Prefill Classes from Website')"),
    ("'Scraping...'", "(translations.scrapingText?.[currentLanguage] || 'Scraping...')"),
    ("'Failed to load class buttons. Please check the console for errors.'", "(translations.failedLoadClassButtons?.[currentLanguage] || 'Failed to load class buttons. Please check the console for errors.')"),
    ("'N/A'", "(translations.naText?.[currentLanguage] || 'N/A')"),
]

repl_students_html = [
    ('<title>User Configuration</title>', '<title data-translate-key="configTitle">User Configuration</title>'),
    ('<h2>Student List</h2>', '<h2 data-translate-key="studentListHeading">Student List</h2>'),
    ('<th>Code</th>', '<th data-translate-key="codeHeader">Code</th>'),
    ('<th>Class</th>', '<th data-translate-key="classHeader">Class</th>'),
    ('<th>Note</th>', '<th data-translate-key="noteHeader">Note</th>'),
    ('<th>Counting Classes</th>', '<th data-translate-key="countingClassesHeader">Counting Classes</th>'),
    ('<th>Actions</th>', '<th data-translate-key="actionsHeader">Actions</th>'),
    ('<button class="class-button" onclick="addStudentConfiguration()">Add Student</button>', '<button class="class-button" onclick="addStudentConfiguration()" data-translate-key="addStudentBtnText">Add Student</button>'),
]

repl_students_js = [
    ("`Error loading students: ${error.message}`", "`${translations.errorLoadingStudents?.[currentLanguage] || 'Error loading students: '}${error.message}`"),
    ("`Students for Class: ${classFromUrl}`", "`${translations.studentsForClassText?.[currentLanguage] || 'Students for Class: '}${classFromUrl}`"),
    ("'>Edit Classes</button>'", "'>' + (translations.editClassesBtnText?.[currentLanguage] || 'Edit Classes') + '</button>'"),
    ("'>QR Code</button>'", "'>' + (translations.qrCodeBtnText?.[currentLanguage] || 'QR Code') + '</button>'"),
    ("'>Remove</button>'", "'>' + (translations.removeBtnText?.[currentLanguage] || 'Remove') + '</button>'"),
    ("`Are you sure you want to remove the student configuration:\\nCode: ${studentCode}\\nClass: ${studentClass}\\nNote: ${studentNote || '(No note)'}?`", "`${(translations.confirmRemoveStudent?.[currentLanguage] || 'Are you sure you want to remove the student configuration:\\nCode: {code}\\nClass: {class}').replace('{code}', studentCode).replace('{class}', studentClass)}\\n${translations.noteHeader?.[currentLanguage] || 'Note'}: ${studentNote || (translations.noNoteText?.[currentLanguage] || '(No note)')}?`"),
    ("'Student configuration removed successfully.'", "(translations.studentRemovedSuccess?.[currentLanguage] || 'Student configuration removed successfully.')"),
    ("`Error removing student configuration: ${data.error || 'Unknown error'}`", "`${translations.errorRemovingStudent?.[currentLanguage] || 'Error removing student configuration: '}${data.error || 'Unknown error'}`"),
    ("'Auto-generated'", "(translations.autoGeneratedText?.[currentLanguage] || 'Auto-generated')"),
    ('placeholder="Class (e.g. 9.A)"', 'placeholder="${translations.classPlaceholderText?.[currentLanguage] || \'Class (e.g. 9.A)\'}"'),
    ('placeholder="Note"', 'placeholder="${translations.notePlaceholderText?.[currentLanguage] || \'Note\'}"'),
    ("'>Save</button>'", "'>' + (translations.saveBtnText?.[currentLanguage] || 'Save') + '</button>'"),
    ("'>Cancel</button>'", "'>' + (translations.cancelBtnText?.[currentLanguage] || 'Cancel') + '</button>'"),
    ('"Class name is required."', '(translations.classNameRequiredText?.[currentLanguage] || "Class name is required.")')
]

repl_config_html = [
    ('<title>User Configuration</title>', '<title data-translate-key="configTitle">User Configuration</title>'),
    ('<h2>User Management</h2>', '<h2 data-translate-key="userManagementHeading">User Management</h2>'),
    ('<th>Username</th>', '<th data-translate-key="usernameHeader">Username</th>'),
    ('<th>Password Status</th>', '<th data-translate-key="passwordStatusHeader">Password Status</th>'),
    ('<h2>Class Management</h2>', '<h2 data-translate-key="classManagementHeading">Class Management</h2>'),
    ('<th>Teacher</th>', '<th data-translate-key="teacherHeader">Teacher</th>'),
    ('<th>Counts</th>', '<th data-translate-key="countsHeader">Counts</th>'),
    ('<button onclick="handleAddClassRow()">Add Class</button>', '<button onclick="handleAddClassRow()" data-translate-key="addClassBtnText">Add Class</button>'),
    ('<button onclick="prefillClasses()">Prefill Classes from Website</button>', '<button onclick="prefillClasses()" data-translate-key="prefillClassesBtnText">Prefill Classes from Website</button>'),
    ('<h2>Oauth Management</h2>', '<h2 data-translate-key="oauthManagementHeading">Oauth Management</h2>'),
    ('<label for="googleOauth">Enable:</label>', '<label for="googleOauth" data-translate-key="enableOauthLabel">Enable:</label>'),
    ('<th>domain</th>', '<th data-translate-key="domainHeader">domain</th>'),
    ('<button onclick="addGoogleOauthDomain()">Add Domain</button>', '<button onclick="addGoogleOauthDomain()" data-translate-key="addDomainBtnText">Add Domain</button>'),
    ('<th>Actions</th>', '<th data-translate-key="actionsHeader">Actions</th>'),
    ('<button onclick="addUser()">Add User</button>', '<button onclick="addUser()" data-translate-key="addUserBtnText">Add User</button>'),
]

repl_config_js = [
    ('"not set"', '(translations.notSetStatus?.[currentLanguage] || "not set")'),
    ('"set"', '(translations.setStatus?.[currentLanguage] || "set")'),
    ('"Google Auth"', '(translations.googleAuthStatus?.[currentLanguage] || "Google Auth")'),
    ('">Set Password</button>`', '">${translations.setPasswordBtnText?.[currentLanguage] || \'Set Password\'}</button>`'),
    ('">Reset Password</button>`', '">${translations.resetPasswordBtnText?.[currentLanguage] || \'Reset Password\'}</button>`'),
    ('">Remove</button>`', '">${translations.removeBtnText?.[currentLanguage] || \'Remove\'}</button>`'),
    ('"Enter new username:"', '(translations.enterNewUsernamePrompt?.[currentLanguage] || "Enter new username:")'),
    ('"Username cannot be empty."', '(translations.usernameEmptyError?.[currentLanguage] || "Username cannot be empty.")'),
    ('"Username already exists locally. Refresh if needed."', '(translations.usernameExistsError?.[currentLanguage] || "Username already exists locally. Refresh if needed.")'),
    ('"User added successfully!"', '(translations.userAddedSuccess?.[currentLanguage] || "User added successfully!")'),
    ('"Failed to add user"', '(translations.failedAddUser?.[currentLanguage] || "Failed to add user")'),
    ('`Failed to add user: ${errorData.error}`', '`${translations.failedAddUserPrefix?.[currentLanguage] || "Failed to add user: "}${errorData.error}`'),
    ('`Remove user ${username}?`', '`${translations.confirmRemoveUser?.[currentLanguage] || "Remove user "}${username}?`'),
    ('"Failed to remove user"', '(translations.failedRemoveUser?.[currentLanguage] || "Failed to remove user")'),
    ('"Failed to reset password"', '(translations.failedResetPassword?.[currentLanguage] || "Failed to reset password")'),
    ('"Username and new password required."', '(translations.usernamePasswordRequired?.[currentLanguage] || "Username and new password required.")'),
    ('placeholder="New Class (e.g. 1.A)"', 'placeholder="${translations.newClassPlaceholder?.[currentLanguage] || \'New Class (e.g. 1.A)\'}"'),
    ('placeholder="Teacher Name"', 'placeholder="${translations.teacherNamePlaceholder?.[currentLanguage] || \'Teacher Name\'}"'),
    ('">Save</button>"', '">${translations.saveBtnText?.[currentLanguage] || \'Save\'}</button>"'),
    ('">Cancel</button>"', '">${translations.cancelBtnText?.[currentLanguage] || \'Cancel\'}</button>"'),
    ('"Are you sure you want to scrape classes from the school website? This will add any new classes found."', '(translations.confirmScrapeClasses?.[currentLanguage] || "Are you sure you want to scrape classes from the school website? This will add any new classes found.")'),
    ('"Error loading classes."', '(translations.errorLoadingClassesText?.[currentLanguage] || "Error loading classes.")'),
    ('"Please enter a class name."', '(translations.pleaseEnterClassName?.[currentLanguage] || "Please enter a class name.")'),
    ('`Are you sure you want to remove class "${className}"?`', '`${translations.confirmRemoveClass?.[currentLanguage] || "Are you sure you want to remove class "}"${className}"?`'),
    ('"Enter the new allowed domain (e.g., example.com):"', '(translations.enterNewDomainPrompt?.[currentLanguage] || "Enter the new allowed domain (e.g., example.com):")'),
    ('"Domain name cannot be empty."', '(translations.domainEmptyError?.[currentLanguage] || "Domain name cannot be empty.")'),
]

repl_change_password_html = [
    ('<title>Change Password - Color Days</title>', '<title data-translate-key="changePasswordTitle">Change Password - Color Days</title>'),
    ('<label for="old_password">Old password:</label>', '<label for="old_password" data-translate-key="oldPasswordLabel">Old password:</label>'),
    ('<label for="password">New password:</label>', '<label for="password" data-translate-key="newPasswordLabel">New password:</label>'),
    ('<button type="submit" class="btn-primary">Change Password</button>', '<button type="submit" class="btn-primary" data-translate-key="changePasswordHeading">Change Password</button>'),
]

repl_change_password_js = [
    ("'Invalid password.'", "(translations.invalidPasswordError?.[currentLanguage] || 'Invalid password.')"),
    ("'Change password request failed. Please check your connection or contact support.'", "(translations.changePasswordRequestFailed?.[currentLanguage] || 'Change password request failed. Please check your connection or contact support.')"),
]

repl_student_is_counting_html = [
    ('<title>User Configuration</title>', '<title data-translate-key="studentIsCountingTitle">Student Counting Configuration</title>'),
    ('<th>Class</th>', '<th data-translate-key="classHeader">Class</th>'),
    ('<th>Counts</th>', '<th data-translate-key="countsHeader">Counts</th>'),
    ('<th>Is Counted By</th>', '<th data-translate-key="isCountedByHeader">Is Counted By</th>'),
]

repl_student_is_counting_js = [
    ("'Error: Student Code Missing'", "(translations.errorStudentCodeMissing?.[currentLanguage] || 'Error: Student Code Missing')"),
    ("'No student code provided in the URL.'", "(translations.noStudentCodeUrl?.[currentLanguage] || 'No student code provided in the URL.')"),
    ("'Error: Day Parameter Invalid'", "(translations.errorDayParameterInvalid?.[currentLanguage] || 'Error: Day Parameter Invalid')"),
    ("'Day parameter is missing or invalid (must be 1, 2, or 3).'", "(translations.dayParameterMissing?.[currentLanguage] || 'Day parameter is missing or invalid (must be 1, 2, or 3).')"),
    ("`This student's class is not assigned to count any classes on ${dayNames[day]}.`", "`${translations.studentNotAssignedAnyClasses?.[currentLanguage] || 'This student\\'s class is not assigned to count any classes on '}${translations['day'+dayNames[day]]?.[currentLanguage] || dayNames[day]}.`"),
    ("'N/A'", "(translations.naText?.[currentLanguage] || 'N/A')"),
]

base_dir = '/Users/david/code/ColorDays/frontend/'
def apply_repl(file_name, repl_list):
    replace_in_file(base_dir + file_name, repl_list)

apply_repl('index.html', repl_index_html)
apply_repl('script.js', repl_script_js)
apply_repl('leaderboard.html', repl_leaderboard_html)
apply_repl('leaderboard.js', repl_leaderboard_js)
apply_repl('login.html', repl_login_html)
apply_repl('login.js', repl_login_js)
apply_repl('menu.html', repl_menu_html)
apply_repl('menu.js', repl_menu_js)
apply_repl('classes.html', repl_classes_html)
apply_repl('classes.js', repl_classes_js)
apply_repl('students.html', repl_students_html)
apply_repl('students.js', repl_students_js)
apply_repl('config.html', repl_config_html)
apply_repl('config.js', repl_config_js)
apply_repl('change-password.html', repl_change_password_html)
apply_repl('change-password.js', repl_change_password_js)
apply_repl('student-is-counting.html', repl_student_is_counting_html)
apply_repl('student-is-counting.js', repl_student_is_counting_js)

print("done")

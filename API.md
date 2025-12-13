# ColorDays API Endpoints

## Authentication Endpoints

### POST /login
Login with username and password.
- **Body:** `{ "username": "...", "password": "..." }`
- **Response:** `{ "success": true, "message": "...", "username": "...", "role": "..." }`
- **Sets Cookies:** ColorDaysUser, ColorDaysSession, SQLAuthUser

### POST /login/student
Login with student code.
- **Body:** `{ "code": "..." }`
- **Response:** `{ "success": true, "message": "...", "note": "...", "class": "..." }`
- **Sets Cookies:** ColorDaysSession, ColorDaysUser, SQLAuthUserStudent

### GET /login/google
Initiate Google OAuth login flow.
- **Redirects to:** Google OAuth consent screen

### GET /oauth2callback
OAuth callback handler (called by Google).
- **Sets Cookies:** ColorDaysUser, ColorDaysSession, GOOGLE_COOKIE_NAME

### POST /logout
Logout and clear session.
- **Response:** `{ "success": true, "message": "Logged out successfully" }`
- **Clears all auth cookies**

### POST /api/auth/change
Change password for current user.
- **Auth Required:** Yes
- **Body:** `{ "currentPassword": "...", "newPassword": "..." }`
- **Response:** `{ "success": true, "message": "..." }`

## User Management (Admin Only)

### GET /api/users
List all users.
- **Auth Required:** Admin
- **Response:** Array of `{ "username": "...", "role": "..." }`

### POST /api/users
Add a new user.
- **Auth Required:** Admin
- **Body:** `{ "username": "...", "password": "..." }` (password optional)
- **Response:** `{ "message": "User added" }`

### POST /api/users/remove
Remove a user.
- **Auth Required:** Admin
- **Body:** `{ "username": "..." }`
- **Response:** `{ "success": true, "message": "..." }`

### POST /api/users/set
### POST /api/users/reset
Set/reset user password.
- **Auth Required:** Admin
- **Body:** `{ "username": "...", "password": "..." }`
- **Response:** `{ "success": true, "message": "..." }`

## Class Management

### GET /api/classes
Get all classes.
- **Auth Required:** Admin, Teacher, or Student
- **Response:** Array of class objects with fields:
  - `class`, `teacher`, `counts1`, `counts2`, `counts3`
  - `iscountedby1`, `iscountedby2`, `iscountedby3`

### POST /api/classes/add
Add a new class.
- **Auth Required:** Admin
- **Body:** `{ "class": "...", "teacher": "...", "counts1": "T/F", "counts2": "T/F", "counts3": "T/F", "iscountedby1": "...", "iscountedby2": "...", "iscountedby3": "..." }`
- **Response:** `{ "success": true, "message": "..." }`

### POST /api/classes/remove
Remove a class.
- **Auth Required:** Admin
- **Body:** `{ "class": "..." }`
- **Response:** `{ "success": true, "message": "..." }`

### POST /api/classes/update_counts
Update whether a class counts on a specific day.
- **Auth Required:** Admin
- **Body:** `{ "class": "...", "countField": "counts1/counts2/counts3", "value": "T/F" }`
- **Response:** `{ "success": true, "message": "..." }`

### POST /api/classes/update_iscountedby
Update which class is responsible for counting another class.
- **Auth Required:** Admin or Teacher
- **Body:** `{ "class": "...", "dayIdentifier": "1/2/3", "value": "..." }`
- **Response:** `{ "success": true, "message": "..." }`

## Student Management

### GET /api/students
Get all students (or filtered for student sessions).
- **Auth Required:** Admin, Teacher, or Student
- **Response:** Array of student objects with fields:
  - `code`, `class`, `note`, `counts_classes` (or `counts_classes_str`)

### POST /api/students/add
Add a new student.
- **Auth Required:** Admin or Teacher
- **Body:** `{ "class": "...", "note": "..." }`
- **Response:** `{ "success": true, "message": "..." }`
- **Note:** Server generates the student code automatically

### POST /api/students/remove
Remove a student.
- **Auth Required:** Admin or Teacher
- **Body:** `{ "code": "..." }`
- **Response:** `{ "success": true, "message": "..." }`

### POST /api/student/update-counting-class
Update which classes a student counts.
- **Auth Required:** Admin or Teacher
- **Body:** `{ "studentCode": "...", "classToUpdate": "...", "isCounting": true/false }`
- **Response:** `{ "success": true, "message": "..." }`

### GET /api/student/counting-details
Get details about what a student should count.
- **Auth Required:** Student session
- **Query Params:** `code=...&day=1/2/3`
- **Response:** `{ "success": true, "class_to_count": "...", "student_class": "...", "day": "..." }`

## Count Data

### GET /api/counts
Get count data for a specific class and day.
- **Auth Required:** Admin, Teacher, or Student (with permission)
- **Query Params:** `class=...&day=monday/tuesday/wednesday`
- **Response:** Array of `{ "type": "student/teacher", "points": 0-6, "count": ... }`

### POST /api/increment
Increment a count value.
- **Auth Required:** Admin, Teacher, or Student (with permission)
- **Body:** `{ "className": "...", "type": "student/teacher", "points": 0-6, "day": "monday/tuesday/wednesday" }`
- **Response:** `{ "success": true, "message": "..." }`

### POST /api/decrement
Decrement a count value.
- **Auth Required:** Admin, Teacher, or Student (with permission)
- **Body:** `{ "className": "...", "type": "student/teacher", "points": 0-6, "day": "monday/tuesday/wednesday" }`
- **Response:** `{ "success": true, "message": "..." }`

## Configuration

### GET /api/data/config
Get server configuration.
- **Auth Required:** No
- **Response:** `{ "DOMAIN": "...", "PORT": ..., "oauth_eneabled": "true/false", "allowed_oauth_domains": [...], "can_students_count_their_own_class": "true/false", "default_language": "en/cs", "smart_sorting": "true/false" }`

### POST /api/data/save/config
Save server configuration.
- **Auth Required:** Admin
- **Body:** Configuration object
- **Response:** `{ "message": "..." }`

### GET /api/translations
Get language translations.
- **Auth Required:** No
- **Response:** Translation object with cs/en keys

### POST /api/language/set
Set user language preference.
- **Auth Required:** No
- **Body:** `{ "language": "cs/en" }`
- **Response:** `{ "message": "..." }`
- **Sets Cookie:** language

## Authorization Levels

- **Public:** No authentication required
- **Student:** Requires student session (SQLAuthUserStudent cookie)
- **Teacher:** Requires teacher role
- **Admin:** Requires administrator role

## Common Response Codes

- **200:** Success
- **201:** Created
- **204:** No Content (OPTIONS requests)
- **400:** Bad Request (missing/invalid parameters)
- **401:** Unauthorized (not logged in)
- **403:** Forbidden (insufficient permissions)
- **404:** Not Found
- **409:** Conflict (resource already exists)
- **500:** Internal Server Error
- **501:** Not Implemented (unsupported HTTP method)

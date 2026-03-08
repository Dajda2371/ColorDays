import json

path = '/Users/david/code/ColorDays/backend/data/language_translations.json'

with open(path, 'r', encoding='utf-8') as f:
    translations = json.load(f)

new_keys = {
    "errorSpecificClassAssignments": {"en": "Could not load your specific class assignments. Showing all available classes.", "cs": "Nepodařilo se načíst vaše konkrétní přiřazení tříd. Zobrazují se všechny dostupné třídy."},
    "errorAssignedClasses": {"en": "Could not load your assigned classes. You may not be assigned to any.", "cs": "Nepodařilo se načíst vaše přiřazené třídy. Možná nejste k žádné přiřazeni."},
    "errorLoadingClassesSuffix": {"en": "Error loading classes: {error}. Please try again later or contact support.", "cs": "Chyba při načítání tříd: {error}. Zkuste to prosím znovu později nebo kontaktujte podporu."},
    "errorMainClassNotSet": {"en": "Your main class is not set. Cannot determine days to display.", "cs": "Vaše hlavní třída není nastavena. Nelze určit dny k zobrazení."},
    "serverErrorText": {"en": "Server error", "cs": "Chyba serveru"},
    "unknownErrorText": {"en": "Unknown error", "cs": "Neznámá chyba"}
}
translations.update(new_keys)

with open(path, 'w', encoding='utf-8') as f:
    json.dump(translations, f, indent=2, ensure_ascii=False)

import os
def replace_in_file(file_path, replacements):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        for old_str, new_str in replacements:
            content = content.replace(old_str, new_str)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    except Exception as e:
        print(f"Error in {file_path}: {e}")

repl_menu_js = [
    ('"Could not load your specific class assignments. Showing all available classes."', '(translations.errorSpecificClassAssignments?.[currentLanguage] || "Could not load your specific class assignments. Showing all available classes.")'),
    ('"Could not load your assigned classes. You may not be assigned to any."', '(translations.errorAssignedClasses?.[currentLanguage] || "Could not load your assigned classes. You may not be assigned to any.")'),
    ('`Error loading classes: ${error.message}. Please try again later or contact support.`', '`${(translations.errorLoadingClassesSuffix?.[currentLanguage] || "Error loading classes: {error}. Please try again later or contact support.").replace("{error}", error.message)}`'),
    ('"Your main class is not set. Cannot determine days to display."', '(translations.errorMainClassNotSet?.[currentLanguage] || "Your main class is not set. Cannot determine days to display.")'),
    ("'Unknown server error'", "(translations.unknownErrorText?.[currentLanguage] || 'Unknown server error')"),
    ("'Server error'", "(translations.serverErrorText?.[currentLanguage] || 'Server error')")
]

replace_in_file('/Users/david/code/ColorDays/frontend/menu.js', repl_menu_js)
print("done")

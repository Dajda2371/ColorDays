import os
import glob
import json

path = '/Users/david/code/ColorDays/backend/data/language_translations.json'

with open(path, 'r', encoding='utf-8') as f:
    translations = json.load(f)

new_keys = {
    "usernamePlaceholder": {"en": "Username", "cs": "Uživatelské jméno"},
    "passwordPlaceholder": {"en": "Password", "cs": "Heslo"},
    "newPasswordPlaceholder": {"en": "New Password", "cs": "Nové heslo"}
}
translations.update(new_keys)

with open(path, 'w', encoding='utf-8') as f:
    json.dump(translations, f, indent=2, ensure_ascii=False)

def update_apply(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        old_func = """function applyTranslations() {
    document.querySelectorAll('[data-translate-key]').forEach(element => {
        const key = element.getAttribute('data-translate-key');
        if (translations[key] && translations[key][currentLanguage]) {
            element.textContent = translations[key][currentLanguage];
        } else if (translations[key] && translations[key]['en']) {
            element.textContent = translations[key]['en'];
        }
    });
}"""

        new_func = """function applyTranslations() {
    document.querySelectorAll('[data-translate-key]').forEach(element => {
        const key = element.getAttribute('data-translate-key');
        const text = translations[key]?.[currentLanguage] || translations[key]?.['en'];
        if (text) {
            if (element.tagName === 'INPUT') {
                element.placeholder = text;
            } else {
                element.textContent = text;
            }
        }
    });
}"""

        # for slight variations
        import re
        content = re.sub(
            r'function applyTranslations\(\) \{.*?\}\);?\n\}', 
            new_func, 
            content, 
            flags=re.DOTALL
        )
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    except Exception as e:
        print(f"Error in {file_path}: {e}")

js_files = glob.glob('/Users/david/code/ColorDays/frontend/*.js')
for jf in js_files:
    update_apply(jf)

# update config.html
def update_html(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    content = content.replace('placeholder="Username"', 'placeholder="Username" data-translate-key="usernamePlaceholder"')
    content = content.replace('placeholder="Password"', 'placeholder="Password" data-translate-key="passwordPlaceholder"')
    content = content.replace('placeholder="New Password"', 'placeholder="New Password" data-translate-key="newPasswordPlaceholder"')
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

update_html('/Users/david/code/ColorDays/frontend/config.html')
print("done")

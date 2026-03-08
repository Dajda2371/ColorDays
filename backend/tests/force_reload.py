import os
import glob
import re

files = glob.glob('/Users/david/code/ColorDays/frontend/*.js')

for f in files:
    with open(f, 'r') as file:
        content = file.read()
    
    # We want to replace:
    #             currentLanguage = lang;
    #             applyTranslations();
    #             displayLoggedInUser();
    # Or just inject window.location.reload(); after currentLanguage = lang; inside setLanguagePreference
    
    # Let's replace:
    #             currentLanguage = lang;
    #             applyTranslations();
    
    new_content = re.sub(
        r'(currentLanguage\s*=\s*lang;\s*applyTranslations\(\);)',
        r'\1 window.location.reload();',
        content
    )
    
    if new_content != content:
        with open(f, 'w') as file:
            file.write(new_content)
        print(f"Updated {f}")
    else:
        print(f"No change or already updated: {f}")
        
    # Also fix where applyTranslations doesn't have displayLoggedInUser
    # Actually the regex above captures currentLanguage = lang; applyTranslations(); which is present in almost all.

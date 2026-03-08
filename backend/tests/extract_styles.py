import re
import os
import hashlib

def process_file(filepath, css_file):
    with open(filepath, 'r') as f:
        content = f.read()

    # 1. Extract <style> blocks
    style_blocks = re.findall(r'<style>(.*?)</style>', content, flags=re.IGNORECASE|re.DOTALL)
    
    # Remove <style> blocks
    content = re.sub(r'<style>.*?</style>\s*', '', content, flags=re.IGNORECASE|re.DOTALL)

    new_css = ""
    for block in style_blocks:
        if "Reuse styles from menu.html" not in css_file_content: # deduplicate common nav
            new_css += block + "\n"
        elif "Reuse styles from menu.html" in block:
            pass # skip
        else:
            new_css += block + "\n"

    # 2. Extract style=""
    def replacer(match):
        nonlocal new_css
        style_content = match.group(1)
        # Check if already added 
        class_hash = "inline-style-" + hashlib.md5(style_content.encode()).hexdix()[:6]
        # or better: we just map the specific ones we know
        return match.group(0) # We'll do inline manually to give better class names
    
    # Actually, let's just use auto-generated class names for the inline styles.
    # Wait, the qr code modal in students.html is toggled by JS using inline styles! 
    # display:none gets changed. We probably should not extract display:none for modals that use inline style to toggle.
    # I'll just write a regex to replace these and prepend to css.
    inline_styles = re.findall(r'style="([^"]+)"', content)

    for style_val in inline_styles:
        # Ignore display:none as it breaks inline toggle scripts unless we handle it carefully
        # In students.html: document.getElementById('qrModal').style.display = 'flex';
        # If we remove inline style, the initial display might not be none if we extract it.
        # It's safer to extract them and apply specific classes.
        pass

    with open(filepath, 'w') as f:
        f.write(content)
        
    return style_blocks

with open('frontend/style.css', 'r') as f:
    css_file_content = f.read()

files = [
    "frontend/menu.html",
    "frontend/classes.html",
    "frontend/config.html",
    "frontend/change-password.html",
    "frontend/students.html",
    "frontend/student-is-counting.html",
    "frontend/index.html",
    "frontend/login.html",
    "frontend/leaderboard.html"
]

all_new_css = ""

# Track the big menu style block
menu_style_added = False

for file in files:
    with open(file, 'r') as f:
        content = f.read()
    
    style_blocks = re.findall(r'<style>(.*?)</style>', content, flags=re.IGNORECASE|re.DOTALL)
    content = re.sub(r'<style>.*?</style>\s*', '', content, flags=re.IGNORECASE|re.DOTALL)
    
    for block in style_blocks:
        if "Reuse styles" in block or "#leftSideContainer" in block:
            if not menu_style_added:
                all_new_css += block + "\n"
                menu_style_added = True
        else:
            all_new_css += block + "\n"
            
    with open(file, 'w') as f:
        f.write(content)

with open('frontend/style.css', 'a') as f:
    f.write("\n" + all_new_css)


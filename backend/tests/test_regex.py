import re
import requests
import html
import urllib3
urllib3.disable_warnings()
headers = {'User-Agent': 'Mozilla/5.0'}
response = requests.get("https://www.skolastenovice.cz/kontakty/", verify=False, headers=headers)
content = response.text
matches = re.findall(r'<td[^>]*>\s*(\d+\.[A-Z])\s*</td>\s*<td[^>]*>\s*(.*?)\s*</td>', content, re.IGNORECASE | re.DOTALL)
found = {}
for cls, t in matches:
    if cls not in found:
        found[cls] = html.unescape(t).strip()
print(sorted(found.items()))

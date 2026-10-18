import re

with open('js/app.js', encoding='utf-8') as f:
    code = f.read()

tabs = set(re.findall(r"switchTab\(['\"]([^'\"]+)['\"]", code))
print("All switchTab calls in app.js:", tabs)

# Look for admin functions
admin_funcs = re.findall(r"(\w*[aA]dmin\w*)\s*\(", code)
print("Admin related functions:", set(admin_funcs))

with open('index.html', encoding='utf-8') as f:
    html = f.read()

admin_ids = re.findall(r'id=["\']([^"\']*[aA]dmin[^"\']*)["\']', html)
print("Admin element IDs in index.html:", set(admin_ids))

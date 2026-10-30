import os

sync_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scripts', 'sync_engine.py'))
with open(sync_path, 'r', encoding='utf-8') as f:
    text = f.read()

target1 = '''                for m in openfile_pattern.finditer(panel_html):
                    furl = m.group(1).strip()
                    flabel = clean_html(m.group(2)).upper()
                    if not furl.startswith("http"):
                        furl = BASE_URL + furl.lstrip("/")
                    found_files.append((furl, flabel))'''

replacement1 = '''                for m in openfile_pattern.finditer(panel_html):
                    furl = m.group(1).strip()
                    flabel = clean_html(m.group(2)).upper()
                    if not furl.lower().endswith('.pdf') and '.pdf' not in furl.lower():
                        continue
                    if not furl.startswith("http"):
                        furl = BASE_URL + furl.lstrip("/")
                    found_files.append((furl, flabel))'''

target2 = '''                for fm in href_pattern.finditer(body_html):
                    furl = fm.group(1).strip()
                    flabel = clean_html(fm.group(2)).upper()
                    if not furl.startswith("http"):
                        furl = BASE_URL + furl.lstrip("/")
                    found_files.append((furl, flabel))'''

replacement2 = '''                for fm in href_pattern.finditer(body_html):
                    furl = fm.group(1).strip()
                    flabel = clean_html(fm.group(2)).upper()
                    if not furl.lower().endswith('.pdf') and '.pdf' not in furl.lower():
                        continue
                    if not furl.startswith("http"):
                        furl = BASE_URL + furl.lstrip("/")
                    found_files.append((furl, flabel))'''

if target1 in text:
    text = text.replace(target1, replacement1, 1)
    print('Patched target 1 in sync_engine.py')
if target2 in text:
    text = text.replace(target2, replacement2, 1)
    print('Patched target 2 in sync_engine.py')

with open(sync_path, 'w', encoding='utf-8') as f:
    f.write(text)

print('Updated sync_engine.py successfully.')

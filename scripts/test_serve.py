import urllib.request

html = urllib.request.urlopen("http://localhost:8080/").read().decode("utf-8")
print('data-tab="model-papers" in HTML:', 'data-tab="model-papers"' in html)
print('id="modelPapersSection" in HTML:', 'id="modelPapersSection"' in html)
print('modelNavCountBadge in HTML:', 'id="modelNavCountBadge"' in html)

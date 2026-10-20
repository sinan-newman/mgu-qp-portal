import urllib.request

html = urllib.request.urlopen("http://localhost:8080/").read().decode("utf-8")
print('headerModelCount in HTML (should be False):', 'id="headerModelCount"' in html)
print('statTotalModelPapers in banner (should be True):', 'id="statTotalModelPapers"' in html)
print('modelPapersSection in HTML (should be False):', 'id="modelPapersSection"' in html)
print('data-tab="model-papers" in HTML (should be False):', 'data-tab="model-papers"' in html)
print('data-tab="departments" in HTML (should be True):', 'data-tab="departments"' in html)
print('data-tab="papers" in HTML (should be True):', 'data-tab="papers"' in html)

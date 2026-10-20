import urllib.request

html = urllib.request.urlopen("http://localhost:8080/").read().decode("utf-8")
print('headerModelCount in HTML:', 'id="headerModelCount"' in html)
print('statTotalModelPapers in HTML:', 'id="statTotalModelPapers"' in html)
print('modelNavCountBadge in HTML:', 'id="modelNavCountBadge"' in html)

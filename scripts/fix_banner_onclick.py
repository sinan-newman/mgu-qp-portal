for path in ['index.html', 'public/index.html']:
    with open(path, 'r', encoding='utf-8') as f:
        c = f.read()
    c = c.replace("onclick=\"App.switchTab('model-papers')\" title=\"Browse 1,649 Model Question Papers\"", "onclick=\"App.switchTab('papers')\" title=\"1,649 Model Question Papers available with course papers\"")
    with open(path, 'w', encoding='utf-8') as f:
        f.write(c)
print('Updated banner stat onclick!')

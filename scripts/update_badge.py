for path in ['index.html', 'public/index.html']:
    with open(path, 'r', encoding='utf-8') as f:
        c = f.read()
    c = c.replace('>2,176<', '>1,649<')
    c = c.replace('2,176 Model', '1,649 Model')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(c)
print('Updated badges to 1,649!')

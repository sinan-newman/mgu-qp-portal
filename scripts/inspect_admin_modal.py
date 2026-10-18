with open('index.html', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'id="adminModal"' in l:
        print("adminModal starts at line:", i+1)
        for j in range(i, min(len(lines), i+120)):
            print(f"{j+1}: {lines[j]}", end="")
        break

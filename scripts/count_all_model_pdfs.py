import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

content_path = r"C:\Users\Navirex\.gemini\antigravity\brain\87d52a0b-0a87-4dfd-b1bf-99a37fa42aef\.system_generated\steps\1921\content.md"

with open(content_path, "r", encoding="utf-8") as f:
    html = f.read()

start = html.find("1st Semester")
content = html[start:]

sem_positions = [(m.start(), m.group(1)) for m in re.finditer(r'([1-8](?:st|nd|rd|th)\s+Semester)', content, re.IGNORECASE)]

all_entries = []

for i in range(len(sem_positions)):
    s_pos = sem_positions[i][0]
    e_pos = sem_positions[i+1][0] if i+1 < len(sem_positions) else len(content)
    s_name = sem_positions[i][1]
    sec = content[s_pos:e_pos]
    
    # sem number
    sem_num = int(re.search(r'([1-8])', s_name).group(1))
    
    links = re.findall(r'<a[^>]+href=[\"\']([^\"\']+\.pdf[^\"\']*)[\"\'][^>]*>(.*?)</a>', sec, re.IGNORECASE | re.DOTALL)
    print(f"{s_name}: {len(links)} PDFs")
    
    for href, ltext in links:
        clean_text = re.sub(r'<[^>]+>', ' ', ltext).strip()
        clean_href = href.split("?")[0].strip()
        all_entries.append({
            "semester": sem_num,
            "label": clean_text,
            "url": clean_href
        })

print(f"\nTotal PDF files across all semesters on page: {len(all_entries)}")

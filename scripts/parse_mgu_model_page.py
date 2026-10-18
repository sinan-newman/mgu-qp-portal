import sys
import re
from html.parser import HTMLParser

sys.stdout.reconfigure(encoding='utf-8')

content_path = r"C:\Users\Navirex\.gemini\antigravity\brain\87d52a0b-0a87-4dfd-b1bf-99a37fa42aef\.system_generated\steps\1921\content.md"

with open(content_path, "r", encoding="utf-8") as f:
    html = f.read()

# Let's locate the entry content
start = html.find("1st Semester")
content = html[start:]

# Split by semester headings or scan sequentially
# Find positions of "1st Semester", "2nd Semester", "3rd Semester", "4th Semester", "5th Semester", etc.
sem_positions = []
for m in re.finditer(r'([1-8](?:st|nd|rd|th)\s+Semester)', content, re.IGNORECASE):
    sem_positions.append((m.start(), m.group(1)))

# Also check for other headers like "5th Semester" or similar
print("Found semester positions:")
for pos, name in sem_positions:
    print(f" - {name} at position {pos}")

# For each section, let's extract all tables and links
for i in range(len(sem_positions)):
    start_pos = sem_positions[i][0]
    end_pos = sem_positions[i+1][0] if i+1 < len(sem_positions) else len(content)
    sem_name = sem_positions[i][1]
    sec_html = content[start_pos:end_pos]
    
    # Extract links in this section
    # Check for THEORY vs PRACTICAL
    theory_pos = sec_html.find("THEORY")
    pract_pos = sec_html.find("PRACTICAL")
    
    links = re.findall(r'<a[^>]+href=[\"\']([^\"\']+\.pdf[^\"\']*)[\"\'][^>]*>(.*?)</a>', sec_html, re.IGNORECASE | re.DOTALL)
    print(f"\n==============================")
    print(f"=== {sem_name.upper()}: {len(links)} PDF files ===")
    print(f"==============================")
    for href, link_text in links:
        clean_text = re.sub(r'<[^>]+>', ' ', link_text).strip()
        clean_href = href.split("?")[0].strip()
        fname = clean_href.split("/")[-1]
        print(f"  {clean_text:35} | {fname}")

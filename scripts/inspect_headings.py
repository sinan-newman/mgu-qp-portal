import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

content_path = r"C:\Users\Navirex\.gemini\antigravity\brain\87d52a0b-0a87-4dfd-b1bf-99a37fa42aef\.system_generated\steps\1921\content.md"

with open(content_path, "r", encoding="utf-8") as f:
    text = f.read()

# Let's find all headers with Semester or Theory/Practical
headers = re.findall(r'<h[1-6][^>]*>(.*?)</h[1-6]>', text, re.IGNORECASE | re.DOTALL)
print("=== Headings on MGU Model QP page ===")
for h in headers:
    clean = re.sub(r'<[^>]+>', ' ', h).strip()
    if clean:
        print("HEADER:", clean)

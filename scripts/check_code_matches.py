import json
import csv

with open('data/papers.json', 'r', encoding='utf-8') as f:
    papers = json.load(f)

# Parse user codes from parse_user_csv
from parse_user_csv import code_to_entry, dept_map

print(f"Total papers: {len(papers)}")

# Check matching papers for each code
code_paper_counts = {}
for p in papers:
    code = p.get('dept_code', '')
    pdept = p.get('parent_dept', '')
    ccode = p.get('course_code', '')
    
    # Check if 3-letter dept code is in code_to_entry
    if code in code_to_entry:
        code_paper_counts[code] = code_paper_counts.get(code, 0) + 1
    elif pdept in code_to_entry:
        code_paper_counts[pdept] = code_paper_counts.get(pdept, 0) + 1

print("\nPaper counts for user codes:")
for code, info in sorted(code_to_entry.items()):
    cnt = code_paper_counts.get(code, 0)
    # Also search by course_code substring
    sub_cnt = sum(1 for p in papers if code in p.get('course_code', ''))
    if cnt > 0 or sub_cnt > 0:
        print(f"Code {code} ({info['programme']}) [{info['department']}] [Minor={info['is_minor']}]: direct={cnt}, in_course_code={sub_cnt}")

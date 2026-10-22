import json
import re

with open("data/papers.json", "r", encoding="utf-8") as f:
    papers = json.load(f)

print(f"Total papers in database: {len(papers)}")

gen_papers = [p for p in papers if p.get("dept_code") == "GEN" or p.get("parent_dept") == "GEN"]
print(f"Total classified as GEN (General Studies): {len(gen_papers)}")

def is_ambiguous(p):
    cc = (p.get("course_code") or "").strip().upper()
    title = (p.get("title") or "").strip()
    dept = (p.get("dept_code") or "").strip().upper()
    
    # 1. Classified under General Studies
    if dept == "GEN":
        return True
    
    # 2. No valid FYUGP course code pattern: MG[1-8][A-Z]{3}[A-Z]{2,5}[A-Z0-9]{3}
    if not cc or not re.match(r'^MG[1-8][A-Z]{5,10}[A-Z0-9]{3}$', cc):
        return True
        
    # 3. Placeholder or generic title
    title_lower = title.lower()
    if title_lower.startswith("course ") or title_lower in ("question paper", "general studies", "evaluation scheme", "", "scheme", "model question paper"):
        return True
        
    return False

ambiguous = [p for p in papers if is_ambiguous(p)]
print(f"Total ambiguous papers needing resolution: {len(ambiguous)}")

print("\n--- Breakdown of Ambiguous Papers ---")
gen_only = [p for p in ambiguous if p.get("dept_code") == "GEN"]
generic_title_only = [p for p in ambiguous if p.get("dept_code") != "GEN" and p.get("title", "").lower().startswith("course ")]
invalid_code_only = [p for p in ambiguous if not re.match(r'^MG[1-8][A-Z]{5,10}[A-Z0-9]{3}$', (p.get("course_code") or "").strip().upper())]

print(f"1. General Studies (GEN) Dept: {len(gen_only)}")
print(f"2. Valid code but generic 'Course ...' title: {len(generic_title_only)}")
print(f"3. Invalid or missing course code: {len(invalid_code_only)}")

print("\nSample 25 Ambiguous Papers:")
for p in ambiguous[:25]:
    files_str = f"QP:{bool(p.get('qp_url'))} Scheme:{bool(p.get('scheme_url'))} Models:{len(p.get('model_papers', []))}"
    url = p.get('qp_url') or p.get('scheme_url') or (p.get('model_papers', [{}])[0].get('cdn_url') if p.get('model_papers') else '')
    print(f"ID: {p.get('id'):20} | QP: {str(p.get('qp_code')):8} | Code: {str(p.get('course_code')):14} | Dept: {str(p.get('dept_code')):4} | Title: {p.get('title')[:35]:35} | {files_str} | URL: {url[:50]}")

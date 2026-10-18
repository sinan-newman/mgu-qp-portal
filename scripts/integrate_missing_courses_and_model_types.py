"""
integrate_missing_courses_and_model_types.py
============================================
1. Enriches all courses in papers.json with practical vs theory model QP metadata.
2. For all courses that have a model question paper but no actual past exam paper yet (213 courses),
   creates a valid course entry in papers.json so they appear on the portal and catalog!
3. Re-syncs to public/data/papers.json.
"""

import json
import os
import re

DATA_DIR = r"C:\Users\Navirex\.gemini\antigravity\scratch\mgu-qp-portal\data"
PUB_DATA_DIR = r"C:\Users\Navirex\.gemini\antigravity\scratch\mgu-qp-portal\public\data"

with open(os.path.join(DATA_DIR, "papers.json"), "r", encoding="utf-8") as f:
    papers = json.load(f)

with open(os.path.join(DATA_DIR, "model_papers.json"), "r", encoding="utf-8") as f:
    all_models = json.load(f)

with open(os.path.join(DATA_DIR, "departments.json"), "r", encoding="utf-8") as f:
    depts_list = json.load(f)

dept_map = {d.get("code"): d.get("name") for d in depts_list if d.get("code")}

# Map models by course_code
models_by_code = {}
for m in all_models:
    cc = m.get("course_code")
    if not cc or cc.startswith("SEM") or "click_here" in cc.lower():
        continue
    cc = cc.strip().upper()
    if cc not in models_by_code:
        models_by_code[cc] = []
    
    # Determine if practical or theory
    title = m.get("title", "")
    src = m.get("source_pdf", "")
    is_pract = bool(re.search(r'practical|lab|experiment', title + " " + src, re.IGNORECASE))
    
    models_by_code[cc].append({
        "id": m.get("model_id"),
        "title": ("Official Practical Model Paper" if is_pract else "Official Theory Model Paper") if len(models_by_code[cc]) > 0 or is_pract else "Official Model Question Paper (FYUGP 2024)",
        "paper_type": "PRACTICAL" if is_pract else "THEORY",
        "pages": m.get("pages", 2),
        "url": m.get("cdn_url") or f"https://cdn.jsdelivr.net/gh/sinan-newman/mgu-qp-storage@main/pdf/{m.get('filename')}",
        "raw_url": m.get("raw_url") or f"https://raw.githubusercontent.com/sinan-newman/mgu-qp-storage/main/pdf/{m.get('filename')}",
        "filename": m.get("filename")
    })

print(f"Total course codes with model papers: {len(models_by_code)}")

# Check existing courses
existing_codes = set()
for p in papers:
    cc = (p.get("course_code") or "").strip().upper()
    if cc:
        existing_codes.add(cc)
        if cc in models_by_code:
            p["model_papers"] = models_by_code[cc]

print(f"Existing unique courses in papers.json: {len(existing_codes)}")

# Create course cards for the orphan courses that have model papers!
orphan_codes = set(models_by_code.keys()) - existing_codes
print(f"Creating new course entries for {len(orphan_codes)} orphan courses with model papers...")

course_type_names = {
    "DSC": "Discipline Specific Core",
    "DSE": "Discipline Specific Elective",
    "MDC": "Multidisciplinary Course",
    "AEC": "Ability Enhancement Course",
    "SEC": "Skill Enhancement Course",
    "VAC": "Value Added Course",
    "CCR": "Common Core",
    "SDC": "Skill Development Course",
    "MPC": "Minor Pathway Course"
}

added_count = 0
for cc in sorted(orphan_codes):
    mps = models_by_code[cc]
    first_m = mps[0]
    
    # Parse code: MG[1-8]([A-Z]{3})([A-Z]{3})?
    m_parse = re.match(r'^MG([1-8])([A-Z]{3})([A-Z]{3})?', cc)
    sem = 1
    ctype = "DSC"
    dept_code = "GEN"
    if m_parse:
        sem = int(m_parse.group(1))
        ctype = m_parse.group(2)
        dept_code = m_parse.group(3) or "GEN"
    
    dept_name = dept_map.get(dept_code, dept_code)
    title = first_m.get("title", "").replace("Official Model Question Paper (FYUGP 2024)", "").strip()
    if not title or title.startswith("Official"):
        # find in all_models
        for am in all_models:
            if am.get("course_code") == cc and am.get("title"):
                title = am.get("title").title()
                break
    if not title or title.startswith("Official"):
        title = f"{dept_name} {course_type_names.get(ctype, ctype)}"

    new_entry = {
        "id": f"model_only_{cc}",
        "qp_code": "AWAITED",
        "course_code": cc,
        "title": title,
        "raw_header": f"{cc} - {title}",
        "semester": sem,
        "semester_label": f"Semester {sem}",
        "course_type": ctype,
        "course_type_name": course_type_names.get(ctype, ctype),
        "dept_code": dept_code,
        "dept_name": dept_name,
        "parent_dept": dept_code,
        "parent_dept_name": dept_name,
        "is_minor": False,
        "exam_id": "model_catalog",
        "exam_name": "FYUGP 2024 (Exam Question Paper Awaited)",
        "batch": "2024 Admission",
        "is_fyugp": True,
        "has_qp": False,
        "qp_url": "",
        "has_scheme": False,
        "scheme_url": "",
        "files": [],
        "has_files": False,
        "minor_name": "",
        "model_papers": mps
    }
    papers.append(new_entry)
    added_count += 1

print(f"Added {added_count} new course entries with official model question papers!")
print(f"Total papers in database now: {len(papers)}")

# Save to data and public/data
with open(os.path.join(DATA_DIR, "papers.json"), "w", encoding="utf-8") as f:
    json.dump(papers, f, indent=2)

with open(os.path.join(PUB_DATA_DIR, "papers.json"), "w", encoding="utf-8") as f:
    json.dump(papers, f, indent=2)

print("Saved updated papers.json to data and public/data!")

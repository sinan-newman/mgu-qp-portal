"""
clean_invalid_codes_and_titles.py
=================================
1. Enforces the strict rule: "Names of Course code will always have number at end."
   - Cleans course codes with trailing text like MG4DSEMAT201TRANS -> MG4DSEMAT201.
   - Merges these model papers into their real catalog courses (e.g. Transforms and Fourier Series).
   - Removes bogus orphan entries.
   - Deletes any course codes that do not have numbers at the end (e.g. MG1DSCPHL).
2. Enforces the strict rule: "name of paper will never be same as department name"
   - Replaces any paper title that matches the department name or department code.
   - Extracts the real course name from the model paper PDF (e.g. after course code hyphen).
3. Updates data/papers.json, public/data/papers.json, and data/model_papers.json.
"""

import json
import os
import re
import pypdf

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")
PUB_DATA_DIR = os.path.join(BASE_DIR, "public", "data")

with open(os.path.join(DATA_DIR, "departments.json"), "r", encoding="utf-8") as f:
    depts = json.load(f)

dept_name_set = set()
dept_code_set = set()
for d in depts:
    if d.get("name"):
        dept_name_set.add(d["name"].strip().lower())
    if d.get("code"):
        dept_code_set.add(d["code"].strip().lower())
    for m in d.get("majors", []):
        if m.get("name"):
            dept_name_set.add(m["name"].strip().lower())
        if m.get("code"):
            dept_code_set.add(m["code"].strip().lower())

def is_dept_name_or_code(val):
    if not val:
        return True
    v = val.strip().lower()
    if len(v) <= 2:
        return True
    return (v in dept_name_set) or (v in dept_code_set)

# Load database
with open(os.path.join(DATA_DIR, "papers.json"), "r", encoding="utf-8") as f:
    papers = json.load(f)

with open(os.path.join(DATA_DIR, "model_papers.json"), "r", encoding="utf-8") as f:
    model_papers_list = json.load(f)

print(f"Loaded {len(papers)} papers from papers.json")
print(f"Loaded {len(model_papers_list)} entries from model_papers.json")

# Build map of clean catalog papers (excluding orphan_ and model_only_)
catalog_papers = {}
for p in papers:
    pid = p.get("id", "")
    if not pid.startswith("orphan_") and not pid.startswith("model_only_"):
        c = (p.get("course_code") or "").strip().upper()
        if c and c[-1].isdigit():
            catalog_papers[c] = p

print(f"Found {len(catalog_papers)} official catalog courses")

def extract_title_from_pdf(pdf_filename, clean_code):
    search_paths = [
        os.path.join(BASE_DIR, "uploads", "model_papers", pdf_filename),
        os.path.join(BASE_DIR, "public", "uploads", "model_papers", pdf_filename),
        os.path.join(BASE_DIR, "..", "mgu-qp-storage", "pdf", pdf_filename)
    ]
    local_path = None
    for sp in search_paths:
        if os.path.exists(sp):
            local_path = sp
            break
    if not local_path:
        return ""

    try:
        reader = pypdf.PdfReader(local_path)
        if len(reader.pages) == 0:
            return ""
        txt = reader.pages[0].extract_text() or ""
        clean_txt = " ".join(txt.split())

        escaped = re.escape(clean_code) if clean_code else ""
        if escaped:
            # Pattern 1: [code] [: - – —] [Title]
            m1 = re.search(escaped + r'\s*[:\-–—\u2013\u2014\ufb01\s]+\s*(?!(?:Part|Section|Answer|Max|Duration|Total|Skill|Time|Marks|Hours|Reg|Roll|No|Semester)\b)([A-Za-z0-9][A-Za-z0-9\s,\/&\':\-–]{3,120}?)(?=\s*(?:\(2024|\bDuration\b|\bTime\b|\bMax\b|\bPart\b|\bSection\b|\d+\s*hrs|\bMarks\b|$))', clean_txt, re.IGNORECASE)
            if m1:
                cand = m1.group(1).strip(" -–:").strip()
                cand = re.sub(r'\s*MODEL\s*QUESTION\s*PAPER.*$', '', cand, flags=re.IGNORECASE)
                cand = re.sub(r'[:\-–—\s]+$', '', cand).strip()
                if not is_dept_name_or_code(cand) and len(cand) >= 4:
                    return cand

        # Pattern 2: COURSE TITLE: [Title]
        m2 = re.search(r'(?:COURSE\s*TITLE|TITLE\s*OF\s*(?:THE\s*)?COURSE|PAPER\s*NAME)\s*[:\-–—\s]+([A-Za-z0-9\s,&\'\/-]{4,100})(?=\s*(?:\(2024|\bDuration\b|\bTime\b|\bMax\b|\bPart\b|$))', clean_txt, re.IGNORECASE)
        if m2:
            cand = m2.group(1).strip(" -–:").strip()
            if not is_dept_name_or_code(cand) and len(cand) >= 4:
                return cand

    except Exception as e:
        pass
    return ""

# Step 1: Process model_papers.json
print("\n--- Cleaning model_papers.json ---")
cleaned_models = []
models_by_clean_code = {}

for m in model_papers_list:
    raw_code = (m.get("course_code") or "").strip().upper()
    # Match FYUGP code ending with 3 digits:
    # Pattern: (MG[1-8](?:DSC|DSE|SEC|MDC|VAC|CCR|AEC|MDE|SDC|MPC|HON|MIN|MDE)[A-Z]{2,4}A?[1-4][0-9]{2})([A-Z]+)?
    match = re.match(r'^(MG[1-8](?:DSC|DSE|SEC|MDC|VAC|CCR|AEC|MDE|SDC|MPC|HON|MIN|MDE)[A-Z]{2,4}A?[1-4][0-9]{2})', raw_code)
    
    if match:
        clean_code = match.group(1)
        m["course_code"] = clean_code
        
        # Check if title is department name
        cur_title = m.get("title", "").strip()
        if is_dept_name_or_code(cur_title):
            # Try catalog first
            cat_p = catalog_papers.get(clean_code)
            if cat_p and cat_p.get("title") and not is_dept_name_or_code(cat_p["title"]):
                m["title"] = cat_p["title"]
            else:
                # Try extracting from PDF
                pdf_t = extract_title_from_pdf(m.get("filename", ""), clean_code)
                if pdf_t:
                    m["title"] = pdf_t
                else:
                    m["title"] = f"Model Question Paper - {clean_code}"
        
        cleaned_models.append(m)
        if clean_code not in models_by_clean_code:
            models_by_clean_code[clean_code] = []
        models_by_clean_code[clean_code].append(m)
    else:
        # Check if code ends with digit at least
        if raw_code and raw_code[-1].isdigit():
            cleaned_models.append(m)
        else:
            # Code does NOT have number at end -> remove as instructed by user
            print(f"  Removing model paper with invalid code (no number at end): {raw_code} ({m.get('filename')})")

print(f"model_papers.json cleaned: {len(cleaned_models)} valid entries retained (from {len(model_papers_list)})")

# Step 2: Clean and merge papers in papers.json
print("\n--- Cleaning papers.json ---")
new_papers_list = []
merged_into_catalog_count = 0
deleted_invalid_code_count = 0
cleaned_orphan_count = 0

for p in papers:
    pid = p.get("id", "")
    raw_code = (p.get("course_code") or "").strip().upper()
    is_orphan = pid.startswith("orphan_") or pid.startswith("model_only_")

    if not is_orphan:
        # Regular catalog or exam paper
        # Ensure code ends in digit
        if raw_code and not raw_code[-1].isdigit():
            # Try to strip trailing letters
            match = re.match(r'^(MG[1-8](?:DSC|DSE|SEC|MDC|VAC|CCR|AEC|MDE|SDC|MPC|HON|MIN|MDE)[A-Z]{2,4}A?[1-4][0-9]{2})', raw_code)
            if match:
                p["course_code"] = match.group(1)
        new_papers_list.append(p)
    else:
        # Orphan or model_only entry
        match = re.match(r'^(MG[1-8](?:DSC|DSE|SEC|MDC|VAC|CCR|AEC|MDE|SDC|MPC|HON|MIN|MDE)[A-Z]{2,4}A?[1-4][0-9]{2})', raw_code)
        
        if not match:
            # Check if code has any number at end
            if not raw_code or not raw_code[-1].isdigit():
                # User request: "Names of Course code will always have number at end. Remove such course codes detected."
                deleted_invalid_code_count += 1
                continue
            clean_code = raw_code
        else:
            clean_code = match.group(1)

        # Check if clean_code exists in official catalog papers!
        if clean_code in catalog_papers:
            # Merge this orphan's model papers into the catalog paper!
            cat_p = catalog_papers[clean_code]
            if "model_papers" not in cat_p or not isinstance(cat_p["model_papers"], list):
                cat_p["model_papers"] = []
            
            for mp in p.get("model_papers", []):
                mp_id = mp.get("id") or mp.get("filename")
                if not any((em.get("id") == mp_id or em.get("filename") == mp.get("filename")) for em in cat_p["model_papers"]):
                    # Update title if needed
                    if is_dept_name_or_code(mp.get("title", "")):
                        mp["title"] = cat_p.get("title") or f"Official Model Question Paper ({clean_code})"
                    cat_p["model_papers"].append(mp)
            
            cat_p["has_files"] = True
            merged_into_catalog_count += 1
            # Do NOT add this orphan to new_papers_list (it is now cleanly merged!)
        else:
            # Clean code is valid and ends with numbers, but not in catalog
            p["course_code"] = clean_code
            
            # Check and fix title if it is equal to department name
            cur_title = (p.get("title") or "").strip()
            if is_dept_name_or_code(cur_title):
                # Try extracting real title from its model paper PDF
                models = p.get("model_papers", [])
                pdf_fn = models[0].get("filename", "") if models else ""
                real_t = extract_title_from_pdf(pdf_fn, clean_code) if pdf_fn else ""
                
                if real_t:
                    p["title"] = real_t
                else:
                    # Parse course type to give proper course title, NEVER department name!
                    m_type = re.match(r'^MG[1-8]([A-Z]{3})', clean_code)
                    ctype = m_type.group(1) if m_type else "DSC"
                    p["title"] = f"Course {clean_code} ({ctype})"
            
            # Ensure model papers inside have clean titles as well
            for mp in p.get("model_papers", []):
                if is_dept_name_or_code(mp.get("title", "")):
                    mp["title"] = p["title"]
            
            cleaned_orphan_count += 1
            new_papers_list.append(p)

print(f"Merged into catalog: {merged_into_catalog_count}")
print(f"Deleted invalid orphan entries (no number at end): {deleted_invalid_code_count}")
print(f"Retained cleaned orphan entries: {cleaned_orphan_count}")
print(f"Total papers in database after cleanup: {len(new_papers_list)}")

# Step 3: Final pass to ensure NO course has title == dept_name
print("\n--- Verifying all paper titles ---")
fixed_titles = 0
for p in new_papers_list:
    t = (p.get("title") or "").strip()
    c = (p.get("course_code") or "").strip().upper()
    if is_dept_name_or_code(t):
        # Fix title
        models = p.get("model_papers", [])
        pdf_fn = models[0].get("filename", "") if models else ""
        real_t = extract_title_from_pdf(pdf_fn, c) if pdf_fn else ""
        if real_t and not is_dept_name_or_code(real_t):
            p["title"] = real_t
        else:
            p["title"] = f"Course {c}"
        p["raw_header"] = f"{c} - {p['title']}"
        fixed_titles += 1

print(f"Fixed remaining department-named titles: {fixed_titles}")

# Save papers.json and public/data/papers.json
with open(os.path.join(DATA_DIR, "papers.json"), "w", encoding="utf-8") as f:
    json.dump(new_papers_list, f, indent=2, ensure_ascii=False)

with open(os.path.join(PUB_DATA_DIR, "papers.json"), "w", encoding="utf-8") as f:
    json.dump(new_papers_list, f, indent=2, ensure_ascii=False)

with open(os.path.join(DATA_DIR, "model_papers.json"), "w", encoding="utf-8") as f:
    json.dump(cleaned_models, f, indent=2, ensure_ascii=False)

print("\nSaved updated database to data/papers.json, public/data/papers.json, and data/model_papers.json!")

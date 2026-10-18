"""
process_all_official_model_qps.py
===================================
Comprehensive processor for all official MGU Model Question Papers.
1. Reads all 296 consolidated files from data/mgu_official_model_links.json.
2. Concurrent worker pool to extract individual question papers (1-7 pages each).
3. Classifies Theory vs Practical based on official category & text.
4. Normalizes course codes (strips '24' prefix, removes inner spaces).
5. Enforces MAX 2 model QPs per course (at most 1 Theory and at most 1 Practical).
6. Saves split PDFs into ../mgu-qp-storage/pdf/.
7. Routes untagged papers (length 1-7 pages) to data/untagged_model_papers.json for admin tagging.
8. Integrates orphan courses into data/papers.json (with has_qp: false).
9. Mirrors data to public/data/.
"""

import sys
import os
import re
import json
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
import pypdf

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")
PUB_DATA_DIR = os.path.join(BASE_DIR, "public", "data")
STORAGE_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "mgu-qp-storage"))
STORAGE_PDF_DIR = os.path.join(STORAGE_DIR, "pdf")
CACHE_DOWNLOAD_DIR = os.path.join(BASE_DIR, "temp_model_downloads")

os.makedirs(STORAGE_PDF_DIR, exist_ok=True)
os.makedirs(PUB_DATA_DIR, exist_ok=True)

# 1. Load official links
links_file = os.path.join(DATA_DIR, "mgu_official_model_links.json")
with open(links_file, "r", encoding="utf-8") as f:
    official_links = json.load(f)

# 2. Load existing portal papers and departments
papers_file = os.path.join(DATA_DIR, "papers.json")
with open(papers_file, "r", encoding="utf-8") as f:
    papers_db = json.load(f)

depts_file = os.path.join(DATA_DIR, "departments.json")
with open(depts_file, "r", encoding="utf-8") as f:
    departments = json.load(f)

dept_name_map = {d.get("code"): d.get("name") for d in departments if d.get("code")}

known_courses = {}
for p in papers_db:
    cc = p.get("course_code")
    if cc:
        clean_c = re.sub(r'[^A-Z0-9]', '', cc.upper())
        if clean_c not in known_courses:
            known_courses[clean_c] = p

print(f"Loaded {len(known_courses)} unique known courses from papers.json.")

# Prepare list of items to process
all_items = []
for sem_str, cats in official_links.items():
    sem_m = re.search(r'([1-8])', sem_str)
    sem_num = int(sem_m.group(1)) if sem_m else 1
    for cat_name, items in cats.items():
        is_default_prac = "practical" in cat_name.lower()
        for it in items:
            url = it["url"].strip()
            name = it["name"].strip()
            raw_fn = os.path.basename(urllib.parse.urlparse(url).path)
            dec_fn = urllib.parse.unquote(raw_fn)
            local_p = os.path.join(CACHE_DOWNLOAD_DIR, raw_fn)
            if not os.path.exists(local_p):
                local_p = os.path.join(CACHE_DOWNLOAD_DIR, dec_fn)
            
            all_items.append({
                "semester": sem_num,
                "semester_label": sem_str,
                "category": cat_name,
                "is_default_prac": is_default_prac,
                "name": name,
                "url": url,
                "local_path": local_p,
                "raw_fn": raw_fn
            })

print(f"Total official items to process: {len(all_items)}")

def normalize_course_code(raw_str):
    if not raw_str:
        return ""
    c = raw_str.strip().upper()
    c = re.sub(r'\s+', '', c)
    c = c.replace("-", "").replace("_", "")
    if c.startswith("24MG"):
        c = c[2:]
    return c

# Function to process a single consolidated PDF
def process_single_pdf(item):
    local_p = item["local_path"]
    if not os.path.exists(local_p) or os.path.getsize(local_p) < 100:
        return []
    
    try:
        reader = pypdf.PdfReader(local_p)
    except Exception as e:
        return []
        
    num_pages = len(reader.pages)
    if num_pages == 0:
        return []
        
    file_is_prac = item["is_default_prac"] or ("practical" in item["name"].lower()) or ("practical" in item["raw_fn"].lower())
    sem = item["semester"]
    
    page_data = []
    for idx, page in enumerate(reader.pages):
        try:
            txt = page.extract_text() or ""
        except Exception:
            txt = ""
        txt_upper = txt.upper()
        
        # Check start markers
        has_univ = any(k in txt_upper for k in ["MAHATMA GANDHI UNIVERSITY", "MGU", "MODEL QUESTION PAPER", "DEGREE EXAMINATION", "SEMESTER EXAMINATION"])
        has_marks = any(k in txt_upper for k in ["MAXIMUM MARKS", "MAX. MARKS", "TOTAL MARKS", "MAX MARKS", "MARKS:"])
        has_time = any(k in txt_upper for k in ["TIME :", "TIME:", "DURATION:", "HOURS", "HRS"])
        has_parts = any(k in txt_upper for k in ["PART A", "PART - A", "PART-A", "SECTION A", "SECTION - A"])
        
        is_start = (has_univ and (has_marks or has_time or has_parts)) or (has_marks and has_time)
        
        # Match course codes in page text
        raw_codes = re.findall(r'(?:24)?\s*(MG\s*[1-8]\s*[A-Z0-9]{3,4}\s*[A-Z0-9]{2,5}\s*\d{0,4})', txt, re.IGNORECASE)
        norm_codes = [normalize_course_code(c) for c in raw_codes]
        norm_codes = [c for c in norm_codes if len(c) >= 10 and c.startswith("MG")]
        matched_known = [c for c in norm_codes if c in known_courses]
        
        # Check if code exists in item name or filename
        fallback_codes = re.findall(r'(?:24)?\s*(MG[1-8][A-Z0-9_]{5,14})', item["name"] + " " + item["raw_fn"], re.IGNORECASE)
        fallback_norm = [normalize_course_code(c) for c in fallback_codes]
        fallback_norm = [c for c in fallback_norm if len(c) >= 10 and c.startswith("MG")]
        
        page_data.append({
            "idx": idx,
            "txt": txt,
            "is_start": is_start,
            "norm_codes": norm_codes,
            "matched_known": matched_known,
            "fallback_codes": fallback_norm
        })
        
    # Group pages into papers (typically 1 to 7 pages each)
    paper_groups = []
    current_start = 0
    current_code = None
    
    for idx in range(num_pages):
        pd = page_data[idx]
        is_new = False
        
        cand_code = pd["matched_known"][0] if pd["matched_known"] else (pd["norm_codes"][0] if pd["norm_codes"] else None)
        
        if idx == 0:
            is_new = True
        elif pd["is_start"] and idx > current_start:
            is_new = True
        elif cand_code and current_code and (cand_code != current_code) and (idx - current_start >= 1):
            is_new = True
        elif (idx - current_start >= 7):
            # Standard question paper is 1-7 pages length
            is_new = True
            
        if is_new and idx > 0:
            paper_groups.append((current_start, idx - 1, current_code))
            current_start = idx
            current_code = cand_code
        elif is_new and idx == 0:
            current_code = cand_code
        else:
            if not current_code and cand_code:
                current_code = cand_code
                
    paper_groups.append((current_start, num_pages - 1, current_code))
    
    extracted_papers = []
    for g_idx, (s_p, e_p, code) in enumerate(paper_groups):
        group_codes = []
        full_text = ""
        for pno in range(s_p, e_p + 1):
            group_codes.extend(page_data[pno]["matched_known"])
            if not group_codes:
                group_codes.extend(page_data[pno]["norm_codes"])
            if not group_codes:
                group_codes.extend(page_data[pno]["fallback_codes"])
            full_text += page_data[pno]["txt"] + "\n"
            
        best_code = group_codes[0] if group_codes else code
        if not best_code and page_data[0]["fallback_codes"]:
            best_code = page_data[0]["fallback_codes"][0]
            
        # Determine Theory vs Practical
        is_practical = file_is_prac or bool(re.search(r'practical\s+examination|practical\s+model|experiment\s+no|conduct\s+one\s+experiment', full_text, re.IGNORECASE))
        if ("theory" in full_text.lower() or "theory examination" in full_text.lower()) and not file_is_prac:
            is_practical = False
            
        paper_type = "PRACTICAL" if is_practical else "THEORY"
        page_count = (e_p - s_p + 1)
        
        extracted_papers.append({
            "semester": sem,
            "source_item": item,
            "start_page": s_p,
            "end_page": e_p,
            "page_count": page_count,
            "course_code": best_code,
            "paper_type": paper_type,
            "full_text": full_text
        })
        
    return extracted_papers

print("\nExtracting and splitting model question papers across 296 official sets...")
all_extracted = []
with ThreadPoolExecutor(max_workers=8) as executor:
    results = list(executor.map(process_single_pdf, all_items))
    for r in results:
        all_extracted.extend(r)

print(f"Total extracted individual question paper segments: {len(all_extracted)}")

# 3. Categorize into Theory, Practical, and Untagged
# Enforce MAX 2 per course (at most 1 Theory, at most 1 Practical)
theory_by_course = {}
practical_by_course = {}
untagged_list = []

for paper in all_extracted:
    cc = paper["course_code"]
    ptype = paper["paper_type"]
    
    if cc:
        if ptype == "THEORY":
            # If not yet recorded or this one has more complete page count (>=2), prefer best
            if cc not in theory_by_course:
                theory_by_course[cc] = paper
            elif paper["page_count"] > theory_by_course[cc]["page_count"] and theory_by_course[cc]["page_count"] == 1:
                theory_by_course[cc] = paper
        else:
            if cc not in practical_by_course:
                practical_by_course[cc] = paper
            elif paper["page_count"] > practical_by_course[cc]["page_count"] and practical_by_course[cc]["page_count"] == 1:
                practical_by_course[cc] = paper
    else:
        untagged_list.append(paper)

print(f"\n--- Model Question Paper Coverage ---")
print(f"Unique courses with Theory Model QP: {len(theory_by_course)}")
print(f"Unique courses with Practical Model QP: {len(practical_by_course)}")
both_count = len(set(theory_by_course.keys()) & set(practical_by_course.keys()))
print(f"Courses with BOTH Theory and Practical Model QPs: {both_count}")
total_courses_covered = len(set(theory_by_course.keys()) | set(practical_by_course.keys()))
print(f"Total distinct courses covered: {total_courses_covered}")
print(f"Untagged question papers for Admin assignment: {len(untagged_list)}")

# 4. Write split PDFs to mgu-qp-storage/pdf/
print("\nWriting split PDF files into storage directory...")
all_model_records = []

def write_paper_pdf(paper, target_filename):
    dest = os.path.join(STORAGE_PDF_DIR, target_filename)
    if os.path.exists(dest) and os.path.getsize(dest) > 500:
        return dest
        
    item = paper["source_item"]
    try:
        reader = pypdf.PdfReader(item["local_path"])
        writer = pypdf.PdfWriter()
        for pno in range(paper["start_page"], paper["end_page"] + 1):
            if pno < len(reader.pages):
                writer.add_page(reader.pages[pno])
        with open(dest, "wb") as f_out:
            writer.write(f_out)
    except Exception as e:
        print(f"Error writing {target_filename}: {e}")
    return dest

# Write Theory PDFs
for cc, paper in theory_by_course.items():
    fname = f"MODEL_{cc}.pdf"
    write_paper_pdf(paper, fname)
    
    cdn_url = f"https://cdn.jsdelivr.net/gh/sinan-newman/mgu-qp-storage@main/pdf/{fname}"
    raw_url = f"https://raw.githubusercontent.com/sinan-newman/mgu-qp-storage/main/pdf/{fname}"
    
    course_info = known_courses.get(cc, {})
    title = course_info.get("title") or paper["source_item"]["name"]
    dept = course_info.get("parent_dept") or course_info.get("dept_code") or "GEN"
    
    rec = {
        "model_id": f"model_{cc}_theory",
        "course_code": cc,
        "title": title,
        "department": dept,
        "semester": paper["semester"],
        "pages": paper["page_count"],
        "filename": fname,
        "cdn_url": cdn_url,
        "raw_url": raw_url,
        "paper_type": "THEORY",
        "source_pdf": paper["source_item"]["raw_fn"]
    }
    all_model_records.append(rec)
    paper["record"] = rec

# Write Practical PDFs
for cc, paper in practical_by_course.items():
    fname = f"MODEL_{cc}_PRACTICAL.pdf"
    write_paper_pdf(paper, fname)
    
    cdn_url = f"https://cdn.jsdelivr.net/gh/sinan-newman/mgu-qp-storage@main/pdf/{fname}"
    raw_url = f"https://raw.githubusercontent.com/sinan-newman/mgu-qp-storage/main/pdf/{fname}"
    
    course_info = known_courses.get(cc, {})
    title = (course_info.get("title") or paper["source_item"]["name"]) + " (Practical)"
    dept = course_info.get("parent_dept") or course_info.get("dept_code") or "GEN"
    
    rec = {
        "model_id": f"model_{cc}_practical",
        "course_code": cc,
        "title": title,
        "department": dept,
        "semester": paper["semester"],
        "pages": paper["page_count"],
        "filename": fname,
        "cdn_url": cdn_url,
        "raw_url": raw_url,
        "paper_type": "PRACTICAL",
        "source_pdf": paper["source_item"]["raw_fn"]
    }
    all_model_records.append(rec)
    paper["record"] = rec

# Write Untagged PDFs
untagged_json_data = []
for idx, paper in enumerate(untagged_list):
    src_name = re.sub(r'[^A-Za-z0-9]', '_', paper["source_item"]["name"])[:20]
    fname = f"MODEL_UNTAGGED_SEM{paper['semester']}_{src_name}_{idx+1}.pdf"
    write_paper_pdf(paper, fname)
    
    cdn_url = f"https://cdn.jsdelivr.net/gh/sinan-newman/mgu-qp-storage@main/pdf/{fname}"
    
    clean_snippet = " ".join(paper["full_text"][:400].split())
    # Check for possible partial code candidate
    code_cand = re.search(r'(?:24)?(MG[1-8][A-Z0-9_]{4,14})', paper["full_text"])
    sug_code = normalize_course_code(code_cand.group(1)) if code_cand else ""
    
    untagged_json_data.append({
        "model_id": f"untagged_{paper['semester']}_{idx+1}",
        "filename": fname,
        "url": cdn_url,
        "pages": paper["page_count"],
        "source_pdf": paper["source_item"]["raw_fn"],
        "snippet": clean_snippet,
        "suggested_code": sug_code,
        "suggested_title": paper["source_item"]["name"],
        "is_practical": paper["paper_type"] == "PRACTICAL",
        "semester": paper["semester"],
        "status": "needs_admin_code"
    })

print(f"Generated {len(all_model_records)} tagged model records and {len(untagged_json_data)} untagged records.")

# 5. Integrate into papers.json
# Ensure at most 2 model QPs per course: 1 Theory and 1 Practical
print("\nUpdating papers.json with official model papers...")
models_by_course = {}

for cc, paper in theory_by_course.items():
    if cc not in models_by_course:
        models_by_course[cc] = []
    rec = paper["record"]
    models_by_course[cc].append({
        "id": rec["model_id"],
        "title": "Official Model Question Paper (FYUGP 2024)",
        "paper_type": "THEORY",
        "pages": rec["pages"],
        "url": rec["cdn_url"],
        "raw_url": rec["raw_url"],
        "filename": rec["filename"]
    })

for cc, paper in practical_by_course.items():
    if cc not in models_by_course:
        models_by_course[cc] = []
    rec = paper["record"]
    models_by_course[cc].append({
        "id": rec["model_id"],
        "title": "Official Practical Model Paper",
        "paper_type": "PRACTICAL",
        "pages": rec["pages"],
        "url": rec["cdn_url"],
        "raw_url": rec["raw_url"],
        "filename": rec["filename"]
    })

existing_codes = set()
for p in papers_db:
    cc = p.get("course_code")
    if cc:
        clean_c = normalize_course_code(cc)
        existing_codes.add(clean_c)
        if clean_c in models_by_course:
            p["model_papers"] = models_by_course[clean_c]

# 6. Integrate orphan courses (courses that have model question papers but had no previous past exam papers)
course_type_names = {
    "DSC": "Discipline Specific Core",
    "DSE": "Discipline Specific Elective",
    "MDC": "Multidisciplinary Course",
    "AEC": "Ability Enhancement Course",
    "SEC": "Skill Enhancement Course",
    "VAC": "Value Added Course",
    "CCR": "Common Core",
    "SDC": "Skill Development Course",
    "MPC": "Minor Pathway Course",
    "MDE": "Multidisciplinary Elective",
    "HON": "Honours Course"
}

orphan_codes = set(models_by_course.keys()) - existing_codes
print(f"Creating course entries for {len(orphan_codes)} orphan courses with model papers...")

for cc in sorted(orphan_codes):
    mps = models_by_course[cc]
    first_m = mps[0]
    
    # Inferred parameters
    m_parse = re.match(r'^MG([1-8])([A-Z]{3})([A-Z]{3})?', cc)
    sem = 1
    ctype = "DSC"
    dept_code = "GEN"
    if m_parse:
        sem = int(m_parse.group(1))
        ctype = m_parse.group(2)
        dept_code = m_parse.group(3) or "GEN"
        
    dept_name = dept_name_map.get(dept_code, dept_code)
    
    # Derive human title from source PDF or model title
    t_obj = theory_by_course.get(cc) or practical_by_course.get(cc)
    raw_title = t_obj["source_item"]["name"] if t_obj else cc
    raw_title = re.sub(r'\s*-\s*Theory.*|\s*-\s*Practical.*', '', raw_title, flags=re.IGNORECASE)
    raw_title = re.sub(r'MG[1-8][A-Z0-9_]{5,14}', '', raw_title).strip(" -–")
    final_title = raw_title if raw_title else f"{dept_name} {course_type_names.get(ctype, ctype)}"
    
    new_course = {
        "id": f"orphan_{cc.lower()}",
        "qp_code": "",
        "course_code": cc,
        "title": final_title,
        "raw_header": f"MG UNIVERSITY FYUGP MODEL PAPER - {final_title}",
        "semester": sem,
        "semester_label": f"Semester {sem}",
        "course_type": ctype,
        "course_type_name": course_type_names.get(ctype, ctype),
        "dept_code": dept_code,
        "dept_name": dept_name,
        "parent_dept": dept_code,
        "parent_dept_name": dept_name,
        "is_minor": False,
        "exam_id": f"fyugp_sem{sem}_model",
        "exam_name": f"Semester {sem} FYUGP (Model Question Paper)",
        "batch": "2024",
        "is_fyugp": True,
        "has_qp": False,
        "qp_url": "",
        "has_scheme": False,
        "scheme_url": "",
        "files": [],
        "has_files": False,
        "minor_name": "",
        "mgu_qp_url": "",
        "raw_qp_url": "",
        "model_papers": mps
    }
    papers_db.append(new_course)

print(f"Total courses now in papers.json database: {len(papers_db)}")

# 7. Save datasets to data/ and public/data/
with open(os.path.join(DATA_DIR, "papers.json"), "w", encoding="utf-8") as f:
    json.dump(papers_db, f, indent=2)
with open(os.path.join(PUB_DATA_DIR, "papers.json"), "w", encoding="utf-8") as f:
    json.dump(papers_db, f, indent=2)

with open(os.path.join(DATA_DIR, "model_papers.json"), "w", encoding="utf-8") as f:
    json.dump(all_model_records, f, indent=2)
with open(os.path.join(PUB_DATA_DIR, "model_papers.json"), "w", encoding="utf-8") as f:
    json.dump(all_model_records, f, indent=2)

with open(os.path.join(DATA_DIR, "untagged_model_papers.json"), "w", encoding="utf-8") as f:
    json.dump(untagged_json_data, f, indent=2)
with open(os.path.join(PUB_DATA_DIR, "untagged_model_papers.json"), "w", encoding="utf-8") as f:
    json.dump(untagged_json_data, f, indent=2)

print("\nSuccessfully updated all catalogs and JSON databases!")

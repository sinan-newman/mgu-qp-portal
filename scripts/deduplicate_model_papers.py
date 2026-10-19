"""
scripts/deduplicate_model_papers.py
===================================
Enforces the strict requirement:
"No course will have 2 model question paper. If one has 2, check whether 1 is practical.
 Otherwise it has to be duplicate. Find the best one amongst them and delete others."

Rules:
1. Every course has AT MOST 1 THEORY model paper and AT MOST 1 PRACTICAL model paper.
2. If a course has 2 model papers, one is guaranteed to be THEORY and one is PRACTICAL.
3. If duplicate model papers of the same type exist:
   - Evaluates each candidate based on filename match, text relevance to course title, and validity.
   - Any displaced candidate whose content belongs to another course missing its paper is reassigned.
   - The single best candidate of each type is kept; all others are deleted.
4. Updates data/papers.json, public/data/papers.json, and data/model_papers.json.
"""

import json
import os
import re
import pypdf

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")
PUB_DATA_DIR = os.path.join(BASE_DIR, "public", "data")

with open(os.path.join(DATA_DIR, "papers.json"), "r", encoding="utf-8") as f:
    papers = json.load(f)

with open(os.path.join(DATA_DIR, "departments.json"), "r", encoding="utf-8") as f:
    depts = json.load(f)

with open(os.path.join(DATA_DIR, "model_papers.json"), "r", encoding="utf-8") as f:
    model_papers_catalog = json.load(f)

dept_names = {d["name"].strip().lower() for d in depts if d.get("name")}
dept_codes = {d["code"].strip().lower() for d in depts if d.get("code")}

PDF_SEARCH_DIRS = [
    os.path.join(BASE_DIR, "uploads", "model_papers"),
    os.path.join(BASE_DIR, "public", "uploads", "model_papers"),
    os.path.join(BASE_DIR, "..", "mgu-qp-storage", "pdf")
]

PDF_CACHE = {}

def get_pdf_info(fn):
    if not fn:
        return {"exists": False, "size": 0, "pages": 0, "text": ""}
    if fn in PDF_CACHE:
        return PDF_CACHE[fn]
    
    local_path = None
    for d in PDF_SEARCH_DIRS:
        fp = os.path.join(d, fn)
        if os.path.isfile(fp):
            local_path = fp
            break
            
    if not local_path:
        res = {"exists": False, "size": 0, "pages": 0, "text": ""}
        PDF_CACHE[fn] = res
        return res
        
    size = os.path.getsize(local_path)
    pages = 0
    txt = ""
    try:
        reader = pypdf.PdfReader(local_path)
        pages = len(reader.pages)
        if pages > 0:
            txt = (reader.pages[0].extract_text() or "")[:600]
    except Exception:
        pass
        
    res = {"exists": True, "size": size, "pages": pages, "text": txt}
    PDF_CACHE[fn] = res
    return res

# Build catalog lookup by clean course_code
catalog_by_code = {}
for p in papers:
    cc = p.get("course_code")
    if cc and cc[-1].isdigit():
        if cc not in catalog_by_code or not p.get("id", "").startswith("orphan_"):
            catalog_by_code[cc] = p

print(f"Catalog indexed: {len(catalog_by_code)} distinct courses.", flush=True)

def score_candidate(model_obj, target_course, ptype):
    """
    Scores candidate model paper. Higher score = better candidate.
    """
    fn = model_obj.get("filename") or os.path.basename(model_obj.get("url", ""))
    mid = model_obj.get("id", "")
    info = get_pdf_info(fn)
    
    score = 0.0
    c_code = target_course.get("course_code", "").upper()
    c_title = target_course.get("title", "").lower()
    
    # 1. Existence and valid file size
    if info["exists"] and info["size"] > 1000:
        score += 100.0
    elif not info["exists"]:
        score -= 200.0
        
    # 2. Exact filename match
    expected_fn = f"MODEL_{c_code}.pdf" if ptype == "THEORY" else f"MODEL_{c_code}_PRACTICAL.pdf"
    if fn.upper() == expected_fn.upper():
        score += 300.0
    elif c_code in fn.upper():
        base_no_ext = os.path.splitext(fn)[0].replace("_PRACTICAL", "").replace("MODEL_", "")
        if base_no_ext.upper() == c_code:
            score += 250.0
        else:
            extra_len = len(base_no_ext) - len(c_code)
            score += max(50.0, 200.0 - (extra_len * 20.0))
            
    # 3. Exact ID match
    expected_id = f"model_{c_code.lower()}_{ptype.lower()}"
    if mid.lower() == expected_id:
        score += 150.0
        
    # 4. Text content match with course title
    pdf_text = info["text"].lower()
    title_words = [w for w in re.findall(r'[a-z0-9]+', c_title) if len(w) > 3]
    if title_words:
        matched_words = [w for w in title_words if w in pdf_text]
        score += ((len(matched_words) / len(title_words)) * 400.0)
        
    # 5. Generic department title penalty for practicals
    m_title = model_obj.get("title", "").strip().lower()
    if ptype == "PRACTICAL":
        is_generic_dept = any(m_title.startswith(d) for d in dept_names) and len(m_title.split()) <= 3
        if is_generic_dept:
            score -= 100.0
        else:
            score += 100.0
            
    pages = info["pages"] or model_obj.get("pages", 1)
    if 2 <= pages <= 5:
        score += 50.0
    elif pages == 1 and ptype == "THEORY":
        score -= 20.0
        
    return score

print("Deduplicating model papers across all courses in papers.json...", flush=True)

courses_fixed = 0
duplicates_removed = 0
reassigned_count = 0
unique_courses_seen = set()

# Map to store resolved model papers per course_code so identical course entries across exam sessions stay in sync
resolved_models_by_course = {}

for p in papers:
    cc = p.get("course_code")
    mps = p.get("model_papers", [])
    if not mps:
        continue
        
    if cc in resolved_models_by_course:
        p["model_papers"] = resolved_models_by_course[cc]
        continue
        
    theories = [m for m in mps if m.get("paper_type", "THEORY").upper() == "THEORY"]
    practicals = [m for m in mps if m.get("paper_type", "THEORY").upper() == "PRACTICAL"]
    others = [m for m in mps if m.get("paper_type", "THEORY").upper() not in ("THEORY", "PRACTICAL")]
    
    for o in others:
        if "practical" in (o.get("id", "") + o.get("title", "") + o.get("filename", "")).lower():
            o["paper_type"] = "PRACTICAL"
            practicals.append(o)
        else:
            o["paper_type"] = "THEORY"
            theories.append(o)
            
    if len(theories) <= 1 and len(practicals) <= 1:
        clean_list = theories + practicals
        p["model_papers"] = clean_list
        resolved_models_by_course[cc] = clean_list
        continue
        
    # Resolve duplicates
    courses_fixed += 1
    new_model_list = []
    
    # Best Theory
    if len(theories) == 1:
        new_model_list.append(theories[0])
    elif len(theories) > 1:
        scored = [(score_candidate(m, p, "THEORY"), m) for m in theories]
        scored.sort(key=lambda x: x[0], reverse=True)
        best_score, best_theory = scored[0]
        new_model_list.append(best_theory)
        duplicates_removed += (len(theories) - 1)
        
        # Check if any displaced theory belongs to another course
        for s, loser in scored[1:]:
            loser_fn = loser.get("filename") or os.path.basename(loser.get("url", ""))
            loser_info = get_pdf_info(loser_fn)
            loser_txt = loser_info["text"].lower()
            
            if "3d printing" in loser_txt and "MG4DSEECT201" in catalog_by_code:
                target = catalog_by_code["MG4DSEECT201"]
                if not target.get("model_papers"):
                    target["model_papers"] = [loser]
                    reassigned_count += 1
            elif "international careers" in loser_txt and "MG4SECENG200" in catalog_by_code:
                target = catalog_by_code["MG4SECENG200"]
                if not target.get("model_papers"):
                    target["model_papers"] = [loser]
                    reassigned_count += 1
            elif "third semester" in loser_txt and "horticulture" in loser_txt and "MG3DSCHTC200" in catalog_by_code:
                target = catalog_by_code["MG3DSCHTC200"]
                if not any(m.get("paper_type") == "THEORY" for m in target.get("model_papers", [])):
                    if "model_papers" not in target or not isinstance(target["model_papers"], list):
                        target["model_papers"] = []
                    target["model_papers"].append(loser)
                    reassigned_count += 1
                    
    # Best Practical
    if len(practicals) == 1:
        new_model_list.append(practicals[0])
    elif len(practicals) > 1:
        scored_p = [(score_candidate(m, p, "PRACTICAL"), m) for m in practicals]
        scored_p.sort(key=lambda x: x[0], reverse=True)
        best_p_score, best_prac = scored_p[0]
        new_model_list.append(best_prac)
        duplicates_removed += (len(practicals) - 1)
        
    p["model_papers"] = new_model_list
    resolved_models_by_course[cc] = new_model_list

# Apply resolved models to all occurrences of each course
for p in papers:
    cc = p.get("course_code")
    if cc in resolved_models_by_course:
        p["model_papers"] = resolved_models_by_course[cc]

print(f"Distinct courses deduplicated: {courses_fixed}", flush=True)
print(f"Duplicate model papers removed: {duplicates_removed}", flush=True)
print(f"Displaced papers reassigned: {reassigned_count}", flush=True)

# Update model_papers.json to reflect the exact cleaned set of model papers
clean_model_papers = []
seen_model_keys = set()

for cc, mps in resolved_models_by_course.items():
    course_obj = catalog_by_code.get(cc, {})
    dept = course_obj.get("dept_code") or course_obj.get("parent_dept") or "GEN"
    sem = course_obj.get("semester", 1)
    for m in mps:
        ptype = m.get("paper_type", "THEORY").upper()
        key = (cc, ptype)
        if key in seen_model_keys:
            continue
        seen_model_keys.add(key)
        
        m_entry = {
            "model_id": m.get("id") or f"model_{cc.lower()}_{ptype.lower()}",
            "course_code": cc,
            "title": m.get("title") or course_obj.get("title", ""),
            "department": dept,
            "semester": sem,
            "pages": m.get("pages", 2),
            "filename": m.get("filename") or os.path.basename(m.get("url", "")),
            "cdn_url": m.get("url") or f"https://cdn.jsdelivr.net/gh/sinan-newman/mgu-qp-storage@main/pdf/{m.get('filename')}",
            "raw_url": m.get("raw_url") or f"https://raw.githubusercontent.com/sinan-newman/mgu-qp-storage/main/pdf/{m.get('filename')}",
            "paper_type": ptype,
            "source_pdf": m.get("source_pdf") or m.get("filename")
        }
        clean_model_papers.append(m_entry)

print(f"Cleaned model_papers.json count: {len(clean_model_papers)} (was {len(model_papers_catalog)})", flush=True)

# Verification
violations = []
for p in papers:
    mps = p.get("model_papers", [])
    if len(mps) > 2:
        violations.append((p.get("course_code"), f"count={len(mps)} > 2"))
    elif len(mps) == 2:
        theories = [m for m in mps if m.get("paper_type", "THEORY").upper() == "THEORY"]
        practicals = [m for m in mps if m.get("paper_type", "THEORY").upper() == "PRACTICAL"]
        if len(theories) != 1 or len(practicals) != 1:
            violations.append((p.get("course_code"), f"2 papers but not 1 theory + 1 practical (theories={len(theories)}, practicals={len(practicals)})"))

print(f"Total rule violations in papers.json: {len(violations)}", flush=True)
if violations:
    for v in violations[:10]:
        print("  Violation:", v, flush=True)
    raise RuntimeError("Verification failed: violations found!")

print("All verification checks PASSED successfully! Writing files...", flush=True)

# Save updated papers.json and public/data/papers.json
with open(os.path.join(DATA_DIR, "papers.json"), "w", encoding="utf-8") as f:
    json.dump(papers, f, indent=2)

with open(os.path.join(PUB_DATA_DIR, "papers.json"), "w", encoding="utf-8") as f:
    json.dump(papers, f, indent=2)

with open(os.path.join(DATA_DIR, "model_papers.json"), "w", encoding="utf-8") as f:
    json.dump(clean_model_papers, f, indent=2)

with open(os.path.join(PUB_DATA_DIR, "model_papers.json"), "w", encoding="utf-8") as f:
    json.dump(clean_model_papers, f, indent=2)

print("Saved all updated datasets successfully!", flush=True)

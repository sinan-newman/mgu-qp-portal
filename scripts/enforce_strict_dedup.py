import os
import json
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
PUBLIC_DATA_DIR = os.path.join(BASE_DIR, "public", "data")

with open(os.path.join(DATA_DIR, "departments.json"), "r", encoding="utf-8") as f:
    depts = json.load(f)
dept_dict = {d["code"]: d["name"] for d in depts}
dept_names = set([d["name"].strip().lower() for d in depts] + [d["code"].strip().lower() for d in depts])

with open(os.path.join(DATA_DIR, "papers.json"), "r", encoding="utf-8") as f:
    papers = json.load(f)

def is_dept_name(t):
    if not t: return True
    t_clean = t.strip().lower()
    return t_clean in dept_names or t_clean in [d.lower() for d in dept_dict.keys()]

# 1. First, collect all model papers across all records grouped by (course_code, paper_type)
all_candidates = {}

for p in papers:
    cc = (p.get("course_code") or "").strip().upper()
    if not cc: continue
    
    if p.get("model_papers") and isinstance(p["model_papers"], list):
        for m in p["model_papers"]:
            pt = (m.get("paper_type") or "THEORY").upper()
            key = (cc, pt)
            
            # Score candidate:
            # - Has positive page count (+10)
            # - Title is not department name (+20)
            # - Title is not generic "Official Model..." (+30)
            # - File actually exists on disk (+40)
            # - Longer descriptive title (+len)
            title = (m.get("title") or "").strip()
            url = m.get("url") or ""
            local_path = os.path.join(BASE_DIR, url.replace("/", os.sep))
            exists = os.path.exists(local_path)
            
            score = 0
            if exists: score += 40
            if not title.startswith("Official Model"): score += 30
            if not is_dept_name(title) and len(title) >= 4: score += 20
            if m.get("pages", 0) > 0: score += 10
            score += min(len(title), 20)
            
            candidate_item = {
                "course_code": cc,
                "course_title": p.get("title") or title,
                "semester": p.get("semester"),
                "dept_code": p.get("dept_code"),
                "dept_name": p.get("dept_name"),
                "course_type": p.get("course_type"),
                "is_signature": p.get("is_signature", False) or bool(re.search(r'A\d{2}$', cc)),
                "model_id": m.get("id"),
                "title": title if not is_dept_name(title) else (p.get("title") or f"Course {cc}"),
                "paper_type": pt,
                "url": url,
                "cdn_url": m.get("cdn_url") or f"https://cdn.jsdelivr.net/gh/sinan-newman/mgu-qp-storage@main/pdf/{os.path.basename(url)}",
                "pages": m.get("pages") or 2,
                "_score": score
            }
            
            if key not in all_candidates or score > all_candidates[key]["_score"]:
                all_candidates[key] = candidate_item

print(f"Extracted {len(all_candidates)} unique (course_code, paper_type) canonical model papers.")

# 2. Build map by course_code -> list of best model papers (at most 1 theory, at most 1 practical)
canonical_by_code = {}
for (cc, pt), item in all_candidates.items():
    if cc not in canonical_by_code:
        canonical_by_code[cc] = []
    # Clean up internal scoring field
    clean_item = dict(item)
    clean_item.pop("_score", None)
    
    # Check signature course
    if re.search(r'A\d{2}$', cc) or 'A0' in cc or 'A1' in cc:
        clean_item['is_signature'] = True
        
    canonical_by_code[cc].append(clean_item)

# 3. Update all records in papers.json
for p in papers:
    cc = (p.get("course_code") or "").strip().upper()
    if cc in canonical_by_code:
        best_models = canonical_by_code[cc]
        p["model_papers"] = [
            {
                "id": m["model_id"],
                "title": m["title"],
                "paper_type": m["paper_type"],
                "url": m["url"],
                "cdn_url": m["cdn_url"],
                "pages": m["pages"],
                "source": "MGU Official FYUGP Model Question Paper"
            }
            for m in best_models
        ]
        p["has_files"] = True
        if re.search(r'A\d{2}$', cc) or 'A0' in cc or 'A1' in cc:
            p["is_signature"] = True
            
        # Clean title if it was department name
        if is_dept_name(p.get("title")):
            non_dept_m = [m["title"] for m in best_models if not is_dept_name(m["title"])]
            if non_dept_m:
                p["title"] = non_dept_m[0]
            else:
                p["title"] = f"Course {cc}"
    else:
        p["model_papers"] = []

# 4. Generate deduplicated model_papers.json catalog
final_model_catalog = []
for (cc, pt), item in sorted(all_candidates.items(), key=lambda x: (x[1].get('semester') or 1, x[0][0])):
    clean_entry = dict(item)
    clean_entry.pop("_score", None)
    final_model_catalog.append(clean_entry)

# Save to data and public/data
with open(os.path.join(DATA_DIR, "papers.json"), "w", encoding="utf-8") as f:
    json.dump(papers, f, indent=2, ensure_ascii=False)
with open(os.path.join(PUBLIC_DATA_DIR, "papers.json"), "w", encoding="utf-8") as f:
    json.dump(papers, f, indent=2, ensure_ascii=False)

with open(os.path.join(DATA_DIR, "model_papers.json"), "w", encoding="utf-8") as f:
    json.dump(final_model_catalog, f, indent=2, ensure_ascii=False)
if os.path.exists(PUBLIC_DATA_DIR):
    with open(os.path.join(PUBLIC_DATA_DIR, "model_papers.json"), "w", encoding="utf-8") as f:
        json.dump(final_model_catalog, f, indent=2, ensure_ascii=False)

print(f"Strict deduplication complete!")
print(f"Total canonical model question papers: {len(final_model_catalog)}")

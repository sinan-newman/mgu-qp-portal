import os
import json
import re
import shutil

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
PUBLIC_DATA_DIR = os.path.join(BASE_DIR, "public", "data")
UPLOADS_MODEL_DIR = os.path.join(BASE_DIR, "uploads", "model_papers")
PUBLIC_UPLOADS_MODEL_DIR = os.path.join(BASE_DIR, "public", "uploads", "model_papers")
STORAGE_PDF_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "mgu-qp-storage", "pdf"))

with open(os.path.join(DATA_DIR, "departments.json"), "r", encoding="utf-8") as f:
    depts = json.load(f)
dept_dict = {d["code"]: d["name"] for d in depts}
dept_names = set([d["name"].strip().lower() for d in depts] + [d["code"].strip().lower() for d in depts])

with open(os.path.join(DATA_DIR, "papers.json"), "r", encoding="utf-8") as f:
    papers = json.load(f)

def clean_title(title):
    if not title:
        return ""
    t = title.strip()
    # Strip administrative suffixes
    t = re.sub(r'\s*(?:Duration\s*:?|Time\s*:?|Max\s*\.?\s*Marks|Total\s*Marks|Marks\s*:|Part\s+[A-Z]|Section\s+[A-Z]|MGU|Admission|\bhrs\b|\bmins\b).*$', '', t, flags=re.IGNORECASE).strip()
    t = re.sub(r'[\s\-–—:]+$', '', t).strip()
    t = re.sub(r'^["\'\(\[]+|["\'\)\]]+$', '', t).strip()
    return t

CORRECTIONS = {
    'MGIMDCCOM101': 'MG1MDCCOM101',
    'MGIDSCSAC101': 'MG1DSCSAC101',
    'MGIDSCSAC100': 'MG1DSCSAC100',
    'MGIDSCFIM100': 'MG1DSCFIM100',
    'MGIDSCSMG100': 'MG1DSCSMG100',
    'MGIMDCSMG100': 'MG1MDCSMG100',
    'MG4DSCSTA20': 'MG4DSCSTA202',
    'MG4DVACENGA00': 'MG4VACENGA00'
}

for p in papers:
    old_code = p.get('course_code', '')
    if old_code in CORRECTIONS:
        new_code = CORRECTIONS[old_code]
        p['course_code'] = new_code
        if p.get('raw_header'):
            p['raw_header'] = p['raw_header'].replace(old_code, new_code)
            
        # Rename files if existing
        for folder in [UPLOADS_MODEL_DIR, PUBLIC_UPLOADS_MODEL_DIR, STORAGE_PDF_DIR]:
            old_f = os.path.join(folder, f"MODEL_{old_code}.pdf")
            new_f = os.path.join(folder, f"MODEL_{new_code}.pdf")
            if os.path.exists(old_f):
                shutil.move(old_f, new_f)
                
        if p.get('model_papers'):
            for m in p['model_papers']:
                m['url'] = m['url'].replace(old_code, new_code)
                m['cdn_url'] = m['cdn_url'].replace(old_code, new_code)
                m['id'] = m['id'].replace(old_code, new_code)

    # Clean titles
    p['title'] = clean_title(p.get('title', ''))
    if p['title'].lower() in dept_names or not p['title']:
        p['title'] = f"Course {p.get('course_code')}"
        
    if p.get('model_papers'):
        for m in p['model_papers']:
            m['title'] = clean_title(m.get('title', ''))
            if m['title'].lower() in dept_names or not m['title']:
                m['title'] = p['title']

# Deduplicate across the entire portal:
# No course will have 2 model question papers unless 1 is theory and 1 is practical
for p in papers:
    if p.get('model_papers') and len(p['model_papers']) > 1:
        theories = [m for m in p['model_papers'] if (m.get('paper_type') or 'THEORY').upper() == 'THEORY']
        practicals = [m for m in p['model_papers'] if (m.get('paper_type') or '').upper() == 'PRACTICAL']
        
        final_list = []
        if theories:
            # Sort by best: pages > 0, non-dept title, length of title
            theories.sort(key=lambda m: (m.get('pages', 0) > 0, len(m.get('title', ''))), reverse=True)
            final_list.append(theories[0])
        if practicals:
            practicals.sort(key=lambda m: (m.get('pages', 0) > 0, len(m.get('title', ''))), reverse=True)
            final_list.append(practicals[0])
        p['model_papers'] = final_list

# Update model_papers.json catalog
all_model_catalog = []
for p in papers:
    if p.get("model_papers") and len(p["model_papers"]) > 0:
        for m in p["model_papers"]:
            all_model_catalog.append({
                "course_code": p.get("course_code"),
                "course_title": p.get("title"),
                "semester": p.get("semester"),
                "dept_code": p.get("dept_code"),
                "dept_name": p.get("dept_name"),
                "course_type": p.get("course_type"),
                "is_signature": p.get("is_signature", False),
                "model_id": m.get("id"),
                "title": m.get("title"),
                "paper_type": m.get("paper_type"),
                "url": m.get("url"),
                "cdn_url": m.get("cdn_url"),
                "pages": m.get("pages")
            })

with open(os.path.join(DATA_DIR, "papers.json"), "w", encoding="utf-8") as f:
    json.dump(papers, f, indent=2, ensure_ascii=False)
with open(os.path.join(PUBLIC_DATA_DIR, "papers.json"), "w", encoding="utf-8") as f:
    json.dump(papers, f, indent=2, ensure_ascii=False)

with open(os.path.join(DATA_DIR, "model_papers.json"), "w", encoding="utf-8") as f:
    json.dump(all_model_catalog, f, indent=2, ensure_ascii=False)
if os.path.exists(PUBLIC_DATA_DIR):
    with open(os.path.join(PUBLIC_DATA_DIR, "model_papers.json"), "w", encoding="utf-8") as f:
        json.dump(all_model_catalog, f, indent=2, ensure_ascii=False)

print(f"Cleanup and normalization complete!")
print(f"Total courses: {len(papers)}")
print(f"Total model papers: {len(all_model_catalog)}")

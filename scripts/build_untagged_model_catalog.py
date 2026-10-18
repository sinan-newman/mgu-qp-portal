"""
build_untagged_model_catalog.py
===============================
Extracts full metadata, snippets, and detected details for all untagged model PDFs
so that the admin can view and assign course codes in the admin panel.
"""

import os
import json
import re
import pypdf

STORAGE_PDF_DIR = r"C:\Users\Navirex\.gemini\antigravity\scratch\mgu-qp-storage\pdf"
DATA_DIR = r"C:\Users\Navirex\.gemini\antigravity\scratch\mgu-qp-portal\data"

with open(os.path.join(DATA_DIR, "model_papers.json"), "r", encoding="utf-8") as f:
    all_models = json.load(f)

with open(os.path.join(DATA_DIR, "papers.json"), "r", encoding="utf-8") as f:
    papers = json.load(f)

# Build a fast course lookup for autocomplete
courses_db = {}
for p in papers:
    cc = p.get("course_code")
    if cc and cc not in courses_db:
        courses_db[cc] = {
            "course_code": cc,
            "title": p.get("title", ""),
            "dept_name": p.get("dept_name") or p.get("dept_code", ""),
            "semester": p.get("semester", 1),
            "course_type": p.get("course_type", "DSC")
        }

print(f"Loaded {len(courses_db)} unique courses from portal database.")

untagged_list = []

for m in all_models:
    cc = m.get("course_code", "")
    fname = m.get("filename", "")
    
    # If course_code starts with SEM or is empty or contains click_here or Fee_Refund
    is_untagged = not cc or cc.startswith("SEM") or "click_here" in cc.lower() or "MODEL_SEM" in fname
    
    if is_untagged:
        pdf_path = os.path.join(STORAGE_PDF_DIR, fname)
        text = ""
        pg_count = m.get("pages", 1)
        if os.path.exists(pdf_path):
            try:
                reader = pypdf.PdfReader(pdf_path)
                pg_count = len(reader.pages)
                for p in reader.pages[:2]: # first 2 pages
                    text += (p.extract_text() or "") + "\n"
            except Exception as e:
                pass
        
        # Check if it's a non-QP circular (like Fee Refund Policy)
        is_circular = "fee refund" in text.lower() or "abstract" in text.lower() and "circular" in text.lower()
        if is_circular:
            continue
            
        # Clean text snippet
        clean_snippet = " ".join(text[:400].split())
        
        # Check for potential course code in text
        # Match (?:24)?MG[1-8][A-Z0-9_]{5,14}
        code_match = re.search(r'(?:24)?(MG[1-8][A-Z0-9_]{5,14})', text)
        suggested_code = code_match.group(1) if code_match else ""
        
        # Check for potential title
        title_match = re.search(r'Course\s*:\s*(?:[^\n\r–-]+[-–])?\s*([^\n\r]+)', text, re.IGNORECASE)
        suggested_title = title_match.group(1).strip() if title_match else m.get("title", "")
        
        # Check if practical
        is_practical = bool(re.search(r'practical|experiment|demonstrate|conduct one', text, re.IGNORECASE))
        
        # Semester from filename or text
        sem_m = re.search(r'SEM([1-8])', fname, re.IGNORECASE) or re.search(r'(FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH)\s+SEMESTER', text, re.IGNORECASE)
        sem_num = 1
        if sem_m:
            val = sem_m.group(1).upper()
            sem_map = {"1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "FIRST": 1, "SECOND": 2, "THIRD": 3, "FOURTH": 4, "FIFTH": 5, "SIXTH": 6}
            sem_num = sem_map.get(val, 1)

        untagged_list.append({
            "model_id": m.get("model_id"),
            "filename": fname,
            "url": m.get("cdn_url") or f"https://cdn.jsdelivr.net/gh/sinan-newman/mgu-qp-storage@main/pdf/{fname}",
            "pages": pg_count,
            "source_pdf": m.get("source_pdf", "Consolidated Department File"),
            "snippet": clean_snippet,
            "suggested_code": suggested_code,
            "suggested_title": suggested_title,
            "is_practical": is_practical,
            "semester": sem_num,
            "status": "needs_admin_code"
        })

print(f"Total valid untagged model question papers for admin tagging: {len(untagged_list)}")

# Save to data/untagged_model_papers.json and public/data/untagged_model_papers.json
out_file = os.path.join(DATA_DIR, "untagged_model_papers.json")
with open(out_file, "w", encoding="utf-8") as f:
    json.dump(untagged_list, f, indent=2)

pub_out_file = os.path.join(r"C:\Users\Navirex\.gemini\antigravity\scratch\mgu-qp-portal\public\data", "untagged_model_papers.json")
with open(pub_out_file, "w", encoding="utf-8") as f:
    json.dump(untagged_list, f, indent=2)

print(f"Saved catalog to {out_file} and {pub_out_file}")

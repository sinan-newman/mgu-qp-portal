"""
process_all_model_qps.py
========================
Automated pipeline to:
1. Fetch all consolidated model question paper links from https://www.mgu.ac.in/examinations/model-question-papers-fyugp-2024/
2. Download consolidated PDFs concurrently.
3. Split each consolidated PDF into individual course model question papers.
4. Save split PDFs into ../mgu-qp-storage/pdf/ with filename MODEL_<course_code>.pdf.
5. Generate data/model_papers.json and update data/papers.json with model question paper references.
"""

import sys
import os
import re
import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
import pypdf

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
STORAGE_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "mgu-qp-storage"))
STORAGE_PDF_DIR = os.path.join(STORAGE_DIR, "pdf")
CACHE_DOWNLOAD_DIR = os.path.join(BASE_DIR, "temp_model_downloads")

os.makedirs(STORAGE_PDF_DIR, exist_ok=True)
os.makedirs(CACHE_DOWNLOAD_DIR, exist_ok=True)

# 1. Load database courses
with open(os.path.join(BASE_DIR, "data", "papers.json"), "r", encoding="utf-8") as f:
    portal_papers = json.load(f)

known_courses = {}
for p in portal_papers:
    code = (p.get("course_code") or "").strip().upper()
    if code and code not in known_courses:
        known_courses[code] = p

print(f"Loaded {len(known_courses)} known course codes from portal database.")

# 2. Extract all model QP links from page
content_file = os.path.join(r"C:\Users\Navirex\.gemini\antigravity\brain\87d52a0b-0a87-4dfd-b1bf-99a37fa42aef\.system_generated\steps\1921\content.md")
with open(content_file, "r", encoding="utf-8") as f:
    html = f.read()

start_idx = html.find("1st Semester")
content = html[start_idx:]

sem_positions = [(m.start(), m.group(1)) for m in re.finditer(r'([1-8](?:st|nd|rd|th)\s+Semester)', content, re.IGNORECASE)]

all_links = []
seen_urls = set()

for i in range(len(sem_positions)):
    s_pos = sem_positions[i][0]
    e_pos = sem_positions[i+1][0] if i+1 < len(sem_positions) else len(content)
    s_name = sem_positions[i][1]
    sec = content[s_pos:e_pos]
    sem_num = int(re.search(r'([1-8])', s_name).group(1))
    
    links = re.findall(r'<a[^>]+href=[\"\']([^\"\']+\.pdf[^\"\']*)[\"\'][^>]*>(.*?)</a>', sec, re.IGNORECASE | re.DOTALL)
    for href, ltext in links:
        clean_text = re.sub(r'<[^>]+>', ' ', ltext).strip()
        clean_href = href.split("?")[0].strip()
        
        # Exclude general policy docs
        if any(k in clean_href.lower() for k in ["institutional-development", "ugc-approval", "fee-refund", "admin.pdf", "right-to-public"]):
            continue
            
        if clean_href in seen_urls:
            continue
        seen_urls.add(clean_href)
        
        fname = clean_href.split("/")[-1]
        all_links.append({
            "semester": sem_num,
            "label": clean_text,
            "url": clean_href,
            "filename": fname
        })

print(f"Discovered {len(all_links)} consolidated model PDF files across Semesters 1-5.")

# 3. Concurrent Download of consolidated PDFs
def download_pdf(item):
    url = item["url"]
    dest = os.path.join(CACHE_DOWNLOAD_DIR, item["filename"])
    if os.path.exists(dest) and os.path.getsize(dest) > 500:
        return item, dest, True
    
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = resp.read()
                if len(data) > 500:
                    with open(dest, "wb") as f:
                        f.write(data)
                    return item, dest, True
        except Exception as e:
            time.sleep(1 + attempt)
    return item, dest, False

print("\nStarting concurrent download of consolidated model PDFs...")
downloaded_items = []
with ThreadPoolExecutor(max_workers=8) as executor:
    futures = [executor.submit(download_pdf, item) for item in all_links]
    for future in as_completed(futures):
        item, dest, success = future.result()
        if success:
            downloaded_items.append((item, dest))

print(f"Successfully downloaded {len(downloaded_items)}/{len(all_links)} consolidated PDFs.")

# 4. Splitting & Course Matching Engine
split_records = []
total_split_qps = 0

for item, pdf_path in downloaded_items:
    try:
        reader = pypdf.PdfReader(pdf_path)
    except Exception as e:
        print(f"Error reading {pdf_path}: {e}")
        continue
        
    num_pages = len(reader.pages)
    if num_pages == 0:
        continue
        
    sem = item["semester"]
    label = item["label"]
    
    # Analyze each page for Question Paper boundaries
    page_data = []
    for idx, page in enumerate(reader.pages):
        try:
            txt = page.extract_text() or ""
        except Exception:
            txt = ""
        
        txt_upper = txt.upper()
        
        # Check start markers
        has_univ = "MAHATMA GANDHI UNIVERSITY" in txt_upper or "MGU" in txt_upper
        has_marks = any(k in txt_upper for k in ["MAXIMUM MARKS", "MAX. MARKS", "TOTAL MARKS", "MAX MARKS"])
        has_time = any(k in txt_upper for k in ["TIME :", "TIME:", "DURATION:", "HOURS", "HRS"])
        has_parts = any(k in txt_upper for k in ["PART A", "PART - A", "PART-A", "SECTION A", "SECTION - A"])
        has_exam = any(k in txt_upper for k in ["SEMESTER EXAMINATION", "MODEL QUESTION PAPER", "DEGREE EXAMINATION"])
        
        is_start = (has_univ and (has_marks or has_time or has_parts or has_exam)) or (has_marks and has_time) or (has_parts and has_exam)
        
        # Find course codes
        found_codes = re.findall(r'\b(MG[1-8][A-Z0-9_]{5,14})\b', txt)
        found_codes = [c.rstrip('_-') for c in found_codes]
        matched_known = [c for c in found_codes if c in known_courses]
        
        page_data.append({
            "idx": idx,
            "txt": txt,
            "is_start": is_start,
            "codes": found_codes,
            "matched_codes": matched_known
        })
    
    # Boundary detection: Group pages into papers
    paper_groups = []
    current_start = 0
    current_code = None
    
    for idx in range(num_pages):
        p = page_data[idx]
        
        # Determine if this page starts a new question paper
        is_new = False
        if idx == 0:
            is_new = True
        elif p["is_start"] and (p["matched_codes"] or p["codes"] or idx > current_start):
            # Only start new if previous had at least 1 page
            is_new = True
        elif p["matched_codes"] and p["matched_codes"][0] != current_code and current_code is not None:
            is_new = True
            
        if is_new and idx > 0:
            paper_groups.append((current_start, idx - 1, current_code))
            current_start = idx
            current_code = p["matched_codes"][0] if p["matched_codes"] else (p["codes"][0] if p["codes"] else None)
        elif is_new and idx == 0:
            current_code = p["matched_codes"][0] if p["matched_codes"] else (p["codes"][0] if p["codes"] else None)
        else:
            if not current_code and p["matched_codes"]:
                current_code = p["matched_codes"][0]
            elif not current_code and p["codes"]:
                current_code = p["codes"][0]
                
    paper_groups.append((current_start, num_pages - 1, current_code))
    
    # Process each detected paper group
    for p_idx, (start_p, end_p, code) in enumerate(paper_groups):
        # Scan pages of this group to confirm best code
        group_codes = []
        for pno in range(start_p, end_p + 1):
            group_codes.extend(page_data[pno]["matched_codes"])
            if not group_codes:
                group_codes.extend(page_data[pno]["codes"])
                
        best_code = group_codes[0] if group_codes else code
        
        # If best_code not found or not in known, try to infer from item label
        course_info = known_courses.get(best_code)
        
        # Build individual PDF
        writer = pypdf.PdfWriter()
        for pno in range(start_p, end_p + 1):
            writer.add_page(reader.pages[pno])
            
        if best_code:
            split_filename = f"MODEL_{best_code}.pdf"
        else:
            clean_label = re.sub(r'[^A-Za-z0-9_]', '_', label)[:25]
            split_filename = f"MODEL_SEM{sem}_{clean_label}_{p_idx+1}.pdf"
            
        split_dest = os.path.join(STORAGE_PDF_DIR, split_filename)
        try:
            with open(split_dest, "wb") as f_out:
                writer.write(f_out)
        except Exception as e:
            continue
            
        total_split_qps += 1
        
        # CDN URL pointing to the user's repository
        cdn_url = f"https://cdn.jsdelivr.net/gh/sinan-newman/mgu-qp-storage@main/pdf/{split_filename}"
        raw_url = f"https://raw.githubusercontent.com/sinan-newman/mgu-qp-storage/main/pdf/{split_filename}"
        
        title = course_info.get("title") if course_info else label
        dept_code = course_info.get("parent_dept") or course_info.get("dept_code") if course_info else "GEN"
        
        split_records.append({
            "model_id": f"model_{best_code or split_filename}",
            "course_code": best_code,
            "title": title,
            "department": dept_code,
            "semester": sem,
            "pages": (end_p - start_p + 1),
            "filename": split_filename,
            "cdn_url": cdn_url,
            "raw_url": raw_url,
            "source_pdf": item["filename"]
        })

print(f"\n========================================================")
print(f"SPLITTING COMPLETE: Generated {total_split_qps} individual model question papers!")
print(f"========================================================")

# 5. Save model_papers.json
model_papers_file = os.path.join(BASE_DIR, "data", "model_papers.json")
public_model_file = os.path.join(BASE_DIR, "public", "data", "model_papers.json")

with open(model_papers_file, "w", encoding="utf-8") as f:
    json.dump(split_records, f, indent=2, ensure_ascii=False)

with open(public_model_file, "w", encoding="utf-8") as f:
    json.dump(split_records, f, indent=2, ensure_ascii=False)

print(f"Saved {len(split_records)} model papers to data/model_papers.json and public/data/model_papers.json")

# 6. Attach model papers into papers.json
# Build code -> model paper mapping
code_to_models = {}
for m in split_records:
    if m.get("course_code"):
        code_to_models.setdefault(m["course_code"], []).append(m)

matched_portal_courses = 0
for p in portal_papers:
    code = (p.get("course_code") or "").strip().upper()
    if code in code_to_models:
        matched_portal_courses += 1
        models = code_to_models[code]
        p["model_papers"] = [{
            "id": m["model_id"],
            "title": f"Official Model Question Paper (FYUGP 2024)",
            "pages": m["pages"],
            "url": m["cdn_url"],
            "raw_url": m["raw_url"],
            "filename": m["filename"]
        } for m in models]

print(f"Attached model papers directly into {matched_portal_courses} course entries in papers.json.")

with open(os.path.join(BASE_DIR, "data", "papers.json"), "w", encoding="utf-8") as f:
    json.dump(portal_papers, f, indent=2, ensure_ascii=False)

with open(os.path.join(BASE_DIR, "public", "data", "papers.json"), "w", encoding="utf-8") as f:
    json.dump(portal_papers, f, indent=2, ensure_ascii=False)

print("Updated papers.json and public/data/papers.json successfully.")

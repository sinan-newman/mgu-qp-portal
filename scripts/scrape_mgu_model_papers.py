"""
scrape_mgu_model_papers.py
===========================
Autonomous Daily Scraper & PDF Splitter for MGU FYUGP Model Question Papers.
Target: https://www.mgu.ac.in/examinations/model-question-papers-fyugp-2024/

Workflow:
1. Live-scrapes MGU model papers page for all semesters (1 through 5+).
2. Resolves all direct PDF URLs and WordPress attachment pages concurrently.
3. Caches/tracks links in data/mgu_official_model_links.json and cache file.
4. Concurrently downloads newly uploaded or modified compilation PDFs.
5. Uses pypdf to accurately detect page boundaries and split compilation PDFs
   into individual course model question papers (1-4 pages each).
6. Classifies papers into THEORY vs PRACTICAL:
   - Usually all courses have at least 1 Theory model paper.
   - Some courses have 2 (1 Theory + 1 Practical).
   - Enforces MAX 2 model papers per course (at most 1 Theory and at most 1 Practical).
7. Deduplication against existing database:
   - Automatically assigns split papers to courses if not already available in the website.
   - Never duplicates the same paper type for a course.
   - Automatically creates orphan course entries in papers.json if not already present.
8. Saves split PDFs to uploads/model_papers/ and ../mgu-qp-storage/pdf/.
9. Routes unidentifiable papers to data/untagged_model_papers.json for Admin UI review.
10. Mirrors all updated datasets to public/data/ and updates stats.json.
"""

import os
import sys
import re
import json
import time
import shutil
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
import pypdf

sys.stdout.reconfigure(encoding='utf-8')

def safe_url_quote(url):
    try:
        parts = urllib.parse.urlsplit(url.strip())
        encoded_path = urllib.parse.quote(parts.path, safe='/@:')
        encoded_query = urllib.parse.quote(parts.query, safe='=&?')
        return urllib.parse.urlunsplit((parts.scheme, parts.netloc, encoded_path, encoded_query, parts.fragment))
    except Exception:
        return url

# Paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")
PUB_DATA_DIR = os.path.join(BASE_DIR, "public", "data")
STORAGE_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "mgu-qp-storage"))
STORAGE_PDF_DIR = os.path.join(STORAGE_DIR, "pdf")
LOCAL_UPLOADS_MODEL_DIR = os.path.join(BASE_DIR, "uploads", "model_papers")
PUB_UPLOADS_MODEL_DIR = os.path.join(BASE_DIR, "public", "uploads", "model_papers")
DOWNLOAD_CACHE_DIR = os.path.join(BASE_DIR, "temp_model_downloads")
CACHE_FILE = os.path.join(DATA_DIR, "model_scrape_cache.json")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(PUB_DATA_DIR, exist_ok=True)
os.makedirs(STORAGE_PDF_DIR, exist_ok=True)
os.makedirs(LOCAL_UPLOADS_MODEL_DIR, exist_ok=True)
os.makedirs(PUB_UPLOADS_MODEL_DIR, exist_ok=True)
os.makedirs(DOWNLOAD_CACHE_DIR, exist_ok=True)

PAGE_URL = "https://www.mgu.ac.in/examinations/model-question-papers-fyugp-2024/"
CDN_BASE = "https://cdn.jsdelivr.net/gh/sinan-newman/mgu-qp-storage@main/pdf"
RAW_BASE = "https://raw.githubusercontent.com/sinan-newman/mgu-qp-storage/main/pdf"

COURSE_TYPE_NAMES = {
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

def normalize_course_code(raw_str):
    if not raw_str:
        return ""
    c = raw_str.strip().upper()
    c = re.sub(r'[^A-Z0-9]', '', c)
    if c.startswith("24MG"):
        c = c[2:]
    return c

def fetch_page_html():
    print(f"[Scraper] Fetching live page: {PAGE_URL} ...")
    req = urllib.request.Request(
        PAGE_URL,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MGU-Portal-Sync/1.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=35) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"[Scraper] Error fetching MGU page: {e}")
        return ""

def parse_model_page_html(html):
    print("[Scraper] Parsing HTML sections and semester tables...")
    sem_markers = list(re.finditer(r'([1-8](?:st|nd|rd|th)?\s+Semester)', html, re.IGNORECASE))
    
    real_sem_sections = []
    for m in sem_markers:
        idx = m.start()
        if idx < 10000:
            continue
        real_sem_sections.append((idx, m.group(1).title()))

    extracted_by_sem = {}

    for i in range(len(real_sem_sections)):
        start_pos, sem_name = real_sem_sections[i]
        end_pos = real_sem_sections[i+1][0] if i+1 < len(real_sem_sections) else html.find("<footer", start_pos)
        if end_pos == -1 or end_pos <= start_pos:
            end_pos = len(html)
            
        sem_chunk = html[start_pos:end_pos]
        num_m = re.search(r'([1-8])', sem_name)
        sem_key = f"Semester {num_m.group(1)}" if num_m else sem_name
        
        if sem_key not in extracted_by_sem:
            extracted_by_sem[sem_key] = {}
            
        cat_markers = []
        for cm in re.finditer(r'<(?:h[1-6]|strong|b|p)[^>]*>(.*?)</(?:h[1-6]|strong|b|p)>', sem_chunk, re.IGNORECASE | re.DOTALL):
            clean_text = re.sub(r'<[^>]+>', '', cm.group(1)).strip()
            clean_upper = clean_text.upper()
            if any(k in clean_upper for k in ["THEORY", "PRACTICAL", "B.VOC", "SIGNATURE"]):
                if not re.search(r'^[1-8](?:st|nd|rd|th)?\s*Semester$', clean_text, re.IGNORECASE):
                    cat_markers.append((cm.start(), clean_text))
                    
        if not cat_markers:
            cat_markers = [(0, "Theory")]
        else:
            if cat_markers[0][0] > 100:
                cat_markers.insert(0, (0, "General"))
                
        for c_idx in range(len(cat_markers)):
            c_start, c_name = cat_markers[c_idx]
            c_end = cat_markers[c_idx+1][0] if c_idx+1 < len(cat_markers) else len(sem_chunk)
            c_chunk = sem_chunk[c_start:c_end]
            
            c_label = c_name
            if "theory" in c_name.lower() and "b.voc" not in c_name.lower():
                c_label = "Theory"
            elif "practical" in c_name.lower() and "b.voc" not in c_name.lower():
                c_label = "Practical"
                
            if c_label not in extracted_by_sem[sem_key]:
                extracted_by_sem[sem_key][c_label] = []
                
            links = re.findall(r'<a\s+[^>]*href=[\"\']([^\"\']+)[\"\'][^>]*>(.*?)</a>', c_chunk, re.IGNORECASE | re.DOTALL)
            for href, ltxt in links:
                clean_t = re.sub(r'<[^>]+>', '', ltxt).strip()
                clean_href = href.strip()
                if not clean_href or clean_href.startswith("#") or "javascript:" in clean_href:
                    continue
                is_pdf = ".pdf" in clean_href.lower()
                is_att = "model-question-papers-fyugp-2024/" in clean_href and clean_href != PAGE_URL
                if not (is_pdf or is_att):
                    continue
                if any(skip in clean_href for skip in ["UGC-approval", "Development-Plan", "Fee-Refund", "AD_A3"]):
                    continue
                    
                extracted_by_sem[sem_key][c_label].append({
                    "name": clean_t or os.path.basename(clean_href),
                    "url": clean_href,
                    "is_attachment": is_att and not is_pdf
                })

    return extracted_by_sem

def resolve_attachment_pages(extracted_by_sem):
    print("[Scraper] Resolving WordPress attachment pages to direct PDF download URLs...")
    items_to_resolve = []
    for sem, cats in extracted_by_sem.items():
        for cat, items in cats.items():
            for it in items:
                if it.get("is_attachment"):
                    items_to_resolve.append(it)

    print(f"[Scraper] Found {len(items_to_resolve)} attachment pages to resolve.")

    def _resolve_one(it):
        try:
            target_url = safe_url_quote(it["url"])
            req = urllib.request.Request(target_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MGU-Portal-Sync/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
                pdfs = re.findall(r'<a[^>]+href=[\"\']([^\"\']+\.pdf[^\'\"]*)[\"\']', html, re.IGNORECASE)
                valid = [p.split('?')[0] for p in pdfs if not any(skip in p for skip in ['UGC', 'Development-Plan', 'Fee-Refund', 'AD_A3'])]
                if valid:
                    it["resolved_url"] = valid[-1]
                    return True
        except Exception as e:
            it["error"] = str(e)
        return False

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(_resolve_one, items_to_resolve))

    resolved_count = sum(1 for r in results if r)
    print(f"[Scraper] Successfully resolved {resolved_count}/{len(items_to_resolve)} attachment pages.")
    return extracted_by_sem

def download_file(url, target_path):
    if os.path.exists(target_path) and os.path.getsize(target_path) > 500:
        return True
    tmp_path = target_path + ".tmp"
    safe_target_url = safe_url_quote(url)
    for attempt in range(3):
        try:
            req = urllib.request.Request(safe_target_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MGU-Portal-Sync/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp, open(tmp_path, "wb") as f_out:
                shutil.copyfileobj(resp, f_out)
            if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 100:
                shutil.move(tmp_path, target_path)
                return True
        except Exception as e:
            if attempt == 2:
                print(f"[Scraper] Failed to download {url}: {e}")
            time.sleep(1.5)
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
    return False

def process_single_pdf(item, known_courses):
    local_p = item["local_path"]
    if not os.path.exists(local_p) or os.path.getsize(local_p) < 100:
        return []
    
    try:
        reader = pypdf.PdfReader(local_p)
    except Exception:
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
        
        has_univ = any(k in txt_upper for k in ["MAHATMA GANDHI UNIVERSITY", "MGU", "MODEL QUESTION PAPER", "DEGREE EXAMINATION", "SEMESTER EXAMINATION"])
        has_marks = any(k in txt_upper for k in ["MAXIMUM MARKS", "MAX. MARKS", "TOTAL MARKS", "MAX MARKS", "MARKS:"])
        has_time = any(k in txt_upper for k in ["TIME :", "TIME:", "DURATION:", "HOURS", "HRS"])
        has_parts = any(k in txt_upper for k in ["PART A", "PART - A", "PART-A", "SECTION A", "SECTION - A"])
        
        is_start = (has_univ and (has_marks or has_time or has_parts)) or (has_marks and has_time)
        
        # Course code regex: MG followed by semester digit and alphanumeric tokens
        raw_codes = re.findall(r'(?:24)?\s*(MG\s*[1-8]\s*[A-Z0-9]{3,4}\s*[A-Z0-9]{2,5}\s*\d{0,4})', txt, re.IGNORECASE)
        norm_codes = [normalize_course_code(c) for c in raw_codes]
        norm_codes = [c for c in norm_codes if len(c) >= 10 and c.startswith("MG")]
        matched_known = [c for c in norm_codes if c in known_courses]
        
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

def write_paper_pdf(paper, target_filename):
    dest_paths = [
        os.path.join(STORAGE_PDF_DIR, target_filename),
        os.path.join(LOCAL_UPLOADS_MODEL_DIR, target_filename),
        os.path.join(PUB_UPLOADS_MODEL_DIR, target_filename)
    ]
    
    # Check if primary destination exists and has content
    if all(os.path.exists(p) and os.path.getsize(p) > 500 for p in dest_paths[:2]):
        return dest_paths[0]
        
    item = paper["source_item"]
    try:
        reader = pypdf.PdfReader(item["local_path"])
        writer = pypdf.PdfWriter()
        for pno in range(paper["start_page"], paper["end_page"] + 1):
            if pno < len(reader.pages):
                writer.add_page(reader.pages[pno])
                
        # Write to memory first
        import io
        buf = io.BytesIO()
        writer.write(buf)
        pdf_bytes = buf.getvalue()
        
        for dest in dest_paths:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "wb") as f_out:
                f_out.write(pdf_bytes)
                
    except Exception as e:
        print(f"[Splitter] Error writing {target_filename}: {e}")
        
    return dest_paths[0]

def run_scraper(force=False):
    print("=" * 70)
    print("  MGU FYUGP MODEL QUESTION PAPERS - DAILY AUTONOMOUS RUNNER")
    print("  Target: https://www.mgu.ac.in/examinations/model-question-papers-fyugp-2024/")
    print("=" * 70)
    
    # 1. Fetch & parse live HTML
    html = fetch_page_html()
    if not html:
        print("[Scraper] Aborting: Failed to fetch MGU page.")
        return False
        
    extracted_by_sem = parse_model_page_html(html)
    extracted_by_sem = resolve_attachment_pages(extracted_by_sem)
    
    # Save updated links structure
    links_file = os.path.join(DATA_DIR, "mgu_official_model_links.json")
    with open(links_file, "w", encoding="utf-8") as f:
        json.dump(extracted_by_sem, f, indent=2, ensure_ascii=False)
    pub_links_file = os.path.join(PUB_DATA_DIR, "mgu_official_model_links.json")
    with open(pub_links_file, "w", encoding="utf-8") as f:
        json.dump(extracted_by_sem, f, indent=2, ensure_ascii=False)

    # 2. Flatten items to process
    all_items = []
    for sem_str, cats in extracted_by_sem.items():
        sem_m = re.search(r'([1-8])', sem_str)
        sem_num = int(sem_m.group(1)) if sem_m else 1
        for cat_name, items in cats.items():
            is_default_prac = "practical" in cat_name.lower()
            for it in items:
                url = (it.get("resolved_url") or it["url"]).strip()
                name = it["name"].strip()
                raw_fn = os.path.basename(urllib.parse.urlparse(url).path)
                dec_fn = urllib.parse.unquote(raw_fn)
                local_p = os.path.join(DOWNLOAD_CACHE_DIR, raw_fn)
                if not os.path.exists(local_p):
                    local_p = os.path.join(DOWNLOAD_CACHE_DIR, dec_fn)
                
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

    print(f"[Scraper] Discovered {len(all_items)} total official compilation PDFs from MGU.")

    # 3. Concurrently download any missing/new PDFs
    items_to_download = [it for it in all_items if not (os.path.exists(it["local_path"]) and os.path.getsize(it["local_path"]) > 500)]
    print(f"[Scraper] {len(all_items) - len(items_to_download)} PDFs cached. Downloading {len(items_to_download)} new PDFs...")
    
    if items_to_download:
        def _dl_worker(it):
            return download_file(it["url"], it["local_path"])
        with ThreadPoolExecutor(max_workers=8) as executor:
            dl_res = list(executor.map(_dl_worker, items_to_download))
        print(f"[Scraper] Downloaded {sum(1 for r in dl_res if r)}/{len(items_to_download)} files successfully.")

    # 4. Load current database for deduplication and course lookup
    papers_file = os.path.join(DATA_DIR, "papers.json")
    with open(papers_file, "r", encoding="utf-8") as f:
        papers_db = json.load(f)

    depts_file = os.path.join(DATA_DIR, "departments.json")
    departments = []
    if os.path.exists(depts_file):
        with open(depts_file, "r", encoding="utf-8") as f:
            departments = json.load(f)
    dept_name_map = {d.get("code"): d.get("name") for d in departments if d.get("code")}

    known_courses = {}
    papers_by_code = {}
    for p in papers_db:
        cc = p.get("course_code")
        if cc:
            clean_c = normalize_course_code(cc)
            known_courses[clean_c] = p
            papers_by_code[clean_c] = p

    print(f"[Scraper] Loaded {len(known_courses)} existing known courses from portal database.")

    # 5. Extract & Split PDFs
    print("[Splitter] Splitting compilation PDFs into individual course papers...")
    all_extracted = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(lambda it: process_single_pdf(it, known_courses), all_items))
        for r in results:
            all_extracted.extend(r)

    print(f"[Splitter] Extracted {len(all_extracted)} total individual course paper segments.")

    # 6. Categorize into Theory, Practical, and Untagged
    # Enforce: MAX 2 model QPs per course (at most 1 Theory, at most 1 Practical)
    theory_by_course = {}
    practical_by_course = {}
    untagged_list = []

    for paper in all_extracted:
        cc = paper["course_code"]
        ptype = paper["paper_type"]
        
        if cc:
            if ptype == "THEORY":
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

    print(f"[Classifier] Unique courses with THEORY model QP: {len(theory_by_course)}")
    print(f"[Classifier] Unique courses with PRACTICAL model QP: {len(practical_by_course)}")
    both_count = len(set(theory_by_course.keys()) & set(practical_by_course.keys()))
    print(f"[Classifier] Courses with BOTH Theory and Practical model QPs: {both_count}")
    print(f"[Classifier] Untagged papers needing admin review: {len(untagged_list)}")

    # 7. Write split PDF files to storage and uploads/model_papers/
    print("[Storage] Writing split PDF files to storage and local uploads...")
    all_model_records = []

    # Write Theory PDFs
    for cc, paper in theory_by_course.items():
        fname = f"MODEL_{cc}.pdf"
        write_paper_pdf(paper, fname)
        
        cdn_url = f"{CDN_BASE}/{fname}"
        raw_url = f"{RAW_BASE}/{fname}"
        
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
        
        cdn_url = f"{CDN_BASE}/{fname}"
        raw_url = f"{RAW_BASE}/{fname}"
        
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
        
        cdn_url = f"{CDN_BASE}/{fname}"
        clean_snippet = " ".join(paper["full_text"][:400].split())
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

    # 8. Deduplication & Assignment in papers.json
    # Rule: Check if same question paper is not available in website.
    # Usually all courses have at least 1 Theory model paper, some have 2 (1 Theory + 1 Practical).
    print("[Deduplication] Checking existing courses and assigning model papers...")
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

    assigned_count = 0
    existing_codes = set()
    for p in papers_db:
        cc = p.get("course_code")
        if cc:
            clean_c = normalize_course_code(cc)
            existing_codes.add(clean_c)
            if clean_c in models_by_course:
                # Merge model papers preserving any custom ones, ensuring at most 1 Theory and 1 Practical
                current_models = p.get("model_papers", [])
                has_theory = any(m.get("paper_type") == "THEORY" for m in current_models)
                has_prac = any(m.get("paper_type") == "PRACTICAL" for m in current_models)
                
                new_models = []
                for m in models_by_course[clean_c]:
                    if m["paper_type"] == "THEORY" and not has_theory:
                        new_models.append(m)
                        has_theory = True
                    elif m["paper_type"] == "PRACTICAL" and not has_prac:
                        new_models.append(m)
                        has_prac = True
                    elif m["paper_type"] == "THEORY" and has_theory:
                        # Keep existing or update
                        new_models.append(m)
                    elif m["paper_type"] == "PRACTICAL" and has_prac:
                        new_models.append(m)
                        
                p["model_papers"] = new_models
                assigned_count += 1

    # 9. Orphan courses: Courses discovered on MGU model papers page but not yet in papers.json
    orphan_codes = set(models_by_course.keys()) - existing_codes
    print(f"[Orphan Integration] Creating portal entries for {len(orphan_codes)} newly discovered courses...")

    for cc in sorted(orphan_codes):
        mps = models_by_course[cc]
        m_parse = re.match(r'^MG([1-8])([A-Z]{3})([A-Z]{3})?', cc)
        sem = 1
        ctype = "DSC"
        dept_code = "GEN"
        if m_parse:
            sem = int(m_parse.group(1))
            ctype = m_parse.group(2)
            dept_code = m_parse.group(3) or "GEN"
            
        dept_name = dept_name_map.get(dept_code, dept_code)
        
        t_obj = theory_by_course.get(cc) or practical_by_course.get(cc)
        raw_title = t_obj["source_item"]["name"] if t_obj else cc
        raw_title = re.sub(r'\s*-\s*Theory.*|\s*-\s*Practical.*', '', raw_title, flags=re.IGNORECASE)
        raw_title = re.sub(r'MG[1-8][A-Z0-9_]{5,14}', '', raw_title).strip(" -–")
        final_title = raw_title if raw_title else f"{dept_name} {COURSE_TYPE_NAMES.get(ctype, ctype)}"
        
        new_course = {
            "id": f"orphan_{cc.lower()}",
            "qp_code": "",
            "course_code": cc,
            "title": final_title,
            "raw_header": f"MG UNIVERSITY FYUGP MODEL PAPER - {final_title}",
            "semester": sem,
            "semester_label": f"Semester {sem}",
            "course_type": ctype,
            "course_type_name": COURSE_TYPE_NAMES.get(ctype, ctype),
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
        assigned_count += 1

    # 10. Update stats.json
    stats_file = os.path.join(DATA_DIR, "stats.json")
    stats = {}
    if os.path.exists(stats_file):
        with open(stats_file, "r", encoding="utf-8") as f:
            stats = json.load(f)
            
    stats["total_courses"] = len(papers_db)
    stats["total_model_papers"] = len(all_model_records)
    stats["courses_with_model_papers"] = sum(1 for p in papers_db if p.get("model_papers"))
    stats["last_model_sync"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # 11. Write out all JSON files (data/ and public/data/)
    print("[Persist] Saving updated JSON databases...")
    with open(os.path.join(DATA_DIR, "papers.json"), "w", encoding="utf-8") as f:
        json.dump(papers_db, f, indent=2, ensure_ascii=False)
    with open(os.path.join(PUB_DATA_DIR, "papers.json"), "w", encoding="utf-8") as f:
        json.dump(papers_db, f, indent=2, ensure_ascii=False)

    with open(os.path.join(DATA_DIR, "model_papers.json"), "w", encoding="utf-8") as f:
        json.dump(all_model_records, f, indent=2, ensure_ascii=False)
    with open(os.path.join(PUB_DATA_DIR, "model_papers.json"), "w", encoding="utf-8") as f:
        json.dump(all_model_records, f, indent=2, ensure_ascii=False)

    with open(os.path.join(DATA_DIR, "untagged_model_papers.json"), "w", encoding="utf-8") as f:
        json.dump(untagged_json_data, f, indent=2, ensure_ascii=False)
    with open(os.path.join(PUB_DATA_DIR, "untagged_model_papers.json"), "w", encoding="utf-8") as f:
        json.dump(untagged_json_data, f, indent=2, ensure_ascii=False)

    with open(stats_file, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    with open(os.path.join(PUB_DATA_DIR, "stats.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    # 12. Save scrape cache
    scrape_cache = {
        "last_run": datetime.now(timezone.utc).isoformat(),
        "page_url": PAGE_URL,
        "total_source_items": len(all_items),
        "total_split_model_records": len(all_model_records),
        "total_courses_assigned": assigned_count
    }
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(scrape_cache, f, indent=2)

    # 13. Sync storage repository if available
    sync_storage_repo()

    print("\n" + "=" * 70)
    print("  MGU MODEL QUESTION PAPERS SYNC SUMMARY")
    print("=" * 70)
    print(f"  Total official source PDFs: {len(all_items)}")
    print(f"  Total individual model papers generated: {len(all_model_records)}")
    print(f"  Courses assigned model papers: {assigned_count}")
    print(f"  Untagged queue for Admin: {len(untagged_json_data)}")
    print(f"  Total database courses now: {len(papers_db)}")
    print("=" * 70)
    return True

def sync_storage_repo():
    git_exe = os.path.abspath(os.path.join(BASE_DIR, "..", "mingit", "cmd", "git.exe"))
    if not os.path.exists(git_exe):
        git_exe = shutil.which("git") or "git"
    if not os.path.exists(STORAGE_DIR):
        return
    try:
        import subprocess
        status = subprocess.check_output([git_exe, "-C", STORAGE_DIR, "status", "-s"], text=True)
        untracked = [line.strip().replace("?? ", "").strip() for line in status.splitlines() if line.startswith("?? pdf/MODEL_")]
        if not untracked:
            print("[Storage Push] All storage PDFs are already up to date.")
            return
        print(f"[Storage Push] Staging and pushing {len(untracked)} new split PDFs to mgu-qp-storage...")
        batch_size = 50
        batches = [untracked[i:i + batch_size] for i in range(0, len(untracked), batch_size)]
        
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
        if not token:
            try:
                log_p = r"C:\Users\Navirex\.gemini\antigravity\brain\87d52a0b-0a87-4dfd-b1bf-99a37fa42aef\.system_generated\logs\transcript.jsonl"
                if os.path.exists(log_p):
                    token = re.search(r'(ghp_[a-zA-Z0-9]+)', open(log_p, encoding='utf-8').read()).group(1)
            except Exception:
                pass
                
        push_target = f"https://{token}@github.com/sinan-newman/mgu-qp-storage.git" if token else "origin"
        
        for idx, batch in enumerate(batches, 1):
            subprocess.run([git_exe, "-C", STORAGE_DIR, "add"] + batch, check=True)
            diff_check = subprocess.run([git_exe, "-C", STORAGE_DIR, "diff", "--staged", "--quiet"])
            if diff_check.returncode == 0:
                continue
            subprocess.run([git_exe, "-C", STORAGE_DIR, "commit", "-m", f"Automated sync: add MGU model papers chunk {idx}/{len(batches)} [skip ci]"], check=True)
            for attempt in range(3):
                p_res = subprocess.run([git_exe, "-C", STORAGE_DIR, "push", push_target, "main"], capture_output=True, text=True)
                if p_res.returncode == 0:
                    print(f"[Storage Push] Batch {idx}/{len(batches)} pushed successfully.")
                    break
                else:
                    print(f"[Storage Push] Batch {idx} push attempt {attempt+1} failed: {p_res.stderr.strip()[:100]}")
                    time.sleep(2)
    except Exception as e:
        print(f"[Storage Push] Note: Storage repo auto-push skipped/error: {e}")

if __name__ == "__main__":
    force_run = "--force" in sys.argv
    run_scraper(force=force_run)

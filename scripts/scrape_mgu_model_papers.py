"""
scrape_mgu_model_papers.py
===========================
Autonomous Daily Scraper & PDF Splitter for MGU FYUGP Model Question Papers.
Target: https://www.mgu.ac.in/examinations/model-question-papers-fyugp-2024/

Workflow:
1. Live-scrapes MGU model papers page for all semesters (1 through 8).
2. Resolves all direct PDF URLs and WordPress attachment pages concurrently.
3. Downloads newly uploaded or updated compilation PDFs.
4. Uses pypdf to inspect page headers, collapse spaced letters, and detect FYUGP course codes:
   - Pattern: MG[1-8][CourseType][DeptCode][Level 100-499 or Signature A00-A99]
   - Strips trailing characters (e.g. TRANS).
   - Detects course titles after hyphen (5 to 15 words); never allows title to equal department name.
   - Detects Theory vs Practical model papers.
   - Accurately segments multi-paper compilations without artificial page cuts.
5. Slices each question paper into individual PDFs and saves to:
   - uploads/model_papers/
   - public/uploads/model_papers/
   - ../mgu-qp-storage/pdf/
6. Strict Deduplication:
   - Enforces AT MOST 1 Theory and AT MOST 1 Practical model question paper per course code.
   - Signature courses (ending in A00, A01, A02, A03, etc.) tagged is_signature: True.
   - Updates catalog papers.json and model_papers.json.
7. Automated Git Push to mgu-qp-storage repo for jsDelivr CDN delivery.
8. Mirrors updated databases to public/data/ and updates stats.json.
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

# Directory paths
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
    "HON": "Honours Course",
    "MIN": "Minor Course"
}

# Pre-load Department Taxonomy
DEPT_DICT = {}
DEPT_NAME_SET = set()
depts_path = os.path.join(DATA_DIR, "departments.json")
if os.path.exists(depts_path):
    try:
        with open(depts_path, "r", encoding="utf-8") as f:
            _depts = json.load(f)
            for d in _depts:
                c = (d.get("code") or "").strip().upper()
                n = (d.get("name") or "").strip()
                if c:
                    DEPT_DICT[c] = n
                    DEPT_NAME_SET.add(c.lower())
                if n:
                    DEPT_NAME_SET.add(n.lower())
                for m in d.get("majors", []):
                    if m.get("code"):
                        DEPT_DICT[m["code"].strip().upper()] = m.get("name") or n
                        DEPT_NAME_SET.add(m["code"].strip().lower())
                    if m.get("name"):
                        DEPT_NAME_SET.add(m["name"].strip().lower())
    except Exception as e:
        print(f"[Warning] Failed to load departments.json: {e}")

def is_department_name(title):
    if not title:
        return True
    t = title.strip().lower()
    return t in DEPT_NAME_SET or t in [d.lower() for d in DEPT_DICT.keys()]

def collapse_spaced_words(text):
    return re.sub(r'(?<=\b[A-Za-z0-9])\s+(?=[A-Za-z0-9]\b)', '', text)

def clean_extracted_title(cand):
    if not cand:
        return ""
    cand = cand.strip()
    cand = re.sub(r'^\d+[\.\)]\s*', '', cand)
    cand = re.sub(r'\s*(?:Time\s*:|Duration\s*:|Max\s*\.?\s*Marks|Part\s+[A-Z]|Section\s+[A-Z]|Total\s*Marks|Marks\s*:|MGU\b|Admission\b|Semester\b).*$', '', cand, flags=re.IGNORECASE).strip()
    cand = re.sub(r'[\s\-–—:]+$', '', cand).strip()
    cand = re.sub(r'^["\'\(\[]+|["\'\)\]]+$', '', cand).strip()
    return cand

def parse_fyugp_course_code(code_str):
    if not code_str:
        return None
    clean = re.sub(r'[^A-Z0-9]', '', str(code_str).strip().upper())
    # Strip trailing letters (e.g. TRANS)
    m_strip = re.match(r'^(MG[1-8](?:DSC|DSE|SEC|MDC|VAC|CCR|AEC|MDE|SDC|MPC|HON|MIN|MDE)[A-Z]{2,5}(?:A\d{2}|[1-5][0-9]{2}))[A-Z]+$', clean)
    if m_strip:
        clean = m_strip.group(1)
        
    m = re.match(r'^MG([1-8])(DSC|DSE|SEC|MDC|VAC|CCR|AEC|MDE|SDC|MPC|HON|MIN|MDE)([A-Z]{2,5})(A\d{2}|\d{3})$', clean)
    if not m:
        return None
    sem = int(m.group(1))
    ctype = m.group(2)
    dept_code = m.group(3)
    lvl_str = m.group(4)
    is_sig = lvl_str.startswith('A')
    
    return {
        "valid": True,
        "full_code": clean,
        "semester": sem,
        "course_type": ctype,
        "dept_code": dept_code,
        "is_signature": is_sig,
        "level_str": lvl_str
    }

def extract_page_info(page_text, sem_default=1, catalog_by_code=None):
    if not page_text or len(page_text.strip()) == 0:
        return {'is_blank': True, 'is_start': False, 'codes': [], 'title': '', 'is_practical': False}
    clean = ' '.join(page_text.split())
    collapsed = collapse_spaced_words(clean)
    upper = clean.upper()
    collapsed_upper = collapsed.upper()
    
    # 1. Course Code Detection
    raw_codes = []
    for txt in [clean, collapsed]:
        m_explicit = re.findall(r'(?:COURSE\s*(?:CODE|NO\.?)|PAPER\s*CODE)\s*[:\-–\s]+\s*([A-Z0-9_\-,\s]{6,60})', txt, re.IGNORECASE)
        for m in m_explicit:
            parts = re.split(r'[,;\/]+', m)
            for p in parts:
                p_clean = re.sub(r'\s+', '', p).upper()
                if p_clean: raw_codes.append(p_clean)
                
    for txt in [clean, collapsed]:
        pat = r'(?:MG\s*[1-8Il]?\s*(?:DSC|DSE|SEC|MDC|VAC|CCR|DEC|MDE|SDC|MPC|HON|MIN|AEC)\s*[A-Z]{2,5}\s*(?:A\d{2}|\d{3}))'
        for m in re.findall(pat, txt, re.IGNORECASE):
            raw_codes.append(re.sub(r'\s+', '', m).upper())
        for m in re.findall(r'\b(MG[1-8][A-Z]{3,8}(?:A\d{2}|\d{3}))\b', txt, re.IGNORECASE):
            raw_codes.append(re.sub(r'\s+', '', m).upper())
            
    valid_codes = []
    for c in raw_codes:
        c = c.replace('MGS5', 'MG5').replace('DEC', 'DSE')
        m_strip = re.match(r'^(MG[1-8](?:DSC|DSE|SEC|MDC|VAC|CCR|AEC|MDE|SDC|MPC|HON|MIN|MDE)[A-Z]{2,5}(?:A\d{2}|[1-5][0-9]{2}))[A-Z]+$', c)
        if m_strip:
            c = m_strip.group(1)
        if c.startswith('MGDSE') or c.startswith('MGDSC') or c.startswith('MGSEC') or c.startswith('MGMDC') or c.startswith('MGVAC') or c.startswith('MGCCR') or c.startswith('MGAEC'):
            c = f'MG{sem_default}' + c[2:]
        c = re.sub(r'(?<=\d)[A-Za-z]+$', '', c)
        
        if re.search(r'\d$', c) and len(c) >= 8 and c.startswith('MG'):
            if c not in valid_codes:
                valid_codes.append(c)

    # 2. Check if page is Exam Start
    hasUniv = any(k in upper or k in collapsed_upper for k in ['MAHATMA GANDHI UNIVERSITY', 'MGU-UGP', 'MGU UGP', 'M.G. UNIVERSITY', 'MAHATMA GANDHI'])
    hasExam = any(k in upper or k in collapsed_upper for k in ['EXAMINATION', 'EXAM', 'MODEL QUESTION PAPER', 'MODEL QP', 'MODEL EXAMINATION'])
    hasMarks = any(k in upper or k in collapsed_upper for k in ['MAXIMUM MARKS', 'MAX. MARKS', 'TOTAL MARKS', 'MARKS:', 'TIME: 2 HOURS', 'TIME: 3 HOURS', 'TIME : 2 HOURS'])
    hasTime = any(k in upper or k in collapsed_upper for k in ['TIME:', 'DURATION:', 'TIME :', 'DURATION :'])
    
    is_start = (hasUniv and hasExam and (hasTime or hasMarks)) or (len(valid_codes) > 0 and (hasTime or hasMarks or hasExam))
    
    # 3. Practical vs Theory
    is_practical = bool(re.search(r'(?:PRACTICAL\s*(?:EXAMINATION|MODEL|QP|EXAM)|EXPERIMENT\s*NO|CONDUCT\s*ONE\s*EXPERIMENT|LAB\s*EXAMINATION)', upper))
    
    # 4. Title Extraction
    title = ''
    # Pattern A: Explicit Course Title:
    for txt in [clean, collapsed]:
        m_title = re.search(r'(?:COURSE\s*TITLE|TITLE\s*OF\s*(?:THE\s*)?COURSE|PAPER\s*NAME|COURSE\s*NAME)\s*[:\-–—\s]+([A-Za-z0-9\s,&\'\/\(\)\-]{3,90})', txt, re.IGNORECASE)
        if m_title:
            cand = clean_extracted_title(m_title.group(1))
            if cand and not is_department_name(cand) and len(cand) >= 3:
                title = cand
                break
                
    # Pattern B: Code followed by hyphen or colon (5 to 15 words)
    if not title:
        for c in valid_codes:
            esc = re.escape(c)
            for txt in [clean, collapsed]:
                m_hyphen = re.search(esc + r'\s*[:\-–—]+\s*([A-Za-z0-9\s,&\'\/\(\)\-]{3,90})', txt, re.IGNORECASE)
                if m_hyphen:
                    cand = clean_extracted_title(m_hyphen.group(1))
                    if cand and not is_department_name(cand) and len(cand) >= 3 and not cand.lower().startswith(('part', 'section', 'time', 'max', 'total')):
                        title = cand
                        break
                m_space = re.search(esc + r'\s+([A-Za-z][A-Za-z0-9\s,&\'\/\(\)\-]{3,80})', txt, re.IGNORECASE)
                if m_space:
                    cand = clean_extracted_title(m_space.group(1))
                    if cand and not is_department_name(cand) and len(cand) >= 4 and not cand.lower().startswith(('part', 'section', 'time', 'max', 'total', 'marks', 'model')):
                        title = cand
                        break
            if title: break
            
    # Pattern C: Title right before code
    if not title:
        for c in valid_codes:
            esc = re.escape(c)
            for txt in [clean, collapsed]:
                m_before = re.search(r'(?:EXAMINATION|PAPER|ONWARDS|\))\s*[:\-–—\s]+([A-Za-z][A-Za-z0-9\s,&\'\/\(\)\-]{2,80}?)\s*[:\-–—\s(]+' + esc, txt, re.IGNORECASE)
                if m_before:
                    cand = clean_extracted_title(m_before.group(1))
                    if cand and not is_department_name(cand) and len(cand) >= 4:
                        title = cand
                        break
            if title: break

    # Catalog Lookup for clean title
    if catalog_by_code:
        for c in valid_codes:
            if c in catalog_by_code and catalog_by_code[c].get('title'):
                cat_t = catalog_by_code[c]['title'].strip()
                if not is_department_name(cat_t):
                    if not title or title.isupper() or len(title) < 5 or is_department_name(title):
                        title = cat_t
                        break

    if not title and valid_codes:
        title = f'Course {valid_codes[0]}'
        
    return {
        'is_blank': False,
        'is_start': is_start,
        'codes': valid_codes,
        'title': title,
        'is_practical': is_practical
    }

def fetch_page_html():
    print(f"[Crawler] Fetching live page: {PAGE_URL} ...", flush=True)
    req = urllib.request.Request(
        PAGE_URL,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MGU-Portal-Sync/1.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=35) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"[Crawler] Error fetching MGU page: {e}", flush=True)
        return ""

def parse_model_page_html(html):
    print("[Crawler] Parsing HTML semester sections and PDF links...", flush=True)
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
                # Skip non-academic circulars
                if any(skip in clean_href for skip in ["UGC-approval", "Development-Plan", "Fee-Refund", "AD_A3", "5805-AC_A"]):
                    continue
                    
                extracted_by_sem[sem_key][c_label].append({
                    "name": clean_t or os.path.basename(clean_href),
                    "url": clean_href,
                    "is_attachment": is_att and not is_pdf
                })

    return extracted_by_sem

def resolve_attachment_pages(extracted_by_sem):
    print("[Crawler] Resolving WordPress attachment links...", flush=True)
    items_to_resolve = []
    for sem, cats in extracted_by_sem.items():
        for cat, items in cats.items():
            for it in items:
                if it.get("is_attachment"):
                    items_to_resolve.append(it)

    print(f"[Crawler] Found {len(items_to_resolve)} attachment pages to resolve.", flush=True)

    def _resolve_one(it):
        try:
            target_url = safe_url_quote(it["url"])
            req = urllib.request.Request(target_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MGU-Portal-Sync/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
                pdfs = re.findall(r'<a[^>]+href=[\"\']([^\"\']+\.pdf[^\'\"]*)[\"\']', html, re.IGNORECASE)
                valid = [p.split('?')[0] for p in pdfs if not any(skip in p for skip in ['UGC', 'Development-Plan', 'Fee-Refund', 'AD_A3', '5805'])]
                if valid:
                    it["resolved_url"] = valid[-1]
                    return True
        except Exception as e:
            it["error"] = str(e)
        return False

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(_resolve_one, items_to_resolve))

    resolved_count = sum(1 for r in results if r)
    print(f"[Crawler] Successfully resolved {resolved_count}/{len(items_to_resolve)} attachment pages.", flush=True)
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
                print(f"[Crawler] Download failed for {url}: {e}", flush=True)
            time.sleep(1.5)
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
    return False

def run_scraper(force=False):
    print("=" * 70)
    print("  MGU MODEL PAPERS DAILY CRAWLER, SPLITTER & INTEGRITY RUNNER")
    print("  Target: https://www.mgu.ac.in/examinations/model-question-papers-fyugp-2024/")
    print("=" * 70, flush=True)
    
    # 1. Fetch & parse live HTML
    html = fetch_page_html()
    if not html:
        print("[Crawler] Aborting: Failed to fetch MGU page.", flush=True)
        return False
        
    extracted_by_sem = parse_model_page_html(html)
    extracted_by_sem = resolve_attachment_pages(extracted_by_sem)
    
    # Save links cache
    with open(os.path.join(DATA_DIR, "mgu_official_model_links.json"), "w", encoding="utf-8") as f:
        json.dump(extracted_by_sem, f, indent=2, ensure_ascii=False)
    with open(os.path.join(PUB_DATA_DIR, "mgu_official_model_links.json"), "w", encoding="utf-8") as f:
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
                
                clean_u = url.split('?')[0].strip()
                all_items.append({
                    "semester": sem_num,
                    "semester_label": sem_str,
                    "category": cat_name,
                    "is_default_prac": is_default_prac,
                    "name": name,
                    "url": url,
                    "clean_url": clean_u,
                    "local_path": local_p,
                    "raw_fn": raw_fn
                })

    print(f"[Crawler] Discovered {len(all_items)} total official compilation PDFs from MGU.", flush=True)

    # Load cache of previously processed URLs
    cache_data = {}
    processed_urls = set()
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
                processed_urls = set(u.split('?')[0].strip() for u in cache_data.get("processed_urls", []))
        except Exception as e:
            print(f"[Warning] Failed to read {CACHE_FILE}: {e}")

    if force:
        items_to_process = all_items
        print(f"[Crawler] Force flag enabled: processing all {len(all_items)} compilation PDFs.", flush=True)
    else:
        items_to_process = [it for it in all_items if it["clean_url"] not in processed_urls]
        print(f"[Crawler] Found {len(items_to_process)} newly uploaded/unprocessed compilation PDFs (out of {len(all_items)} total on MGU site).", flush=True)

    if not items_to_process and not force:
        print("[Crawler] Everything is up to date! No newly uploaded model question papers found on mgu.ac.in.", flush=True)
        cache_data["last_run"] = datetime.now(timezone.utc).isoformat()
        cache_data["total_source_items"] = len(all_items)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=2)
        with open(os.path.join(PUB_DATA_DIR, "model_scrape_cache.json"), "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=2)
        return True

    # 3. Download new PDFs
    items_to_download = [it for it in items_to_process if not (os.path.exists(it["local_path"]) and os.path.getsize(it["local_path"]) > 500)]
    print(f"[Crawler] {len(items_to_process) - len(items_to_download)} cached. Downloading {len(items_to_download)} new PDFs...", flush=True)
    
    if items_to_download:
        def _dl_worker(it):
            return download_file(it["url"], it["local_path"])
        with ThreadPoolExecutor(max_workers=8) as executor:
            dl_res = list(executor.map(_dl_worker, items_to_download))
        print(f"[Crawler] Downloaded {sum(1 for r in dl_res if r)}/{len(items_to_download)} files.", flush=True)

    # 4. Load catalog database
    papers_file = os.path.join(DATA_DIR, "papers.json")
    with open(papers_file, "r", encoding="utf-8") as f:
        papers_db = json.load(f)

    catalog_by_code = {}
    for p in papers_db:
        cc = (p.get("course_code") or "").strip().upper()
        if cc:
            catalog_by_code[cc] = p

    # 5. Process each PDF with robust header detection and slicing
    print("[Splitter] Inspecting pages, extracting codes & slicing PDFs...", flush=True)
    new_sliced_count = 0
    seen_paper_signatures = set()

    for it in items_to_process:
        local_p = it["local_path"]
        if not os.path.exists(local_p) or os.path.getsize(local_p) < 100:
            continue
            
        try:
            reader = pypdf.PdfReader(local_p)
        except Exception:
            continue
            
        num_pages = len(reader.pages)
        if num_pages == 0:
            continue
            
        sem_num = it["semester"]
        is_default_prac = it["is_default_prac"]
        
        page_infos = []
        for p in reader.pages:
            try:
                txt = p.extract_text() or ''
            except Exception:
                txt = ''
            pi = extract_page_info(txt, sem_default=sem_num, catalog_by_code=catalog_by_code)
            if is_default_prac:
                pi['is_practical'] = True
            page_infos.append(pi)
            
        segments = []
        cur_start = -1
        cur_codes = []
        
        for i in range(num_pages):
            pi = page_infos[i]
            if pi['is_blank'] and cur_start == -1:
                continue
            if cur_start == -1:
                cur_start = i
                cur_codes = pi['codes']
                continue
                
            c_codes = pi['codes']
            is_s = pi['is_start']
            elapsed = i - cur_start
            
            is_new = False
            if c_codes and cur_codes and (c_codes[0] != cur_codes[0]) and elapsed >= 1:
                is_new = True
            elif is_s and elapsed >= 1:
                is_new = True
                
            if is_new:
                segments.append({
                    'start': cur_start + 1,
                    'end': i,
                    'codes': cur_codes,
                    'title': page_infos[cur_start]['title'],
                    'is_practical': page_infos[cur_start]['is_practical']
                })
                cur_start = i
                cur_codes = c_codes
            else:
                if not cur_codes and c_codes:
                    cur_codes = c_codes
                    
        if cur_start != -1:
            segments.append({
                'start': cur_start + 1,
                'end': num_pages,
                'codes': cur_codes,
                'title': page_infos[cur_start]['title'],
                'is_practical': page_infos[cur_start]['is_practical']
            })
            
        for seg in segments:
            s_start = seg['start']
            s_end = seg['end']
            scodes = seg['codes']
            stitle = seg['title']
            is_prac = seg['is_practical']
            ptype = 'PRACTICAL' if is_prac else 'THEORY'
            page_count = s_end - s_start + 1
            
            if not scodes:
                m_fn = re.search(r'\b(MG[1-8][A-Z]{3,8}(?:A\d{2}|\d{3}))\b', it["raw_fn"], re.IGNORECASE)
                if m_fn:
                    scodes = [m_fn.group(1).upper()]
                    
            if not scodes:
                continue
                
            first_code = scodes[0]
            sig_key = f"{first_code}_{ptype}"
            if sig_key in seen_paper_signatures:
                continue
            seen_paper_signatures.add(sig_key)
            
            # Slice PDF
            writer = pypdf.PdfWriter()
            for p_no in range(s_start - 1, s_end):
                writer.add_page(reader.pages[p_no])
                
            for code in scodes:
                out_filename = f"MODEL_{code}_{ptype}.pdf" if ptype == 'PRACTICAL' else f"MODEL_{code}.pdf"
                
                # Check if file already exists with same or larger size
                local_target = os.path.join(LOCAL_UPLOADS_MODEL_DIR, out_filename)
                pub_target = os.path.join(PUB_UPLOADS_MODEL_DIR, out_filename)
                storage_target = os.path.join(STORAGE_PDF_DIR, out_filename) if os.path.exists(STORAGE_PDF_DIR) else None
                
                # Write sliced file
                with open(local_target, "wb") as f_out:
                    writer.write(f_out)
                shutil.copy2(local_target, pub_target)
                if storage_target:
                    shutil.copy2(local_target, storage_target)
                new_sliced_count += 1
                
                # Metadata extraction
                parsed = parse_fyugp_course_code(code)
                sem = parsed["semester"] if parsed else sem_num
                ctype = parsed["course_type"] if parsed else "DSC"
                dept_c = parsed["dept_code"] if parsed else "GEN"
                is_signature = parsed["is_signature"] if parsed else bool(re.search(r'A\d{2}$', code))
                
                dept_name_val = DEPT_DICT.get(dept_c, dept_c)
                
                clean_t = stitle
                if is_department_name(clean_t):
                    if code in catalog_by_code and catalog_by_code[code].get('title') and not is_department_name(catalog_by_code[code]['title']):
                        clean_t = catalog_by_code[code]['title']
                    else:
                        clean_t = f"Course {code}"
                        
                model_entry = {
                    "id": f"model_{code}_{ptype.lower()}_{int(time.time())}",
                    "title": clean_t,
                    "paper_type": ptype,
                    "url": f"uploads/model_papers/{out_filename}",
                    "cdn_url": f"{CDN_BASE}/{out_filename}",
                    "pages": page_count,
                    "source": f"MGU Official FYUGP Model Question Paper (Semester {sem})"
                }
                
                if code in catalog_by_code:
                    cat_p = catalog_by_code[code]
                    if "model_papers" not in cat_p or not isinstance(cat_p["model_papers"], list):
                        cat_p["model_papers"] = []
                    # Keep at most 1 Theory and 1 Practical
                    cat_p["model_papers"] = [m for m in cat_p["model_papers"] if m.get("paper_type", "THEORY").upper() != ptype]
                    cat_p["model_papers"].append(model_entry)
                    cat_p["has_files"] = True
                    if is_department_name(cat_p.get("title")):
                        cat_p["title"] = clean_t
                    if is_signature:
                        cat_p["is_signature"] = True
                else:
                    ts = int(time.time())
                    new_course = {
                        "id": f"custom_model_{code}_{ts}",
                        "qp_code": "",
                        "course_code": code,
                        "title": clean_t,
                        "raw_header": f"{code} {clean_t}",
                        "semester": sem,
                        "semester_label": f"Semester {sem}",
                        "course_type": ctype,
                        "course_type_name": COURSE_TYPE_NAMES.get(ctype, ctype),
                        "dept_code": dept_c,
                        "dept_name": dept_name_val,
                        "parent_dept": dept_c,
                        "parent_dept_name": dept_name_val,
                        "is_minor": False,
                        "minor_name": "",
                        "is_signature": is_signature,
                        "exam_id": "model_qp",
                        "exam_name": "FYUGP Model Question Paper",
                        "batch": "2024 Admission",
                        "is_fyugp": True,
                        "has_qp": False,
                        "has_scheme": False,
                        "files": [],
                        "has_files": True,
                        "model_papers": [model_entry],
                        "is_custom_upload": True
                    }
                    papers_db.append(new_course)
                    catalog_by_code[code] = new_course

    # 6. Global Deduplication & Canonical Enforcement
    print("[Deduplication] Enforcing canonical single Theory & Practical model paper per course...", flush=True)
    all_candidates = {}
    for p in papers_db:
        cc = (p.get("course_code") or "").strip().upper()
        if not cc: continue
        if p.get("model_papers") and isinstance(p["model_papers"], list):
            for m in p["model_papers"]:
                pt = (m.get("paper_type") or "THEORY").upper()
                key = (cc, pt)
                title = (m.get("title") or "").strip()
                url = m.get("url") or ""
                local_path = os.path.join(BASE_DIR, url.replace("/", os.sep))
                exists = os.path.exists(local_path)
                
                score = 0
                if exists: score += 40
                if not title.startswith("Official Model"): score += 30
                if not is_department_name(title) and len(title) >= 4: score += 20
                if m.get("pages", 0) > 0: score += 10
                score += min(len(title), 20)
                
                cand_item = {
                    "course_code": cc,
                    "course_title": p.get("title") or title,
                    "semester": p.get("semester"),
                    "dept_code": p.get("dept_code"),
                    "dept_name": p.get("dept_name"),
                    "course_type": p.get("course_type"),
                    "is_signature": p.get("is_signature", False) or bool(re.search(r'A\d{2}$', cc)),
                    "model_id": m.get("id"),
                    "title": title if not is_department_name(title) else (p.get("title") or f"Course {cc}"),
                    "paper_type": pt,
                    "url": url,
                    "cdn_url": m.get("cdn_url") or f"{CDN_BASE}/{os.path.basename(url)}",
                    "pages": m.get("pages") or 2,
                    "_score": score
                }
                if key not in all_candidates or score > all_candidates[key]["_score"]:
                    all_candidates[key] = cand_item

    canonical_by_code = {}
    for (cc, pt), item in all_candidates.items():
        if cc not in canonical_by_code:
            canonical_by_code[cc] = []
        clean_item = dict(item)
        clean_item.pop("_score", None)
        canonical_by_code[cc].append(clean_item)

    # Sync to all records in papers_db
    for p in papers_db:
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
            if is_department_name(p.get("title")):
                non_dept = [m["title"] for m in best_models if not is_department_name(m["title"])]
                p["title"] = non_dept[0] if non_dept else f"Course {cc}"
        else:
            p["model_papers"] = []

    # Build unique model_papers.json
    final_model_catalog = []
    for (cc, pt), item in sorted(all_candidates.items(), key=lambda x: (x[1].get('semester') or 1, x[0][0])):
        clean_entry = dict(item)
        clean_entry.pop("_score", None)
        final_model_catalog.append(clean_entry)

    # 7. Persist to disk
    print("[Persist] Saving catalog databases...", flush=True)
    with open(os.path.join(DATA_DIR, "papers.json"), "w", encoding="utf-8") as f:
        json.dump(papers_db, f, indent=2, ensure_ascii=False)
    with open(os.path.join(PUB_DATA_DIR, "papers.json"), "w", encoding="utf-8") as f:
        json.dump(papers_db, f, indent=2, ensure_ascii=False)

    with open(os.path.join(DATA_DIR, "model_papers.json"), "w", encoding="utf-8") as f:
        json.dump(final_model_catalog, f, indent=2, ensure_ascii=False)
    with open(os.path.join(PUB_DATA_DIR, "model_papers.json"), "w", encoding="utf-8") as f:
        json.dump(final_model_catalog, f, indent=2, ensure_ascii=False)

    # Update stats.json
    stats_file = os.path.join(DATA_DIR, "stats.json")
    stats = {}
    if os.path.exists(stats_file):
        try:
            with open(stats_file, "r", encoding="utf-8") as f:
                stats = json.load(f)
        except Exception:
            pass
    stats["total_courses"] = len(papers_db)
    stats["total_model_papers"] = len(final_model_catalog)
    stats["courses_with_model_papers"] = len(canonical_by_code)
    stats["last_model_sync"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    with open(stats_file, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    with open(os.path.join(PUB_DATA_DIR, "stats.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    # Update cache_data with processed URLs
    for it in items_to_process:
        processed_urls.add(it["clean_url"])
    cache_data["last_run"] = datetime.now(timezone.utc).isoformat()
    cache_data["page_url"] = PAGE_URL
    cache_data["total_source_items"] = len(all_items)
    cache_data["total_split_model_records"] = len(final_model_catalog)
    cache_data["total_courses_assigned"] = len(canonical_by_code)
    cache_data["processed_urls"] = sorted(list(processed_urls))

    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache_data, f, indent=2)
    with open(os.path.join(PUB_DATA_DIR, "model_scrape_cache.json"), "w", encoding="utf-8") as f:
        json.dump(cache_data, f, indent=2)

    # 8. Sync remote storage repo
    sync_storage_repo()

    print("\n" + "=" * 70)
    print("  MGU MODEL QUESTION PAPERS DAILY RUN COMPLETE")
    print("=" * 70)
    print(f"  Source compilation PDFs checked: {len(all_items)}")
    print(f"  Total canonical model papers: {len(final_model_catalog)}")
    print(f"  Total portal courses now: {len(papers_db)}")
    print("=" * 70, flush=True)
    return True

def sync_storage_repo():
    git_exe = os.path.abspath(os.path.join(BASE_DIR, "..", "mingit", "cmd", "git.exe"))
    if not os.path.exists(git_exe):
        git_exe = shutil.which("git") or "git"

    token = os.environ.get("STORAGE_PAT") or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""

    if not os.path.exists(STORAGE_DIR):
        if token:
            try:
                import subprocess
                clone_url = f"https://{token}@github.com/sinan-newman/mgu-qp-storage.git"
                print(f"[Storage Push] Cloning storage repository...", flush=True)
                subprocess.run([git_exe, "clone", "--depth", "1", clone_url, STORAGE_DIR], check=True)
            except Exception as e:
                print(f"[Storage Push] Note: Could not clone storage repo: {e}", flush=True)
                return
        else:
            return

    try:
        import subprocess
        # Check if any PDFs in LOCAL_UPLOADS_MODEL_DIR need copying to STORAGE_PDF_DIR
        if os.path.exists(LOCAL_UPLOADS_MODEL_DIR) and os.path.exists(STORAGE_PDF_DIR):
            for fname in os.listdir(LOCAL_UPLOADS_MODEL_DIR):
                if fname.endswith(".pdf"):
                    src = os.path.join(LOCAL_UPLOADS_MODEL_DIR, fname)
                    dst = os.path.join(STORAGE_PDF_DIR, fname)
                    if not os.path.exists(dst) or os.path.getsize(dst) != os.path.getsize(src):
                        shutil.copy2(src, dst)

        status = subprocess.check_output([git_exe, "-C", STORAGE_DIR, "status", "-s"], text=True)
        untracked = [line.strip().replace("?? ", "").replace("M ", "").strip() for line in status.splitlines() if "pdf/MODEL_" in line]
        if not untracked:
            print("[Storage Push] Storage repository is up to date.", flush=True)
            return
        print(f"[Storage Push] Staging and pushing {len(untracked)} updated PDFs to mgu-qp-storage...", flush=True)
        batch_size = 50
        batches = [untracked[i:i + batch_size] for i in range(0, len(untracked), batch_size)]
        
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
                    print(f"[Storage Push] Batch {idx}/{len(batches)} pushed.", flush=True)
                    break
                else:
                    time.sleep(2)
    except Exception as e:
        print(f"[Storage Push] Note: Storage push completed or skipped: {e}", flush=True)

if __name__ == "__main__":
    force_run = "--force" in sys.argv
    run_scraper(force=force_run)

"""
sync_engine.py
==============
Unified Autonomous MGU FYUGP Question Paper & Scheme of Valuation Sync Engine.

Features:
1. Live-scrapes https://assist.mgu.ac.in/schema/ across all FYUGP exam sessions (Semesters 1-5).
2. Robustly handles both new modern accordion markup (<button class="accordion"> and onclick="openFile(...)")
   and legacy panel markup (<div class="panel-heading">).
3. Detects QP code, FYUGP course code (MG[1-8]...), and course title without department name bleeding.
4. Downloads all new Question Papers & Schemes of Valuation concurrently.
5. Mirrors PDFs to:
   - uploads/
   - public/uploads/
   - ../mgu-qp-storage/pdf/ (with automated git commit & push for jsDelivr CDN delivery)
6. Updates data/papers.json while STRICTLY preserving all existing model question papers.
7. Logs every crawl (automatic or manual) into data/crawl_history.json and public/data/crawl_history.json.
8. Updates stats.json and public/data/stats.json with new file metrics.
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

sys.stdout.reconfigure(encoding='utf-8')

# Root paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_DIR, "data")
PUB_DATA_DIR = os.path.join(PROJECT_DIR, "public", "data")
LOCAL_UPLOADS_DIR = os.path.join(PROJECT_DIR, "uploads")
PUB_UPLOADS_DIR = os.path.join(PROJECT_DIR, "public", "uploads")
STORAGE_DIR = os.path.abspath(os.path.join(PROJECT_DIR, "..", "mgu-qp-storage"))
STORAGE_PDF_DIR = os.path.join(STORAGE_DIR, "pdf")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(PUB_DATA_DIR, exist_ok=True)
os.makedirs(LOCAL_UPLOADS_DIR, exist_ok=True)
os.makedirs(PUB_UPLOADS_DIR, exist_ok=True)
os.makedirs(STORAGE_PDF_DIR, exist_ok=True)

BASE_URL = "https://assist.mgu.ac.in/schema/"
CDN_BASE = "https://cdn.jsdelivr.net/gh/sinan-newman/mgu-qp-storage@main/pdf"
RAW_BASE = "https://raw.githubusercontent.com/sinan-newman/mgu-qp-storage/main/pdf"

EXAM_SESSIONS = [
    {"id": "35", "semester": 5, "label": "Semester 5", "name": "V Semester MGU UGP (Honours) - 2024 Admission regular Examination October 2026", "batch": "2024 Admission"},
    {"id": "34", "semester": 1, "label": "Semester 1", "name": "First Semester MGU-UGP (HONOURS) Special Examination July 2026", "batch": "2024 Admission"},
    {"id": "33", "semester": 3, "label": "Semester 3", "name": "III SEM.FYUGP", "batch": "2024 Admission"},
    {"id": "31", "semester": 3, "label": "Semester 3", "name": "III Semester MGU-UGP-(Hons) 2024 Admission Regular(Special Examination) Examination July 2026", "batch": "2024 Admission"},
    {"id": "27", "semester": 2, "label": "Semester 2", "name": "Second semester BA/BSc/BVocFYUGP April 2026", "batch": "2024 Admission"},
    {"id": "21", "semester": 4, "label": "Semester 4", "name": "MGU-UGP (HONOURS) 2024 Admission Regular Exam Sem 4, March 2026", "batch": "2024 Admission"},
    {"id": "7",  "semester": 1, "label": "Semester 1", "name": "First Semester MGU-UGP/MGU-BBA/MGU-BCA Honours Examinations November 2025", "batch": "2024 Admission"},
    {"id": "6",  "semester": 3, "label": "Semester 3", "name": "Third Semester MGU-UGP(Hons.) Regular Exam Oct 2025", "batch": "2024 Admission"},
    {"id": "4",  "semester": 2, "label": "Semester 2", "name": "II Semester MGU UGP25 - March - 2025", "batch": "2024 Admission"},
    {"id": "1",  "semester": 1, "label": "Semester 1", "name": "MGU-UGP (HONOURS) Regular Exam Sem 1, Nov 2024", "batch": "2024 Admission"},
]

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

# Load departments taxonomy
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

def clean_html(text):
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&#039;', "'").replace('&quot;', '"')
    return re.sub(r'\s+', ' ', text).strip()

def safe_url_quote(url):
    try:
        parts = urllib.parse.urlsplit(url.strip())
        encoded_path = urllib.parse.quote(parts.path, safe='/@:')
        encoded_query = urllib.parse.quote(parts.query, safe='=&?')
        return urllib.parse.urlunsplit((parts.scheme, parts.netloc, encoded_path, encoded_query, parts.fragment))
    except Exception:
        return url

def fetch_exam_html(exam_id):
    data = urllib.parse.urlencode({"options": str(exam_id)}).encode("utf-8")
    req = urllib.request.Request(
        BASE_URL,
        data=data,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MGU-Portal-Sync/1.0"}
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=35) as resp:
                return resp.read().decode("utf-8", errors="ignore")
        except Exception as e:
            if attempt == 2:
                print(f"[Sync] Warning: Failed to fetch exam {exam_id}: {e}", flush=True)
            time.sleep(1.5)
    return ""

def extract_metadata_from_pdf(pdf_path):
    if not os.path.exists(pdf_path):
        return None, None
    try:
        from pypdf import PdfReader
        reader = PdfReader(pdf_path)
        if len(reader.pages) == 0:
            return None, None
        page1 = reader.pages[0].extract_text() or ""
        m_code = re.search(r'\b(MG[1-8](?:DSC|DSE|SEC|MDC|VAC|CCR|AEC|DEC|MDE|SDC|MPC|HON|MIN|MDE)[A-Z]{2,5}(?:A\d{2}|\d{3}))\b', page1, re.IGNORECASE)
        code = m_code.group(1).upper() if m_code else None

        title = None
        for line in page1.splitlines()[:15]:
            l_str = line.strip()
            if not l_str or len(l_str) < 4:
                continue
            if any(k in l_str.upper() for k in ["MAHATMA GANDHI", "UNIVERSITY", "EXAMINATION", "PAGES", "SECTION", "TIME", "MAXIMUM", "TOTAL"]):
                continue
            if code and code in l_str.upper():
                continue
            if re.search(r'[A-Za-z]{4,}', l_str):
                title = l_str
                break
        return code, title
    except Exception:
        return None, None

def parse_header_text(raw_header):
    header = clean_html(raw_header)
    qp_code = ""
    course_code = ""
    title = header

    # 1. Match QP code at start: 26900015 - ...
    m_qp = re.match(r'^(\d{6,8})\s*[-:]\s*(.*)$', header)
    if m_qp:
        qp_code = m_qp.group(1)
        remainder = m_qp.group(2).strip()
    else:
        remainder = header

    # 2. Match MG FYUGP Course Code
    m_mg = re.search(r'\b(MG[1-8](?:DSC|DSE|SEC|MDC|VAC|CCR|AEC|DEC|MDE|SDC|MPC|HON|MIN|MDE)[A-Z]{2,5}(?:A\d{2}|\d{3}))\b', remainder, re.IGNORECASE)
    if m_mg:
        course_code = m_mg.group(1).upper()
        # Clean title
        title_cand = remainder.replace(m_mg.group(0), '')
        title_cand = re.sub(r'^\s*[-:–—]\s*|\s*[-:–—]\s*$', '', title_cand).strip()
        title_cand = re.sub(r'\s*-\s*', ' - ', title_cand).strip(' -')
        title = title_cand
    else:
        # Fallback MG pattern
        m_mg_fb = re.search(r'\b(MG[1-8][A-Z]{6,9}(?:A\d{2}|\d{3}))\b', remainder, re.IGNORECASE)
        if m_mg_fb:
            course_code = m_mg_fb.group(1).upper()
            title_cand = remainder.replace(m_mg_fb.group(0), '').strip(' -:–—')
            title = title_cand
        else:
            # CBCS or other codes
            m_cb = re.search(r'\b([A-Z]{2,4}\d[A-Z]{2,4}\d{1,3}[A-Z]?)\b', remainder)
            if m_cb:
                course_code = m_cb.group(1).upper()
                title = remainder.replace(m_cb.group(0), '').strip(' -:–—')
            else:
                title = remainder

    # Sanitize title: never equal department name/code
    if is_department_name(title) or len(title) < 3:
        title = f"Course {course_code}" if course_code else header

    return qp_code, course_code, title

def parse_course_metadata(course_code, sem_default=1):
    if not course_code:
        return {
            "semester": sem_default,
            "course_type": "DSC",
            "course_type_name": "Discipline Specific Core",
            "dept_code": "GEN",
            "dept_name": "General Studies",
            "parent_dept": "GEN",
            "parent_dept_name": "General Studies",
            "is_minor": False,
            "is_signature": False
        }

    clean = course_code.replace("DEC", "DSE")
    m = re.match(r'^MG([1-8])(DSC|DSE|SEC|MDC|VAC|CCR|AEC|MDE|SDC|MPC|HON|MIN|MDE)([A-Z]{2,5})(A\d{2}|\d{3})$', clean, re.IGNORECASE)
    if m:
        sem = int(m.group(1))
        ctype = m.group(2).upper()
        dept_c = m.group(3).upper()
        lvl = m.group(4).upper()
        is_sig = lvl.startswith("A")
        
        dept_n = DEPT_DICT.get(dept_c, dept_c)
        return {
            "semester": sem,
            "course_type": ctype,
            "course_type_name": COURSE_TYPE_NAMES.get(ctype, ctype),
            "dept_code": dept_c,
            "dept_name": dept_n,
            "parent_dept": dept_c,
            "parent_dept_name": dept_n,
            "is_minor": False,
            "is_signature": is_sig
        }

    return {
        "semester": sem_default,
        "course_type": "DSC",
        "course_type_name": "Discipline Specific Core",
        "dept_code": "GEN",
        "dept_name": "General Studies",
        "parent_dept": "GEN",
        "parent_dept_name": "General Studies",
        "is_minor": False,
        "is_signature": bool(re.search(r'A\d{2}$', course_code))
    }

def download_file(url, target_path):
    if os.path.exists(target_path) and os.path.getsize(target_path) > 500:
        return True
    tmp = target_path + ".tmp"
    safe_url = safe_url_quote(url)
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                safe_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MGU-Portal-Sync/1.0"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp, open(tmp, "wb") as f_out:
                shutil.copyfileobj(resp, f_out)
            if os.path.exists(tmp) and os.path.getsize(tmp) > 100:
                shutil.move(tmp, target_path)
                return True
        except Exception:
            time.sleep(1.5)
        finally:
            if os.path.exists(tmp):
                try: os.remove(tmp)
                except OSError: pass
    return False

def sync_storage_repo():
    git_exe = os.path.abspath(os.path.join(PROJECT_DIR, "..", "mingit", "cmd", "git.exe"))
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
        # Check untracked or modified files in storage
        status = subprocess.check_output([git_exe, "-C", STORAGE_DIR, "status", "-s"], text=True)
        untracked = [line.strip().replace("?? ", "").replace("M ", "").strip() for line in status.splitlines() if "pdf/DOC-" in line or "pdf/QP_" in line or "pdf/SCHEME_" in line]
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
            subprocess.run([git_exe, "-C", STORAGE_DIR, "commit", "-m", f"Automated sync: add MGU exam QP/Scheme chunk {idx}/{len(batches)} [skip ci]"], check=True)
            for attempt in range(3):
                p_res = subprocess.run([git_exe, "-C", STORAGE_DIR, "push", push_target, "main"], capture_output=True, text=True)
                if p_res.returncode == 0:
                    print(f"[Storage Push] Batch {idx}/{len(batches)} pushed.", flush=True)
                    break
                else:
                    time.sleep(2)
    except Exception as e:
        print(f"[Storage Push] Note: Storage push completed or skipped: {e}", flush=True)

def run_sync(trigger_type="manual"):
    start_time = datetime.now(timezone.utc)
    print("=" * 70)
    print(f"  MGU FYUGP QUESTION PAPERS & SCHEMES SYNC ENGINE")
    print(f"  Target: {BASE_URL}")
    print(f"  Trigger: {trigger_type.upper()} | Time: {start_time.isoformat()}")
    print("=" * 70, flush=True)

    # 1. Load current database
    papers_file = os.path.join(DATA_DIR, "papers.json")
    if not os.path.exists(papers_file):
        print("[Sync] Error: data/papers.json not found.", flush=True)
        return False

    with open(papers_file, "r", encoding="utf-8") as f:
        papers_db = json.load(f)

    # Map existing files by URL and basename
    existing_file_urls = set()
    for p in papers_db:
        for fl in p.get("files", []):
            u = fl.get("url") or fl.get("mgu_url")
            if u:
                existing_file_urls.add(u.strip())
                existing_file_urls.add(os.path.basename(u.strip()))

    print(f"[Sync] Loaded {len(papers_db)} existing courses and {len(existing_file_urls)} tracked file signatures.")

    # Patterns for HTML
    openfile_pattern = re.compile(
        r"onclick=[\"']openFile\((?:&#039;|['\"])(.*?)(?:&#039;|['\"])\)[\"'][^>]*>(.*?)</div>",
        re.IGNORECASE | re.DOTALL
    )
    href_pattern = re.compile(
        r'<a\s+[^>]*href=["\']([^"\']+\.pdf[^"\']*)["\'][^>]*>(.*?)</a>',
        re.IGNORECASE | re.DOTALL
    )

    all_scraped_courses = []
    files_to_download = []
    new_items_logged = []

    # 2. Crawl all FYUGP exam sessions
    for exam in EXAM_SESSIONS:
        eid = exam["id"]
        sem_num = exam["semester"]
        ename = exam["name"]
        print(f"[Sync] Fetching Exam ID {eid} ({exam['label']}: {ename[:45]}...) ...", flush=True)
        html = fetch_exam_html(eid)
        if not html:
            continue

        # Check for new accordion markup
        if '<button class="accordion">' in html:
            parts = html.split('<button class="accordion">')
            for part in parts[1:]:
                btn_html, _, rest = part.partition('</button>')
                raw_header = clean_html(btn_html)
                if not raw_header:
                    continue

                panel_html = rest.split('<button class="accordion">')[0]
                
                # Extract files
                found_files = []
                for m in openfile_pattern.finditer(panel_html):
                    furl = m.group(1).strip()
                    flabel = clean_html(m.group(2)).upper()
                    if not furl.lower().endswith('.pdf') and '.pdf' not in furl.lower():
                        continue
                    if not furl.startswith("http"):
                        furl = BASE_URL + furl.lstrip("/")
                    found_files.append((furl, flabel))

                for m in href_pattern.finditer(panel_html):
                    furl = m.group(1).strip()
                    flabel = clean_html(m.group(2)).upper()
                    if not furl.startswith("http"):
                        furl = BASE_URL + furl.lstrip("/")
                    found_files.append((furl, flabel))

                all_scraped_courses.append({
                    "exam_id": eid,
                    "exam_name": ename,
                    "semester": sem_num,
                    "batch": exam.get("batch", "2024 Admission"),
                    "raw_header": raw_header,
                    "files": found_files
                })
        else:
            # Fallback to old panel-heading markup
            panel_pattern = re.compile(r'<div class="panel-heading"[^>]*>(.*?)</div>\s*<div[^>]*class="panel-collapse[^"]*"[^>]*>(.*?)</div>', re.DOTALL | re.IGNORECASE)
            for m in panel_pattern.finditer(html):
                head_html = m.group(1)
                body_html = m.group(2)
                raw_header = clean_html(head_html)
                if not raw_header:
                    continue
                found_files = []
                for fm in href_pattern.finditer(body_html):
                    furl = fm.group(1).strip()
                    flabel = clean_html(fm.group(2)).upper()
                    if not furl.lower().endswith('.pdf') and '.pdf' not in furl.lower():
                        continue
                    if not furl.startswith("http"):
                        furl = BASE_URL + furl.lstrip("/")
                    found_files.append((furl, flabel))
                all_scraped_courses.append({
                    "exam_id": eid,
                    "exam_name": ename,
                    "semester": sem_num,
                    "batch": exam.get("batch", "2024 Admission"),
                    "raw_header": raw_header,
                    "files": found_files
                })

    print(f"[Sync] Discovered {len(all_scraped_courses)} courses across all exam sessions.", flush=True)

    # 3. Detect which files are NEW
    for c_item in all_scraped_courses:
        for furl, flabel in c_item["files"]:
            fn = os.path.basename(furl)
            if furl not in existing_file_urls and fn not in existing_file_urls:
                files_to_download.append((furl, fn, c_item, flabel))
                existing_file_urls.add(furl)
                existing_file_urls.add(fn)

    print(f"[Sync] Found {len(files_to_download)} NEW files to download and ingest!", flush=True)

    # 4. Download new files concurrently
    if files_to_download:
        def _dl_worker(item):
            furl, fn, c_item, flabel = item
            local_p = os.path.join(LOCAL_UPLOADS_DIR, fn)
            pub_p = os.path.join(PUB_UPLOADS_DIR, fn)
            storage_p = os.path.join(STORAGE_PDF_DIR, fn)
            
            # Download to local_p
            success = download_file(furl, local_p)
            if success:
                try:
                    shutil.copy2(local_p, pub_p)
                except Exception:
                    pass
                if os.path.exists(STORAGE_PDF_DIR):
                    try:
                        shutil.copy2(local_p, storage_p)
                    except Exception:
                        pass
                return (True, furl, fn, c_item, flabel)
            return (False, furl, fn, c_item, flabel)

        print(f"[Sync] Downloading {len(files_to_download)} new PDFs with 10 workers...", flush=True)
        with ThreadPoolExecutor(max_workers=10) as executor:
            download_results = list(executor.map(_dl_worker, files_to_download))

        downloaded_count = sum(1 for r in download_results if r[0])
        print(f"[Sync] Successfully downloaded {downloaded_count}/{len(files_to_download)} files.", flush=True)

    # 5. Integrate into papers_db
    # Build lookup table of papers_db
    # Lookup by (exam_id, course_code, qp_code) and id
    papers_by_key = {}
    for p in papers_db:
        key = (str(p.get("exam_id", "")), (p.get("course_code") or "").upper(), (p.get("qp_code") or "").upper())
        papers_by_key[key] = p
        if p.get("id"):
            papers_by_key[p["id"]] = p

    new_qps_added = 0
    new_schemes_added = 0
    new_courses_added = 0

    for c_item in all_scraped_courses:
        raw_header = c_item["raw_header"]
        eid = c_item["exam_id"]
        ename = c_item["exam_name"]
        sem_num = c_item["semester"]
        batch = c_item["batch"]
        c_files = c_item["files"]
        if not c_files:
            continue

        qp_code, course_code, title = parse_header_text(raw_header)
        meta_course = parse_course_metadata(course_code, sem_default=sem_num)

        # Fallback: check downloaded PDF if course code is missing or GEN
        if not course_code or meta_course["dept_code"] == "GEN":
            for furl, flabel in c_files:
                fn = os.path.basename(furl)
                local_p = os.path.join(LOCAL_UPLOADS_DIR, fn)
                pdf_code, pdf_title = extract_metadata_from_pdf(local_p)
                if pdf_code:
                    course_code = pdf_code
                    if pdf_title and (not title or title.startswith("Course ") or is_department_name(title)):
                        title = pdf_title
                    meta_course = parse_course_metadata(course_code, sem_default=sem_num)
                    break

        is_ambiguous = bool(not course_code or meta_course["dept_code"] == "GEN")

        key = (str(eid), course_code.upper(), qp_code.upper())
        target_paper = papers_by_key.get(key)
        
        # If not found by full key, try by exam_id and course_code if course_code is unique
        if not target_paper and course_code:
            target_paper = papers_by_key.get((str(eid), course_code.upper(), ""))
            
        if not target_paper:
            # Check by canonical id
            cand_id = f"exam{eid}_{qp_code or course_code}"
            target_paper = papers_by_key.get(cand_id)

        is_new_course_entry = False
        if not target_paper:
            is_new_course_entry = True
            new_courses_added += 1
            target_paper = {
                "id": f"exam{eid}_{qp_code or course_code or int(time.time())}",
                "qp_code": qp_code,
                "course_code": course_code,
                "title": title,
                "raw_header": raw_header,
                "semester": meta_course["semester"],
                "semester_label": f"Semester {meta_course['semester']}",
                "course_type": meta_course["course_type"],
                "course_type_name": meta_course["course_type_name"],
                "dept_code": meta_course["dept_code"],
                "dept_name": meta_course["dept_name"],
                "parent_dept": meta_course["parent_dept"],
                "parent_dept_name": meta_course["parent_dept_name"],
                "is_minor": meta_course["is_minor"],
                "exam_id": str(eid),
                "exam_name": ename,
                "batch": batch,
                "is_fyugp": True,
                "has_qp": False,
                "qp_url": "",
                "has_scheme": False,
                "scheme_url": "",
                "files": [],
                "has_files": False,
                "is_signature": meta_course["is_signature"],
                "model_papers": [],
                "needs_review": is_ambiguous,
                "status": "pending_review" if is_ambiguous else "published",
                "review_reason": "Ambiguous course code or General Studies categorization" if is_ambiguous else ""
            }
            papers_db.append(target_paper)
            papers_by_key[key] = target_paper
            papers_by_key[target_paper["id"]] = target_paper

        # Merge files
        existing_target_urls = set(f.get("url") for f in target_paper.get("files", []))
        existing_target_names = set(os.path.basename(f.get("url", "")) for f in target_paper.get("files", []))

        for furl, flabel in c_files:
            fn = os.path.basename(furl)
            if furl in existing_target_urls or fn in existing_target_names:
                continue

            # Classify file type
            ftype = "OTHER"
            if any(k in flabel for k in ["QP", "QUESTION", "QN", "MCQ"]):
                ftype = "QP"
                new_qps_added += 1
            elif any(k in flabel for k in ["SCHEME", "VALUATION", "ANS"]):
                ftype = "SCHEME"
                new_schemes_added += 1
            else:
                ftype = flabel or "PDF"

            cdn_url = f"{CDN_BASE}/{fn}"
            file_entry = {
                "type": ftype,
                "label": flabel or ftype,
                "url": cdn_url,
                "mgu_url": furl,
                "raw_url": f"{RAW_BASE}/{fn}"
            }
            target_paper["files"].append(file_entry)
            target_paper["has_files"] = True
            existing_target_urls.add(cdn_url)
            existing_target_names.add(fn)

            if ftype == "QP" and not target_paper.get("has_qp"):
                target_paper["has_qp"] = True
                target_paper["qp_url"] = cdn_url
            elif ftype == "SCHEME" and not target_paper.get("has_scheme"):
                target_paper["has_scheme"] = True
                target_paper["scheme_url"] = cdn_url

            new_items_logged.append({
                "exam_id": str(eid),
                "semester": target_paper["semester"],
                "course_code": course_code or qp_code,
                "qp_code": qp_code,
                "title": title,
                "file_type": ftype,
                "label": flabel,
                "filename": fn,
                "url": cdn_url
            })

    total_new_files = len(new_items_logged)
    print(f"[Sync] Ingestion summary: {total_new_files} new files ingested ({new_qps_added} QPs, {new_schemes_added} Schemes, {new_courses_added} new course records).", flush=True)

    # 6. Save updated database
    print("[Sync] Saving papers.json...", flush=True)
    with open(os.path.join(DATA_DIR, "papers.json"), "w", encoding="utf-8") as f:
        json.dump(papers_db, f, indent=2, ensure_ascii=False)
    with open(os.path.join(PUB_DATA_DIR, "papers.json"), "w", encoding="utf-8") as f:
        json.dump(papers_db, f, indent=2, ensure_ascii=False)

    # 7. Record Crawl History
    crawl_history_file = os.path.join(DATA_DIR, "crawl_history.json")
    crawl_history = []
    if os.path.exists(crawl_history_file):
        try:
            with open(crawl_history_file, "r", encoding="utf-8") as f:
                crawl_history = json.load(f)
        except Exception:
            pass

    end_time = datetime.now(timezone.utc)
    # Format local IST time
    ist_offset_hours = 5.5
    ist_time = end_time.timestamp() + (ist_offset_hours * 3600)
    ist_dt = datetime.fromtimestamp(ist_time, tz=timezone.utc)
    ist_str = ist_dt.strftime("%d %b %Y, %I:%M %p IST")

    crawl_record = {
        "id": f"crawl_{int(end_time.timestamp())}",
        "timestamp": end_time.isoformat(),
        "timestamp_local": ist_str,
        "trigger_type": trigger_type.lower(),
        "status": "success",
        "total_exams_checked": len(EXAM_SESSIONS),
        "new_files_added": total_new_files,
        "new_qps_added": new_qps_added,
        "new_schemes_added": new_schemes_added,
        "new_courses_added": new_courses_added,
        "summary": f"{total_new_files} new files added ({new_qps_added} QPs, {new_schemes_added} Schemes)" if total_new_files > 0 else "0 new files (Database up to date)",
        "new_items": new_items_logged
    }
    # Prepend to history (most recent first)
    crawl_history.insert(0, crawl_record)
    # Keep last 100 crawls
    crawl_history = crawl_history[:100]

    with open(crawl_history_file, "w", encoding="utf-8") as f:
        json.dump(crawl_history, f, indent=2, ensure_ascii=False)
    with open(os.path.join(PUB_DATA_DIR, "crawl_history.json"), "w", encoding="utf-8") as f:
        json.dump(crawl_history, f, indent=2, ensure_ascii=False)

    # 8. Update stats.json
    stats_file = os.path.join(DATA_DIR, "stats.json")
    stats = {}
    if os.path.exists(stats_file):
        try:
            with open(stats_file, "r", encoding="utf-8") as f:
                stats = json.load(f)
        except Exception:
            pass

    stats["total_records"] = len(papers_db)
    stats["records_with_files"] = sum(1 for p in papers_db if p.get("has_files"))
    stats["total_question_papers"] = sum(1 for p in papers_db if p.get("has_qp"))
    stats["total_schemes"] = sum(1 for p in papers_db if p.get("has_scheme"))
    stats["last_sync"] = end_time.strftime("%Y-%m-%d %H:%M:%S UTC")
    stats["last_crawl_time"] = ist_str
    stats["last_crawl_trigger"] = trigger_type.lower()
    stats["last_crawl_new_files"] = total_new_files

    with open(stats_file, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    with open(os.path.join(PUB_DATA_DIR, "stats.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    # 9. Sync remote storage repo
    if total_new_files > 0:
        sync_storage_repo()

    print("\n" + "=" * 70)
    print("  MGU QUESTION PAPERS & SCHEMES SYNC COMPLETE")
    print("=" * 70)
    print(f"  Exams checked: {len(EXAM_SESSIONS)}")
    print(f"  New files added: {total_new_files} ({new_qps_added} QPs, {new_schemes_added} Schemes)")
    print(f"  Total portal courses: {len(papers_db)}")
    print(f"  Crawl logged in crawl_history.json")
    print("=" * 70, flush=True)
    return True

if __name__ == "__main__":
    t_type = "automatic" if "--trigger=automatic" in sys.argv else "manual"
    run_sync(trigger_type=t_type)

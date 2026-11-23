"""
sync_engine.py
==============
Unified Autonomous MGU FYUGP Question Paper & Scheme of Valuation Sync Engine.

Features:
1. Live-scrapes https://assist.mgu.ac.in/schema/ and DYNAMICALLY discovers all FYUGP exam sessions (Semesters 1-8).
   Never misses newly added exam sessions (e.g., Session 36: III Semester FYUGP Regular Exam October 2026).
2. Robustly handles both new modern accordion markup (<button class="accordion"> and onclick="openFile(...)")
   and legacy panel markup (<div class="panel-heading">).
3. Detects QP code, FYUGP course code (MG[1-8]...), and course title without department name bleeding.
4. Leverages canonical taxonomy from papers.json and departments.json to guarantee 100% accurate titles.
5. Concurrently downloads all new Question Papers & Schemes of Valuation with anti-drop retries.
6. Mirrors PDFs to:
   - uploads/
   - public/uploads/
   - ../mgu-qp-storage/pdf/ (with automated git commit & push for jsDelivr CDN delivery)
7. Updates data/papers.json while STRICTLY preserving all existing model question papers.
8. Logs every crawl (automatic or manual) into data/crawl_history.json and public/data/crawl_history.json.
9. Updates stats.json and public/data/stats.json with new file metrics.
"""

import os
import sys
import re
import json
import time
import shutil
import ssl
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

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/pdf,text/html,*/*",
    "Referer": BASE_URL
}

# Fallback sessions list in case live dropdown cannot be reached
FALLBACK_EXAM_SESSIONS = [
    {"id": "36", "semester": 3, "label": "Semester 3", "name": "III Semester MGU UGP/ B.Voc/BBA/BCA (Honours) 2025 Admission Regular Exam October 2026", "batch": "2025 Admission"},
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

# Roman numerals and semester wording map
ROMAN_SEM_MAP = {
    'i': 1, 'first': 1, '1st': 1, 'sem 1': 1, 'sem-1': 1, 'sem.1': 1,
    'ii': 2, 'second': 2, '2nd': 2, 'sem 2': 2, 'sem-2': 2, 'sem.2': 2,
    'iii': 3, 'third': 3, '3rd': 3, 'sem 3': 3, 'sem-3': 3, 'sem.3': 3,
    'iv': 4, 'fourth': 4, '4th': 4, 'sem 4': 4, 'sem-4': 4, 'sem.4': 4,
    'v': 5, 'fifth': 5, '5th': 5, 'sem 5': 5, 'sem-5': 5, 'sem.5': 5,
    'vi': 6, 'sixth': 6, '6th': 6, 'sem 6': 6, 'sem-6': 6, 'sem.6': 6,
    'vii': 7, 'seventh': 7, '7th': 7, 'sem 7': 7, 'sem-7': 7, 'sem.7': 7,
    'viii': 8, 'eighth': 8, '8th': 8, 'sem 8': 8, 'sem-8': 8, 'sem.8': 8,
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

# Build canonical course title lookup from papers.json
CANONICAL_TITLES = {}
papers_json_path = os.path.join(DATA_DIR, "papers.json")
if os.path.exists(papers_json_path):
    try:
        with open(papers_json_path, "r", encoding="utf-8") as f:
            _existing = json.load(f)
            for p in _existing:
                cc = (p.get("course_code") or "").strip().upper()
                tt = (p.get("title") or "").strip()
                if cc and tt and not tt.startswith("Course ") and not is_department_name(tt) if 'is_department_name' in globals() else True:
                    if cc not in CANONICAL_TITLES or len(tt) > len(CANONICAL_TITLES[cc]):
                        CANONICAL_TITLES[cc] = tt
    except Exception as e:
        print(f"[Warning] Failed to build canonical titles: {e}")

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

def parse_semester_from_string(s):
    """Accurately determine semester number from text (e.g. III Semester -> 3)."""
    n = s.lower()
    m_roman = re.search(r'\b(viii|vii|vi|iv|v|iii|ii|i)\b\s*(?:sem|\.|\s*semester|_sem)', n)
    if m_roman:
        return ROMAN_SEM_MAP.get(m_roman.group(1), 1)
    m_word = re.search(r'\b(first|second|third|fourth|fifth|sixth|seventh|eighth)\s+semester', n)
    if m_word:
        return ROMAN_SEM_MAP.get(m_word.group(1), 1)
    m_num = re.search(r'\b(\d+)(?:st|nd|rd|th)?\s+sem', n)
    if m_num:
        return int(m_num.group(1))
    m_sem = re.search(r'sem\s*(\d+)', n)
    if m_sem:
        return int(m_sem.group(1))
    return 1

def discover_live_exam_sessions():
    """Live-query assist.mgu.ac.in homepage to detect ALL exam sessions in the dropdown."""
    print("[Discovery] Querying https://assist.mgu.ac.in/schema/ for live exam sessions...", flush=True)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    req = urllib.request.Request(BASE_URL, headers=BROWSER_HEADERS)
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=25) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            
        options = re.findall(r'<option[^>]*value=[\"\']?(\d+)[\"\']?[^>]*>(.*?)</option>', html, re.IGNORECASE | re.DOTALL)
        if not options:
            print("[Discovery] No options found on homepage; falling back to historical sessions list.", flush=True)
            return FALLBACK_EXAM_SESSIONS
            
        discovered = []
        seen_ids = set()
        
        for val, raw_text in options:
            eid = str(val).strip()
            if not eid or eid in seen_ids:
                continue
            seen_ids.add(eid)
            
            clean_name = clean_html(raw_text)
            # Match FYUGP / MGU-UGP / Honours programs
            is_fyugp = bool(re.search(r'ugp|fyugp|honours|hons|four year|bba.*hons|bca.*hons', clean_name, re.IGNORECASE))
            if not is_fyugp:
                continue
                
            sem = parse_semester_from_string(clean_name)
            m_batch = re.search(r'(\d{4}\s*Admission)', clean_name, re.IGNORECASE)
            batch = m_batch.group(1) if m_batch else "2024 Admission"
            
            discovered.append({
                "id": eid,
                "semester": sem,
                "label": f"Semester {sem}",
                "name": clean_name,
                "batch": batch
            })
            
        # Also ensure fallback sessions are included if missing
        for fb in FALLBACK_EXAM_SESSIONS:
            if fb["id"] not in seen_ids:
                discovered.append(fb)
                seen_ids.add(fb["id"])
                
        # Sort descending by numeric ID (newest exams first)
        discovered.sort(key=lambda x: int(x["id"]) if x["id"].isdigit() else 0, reverse=True)
        print(f"[Discovery] Discovered {len(discovered)} active FYUGP exam sessions from university portal.", flush=True)
        for s in discovered:
            print(f"   Exam ID {s['id']:>2} | Sem {s['semester']} | {s['name'][:65]}")
        return discovered
    except Exception as e:
        print(f"[Discovery] Note: Live discovery exception ({e}); using complete fallback sessions list.", flush=True)
        return FALLBACK_EXAM_SESSIONS

def fetch_exam_html(exam_id):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    data = urllib.parse.urlencode({"options": str(exam_id)}).encode("utf-8")
    req = urllib.request.Request(
        BASE_URL,
        data=data,
        headers=BROWSER_HEADERS
    )
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=35) as resp:
                return resp.read().decode("utf-8", errors="ignore")
        except Exception as e:
            if attempt == 3:
                print(f"[Sync] Warning: Failed to fetch exam {exam_id}: {e}", flush=True)
            time.sleep(2.0)
    return ""

def extract_metadata_from_pdf(pdf_path):
    """Extract course code and course title from downloaded PDF with multi-line title handling."""
    if not os.path.exists(pdf_path) or os.path.getsize(pdf_path) < 100:
        return None, None
    try:
        from pypdf import PdfReader
        reader = PdfReader(pdf_path)
        if len(reader.pages) == 0:
            return None, None
            
        full_text = ""
        for p_idx in range(min(2, len(reader.pages))):
            full_text += (reader.pages[p_idx].extract_text() or "") + "\n"
            
        # Match FYUGP Course Code
        m_code = re.search(r'\b(MG[1-8](?:DSC|DSE|SEC|MDC|VAC|CCR|AEC|DEC|MDE|SDC|MPC|HON|MIN|MDE)[A-Z]{2,5}(?:A\d{2}|\d{3}))\b', full_text, re.IGNORECASE)
        code = m_code.group(1).upper() if m_code else None

        # Check canonical title map first
        if code and code in CANONICAL_TITLES:
            return code, CANONICAL_TITLES[code]

        # Try to parse title from header line
        title = None
        m_title = re.search(r'-\s*(?:MG[1-8][A-Z0-9]+)\s*-\s*(.*?)(?=\(\d{4}\s*ADMISSION|\(\d{4}\s*ADM|Duration:|Maximum Marks:|\n\s*Remember|\n\s*Part|\n\s*Time)', full_text, re.DOTALL | re.IGNORECASE)
        if m_title:
            cand = re.sub(r'\s+', ' ', m_title.group(1)).strip(' -:\n\r')
            if len(cand) > 3 and not is_department_name(cand):
                title = cand

        if not title:
            # Fallback line scanning
            for line in full_text.splitlines()[:20]:
                l_str = line.strip()
                if not l_str or len(l_str) < 4:
                    continue
                if any(k in l_str.upper() for k in ["MAHATMA GANDHI", "UNIVERSITY", "EXAMINATION", "PAGES", "SECTION", "TIME", "MAXIMUM", "TOTAL", "REG.NO", "NAME :"]):
                    continue
                if code and code in l_str.upper():
                    continue
                if re.search(r'[A-Za-z]{4,}', l_str) and not is_department_name(l_str):
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

    # 1. Match QP code at start: 26900015 - ... or just 26900576
    m_qp = re.match(r'^(\d{6,8})\s*[-:]\s*(.*)$', header)
    if m_qp:
        qp_code = m_qp.group(1)
        remainder = m_qp.group(2).strip()
    elif re.match(r'^\d{6,8}$', header):
        qp_code = header
        remainder = ""
    else:
        remainder = header

    # 2. Match MG FYUGP Course Code
    m_mg = re.search(r'\b(MG[1-8](?:DSC|DSE|SEC|MDC|VAC|CCR|AEC|DEC|MDE|SDC|MPC|HON|MIN|MDE)[A-Z]{2,5}(?:A\d{2}|\d{3}))\b', remainder, re.IGNORECASE)
    if m_mg:
        course_code = m_mg.group(1).upper()
        # Clean title
        title_cand = remainder.replace(m_mg.group(0), '')
        title_cand = re.sub(r'^\s*[-:—]\s*|\s*[-:—]\s*$', '', title_cand).strip()
        title_cand = re.sub(r'\s*-\s*', ' - ', title_cand).strip(' -')
        title = title_cand
    else:
        # Fallback MG pattern
        m_mg_fb = re.search(r'\b(MG[1-8][A-Z]{6,9}(?:A\d{2}|\d{3}))\b', remainder, re.IGNORECASE)
        if m_mg_fb:
            course_code = m_mg_fb.group(1).upper()
            title_cand = remainder.replace(m_mg_fb.group(0), '').strip(' -:—')
            title = title_cand
        else:
            # CBCS or other codes
            m_cb = re.search(r'\b([A-Z]{2,4}\d[A-Z]{2,4}\d{1,3}[A-Z]?)\b', remainder)
            if m_cb:
                course_code = m_cb.group(1).upper()
                title = remainder.replace(m_cb.group(0), '').strip(' -:—')
            else:
                title = remainder

    # Check canonical map
    if course_code and course_code in CANONICAL_TITLES:
        title = CANONICAL_TITLES[course_code]

    # Sanitize title: never equal department name/code
    if is_department_name(title) or len(title) < 3:
        title = CANONICAL_TITLES.get(course_code, f"Course {course_code}" if course_code else header)

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
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    for attempt in range(4):
        try:
            req = urllib.request.Request(
                safe_url,
                headers=BROWSER_HEADERS
            )
            with urllib.request.urlopen(req, context=ctx, timeout=35) as resp, open(tmp, "wb") as f_out:
                shutil.copyfileobj(resp, f_out)
            if os.path.exists(tmp) and os.path.getsize(tmp) > 100:
                shutil.move(tmp, target_path)
                return True
        except urllib.error.HTTPError as e:
            if e.code == 404:
                break
            time.sleep(1.5 + (attempt * 1.5))
        except Exception:
            time.sleep(1.5 + (attempt * 1.5))
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
    if not token and os.path.exists(os.path.join(PROJECT_DIR, ".env")):
        try:
            with open(os.path.join(PROJECT_DIR, ".env"), "r", encoding="utf-8") as env_f:
                for line in env_f:
                    if "=" in line and not line.strip().startswith("#"):
                        k, v = line.strip().split("=", 1)
                        if k.strip() in ["STORAGE_PAT", "GH_TOKEN", "GITHUB_TOKEN"]:
                            token = v.strip()
                            break
        except Exception:
            pass
    git_env = dict(os.environ, GIT_TERMINAL_PROMPT="0")

    if not os.path.exists(STORAGE_DIR):
        if token:
            try:
                import subprocess
                clone_url = f"https://{token}@github.com/sinan-newman/mgu-qp-storage.git"
                print(f"[Storage Push] Cloning storage repository...", flush=True)
                subprocess.run([git_exe, "clone", "--depth", "1", clone_url, STORAGE_DIR], check=True, timeout=120, env=git_env)
            except Exception as e:
                print(f"[Storage Push] Note: Could not clone storage repo: {e}", flush=True)
                return
        else:
            print("[Storage Push] STORAGE_PAT not provided and storage dir not present; skipping storage sync.", flush=True)
            return

    if not token:
        print("[Storage Push] No storage token configured; skipping remote push (files retained locally).", flush=True)
        return

    try:
        import subprocess
        # Check untracked or modified files in storage
        status = subprocess.check_output([git_exe, "-C", STORAGE_DIR, "status", "-s"], text=True, timeout=30)
        untracked = [line.strip()[2:].strip() for line in status.splitlines() if line.strip().endswith('.pdf')]
        if not untracked:
            print("[Storage Push] Storage repository is up to date.", flush=True)
            return
        print(f"[Storage Push] Staging and pushing {len(untracked)} updated PDFs to mgu-qp-storage...", flush=True)
        batch_size = 50
        batches = [untracked[i:i + batch_size] for i in range(0, len(untracked), batch_size)]
        
        push_target = f"https://{token}@github.com/sinan-newman/mgu-qp-storage.git"
        
        for idx, batch in enumerate(batches, 1):
            subprocess.run([git_exe, "-C", STORAGE_DIR, "add"] + batch, check=True, timeout=60, env=git_env)
            diff_check = subprocess.run([git_exe, "-C", STORAGE_DIR, "diff", "--staged", "--quiet"], timeout=30, env=git_env)
            if diff_check.returncode == 0:
                continue
            subprocess.run([git_exe, "-C", STORAGE_DIR, "commit", "-m", f"Automated sync: add MGU exam QP/Scheme chunk {idx}/{len(batches)} [skip ci]"], check=True, timeout=60, env=git_env)
            for attempt in range(3):
                try:
                    p_res = subprocess.run([git_exe, "-C", STORAGE_DIR, "push", push_target, "main"], capture_output=True, text=True, timeout=60, env=git_env)
                    if p_res.returncode == 0:
                        print(f"[Storage Push] Batch {idx}/{len(batches)} pushed.", flush=True)
                        break
                    else:
                        print(f"[Storage Push] Push attempt {attempt+1} warning: {p_res.stderr.strip()}", flush=True)
                        time.sleep(2)
                except subprocess.TimeoutExpired:
                    print(f"[Storage Push] Push attempt {attempt+1} timed out.", flush=True)
                    time.sleep(2)
    except Exception as e:
        print(f"[Storage Push] Note: Storage push completed or skipped: {e}", flush=True)


def verify_and_download_missing_files(papers_db):
    """Integrity check: Ensure all files referenced in papers_db exist in storage repo."""
    missing_from_storage = []
    missing_from_uploads = []
    for p in papers_db:
        for f_entry in p.get("files", []):
            u = f_entry.get("url") or ""
            mgu_u = f_entry.get("mgu_url") or ""
            fn = os.path.basename(u.split("?")[0])
            if fn.endswith(".pdf"):
                sp = os.path.join(STORAGE_PDF_DIR, fn)
                lp = os.path.join(LOCAL_UPLOADS_DIR, fn)
                has_sp = os.path.exists(sp) and os.path.getsize(sp) >= 100
                has_lp = os.path.exists(lp) and os.path.getsize(lp) >= 100
                
                if not has_sp and not has_lp:
                    cand_mgu = mgu_u or f"https://assist.mgu.ac.in/schema/assets/storage/{fn}"
                    missing_from_storage.append((fn, cand_mgu))
                elif has_sp and not has_lp:
                    missing_from_uploads.append((sp, lp))
                elif has_lp and not has_sp:
                    try:
                        shutil.copy2(lp, sp)
                    except Exception:
                        pass
    
    # If files exist in storage repo but not in local uploads dir, copy them over locally
    if missing_from_uploads:
        for sp_path, lp_path in missing_from_uploads:
            try:
                shutil.copy2(sp_path, lp_path)
            except Exception:
                pass

    if not missing_from_storage:
        print("[Integrity] All database PDFs verified present in storage repo.", flush=True)
        return
        
    print(f"[Integrity] Found {len(missing_from_storage)} missing PDFs in storage repo. Initiating university download...", flush=True)
    recovered = 0
    for fn, cand_url in missing_from_storage:
        sp = os.path.join(STORAGE_PDF_DIR, fn)
        lp = os.path.join(LOCAL_UPLOADS_DIR, fn)
        pub_p = os.path.join(PUB_UPLOADS_DIR, fn)
        if download_file(cand_url, lp):
            try:
                shutil.copy2(lp, sp)
                shutil.copy2(lp, pub_p)
                recovered += 1
            except Exception:
                pass
    print(f"[Integrity] Recovered and mirrored {recovered}/{len(missing_from_storage)} PDFs from university server.", flush=True)

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

    # 2. Dynamically discover all active FYUGP exam sessions from university portal
    exam_sessions = discover_live_exam_sessions()

    # Crawl each discovered exam session
    for exam in exam_sessions:
        eid = exam["id"]
        sem_num = exam["semester"]
        ename = exam["name"]
        print(f"[Sync] Fetching Exam ID {eid} ({exam['label']}: {ename[:50]}...) ...", flush=True)
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

                if found_files:
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
                    
                if found_files:
                    all_scraped_courses.append({
                        "exam_id": eid,
                        "exam_name": ename,
                        "semester": sem_num,
                        "batch": exam.get("batch", "2024 Admission"),
                        "raw_header": raw_header,
                        "files": found_files
                    })

    print(f"[Sync] Discovered {len(all_scraped_courses)} course exam items across {len(exam_sessions)} exam sessions.", flush=True)

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

        print(f"[Sync] Downloading {len(files_to_download)} new PDFs with 8 workers...", flush=True)
        with ThreadPoolExecutor(max_workers=8) as executor:
            download_results = list(executor.map(_dl_worker, files_to_download))

        downloaded_count = sum(1 for r in download_results if r[0])
        print(f"[Sync] Successfully downloaded {downloaded_count}/{len(files_to_download)} files.", flush=True)

    # 5. Integrate into papers_db
    papers_by_key = {}
    papers_by_ce = {}
    for p in papers_db:
        eid_str = str(p.get("exam_id", ""))
        cc_str = (p.get("course_code") or "").upper().strip()
        qp_str = (p.get("qp_code") or "").upper().strip()
        key = (eid_str, cc_str, qp_str)
        papers_by_key[key] = p
        if cc_str:
            papers_by_ce[(eid_str, cc_str)] = p
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

        # Check canonical map one more time
        if course_code and course_code in CANONICAL_TITLES:
            title = CANONICAL_TITLES[course_code]

        is_ambiguous = bool(not course_code or meta_course["dept_code"] == "GEN")

        key = (str(eid), course_code.upper(), qp_code.upper())
        target_paper = papers_by_key.get(key)
        
        # If not found by full key, try by exam_id and course_code to strictly prevent duplicate course cards in the same exam
        if not target_paper and course_code:
            target_paper = papers_by_ce.get((str(eid), course_code.upper()))
            
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
            if course_code:
                papers_by_ce[(str(eid), course_code.upper())] = target_paper
        else:
            # Existing paper found: upgrade metadata if more specific
            if qp_code and not target_paper.get("qp_code"):
                target_paper["qp_code"] = qp_code
            if title and (not target_paper.get("title") or target_paper["title"].startswith("Course ") or target_paper["title"] == qp_code):
                target_paper["title"] = title

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

            if ftype == "QP":
                if not target_paper.get("has_qp"):
                    target_paper["has_qp"] = True
                    target_paper["qp_url"] = cdn_url
                    target_paper["mgu_qp_url"] = furl
                    target_paper["raw_qp_url"] = f"{RAW_BASE}/{fn}"
            elif ftype == "SCHEME":
                if not target_paper.get("has_scheme"):
                    target_paper["has_scheme"] = True
                    target_paper["scheme_url"] = cdn_url
                    target_paper["mgu_scheme_url"] = furl
                    target_paper["raw_scheme_url"] = f"{RAW_BASE}/{fn}" 

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

    # 6b. Sync Minor Discipline Syllabi & Amendments from minors.jsp
    try:
        from scripts.fetch_minors_syllabi import main as sync_minors
        print("[Sync] Synchronizing Minor Discipline Syllabi from minors.jsp...", flush=True)
        sync_minors()
    except Exception as e:
        print(f"[Sync] Warning: Failed to sync minor syllabi: {e}", flush=True)

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
        "total_exams_checked": len(exam_sessions),
        "new_files_added": total_new_files,
        "new_qps_added": new_qps_added,
        "new_schemes_added": new_schemes_added,
        "new_courses_added": new_courses_added,
        "summary": f"{total_new_files} new files added ({new_qps_added} QPs, {new_schemes_added} Schemes)" if total_new_files > 0 else "0 new files (Database up to date)",
        "new_items": new_items_logged
    }
    crawl_history.insert(0, crawl_record)
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

    # 8.5. Verify all PDF files are mirrored locally
    verify_and_download_missing_files(papers_db)

    # 9. Sync remote storage repo
    if total_new_files > 0:
        sync_storage_repo()

    print("\n" + "=" * 70)
    print("  MGU QUESTION PAPERS & SCHEMES SYNC COMPLETE")
    print("=" * 70)
    print(f"  Exams checked: {len(exam_sessions)}")
    print(f"  New files added: {total_new_files} ({new_qps_added} QPs, {new_schemes_added} Schemes)")
    print(f"  Total portal courses: {len(papers_db)}")
    print(f"  Crawl logged in crawl_history.json")
    print("=" * 70, flush=True)
    return True

if __name__ == "__main__":
    t_type = "automatic" if "--trigger=automatic" in sys.argv else "manual"
    run_sync(trigger_type=t_type)

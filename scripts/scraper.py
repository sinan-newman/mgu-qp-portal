"""
MGU Question Paper & Scheme Scraper / Sync Engine
Fetches question papers, schemes, and course metadata from https://assist.mgu.ac.in/schema/
"""

import urllib.request
import urllib.parse
import re
import json
import os
import sys
import time
from datetime import datetime

# Root paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_DIR, "data")
CACHE_DIR = os.path.join(PROJECT_DIR, ".cache")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

# Import helper mappings
sys.path.append(SCRIPT_DIR)
try:
    from generate_core_data import PARENT_DEPT_LOOKUP, DEPT_NAMES, TYPE_NAMES
except ImportError:
    PARENT_DEPT_LOOKUP = {}
    DEPT_NAMES = {}
    TYPE_NAMES = {}

BASE_URL = "https://assist.mgu.ac.in/schema/"

EXAM_SESSIONS = [
    {"id": "35", "semester": 5, "label": "Semester 5", "name": "V Semester MGU UGP (Honours) - 2024 Admission regular Examination October 2026", "batch": "2024 Admission"},
    {"id": "34", "semester": 1, "label": "Semester 1", "name": "First Semester MGU-UGP (HONOURS) Special Examination July 2026", "batch": "2024 Admission"},
    {"id": "31", "semester": 3, "label": "Semester 3", "name": "III Semester MGU-UGP-(Hons) 2024 Admission Regular(Special Examination) Examination July 2026", "batch": "2024 Admission"},
    {"id": "27", "semester": 2, "label": "Semester 2", "name": "Second semester BA/BSc/BVocFYUGP April 2026", "batch": "2024 Admission"},
    {"id": "21", "semester": 4, "label": "Semester 4", "name": "MGU-UGP (HONOURS) 2024 Admission Regular Exam Sem 4, March 2026", "batch": "2024 Admission"},
    {"id": "7",  "semester": 1, "label": "Semester 1", "name": "First Semester MGU-UGP/MGU-BBA/MGU-BCA Honours Examinations November 2025", "batch": "2024 Admission"},
    {"id": "6",  "semester": 3, "label": "Semester 3", "name": "Third Semester MGU-UGP(Hons.) Regular Exam Oct 2025", "batch": "2024 Admission"},
    {"id": "4",  "semester": 2, "label": "Semester 2", "name": "II Semester MGU UGP25 - March - 2025", "batch": "2024 Admission"},
    {"id": "1",  "semester": 1, "label": "Semester 1", "name": "MGU-UGP (HONOURS) Regular Exam Sem 1, Nov 2024", "batch": "2024 Admission"},
]

CBCS_PREFIX_MAP = {
    "EN": "ENG", "ML": "MAL", "CO": "COM", "CM": "COM", "BC": "COM",
    "MM": "MAT", "MT": "MAT", "PH": "PHY", "CH": "CHE", "BO": "BOT",
    "ZY": "ZGY", "ZL": "ZGY", "CS": "CSC", "CA": "CSC", "EC": "ECO",
    "HY": "HIS", "PO": "POL", "PS": "POL", "PY": "PSY", "ST": "STA",
    "HN": "HIN", "SW": "BSW", "TT": "TTM", "BA": "BBA", "BB": "BBA",
    "BC": "BCH", "BT": "BTG", "BI": "BIF", "GE": "GEO", "SO": "SOC",
    "PL": "PHI", "SK": "SAN", "AR": "ARB"
}

def clean_html(text):
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&#039;', "'").replace('&quot;', '"')
    return re.sub(r'\s+', ' ', text).strip()

def fetch_exam_html(exam_id):
    data = urllib.parse.urlencode({"options": str(exam_id)}).encode("utf-8")
    req = urllib.request.Request(
        BASE_URL,
        data=data,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MGU-Portal-Sync/1.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=35) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"Error fetching exam ID {exam_id}: {e}", file=sys.stderr)
        return ""

def parse_header(header):
    qp_code = ""
    course_code = ""
    title = header

    # QP code prefix
    m_qp = re.match(r'^(\d{6,8})\s*[-:]\s*(.*)$', header)
    if m_qp:
        qp_code = m_qp.group(1)
        remainder = m_qp.group(2).strip()
    else:
        remainder = header

    # MG Code pattern
    m_mg = re.search(r'\b(MG[1-8][A-Z]{3}[A-Z]{3}[A-Z0-9]{3,4})\b', remainder, re.IGNORECASE)
    if m_mg:
        course_code = m_mg.group(1).upper()
        title = remainder.replace(m_mg.group(1), '')
        title = re.sub(r'^\s*[-:]\s*|\s*[-:]\s*$', '', title).strip()
        title = re.sub(r'\s*-\s*', ' - ', title).strip(' -')
    else:
        m_cbcs = re.search(r'\b([A-Z]{2,4}\d[A-Z]{2,4}\d{1,3}[A-Z]?)\b', remainder)
        if m_cbcs:
            course_code = m_cbcs.group(1).upper()
            title = remainder.replace(m_cbcs.group(1), '').strip(' -:')
        else:
            title = remainder

    return qp_code, course_code, title

def parse_course_metadata(code, exam_meta):
    if not code:
        return {
            "semester": exam_meta["semester"],
            "course_type": "CBCS" if "CBCS" in exam_meta["name"] else "GEN",
            "course_type_name": "CBCS Course" if "CBCS" in exam_meta["name"] else "General Course",
            "dept_code": "GEN",
            "dept_name": "General Studies",
            "parent_dept": "GEN",
            "parent_dept_name": "General Studies",
            "is_minor": False,
            "course_number": ""
        }

    # Standard MG FYUGP
    m_mg = re.match(r'^MG([1-8])([A-Z]{3})([A-Z]{3})([A-Z0-9]+)$', code, re.IGNORECASE)
    if m_mg:
        sem = int(m_mg.group(1))
        ctype = m_mg.group(2).upper()
        dept = m_mg.group(3).upper()
        cnum = m_mg.group(4).upper()
        parent_dept = PARENT_DEPT_LOOKUP.get(dept, dept)
        return {
            "semester": sem,
            "course_type": ctype,
            "course_type_name": TYPE_NAMES.get(ctype, ctype),
            "dept_code": dept,
            "dept_name": DEPT_NAMES.get(dept, dept),
            "parent_dept": parent_dept,
            "parent_dept_name": DEPT_NAMES.get(parent_dept, parent_dept),
            "is_minor": dept != parent_dept,
            "course_number": cnum
        }

    # CBCS code
    m_cb = re.match(r'^([A-Z]{2,3})(\d)([A-Z]{2,4})(\d+.*)$', code, re.IGNORECASE)
    if m_cb:
        prefix = m_cb.group(1).upper()
        sem = int(m_cb.group(2))
        ctype = m_cb.group(3).upper()
        cnum = m_cb.group(4).upper()
        parent_dept = CBCS_PREFIX_MAP.get(prefix, prefix)
        return {
            "semester": sem,
            "course_type": "CBCS",
            "course_type_name": f"CBCS ({ctype})",
            "dept_code": prefix,
            "dept_name": DEPT_NAMES.get(parent_dept, parent_dept),
            "parent_dept": parent_dept,
            "parent_dept_name": DEPT_NAMES.get(parent_dept, parent_dept),
            "is_minor": False,
            "course_number": cnum
        }

    return {
        "semester": exam_meta["semester"],
        "course_type": "CBCS" if "CBCS" in exam_meta["name"] else "GEN",
        "course_type_name": "CBCS Course" if "CBCS" in exam_meta["name"] else "General Course",
        "dept_code": "GEN",
        "dept_name": "General Studies",
        "parent_dept": "GEN",
        "parent_dept_name": "General Studies",
        "is_minor": False,
        "course_number": ""
    }

def run_sync(use_cache=True):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting sync with MGU portal...")
    
    file_pattern = re.compile(
        r"onclick=[\"']openFile\((?:&#039;|['\"])(.*?)(?:&#039;|['\"])\)[\"'][^>]*>(.*?)</div>",
        re.IGNORECASE | re.DOTALL
    )
    
    all_papers = []
    
    for meta in EXAM_SESSIONS:
        cache_file = os.path.join(CACHE_DIR, f"exam_{meta['id']}.html")
        html = ""
        
        # Check cache or scratch root
        scratch_cache = os.path.join(r"C:\Users\Navirex\.gemini\antigravity\scratch", f"exam_{meta['id']}.html")
        if use_cache and os.path.exists(scratch_cache):
            with open(scratch_cache, "r", encoding="utf-8") as f:
                html = f.read()
        elif use_cache and os.path.exists(cache_file):
            with open(cache_file, "r", encoding="utf-8") as f:
                html = f.read()
        else:
            print(f"Fetching {meta['name']} (Option {meta['id']})...")
            html = fetch_exam_html(meta["id"])
            if html:
                with open(cache_file, "w", encoding="utf-8") as f:
                    f.write(html)
            time.sleep(0.5)
            
        if not html:
            continue
            
        parts = html.split('<button class="accordion">')
        for idx, part in enumerate(parts[1:]):
            btn_html, _, rest = part.partition('</button>')
            raw_header = clean_html(btn_html)
            qp_code, course_code, title = parse_header(raw_header)
            
            panel_html = rest.split('<button class="accordion">')[0]
            
            files = []
            has_qp = False
            has_scheme = False
            qp_url = ""
            scheme_url = ""
            
            for m in file_pattern.finditer(panel_html):
                furl = m.group(1).strip()
                ftype_raw = clean_html(m.group(2)).upper()
                if not furl.startswith("http"):
                    furl = BASE_URL + furl.lstrip("/")
                    
                ftype = "OTHER"
                if "QP" in ftype_raw or "QUESTION" in ftype_raw:
                    ftype = "QP"
                    has_qp = True
                    if not qp_url:
                        qp_url = furl
                elif "SCHEME" in ftype_raw:
                    ftype = "SCHEME"
                    has_scheme = True
                    if not scheme_url:
                        scheme_url = furl
                elif "MARKSHEET" in ftype_raw or "MARK" in ftype_raw:
                    ftype = "MARKSHEET"
                else:
                    ftype = ftype_raw or "PDF"
                    
                files.append({"type": ftype, "label": ftype_raw or ftype, "url": furl})
                
            if files and not qp_url and not scheme_url:
                qp_url = files[0]["url"]
                has_qp = True

            meta_course = parse_course_metadata(course_code, meta)
            
            item = {
                "id": f"exam{meta['id']}_{qp_code or course_code or idx}",
                "qp_code": qp_code,
                "course_code": course_code,
                "title": title or raw_header or f"Course {course_code}",
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
                "exam_id": meta["id"],
                "exam_name": meta["name"],
                "batch": meta["batch"],
                "has_qp": has_qp,
                "qp_url": qp_url,
                "has_scheme": has_scheme,
                "scheme_url": scheme_url,
                "files": files,
                "has_files": len(files) > 0
            }
            all_papers.append(item)
            
    # Save outputs
    papers_path = os.path.join(DATA_DIR, "papers.json")
    with open(papers_path, "w", encoding="utf-8") as f:
        json.dump(all_papers, f, indent=2)
        
    stats = {
        "total_records": len(all_papers),
        "records_with_files": sum(1 for p in all_papers if p["has_files"]),
        "total_question_papers": sum(1 for p in all_papers if p["has_qp"]),
        "total_schemes": sum(1 for p in all_papers if p["has_scheme"]),
        "total_mg_courses": sum(1 for p in all_papers if p["course_code"].startswith("MG")),
        "departments_count": len(set(p["parent_dept"] for p in all_papers if p["parent_dept"] != "GEN")),
        "last_sync": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "source": BASE_URL
    }
    
    stats_path = os.path.join(DATA_DIR, "stats.json")
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
        
    print(f"Sync complete! Saved {len(all_papers)} papers and stats.")
    return stats

if __name__ == "__main__":
    force_fetch = "--force" in sys.argv
    run_sync(use_cache=not force_fetch)

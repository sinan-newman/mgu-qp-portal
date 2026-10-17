import glob
import re
import json
import os

from generate_core_data import PARENT_DEPT_LOOKUP, DEPT_NAMES, TYPE_NAMES

# Paths
PROJECT_DIR = r"C:\Users\Navirex\.gemini\antigravity\scratch\mgu-qp-portal"
DATA_DIR = os.path.join(PROJECT_DIR, "data")
PUBLIC_DATA_DIR = os.path.join(PROJECT_DIR, "public", "data")
SCRATCH_DIR = r"C:\Users\Navirex\.gemini\antigravity\scratch"

# Load model course list for quick lookup
MODEL_COURSES_PATH = os.path.join(DATA_DIR, "model_courses.json")
MODEL_COURSES = {}
TITLE_TO_COURSE = {}
if os.path.exists(MODEL_COURSES_PATH):
    with open(MODEL_COURSES_PATH, "r", encoding="utf-8") as f:
        for c in json.load(f):
            MODEL_COURSES[c["course_code"]] = c
            t_clean = c.get("title", "").strip().lower()
            if t_clean:
                TITLE_TO_COURSE[t_clean] = c

# ONLY FYUGP (MGU-UGP Honours & FYUGP 2024 Admission) Exams
# CBCS exams (options 2, 3, 5) have been completely removed
EXAM_METADATA = {
    "exam_1.html": {"id": "1", "semester": 1, "sem_label": "Semester 1", "exam_name": "MGU-UGP (HONOURS) Regular Exam Sem 1, Nov 2024", "batch": "2024 Admission"},
    "exam_4.html": {"id": "4", "semester": 2, "sem_label": "Semester 2", "exam_name": "II Semester MGU UGP25 - March - 2025", "batch": "2024 Admission"},
    "exam_6.html": {"id": "6", "semester": 3, "sem_label": "Semester 3", "exam_name": "Third Semester MGU-UGP(Hons.) Regular Exam Oct 2025", "batch": "2024 Admission"},
    "exam_7.html": {"id": "7", "semester": 1, "sem_label": "Semester 1", "exam_name": "First Semester MGU-UGP/MGU-BBA/MGU-BCA Honours Examinations November 2025", "batch": "2024 Admission"},
    "exam_21.html": {"id": "21", "semester": 4, "sem_label": "Semester 4", "exam_name": "MGU-UGP (HONOURS) 2024 Admission Regular Exam Sem 4, March 2026", "batch": "2024 Admission"},
    "exam_27.html": {"id": "27", "semester": 2, "sem_label": "Semester 2", "exam_name": "Second semester BA/BSc/BVocFYUGP April 2026", "batch": "2024 Admission"},
    "exam_31.html": {"id": "31", "semester": 3, "sem_label": "Semester 3", "exam_name": "III Semester MGU-UGP-(Hons) 2024 Admission Regular(Special Examination) Examination July 2026", "batch": "2024 Admission"},
    "exam_33.html": {"id": "33", "semester": 3, "sem_label": "Semester 3", "exam_name": "III SEM.FYUGP", "batch": "2024 Admission"},
    "exam_34.html": {"id": "34", "semester": 1, "sem_label": "Semester 1", "exam_name": "First Semester MGU-UGP (HONOURS) Special Examination July 2026", "batch": "2024 Admission"},
    "exam_35.html": {"id": "35", "semester": 5, "sem_label": "Semester 5", "exam_name": "V Semester MGU UGP (Honours) - 2024 Admission regular Examination October 2026", "batch": "2024 Admission"},
}

def clean_html(text):
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&#039;', "'").replace('&quot;', '"')
    return re.sub(r'\s+', ' ', text).strip()

def parse_header_rich(header):
    qp_code = ""
    course_code = ""
    title = header

    # QP code prefix (e.g. 24900123 - ... or 24900123: ...)
    m_qp = re.match(r'^(\d{6,8})\s*[-:]\s*(.*)$', header)
    if m_qp:
        qp_code = m_qp.group(1)
        remainder = m_qp.group(2).strip()
    else:
        remainder = header

    # MG code: MG(1-8)(3 letters)(3 letters)(3-4 alphanumeric)
    m_mg = re.search(r'\b(MG[1-8][A-Z]{3}[A-Z]{3}[A-Z0-9]{2,4})\b', remainder, re.IGNORECASE)
    if m_mg:
        course_code = m_mg.group(1).upper()
        # Clean title
        title = remainder.replace(m_mg.group(1), '')
        title = re.sub(r'^\s*[-:]\s*|\s*[-:]\s*$', '', title).strip()
        title = re.sub(r'\s*-\s*', ' - ', title).strip(' -')
    else:
        # Check if remainder is just another QP code or empty
        m_only_digits = re.match(r'^\d{6,8}$', remainder)
        if m_only_digits and not qp_code:
            qp_code = m_only_digits.group(0)
            title = ""
        else:
            title = remainder

    return qp_code, course_code, title

def parse_course_code_enhanced(code):
    if not code:
        return None
    # Standard MG pattern e.g. MG3DSEMAT202
    m = re.match(r'^MG([1-8])([A-Z]{3})([A-Z]{3})([A-Z0-9]+)$', code, re.IGNORECASE)
    if m:
        sem = int(m.group(1))
        ctype = m.group(2).upper()
        dept = m.group(3).upper()
        cnum = m.group(4).upper()
        
        parent_dept = PARENT_DEPT_LOOKUP.get(dept, dept)
        is_minor = dept != parent_dept
        
        return {
            "semester": sem,
            "course_type": ctype,
            "course_type_name": TYPE_NAMES.get(ctype, ctype),
            "dept_code": dept,
            "dept_name": DEPT_NAMES.get(dept, dept),
            "parent_dept": parent_dept,
            "parent_dept_name": DEPT_NAMES.get(parent_dept, parent_dept),
            "is_minor": is_minor,
            "course_number": cnum
        }
        
    return None

def build_database_v3():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(PUBLIC_DATA_DIR, exist_ok=True)
    
    file_pattern = re.compile(
        r"onclick=[\"']openFile\((?:&#039;|['\"])(.*?)(?:&#039;|['\"])\)[\"'][^>]*>(.*?)</div>",
        re.IGNORECASE | re.DOTALL
    )
    
    all_papers = []
    
    for filename, meta in EXAM_METADATA.items():
        fpath = os.path.join(SCRATCH_DIR, filename)
        if not os.path.exists(fpath):
            continue
            
        with open(fpath, "r", encoding="utf-8") as f:
            html = f.read()
            
        parts = html.split('<button class="accordion">')
        for idx, part in enumerate(parts[1:]):
            btn_html, _, rest = part.partition('</button>')
            raw_header = clean_html(btn_html)
            if not raw_header:
                continue

            qp_code, course_code, title = parse_header_rich(raw_header)
            
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
                    furl = "https://assist.mgu.ac.in/schema/" + furl.lstrip("/")
                    
                ftype = "OTHER"
                if any(k in ftype_raw for k in ["QP", "QUESTION", "QN", "MCQ"]):
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
                
            if files and not qp_url:
                # If MGU only provided a single combined SCHEME/QP PDF, allow QP preview from it
                qp_url = files[0]["url"]
                has_qp = True

            # If no files and no course code, skip pure blank header artifacts
            if not files and not course_code and len(raw_header) < 15:
                continue

            # Try to enrich from model courses
            if course_code and course_code in MODEL_COURSES:
                model_info = MODEL_COURSES[course_code]
                if not title:
                    title = model_info.get("title", "")
            elif title and title.strip().lower() in TITLE_TO_COURSE:
                model_info = TITLE_TO_COURSE[title.strip().lower()]
                if not course_code:
                    course_code = model_info.get("course_code", "")

            parsed = parse_course_code_enhanced(course_code)
            
            sem = parsed["semester"] if parsed else meta["semester"]
            sem_label = f"Semester {sem}"
            
            ctype = parsed["course_type"] if parsed else "FYUGP"
            ctype_name = parsed["course_type_name"] if parsed else "FYUGP Course"
            
            dept_code = parsed["dept_code"] if parsed else "GEN"
            dept_name = parsed["dept_name"] if parsed else ("General Studies" if dept_code == "GEN" else DEPT_NAMES.get(dept_code, dept_code))
            parent_dept = parsed["parent_dept"] if parsed else dept_code
            parent_dept_name = parsed["parent_dept_name"] if parsed else ("General Studies" if parent_dept == "GEN" else DEPT_NAMES.get(parent_dept, parent_dept))
            is_minor = parsed["is_minor"] if parsed else False
            
            unique_id = f"exam{meta['id']}_{qp_code or course_code or idx}"
            
            # Format clean display title
            display_title = title or (f"{ctype} Course - {course_code}" if course_code else raw_header)
            
            item = {
                "id": unique_id,
                "qp_code": qp_code,
                "course_code": course_code,
                "title": display_title,
                "raw_header": raw_header,
                "semester": sem,
                "semester_label": sem_label,
                "course_type": ctype,
                "course_type_name": ctype_name,
                "dept_code": dept_code,
                "dept_name": dept_name,
                "parent_dept": parent_dept,
                "parent_dept_name": parent_dept_name,
                "is_minor": is_minor,
                "exam_id": meta["id"],
                "exam_name": meta["exam_name"],
                "batch": "2024 Admission",
                "is_fyugp": True,
                "has_qp": has_qp,
                "qp_url": qp_url,
                "has_scheme": has_scheme,
                "scheme_url": scheme_url,
                "files": files,
                "has_files": len(files) > 0
            }
            all_papers.append(item)
            
    # Calculate stats for FYUGP only
    total_papers = len(all_papers)
    with_files = [p for p in all_papers if p["has_files"]]
    qps = [p for p in all_papers if p["has_qp"]]
    schemes = [p for p in all_papers if p["has_scheme"]]
    mg_courses = [p for p in all_papers if p["course_code"].startswith("MG")]
    
    unique_depts = sorted(list(set(p["parent_dept"] for p in all_papers if p["parent_dept"] != "GEN")))
    
    stats = {
        "total_records": total_papers,
        "records_with_files": len(with_files),
        "total_question_papers": len(qps),
        "total_schemes": len(schemes),
        "total_mg_fyugp_courses": len(mg_courses),
        "departments_count": len(unique_depts),
        "batch_scope": "FYUGP (MGU-UGP Honours) Only",
        "last_sync": "2026-10-17 10:15 UTC",
        "source_portal": "https://assist.mgu.ac.in/schema/"
    }
    
    # Write to data/ and public/data/
    for folder in [DATA_DIR, PUBLIC_DATA_DIR]:
        with open(os.path.join(folder, "papers.json"), "w", encoding="utf-8") as f:
            json.dump(all_papers, f, indent=2)
            
        with open(os.path.join(folder, "stats.json"), "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2)
            
    print(f"Rebuilt FYUGP database successfully!")
    print(f"Total FYUGP records: {total_papers}")
    print(f"Records with PDF files: {len(with_files)}")
    print(f"Question Papers: {len(qps)}")
    print(f"Evaluation Schemes: {len(schemes)}")
    print(f"MG FYUGP Courses: {len(mg_courses)}")
    print(f"Departments identified: {len(unique_depts)}")

if __name__ == "__main__":
    build_database_v3()

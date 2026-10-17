import glob
import re
import json
import os

from generate_core_data import PARENT_DEPT_LOOKUP, DEPT_NAMES, TYPE_NAMES, parse_course_code

# Load model course list for quick lookup
MODEL_COURSES_PATH = r"C:\Users\Navirex\.gemini\antigravity\scratch\mgu-qp-portal\data\model_courses.json"
MODEL_COURSES = {}
if os.path.exists(MODEL_COURSES_PATH):
    with open(MODEL_COURSES_PATH, "r", encoding="utf-8") as f:
        for c in json.load(f):
            MODEL_COURSES[c["course_code"]] = c

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
    "exam_5.html": {"id": "5", "semester": 4, "sem_label": "Semester 4 (CBCS)", "exam_name": "IV_Sem CBCS EXAMINATION MARCH 2025", "batch": "CBCS"},
    "exam_3.html": {"id": "3", "semester": 5, "sem_label": "Semester 5 (CBCS)", "exam_name": "FIFTH SEMESTER CBCS SUPPLEMENTARY EXAMINATION FEBRUARY 2025", "batch": "CBCS"},
    "exam_2.html": {"id": "2", "semester": 6, "sem_label": "Semester 6 (CBCS)", "exam_name": "SIXTH SEMESTER CBCS EXAMINATION MARCH 2025", "batch": "CBCS"},
}

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

def parse_header_rich(header):
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

    # MG code: MG(1-8)(3 letters)(3 letters)(3-4 alphanumeric)
    m_mg = re.search(r'\b(MG[1-8][A-Z]{3}[A-Z]{3}[A-Z0-9]{3,4})\b', remainder, re.IGNORECASE)
    if m_mg:
        course_code = m_mg.group(1).upper()
        # Clean title
        title = remainder.replace(m_mg.group(1), '')
        title = re.sub(r'^\s*[-:]\s*|\s*[-:]\s*$', '', title).strip()
        title = re.sub(r'\s*-\s*', ' - ', title).strip(' -')
    else:
        # Check CBCS code e.g. CS6CRT15, SW6CRT24
        m_cbcs = re.search(r'\b([A-Z]{2,4}\d[A-Z]{2,4}\d{1,3}[A-Z]?)\b', remainder)
        if m_cbcs:
            course_code = m_cbcs.group(1).upper()
            title = remainder.replace(m_cbcs.group(1), '').strip(' -:')
        else:
            title = remainder

    return qp_code, course_code, title

def parse_course_code_enhanced(code):
    if not code:
        return None
    # Standard MG pattern
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
    
    # CBCS pattern e.g. CS6CRT15
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
        
    return None

def build_database_v2():
    scratch_dir = r"C:\Users\Navirex\.gemini\antigravity\scratch"
    out_dir = r"C:\Users\Navirex\.gemini\antigravity\scratch\mgu-qp-portal\data"
    
    file_pattern = re.compile(
        r"onclick=[\"']openFile\((?:&#039;|['\"])(.*?)(?:&#039;|['\"])\)[\"'][^>]*>(.*?)</div>",
        re.IGNORECASE | re.DOTALL
    )
    
    all_papers = []
    
    for filename, meta in EXAM_METADATA.items():
        fpath = os.path.join(scratch_dir, filename)
        if not os.path.exists(fpath):
            continue
            
        with open(fpath, "r", encoding="utf-8") as f:
            html = f.read()
            
        parts = html.split('<button class="accordion">')
        for idx, part in enumerate(parts[1:]):
            btn_html, _, rest = part.partition('</button>')
            raw_header = clean_html(btn_html)
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

            # If course_code in model_courses, get enriched metadata
            model_info = MODEL_COURSES.get(course_code)
            if model_info and not title:
                title = model_info["title"]

            parsed = parse_course_code_enhanced(course_code)
            
            sem = parsed["semester"] if parsed else meta["semester"]
            sem_label = f"Semester {sem}"
            
            ctype = parsed["course_type"] if parsed else ("CBCS" if "CBCS" in meta["exam_name"] else "GEN")
            ctype_name = parsed["course_type_name"] if parsed else ("CBCS Core" if "CBCS" in meta["exam_name"] else "General Course")
            
            dept_code = parsed["dept_code"] if parsed else "GEN"
            dept_name = parsed["dept_name"] if parsed else ("General" if dept_code == "GEN" else DEPT_NAMES.get(dept_code, dept_code))
            parent_dept = parsed["parent_dept"] if parsed else dept_code
            parent_dept_name = parsed["parent_dept_name"] if parsed else ("General Studies" if parent_dept == "GEN" else DEPT_NAMES.get(parent_dept, parent_dept))
            is_minor = parsed["is_minor"] if parsed else False
            
            unique_id = f"exam{meta['id']}_{qp_code or course_code or idx}"
            
            item = {
                "id": unique_id,
                "qp_code": qp_code,
                "course_code": course_code,
                "title": title or raw_header or f"Course {course_code}",
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
                "batch": meta["batch"],
                "has_qp": has_qp,
                "qp_url": qp_url,
                "has_scheme": has_scheme,
                "scheme_url": scheme_url,
                "files": files,
                "has_files": len(files) > 0
            }
            all_papers.append(item)
            
    # Calculate stats
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
        "last_sync": "2026-10-17 07:48 UTC",
        "source_portal": "https://assist.mgu.ac.in/schema/"
    }
    
    with open(os.path.join(out_dir, "papers.json"), "w", encoding="utf-8") as f:
        json.dump(all_papers, f, indent=2)
        
    with open(os.path.join(out_dir, "stats.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
        
    print(f"Updated papers.json: {total_papers} records, {len(with_files)} with files.")
    print(f"Parent departments identified: {len(unique_depts)}")

if __name__ == "__main__":
    build_database_v2()

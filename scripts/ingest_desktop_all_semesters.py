import os
import sys
import re
import json
import time
import shutil
import pypdf

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
PUBLIC_DATA_DIR = os.path.join(BASE_DIR, "public", "data")
UPLOADS_MODEL_DIR = os.path.join(BASE_DIR, "uploads", "model_papers")
PUBLIC_UPLOADS_MODEL_DIR = os.path.join(BASE_DIR, "public", "uploads", "model_papers")
STORAGE_PDF_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "mgu-qp-storage", "pdf"))

SEMESTER_FOLDERS = [
    (1, r"c:\Users\Navirex\Desktop\Semester1"),
    (2, r"c:\Users\Navirex\Desktop\Semester2"),
    (3, r"c:\Users\Navirex\Desktop\Semester3"),
    (4, r"c:\Users\Navirex\Desktop\Semester4"),
]

SKIP_FILES = {
    'institutional-development-plan-2025-35.pdf',
    'mgu_ugc-approval_pdf.pdf',
    '5805-ac_a_1-2024-mgu.pdf',
    '87592-ad_a3-4-2022-admin.pdf'
}

os.makedirs(UPLOADS_MODEL_DIR, exist_ok=True)
os.makedirs(PUBLIC_UPLOADS_MODEL_DIR, exist_ok=True)
if os.path.exists(os.path.dirname(STORAGE_PDF_DIR)):
    os.makedirs(STORAGE_PDF_DIR, exist_ok=True)

with open(os.path.join(DATA_DIR, "departments.json"), "r", encoding="utf-8") as f:
    depts = json.load(f)
dept_dict = {d["code"]: d["name"] for d in depts}
dept_names = set([d["name"].strip().lower() for d in depts] + [d["code"].strip().lower() for d in depts])

with open(os.path.join(DATA_DIR, "papers.json"), "r", encoding="utf-8") as f:
    papers = json.load(f)

# Build map of catalog courses
catalog_by_code = {}
for p in papers:
    cc = (p.get("course_code") or "").strip().upper()
    if cc:
        catalog_by_code[cc] = p

def is_department_name(title):
    if not title:
        return True
    t = title.strip().lower()
    return t in dept_names or t in [d.lower() for d in dept_dict.keys()]

def collapse_spaced_words(text):
    return re.sub(r'(?<=\b[A-Za-z0-9])\s+(?=[A-Za-z0-9]\b)', '', text)

def clean_extracted_title(cand):
    if not cand:
        return ""
    cand = cand.strip()
    # Remove leading numbering like "1. ", "01. "
    cand = re.sub(r'^\d+[\.\)]\s*', '', cand)
    # Remove trailing metadata (Time, Duration, Marks, Part, Section, MGU, Semester)
    cand = re.sub(r'\s*(?:Time\s*:|Duration\s*:|Max\s*\.?\s*Marks|Part\s+[A-Z]|Section\s+[A-Z]|Total\s*Marks|Marks\s*:|MGU\b|Admission\b|Semester\b).*$', '', cand, flags=re.IGNORECASE).strip()
    # Remove trailing hyphens or colons
    cand = re.sub(r'[\s\-–—:]+$', '', cand).strip()
    # Remove surrounding quotes or parentheses
    cand = re.sub(r'^["\'\(\[]+|["\'\)\]]+$', '', cand).strip()
    return cand

def extract_page_info(page_text, sem_default=1):
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
        # Suffix removal: remove TRANS or trailing non-numeric characters
        m_strip = re.match(r'^(MG[1-8](?:DSC|DSE|SEC|MDC|VAC|CCR|AEC|MDE|SDC|MPC|HON|MIN|MDE)[A-Z]{2,5}(?:A\d{2}|[1-5][0-9]{2}))[A-Z]+$', c)
        if m_strip:
            c = m_strip.group(1)
            
        # Ensure code starts with MG and has semester
        if c.startswith('MGDSE') or c.startswith('MGDSC') or c.startswith('MGSEC') or c.startswith('MGMDC') or c.startswith('MGVAC') or c.startswith('MGCCR') or c.startswith('MGAEC'):
            c = f'MG{sem_default}' + c[2:]
            
        # Strip any remaining trailing alphabetic characters
        c = re.sub(r'(?<=\d)[A-Za-z]+$', '', c)
        
        # Must end in a digit e.g. 100, 201, A01, A02, A00
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
                
    # Pattern B: Code followed by hyphen or colon (hyphen followed by 5 to 15 words)
    if not title:
        for c in valid_codes:
            esc = re.escape(c)
            for txt in [clean, collapsed]:
                # Hyphen / dash / colon after code
                m_hyphen = re.search(esc + r'\s*[:\-–—]+\s*([A-Za-z0-9\s,&\'\/\(\)\-]{3,90})', txt, re.IGNORECASE)
                if m_hyphen:
                    cand = clean_extracted_title(m_hyphen.group(1))
                    if cand and not is_department_name(cand) and len(cand) >= 3 and not cand.lower().startswith(('part', 'section', 'time', 'max', 'total')):
                        title = cand
                        break
                # Space after code
                m_space = re.search(esc + r'\s+([A-Za-z][A-Za-z0-9\s,&\'\/\(\)\-]{3,80})', txt, re.IGNORECASE)
                if m_space:
                    cand = clean_extracted_title(m_space.group(1))
                    if cand and not is_department_name(cand) and len(cand) >= 4 and not cand.lower().startswith(('part', 'section', 'time', 'max', 'total', 'marks', 'model')):
                        title = cand
                        break
            if title: break
            
    # Pattern C: Title right before code: e.g. "FUNCTIONAL ZOOLOGY - MG4DSCZGY202"
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
    matched_cat = None
    for c in valid_codes:
        if c in catalog_by_code:
            matched_cat = catalog_by_code[c]
            break
            
    if matched_cat and matched_cat.get('title'):
        cat_t = matched_cat['title'].strip()
        if not is_department_name(cat_t):
            if not title or title.isupper() or len(title) < 5 or is_department_name(title):
                title = cat_t
                
    if not title and valid_codes:
        title = f'Course {valid_codes[0]}'
        
    return {
        'is_blank': False,
        'is_start': is_start,
        'codes': valid_codes,
        'title': title,
        'is_practical': is_practical,
        'matched_cat': matched_cat
    }

print("==================================================================")
print("BATCH INGESTION: Semesters 1, 2, 3, and 4 FYUGP Model Question Papers")
print("==================================================================", flush=True)

total_sliced_all = 0
total_updated_cat = 0
total_added_cat = 0
seen_paper_signatures = set()

for sem_num, folder_path in SEMESTER_FOLDERS:
    if not os.path.exists(folder_path):
        print(f"Skipping {folder_path} (not found)", flush=True)
        continue
        
    files = sorted([f for f in os.listdir(folder_path) if f.lower().endswith('.pdf') and f.lower() not in SKIP_FILES])
    print(f"\n==================================================================")
    print(f"--- SEMESTER {sem_num} ({len(files)} compilation PDFs in {folder_path}) ---")
    print(f"==================================================================", flush=True)
    
    for fname in files:
        fpath = os.path.join(folder_path, fname)
        try:
            reader = pypdf.PdfReader(fpath)
        except Exception as e:
            print(f"Failed to read {fname}: {e}", flush=True)
            continue
            
        num_pages = len(reader.pages)
        if num_pages == 0:
            continue
            
        page_infos = []
        for p in reader.pages:
            try:
                t = p.extract_text() or ''
            except Exception:
                t = ''
            page_infos.append(extract_page_info(t, sem_default=sem_num))
            
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
            
        print(f"\nPDF: {fname} ({num_pages}p) -> {len(segments)} model paper segments", flush=True)
        
        for seg in segments:
            s_start = seg['start']
            s_end = seg['end']
            scodes = seg['codes']
            stitle = seg['title']
            is_prac = seg['is_practical']
            ptype = 'PRACTICAL' if is_prac else 'THEORY'
            page_count = s_end - s_start + 1
            
            # If no code extracted from page text, attempt extraction from filename e.g. MG2AECMAL100-...
            if not scodes:
                m_file = re.search(r'\b(MG[1-8][A-Z]{3,8}(?:A\d{2}|\d{3}))\b', fname, re.IGNORECASE)
                if m_file:
                    scodes = [m_file.group(1).upper()]
                    
            if not scodes:
                print(f"  [SKIPPED] Pages {s_start}–{s_end}: No valid FYUGP course code found.", flush=True)
                continue
                
            first_code = scodes[0]
            sig_key = f"{first_code}_{ptype}"
            if sig_key in seen_paper_signatures:
                print(f"  [DUPLICATE WITHIN RUN SKIPPED] {first_code} ({ptype}) Pages {s_start}–{s_end}", flush=True)
                continue
            seen_paper_signatures.add(sig_key)
            
            # Slice PDF
            writer = pypdf.PdfWriter()
            for p_no in range(s_start - 1, s_end):
                writer.add_page(reader.pages[p_no])
                
            for code in scodes:
                out_filename = f"MODEL_{code}_{ptype}.pdf" if ptype == 'PRACTICAL' else f"MODEL_{code}.pdf"
                
                # 1. Local uploads
                local_target = os.path.join(UPLOADS_MODEL_DIR, out_filename)
                with open(local_target, "wb") as f_out:
                    writer.write(f_out)
                    
                # 2. Public uploads
                pub_target = os.path.join(PUBLIC_UPLOADS_MODEL_DIR, out_filename)
                shutil.copy2(local_target, pub_target)
                
                # 3. Storage repo
                if os.path.exists(STORAGE_PDF_DIR):
                    storage_target = os.path.join(STORAGE_PDF_DIR, out_filename)
                    shutil.copy2(local_target, storage_target)
                    
                total_sliced_all += 1
                
                # Parse metadata from code
                m_code = re.match(r'^MG([1-8])(DSC|DSE|SEC|MDC|VAC|CCR|AEC|MDE|SDC|MPC|HON|MIN|MDE)([A-Z]{2,5})(A\d{2}|\d{3})$', code)
                sem = sem_num
                ctype = 'DSC'
                dept_c = 'GEN'
                is_signature = bool(re.search(r'A\d{2}$', code))
                
                if m_code:
                    sem = int(m_code.group(1))
                    ctype = m_code.group(2)
                    dept_c = m_code.group(3)
                    if m_code.group(4).startswith('A'):
                        is_signature = True
                elif 'A0' in code or 'A1' in code:
                    is_signature = True
                    
                dept_name_val = dept_dict.get(dept_c, dept_c)
                
                clean_title = stitle
                if is_department_name(clean_title):
                    if code in catalog_by_code and catalog_by_code[code].get('title') and not is_department_name(catalog_by_code[code]['title']):
                        clean_title = catalog_by_code[code]['title']
                    else:
                        clean_title = f"Course {code}"
                        
                model_entry = {
                    "id": f"model_{code}_{ptype.lower()}_{int(time.time())}",
                    "title": clean_title,
                    "paper_type": ptype,
                    "url": f"uploads/model_papers/{out_filename}",
                    "cdn_url": f"https://cdn.jsdelivr.net/gh/sinan-newman/mgu-qp-storage@main/pdf/{out_filename}",
                    "pages": page_count,
                    "source": f"MGU Official FYUGP Model Question Paper (Semester {sem} Compilation)"
                }
                
                if code in catalog_by_code:
                    cat_paper = catalog_by_code[code]
                    if "model_papers" not in cat_paper or not isinstance(cat_paper["model_papers"], list):
                        cat_paper["model_papers"] = []
                        
                    # Rule: At most 1 Theory and at most 1 Practical per course
                    # Replace existing of the same type
                    cat_paper["model_papers"] = [m for m in cat_paper["model_papers"] if m.get("paper_type", "THEORY").upper() != ptype]
                    cat_paper["model_papers"].append(model_entry)
                    cat_paper["has_files"] = True
                    
                    if is_department_name(cat_paper.get("title")):
                        cat_paper["title"] = clean_title
                        
                    if is_signature:
                        cat_paper["is_signature"] = True
                        
                    total_updated_cat += 1
                else:
                    ts = int(time.time())
                    new_cat_paper = {
                        "id": f"custom_model_{code}_{ts}",
                        "qp_code": "",
                        "course_code": code,
                        "title": clean_title,
                        "raw_header": f"{code} {clean_title}",
                        "semester": sem,
                        "semester_label": f"Semester {sem}",
                        "course_type": ctype,
                        "course_type_name": ctype,
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
                    papers.append(new_cat_paper)
                    catalog_by_code[code] = new_cat_paper
                    total_added_cat += 1
                    
            print(f"  ✓ Extracted Pages {s_start:2d}–{s_end:2d} ({page_count}p) -> Codes={scodes} | Type={ptype} | Title=\"{clean_title}\"", flush=True)

# Post-processing: Rigorous Portal-Wide Deduplication and Quality Enforcement
print("\n==================================================================")
print("RUNNING GLOBAL DEDUPLICATION & INTEGRITY CHECK ACROSS ALL COURSES")
print("==================================================================", flush=True)

total_deduped = 0
for p in papers:
    # 1. Clean course title if it equals department name
    if is_department_name(p.get("title")):
        if p.get("model_papers") and len(p["model_papers"]) > 0:
            first_m_title = p["model_papers"][0].get("title")
            if first_m_title and not is_department_name(first_m_title):
                p["title"] = first_m_title
            else:
                p["title"] = f"Course {p.get('course_code')}"
        else:
            p["title"] = f"Course {p.get('course_code')}"

    # 2. Check signature flag
    cc = p.get("course_code") or ""
    if re.search(r'A\d{2}$', cc) or 'A0' in cc or 'A1' in cc:
        p["is_signature"] = True

    # 3. Deduplicate model_papers: Enforce at most 1 Theory and at most 1 Practical
    if p.get("model_papers") and len(p["model_papers"]) > 1:
        theories = [m for m in p["model_papers"] if (m.get("paper_type") or "THEORY").upper() == "THEORY"]
        practicals = [m for m in p["model_papers"] if (m.get("paper_type") or "").upper() == "PRACTICAL"]
        
        final_models = []
        if theories:
            # Pick the best theory model paper (prefer one with valid pages, cdn_url, non-department title)
            theories.sort(key=lambda m: (
                m.get("pages", 0) > 0,
                not is_department_name(m.get("title")),
                bool(m.get("cdn_url")),
                len(m.get("title", ""))
            ), reverse=True)
            final_models.append(theories[0])
            if len(theories) > 1:
                total_deduped += (len(theories) - 1)
                
        if practicals:
            practicals.sort(key=lambda m: (
                m.get("pages", 0) > 0,
                not is_department_name(m.get("title")),
                bool(m.get("cdn_url")),
                len(m.get("title", ""))
            ), reverse=True)
            final_models.append(practicals[0])
            if len(practicals) > 1:
                total_deduped += (len(practicals) - 1)
                
        p["model_papers"] = final_models

print(f"Portal-wide deduplication complete: {total_deduped} duplicate model papers removed.")

# Save updated papers.json to both locations
print("\nSaving updated catalog database...")
with open(os.path.join(DATA_DIR, "papers.json"), "w", encoding="utf-8") as f:
    json.dump(papers, f, indent=2, ensure_ascii=False)
with open(os.path.join(PUBLIC_DATA_DIR, "papers.json"), "w", encoding="utf-8") as f:
    json.dump(papers, f, indent=2, ensure_ascii=False)

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

with open(os.path.join(DATA_DIR, "model_papers.json"), "w", encoding="utf-8") as f:
    json.dump(all_model_catalog, f, indent=2, ensure_ascii=False)
if os.path.exists(PUBLIC_DATA_DIR):
    with open(os.path.join(PUBLIC_DATA_DIR, "model_papers.json"), "w", encoding="utf-8") as f:
        json.dump(all_model_catalog, f, indent=2, ensure_ascii=False)

print("\n==================================================================")
print("BATCH INGESTION & DEDUPLICATION FINISHED SUCCESSFULLY!")
print(f"Total sliced model PDFs generated: {total_sliced_all}")
print(f"Existing catalog courses updated: {total_updated_cat}")
print(f"New courses added to catalog: {total_added_cat}")
print(f"Total courses now in database: {len(papers)}")
print(f"Total model papers across all semesters: {len(all_model_catalog)}")
print("==================================================================", flush=True)

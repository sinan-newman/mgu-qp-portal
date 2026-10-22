import json
import re
import os
import pypdf

STORAGE_DIR = r"C:\Users\Navirex\.gemini\antigravity\scratch\mgu-qp-storage\pdf"
PORTAL_DIR = r"C:\Users\Navirex\.gemini\antigravity\scratch\mgu-qp-portal"

# Department name mapping
DEPT_NAMES = {
    "ENG": "English", "COM": "Commerce", "MAT": "Mathematics", "PHY": "Physics",
    "CHE": "Chemistry", "CHY": "Chemistry", "BOT": "Botany", "ZGY": "Zoology",
    "ECO": "Economics", "HIS": "History", "POL": "Political Science", "SOC": "Sociology",
    "MAL": "Malayalam", "HIN": "Hindi", "ARA": "Arabic", "ARB": "Arabic", "SAN": "Sanskrit",
    "SYR": "Syriac", "FRH": "French", "GER": "German", "CSC": "Computer Science",
    "BCA": "Computer Applications", "BBA": "Business Administration", "PSY": "Psychology",
    "BCH": "Biochemistry", "BIF": "Bioinformatics", "FTM": "Food Technology", "FTA": "Food Technology",
    "FSQ": "Food Science & Quality", "MVN": "Music (Veena)", "MVO": "Music (Vocal)",
    "MVL": "Music (Violin)", "KMD": "Kathakali Maddalam", "MHN": "Mohiniyattam",
    "FDG": "Fashion Design", "TXL": "Textiles", "REM": "Renewable Energy", "SAC": "Sports Coaching",
    "SMG": "Sports Management", "FIM": "Fitness Management", "CMA": "Computer Animation",
    "GRA": "Graphic Design", "IAA": "Interior Architecture", "STA": "Statistics", "PHL": "Philosophy"
}

COURSE_TYPE_NAMES = {
    "DSC": "Discipline Specific Core",
    "DSE": "Discipline Specific Elective",
    "MDC": "Multi-Disciplinary Course",
    "SEC": "Skill Enhancement Course",
    "VAC": "Value Added Course",
    "AEC": "Ability Enhancement Course",
    "CCR": "Common Core",
    "MDE": "Major Department Elective",
    "MPC": "Minor Pathway Course",
    "SDC": "Skill Development Component"
}

def clean_course_title(raw):
    if not raw: return ""
    cand = raw.strip()
    cand = re.sub(r'^(COURSE\s*NAME\s*[:\-–]*|COURSE\s*TITLE\s*[:\-–]*|COURSE\s*[:\-–]*|TITLE\s*[:\-–]*)', '', cand, flags=re.I).strip()
    cand = re.sub(r'[\t]+', ' ', cand)
    cand = re.sub(r'\s*\(202\d.*$', '', cand)
    cand = re.sub(r'\s*\(QP\s*Code.*$', '', cand, flags=re.I)
    cand = re.sub(r'\s*–\s*Answer\s*Key.*$', '', cand, flags=re.I)
    cand = re.sub(r'\s*-\s*Answer\s*Scheme.*$', '', cand, flags=re.I)
    cand = re.sub(r'\s*Duration.*$', '', cand, flags=re.I)
    cand = re.sub(r'\s*Time\s*:?.*$', '', cand, flags=re.I)
    cand = re.sub(r'\s*Maximum\s*Marks.*$', '', cand, flags=re.I)
    cand = cand.strip(" -–:;,.()[]")
    
    # Title-case if all caps
    if cand.isupper() and len(cand) > 4:
        cand = cand.title()
    return cand

def get_dept_from_code(code):
    if not code or len(code) < 9: return "GEN", "General Studies"
    m = re.match(r'^MG[1-8](?:DSC|DSE|SEC|MDC|VAC|CCR|AEC|MDE|SDC|MPC|HON|MIN|MDE)([A-Z]{2,5})(?:A\d{2}|\d{3})$', code)
    if m:
        dept = m.group(1).upper()
        return dept, DEPT_NAMES.get(dept, dept)
    return "GEN", "General Studies"

def extract_pdf_metadata(pdf_path):
    if not os.path.exists(pdf_path): return None
    try:
        reader = pypdf.PdfReader(pdf_path)
        txt = ""
        for page in reader.pages[:2]:
            txt += (page.extract_text() or "") + "\n"
            
        m_cc = re.search(r'\b(MG[1-8](?:DSC|DSE|SEC|MDC|VAC|CCR|AEC|MDE|SDC|MPC|HON|MIN|MDE)[A-Z]{2,5}(?:A\d{2}|\d{3}))\b', txt, re.I)
        m_qp = re.search(r'\b(2[4-6]\d{6})\b', txt)
        
        extracted_cc = m_cc.group(1).upper() if m_cc else None
        extracted_qp = m_qp.group(1) if m_qp else None
        extracted_title = None
        
        if extracted_cc:
            m_title = re.search(re.escape(extracted_cc) + r'[\s–\-:]+([A-Za-z0-9\s,\(\)&\'\-]{3,80})', txt)
            if m_title:
                cand = m_title.group(1).splitlines()[0].strip()
                cand = clean_course_title(cand)
                if len(cand) > 3 and not cand.lower().startswith("course "):
                    extracted_title = cand
                    
        return {
            "course_code": extracted_cc,
            "qp_code": extracted_qp,
            "title": extracted_title,
            "text": txt[:500]
        }
    except Exception as e:
        return {"error": str(e)}

# Load papers
papers_file = os.path.join(PORTAL_DIR, "data", "papers.json")
with open(papers_file, "r", encoding="utf-8") as f:
    papers = json.load(f)

print(f"Initial paper records: {len(papers)}")

# Build course_code -> canonical paper map
by_code_and_sem = {}
for p in papers:
    cc = (p.get("course_code") or "").strip().upper()
    sem = p.get("semester")
    if cc and sem:
        key = (cc, sem)
        if key not in by_code_and_sem:
            by_code_and_sem[key] = p

# 1. Dismantle exam31_1792678404
e31_paper = next((p for p in papers if p.get("id") == "exam31_1792678404"), None)
e31_new_papers = []

if e31_paper:
    files = e31_paper.get("files", [])
    print(f"\nDismantling exam31_1792678404 ({len(files)} files)...")
    
    file_info = []
    for f in files:
        url = f.get("url", "")
        ftype = f.get("type", "QP")
        fn = os.path.basename(url)
        fpath = os.path.join(STORAGE_DIR, fn)
        meta = extract_pdf_metadata(fpath) or {}
        file_info.append({
            "file": f,
            "fn": fn,
            "type": ftype,
            "url": url,
            "course_code": meta.get("course_code"),
            "qp_code": meta.get("qp_code"),
            "title": meta.get("title")
        })
        
    # Match QP code cross-references
    qp_to_code = {r["qp_code"]: r["course_code"] for r in file_info if r.get("qp_code") and r.get("course_code")}
    qp_to_title = {r["qp_code"]: r["title"] for r in file_info if r.get("qp_code") and r.get("title")}
    
    for r in file_info:
        if not r.get("course_code") and r.get("qp_code") in qp_to_code:
            r["course_code"] = qp_to_code[r["qp_code"]]
        if not r.get("title") and r.get("qp_code") in qp_to_title:
            r["title"] = qp_to_title[r["qp_code"]]
            
    # Group by course_code (or qp_code)
    groups = {}
    for r in file_info:
        key = r.get("course_code") or r.get("qp_code") or r["fn"]
        if key not in groups:
            groups[key] = {
                "course_code": r.get("course_code"),
                "qp_code": r.get("qp_code"),
                "title": r.get("title") or "",
                "files": []
            }
        groups[key]["files"].append(r["file"])
        if r.get("title") and not groups[key]["title"]:
            groups[key]["title"] = r["title"]
        if r.get("course_code") and not groups[key]["course_code"]:
            groups[key]["course_code"] = r["course_code"]
        if r.get("qp_code") and not groups[key]["qp_code"]:
            groups[key]["qp_code"] = r["qp_code"]
            
    print(f"Grouped into {len(groups)} distinct exam31 sets.")
    
    for k, g in groups.items():
        cc = g.get("course_code")
        sem = 3
        title = clean_course_title(g.get("title"))
        qp_code = g.get("qp_code")
        
        qp_file = next((f for f in g["files"] if f.get("type") == "QP"), None)
        sch_file = next((f for f in g["files"] if f.get("type") == "SCHEME"), None)
        
        # Check if course code already exists in Semester 3
        if cc and (cc, 3) in by_code_and_sem:
            target = by_code_and_sem[(cc, 3)]
            # Merge files
            if qp_file and not target.get("has_qp"):
                target["qp_url"] = qp_file["url"]
                target["has_qp"] = True
            if sch_file and not target.get("has_scheme"):
                target["scheme_url"] = sch_file["url"]
                target["has_scheme"] = True
            for f in g["files"]:
                if not any(tf.get("url") == f.get("url") for tf in target.get("files", [])):
                    target.setdefault("files", []).append(f)
            target["has_files"] = True
            if title and (not target.get("title") or target["title"].lower().startswith("course ")):
                target["title"] = title
            print(f"  Merged exam31 {cc} with existing Semester 3 record {target['id']}")
        elif cc:
            dept_c, dept_n = get_dept_from_code(cc)
            ctype = "DSC"
            m_type = re.search(r'MG[1-8](DSC|DSE|SEC|MDC|VAC|CCR|AEC|MDE|SDC|MPC|HON|MIN|MDE)', cc)
            if m_type: ctype = m_type.group(1).upper()
            
            new_id = f"exam31_{qp_code or cc.lower()}"
            new_rec = {
                "id": new_id,
                "qp_code": qp_code or "",
                "course_code": cc,
                "title": title or f"{dept_n} Course {cc}",
                "raw_header": f"{qp_code or ''} - {cc} - {title or dept_n}",
                "semester": 3,
                "semester_label": "Semester 3",
                "course_type": ctype,
                "course_type_name": COURSE_TYPE_NAMES.get(ctype, ctype),
                "dept_code": dept_c,
                "dept_name": dept_n,
                "parent_dept": dept_c,
                "parent_dept_name": dept_n,
                "is_minor": False,
                "exam_id": "31",
                "exam_name": "MGU UGP (Honours) Special Examination October 2025/July 2026",
                "batch": "2024 Admission",
                "is_fyugp": True,
                "has_qp": bool(qp_file),
                "qp_url": qp_file["url"] if qp_file else "",
                "has_scheme": bool(sch_file),
                "scheme_url": sch_file["url"] if sch_file else "",
                "files": g["files"],
                "has_files": True,
                "minor_name": "",
                "model_papers": [],
                "is_signature": bool(re.search(r'A\d{2}$', cc)),
                "needs_review": False,
                "status": "published"
            }
            e31_new_papers.append(new_rec)
            by_code_and_sem[(cc, 3)] = new_rec
            print(f"  Created new published record for {cc} ({title})")
        else:
            # Fallback for completely unrecognizable files: keep for admin review
            new_id = f"exam31_pending_{k}"
            new_rec = {
                "id": new_id,
                "qp_code": qp_code or "",
                "course_code": "",
                "title": f"Question Paper / Scheme (QP: {qp_code or 'Unknown'})",
                "raw_header": f"Exam 31 - QP {qp_code or 'Pending'}",
                "semester": 3,
                "semester_label": "Semester 3",
                "course_type": "DSC",
                "dept_code": "GEN",
                "dept_name": "General Studies",
                "parent_dept": "GEN",
                "parent_dept_name": "General Studies",
                "is_minor": False,
                "exam_id": "31",
                "has_qp": bool(qp_file),
                "qp_url": qp_file["url"] if qp_file else "",
                "has_scheme": bool(sch_file),
                "scheme_url": sch_file["url"] if sch_file else "",
                "files": g["files"],
                "has_files": True,
                "needs_review": True,
                "status": "pending_review",
                "ambiguity_reason": "Missing course code. Admin verification needed."
            }
            e31_new_papers.append(new_rec)
            print(f"  Kept pending review record for {new_id}")

# 2. Drop duplicate orphan records
drop_ids = {
    "exam31_1792678404",  # dismantled
    "exam4_1792678404",   # duplicate of exam4_25900155 (MG2DSCPHY100)
    "exam7_1792678404",   # duplicate of exam7_25901053 (MG1SDCREM102)
    "exam34_1792678404",  # duplicate of exam34_25901909 (MG1AECSYR102)
    "orphan_mg3dscvn200cours",
    "orphan_mg3dscvn201cours",
    "orphan_mg3dscvn202cours"
}

cleaned_papers = [p for p in papers if p.get("id") not in drop_ids]
cleaned_papers.extend(e31_new_papers)
print(f"\nPapers count after dismantling exam31 and dropping duplicates: {len(cleaned_papers)}")

# 3. Known typos correction & department assignment
known_corrections = {
    "model_only_MG2MDC3NG101": {
        "course_code": "MG1MDCENG101",
        "title": "Sports, Literature and Cinema",
        "dept_code": "ENG",
        "dept_name": "English",
        "semester": 1
    },
    "model_only_MG3DSCOM201": {
        "course_code": "MG3DSCCOM201",
        "title": "Quantitative Techniques for Business",
        "dept_code": "COM",
        "dept_name": "Commerce",
        "semester": 3
    },
    "model_only_MG3MPCHY200": {
        "course_code": "MG3MPCCHY200",
        "title": "Bio-Organic Chemistry",
        "dept_code": "CHY",
        "dept_name": "Chemistry",
        "semester": 3
    },
    "model_only_MG3DSCVN200": {
        "course_code": "MG3DSCMVN200",
        "title": "Varnams and Simple Kritis - I",
        "dept_code": "MVN",
        "dept_name": "Music (Veena)",
        "semester": 3
    },
    "model_only_MG3DSCVN201": {
        "course_code": "MG3DSCMVN201",
        "title": "Simple Kritis and Pancharathnam",
        "dept_code": "MVN",
        "dept_name": "Music (Veena)",
        "semester": 3
    },
    "model_only_MG3DSCVN202": {
        "course_code": "MG3DSCMVN202",
        "title": "Varnams and Simple Kritis",
        "dept_code": "MVN",
        "dept_name": "Music (Veena)",
        "semester": 3
    },
    "custom_model_MGIMDCCOM101_1792485466": {
        "course_code": "MG1MDCCOM101",
        "title": "Personal Finance and Planning",
        "dept_code": "COM",
        "dept_name": "Commerce",
        "semester": 1
    },
    "custom_model_MGIDSCSAC100_1792485478": {
        "course_code": "MG1DSCSAC100",
        "title": "Athletics Fundamentals and Techniques",
        "dept_code": "SAC",
        "dept_name": "Sports Coaching",
        "semester": 1
    },
    "custom_model_MGIDSCSAC101_1792485478": {
        "course_code": "MG1DSCSAC101",
        "title": "Techniques, Fundamentals and Spotting",
        "dept_code": "SAC",
        "dept_name": "Sports Coaching",
        "semester": 1
    },
    "custom_model_MGIDSCFIM100_1792485478": {
        "course_code": "MG1DSCFIM100",
        "title": "Health and Fitness Education",
        "dept_code": "FIM",
        "dept_name": "Fitness Management",
        "semester": 1
    },
    "custom_model_MGIDSCSMG100_1792485478": {
        "course_code": "MG1DSCSMG100",
        "title": "Introduction to Sports Management",
        "dept_code": "SMG",
        "dept_name": "Sports Management",
        "semester": 1
    },
    "custom_model_MGIMDCSMG100_1792485478": {
        "course_code": "MG1MDCSMG100",
        "title": "Leadership Skills in Management",
        "dept_code": "SMG",
        "dept_name": "Sports Management",
        "semester": 1
    }
}

# Apply known corrections and merge duplicates
final_papers = []
dropped_as_merged = set()

# Re-index
for p in cleaned_papers:
    pid = p.get("id")
    if pid in known_corrections:
        fix = known_corrections[pid]
        p["course_code"] = fix["course_code"]
        p["title"] = fix["title"]
        p["dept_code"] = fix["dept_code"]
        p["dept_name"] = fix["dept_name"]
        p["parent_dept"] = fix["dept_code"]
        p["parent_dept_name"] = fix["dept_name"]
        p["semester"] = fix["semester"]
        p["semester_label"] = f"Semester {fix['semester']}"
        p["needs_review"] = False
        p["status"] = "published"
        print(f"Applied known correction to {pid}: {p['course_code']} - {p['title']}")

# 4. Resolve remaining generic "Course ..." titles via PDF inspection
resolved_title_count = 0
for p in cleaned_papers:
    title = (p.get("title") or "").strip()
    cc = (p.get("course_code") or "").strip().upper()
    
    # If title is placeholder like "Course MG..."
    if title.lower().startswith("course ") or title.lower() in ("question paper", "general studies", "") or title == cc:
        # Check attached files
        cand_files = []
        if p.get("qp_url"): cand_files.append(p["qp_url"])
        if p.get("scheme_url"): cand_files.append(p["scheme_url"])
        for m in p.get("model_papers", []):
            if m.get("cdn_url"): cand_files.append(m["cdn_url"])
            elif m.get("url"): cand_files.append(m["url"])
            
        found_title = None
        for u in cand_files:
            fn = os.path.basename(u)
            fpath = os.path.join(STORAGE_DIR, fn)
            meta = extract_pdf_metadata(fpath)
            if meta and meta.get("title"):
                found_title = clean_course_title(meta["title"])
                break
                
        if found_title and len(found_title) > 3 and not found_title.lower().startswith("course "):
            p["title"] = found_title
            resolved_title_count += 1
            print(f"  Extracted clean title for {cc}: '{found_title}'")

print(f"Extracted clean titles for {resolved_title_count} papers from PDFs.")

# 5. Flag remaining ambiguous papers for Admin Review Queue
pending_review_count = 0
published_count = 0

for p in cleaned_papers:
    cc = (p.get("course_code") or "").strip().upper()
    title = (p.get("title") or "").strip()
    dept = (p.get("dept_code") or "").strip().upper()
    
    is_invalid_code = not cc or not re.match(r'^MG[1-8][A-Z]{5,10}[A-Z0-9]{3}$', cc)
    is_gen = dept == "GEN"
    is_bad_title = not title or title.lower().startswith("course ") or title.lower() in ("question paper", "general studies", "")
    
    if is_invalid_code or is_gen or is_bad_title:
        p["needs_review"] = True
        p["status"] = "pending_review"
        reasons = []
        if is_invalid_code: reasons.append("Missing or non-standard course code")
        if is_gen: reasons.append("Categorized under General Studies")
        if is_bad_title: reasons.append("Placeholder or generic course title")
        p["ambiguity_reason"] = "; ".join(reasons)
        pending_review_count += 1
    else:
        p["needs_review"] = False
        p["status"] = "published"
        published_count += 1

print(f"\nFinal Summary:")
print(f"  Total papers in database: {len(cleaned_papers)}")
print(f"  Published (fully verified): {published_count}")
print(f"  Pending Admin Review (quarantined): {pending_review_count}")

# Save to data/papers.json and public/data/papers.json
with open(papers_file, "w", encoding="utf-8") as f:
    json.dump(cleaned_papers, f, indent=2, ensure_ascii=False)
public_papers_file = os.path.join(PORTAL_DIR, "public", "data", "papers.json")
with open(public_papers_file, "w", encoding="utf-8") as f:
    json.dump(cleaned_papers, f, indent=2, ensure_ascii=False)

print("Saved updated database to data/papers.json and public/data/papers.json successfully.")

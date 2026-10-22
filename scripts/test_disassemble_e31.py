import json
import re
import os
import pypdf

STORAGE_DIR = r"C:\Users\Navirex\.gemini\antigravity\scratch\mgu-qp-storage\pdf"
PORTAL_DIR = r"C:\Users\Navirex\.gemini\antigravity\scratch\mgu-qp-portal"

with open(os.path.join(PORTAL_DIR, "data", "papers.json"), "r", encoding="utf-8") as f:
    papers = json.load(f)

print(f"Initial papers count: {len(papers)}")

# Map of course codes to their known titles from the database or catalog
known_titles = {}
for p in papers:
    cc = (p.get("course_code") or "").strip().upper()
    title = (p.get("title") or "").strip()
    if cc and title and not title.lower().startswith("course ") and title.lower() not in ("question paper", "general studies"):
        if cc not in known_titles:
            known_titles[cc] = title

print(f"Known course titles dictionary size: {len(known_titles)}")

# Track what happens
disassembled_e31 = []
merged_duplicates = []
updated_records = []
pending_review_records = []

# 1. Process exam31_1792678404
e31_paper = next((p for p in papers if p.get("id") == "exam31_1792678404"), None)
if e31_paper:
    files = e31_paper.get("files", [])
    print(f"exam31 has {len(files)} files to dismantle...")
    
    # Group files by QP code or course code extracted from their PDF
    file_info_list = []
    for f in files:
        url = f.get("url", "")
        ftype = f.get("type", "QP")
        fn = os.path.basename(url)
        fpath = os.path.join(STORAGE_DIR, fn)
        
        extracted_cc = None
        extracted_qp = None
        extracted_title = None
        
        if os.path.exists(fpath):
            try:
                reader = pypdf.PdfReader(fpath)
                txt = (reader.pages[0].extract_text() or "") + (reader.pages[1].extract_text() or "" if len(reader.pages) > 1 else "")
                m_cc = re.search(r'\b(MG[1-8](?:DSC|DSE|SEC|MDC|VAC|CCR|AEC|MDE|SDC|MPC|HON|MIN|MDE)[A-Z]{2,5}(?:A\d{2}|\d{3}))\b', txt, re.I)
                m_qp = re.search(r'\b(2[4-6]\d{6})\b', txt)
                if m_cc: extracted_cc = m_cc.group(1).upper()
                if m_qp: extracted_qp = m_qp.group(1)
                
                if extracted_cc:
                    m_title = re.search(re.escape(extracted_cc) + r'[\s–\-:]+([A-Za-z0-9\s,\(\)&\'\-]{3,80})', txt)
                    if m_title:
                        cand = m_title.group(1).splitlines()[0].strip()
                        cand = re.split(r'\(202\d|Duration|Time|Maximum|Answer|Part|Total', cand, flags=re.I)[0].strip()
                        if len(cand) > 3 and not re.match(r'^(Course|Question|Answer Scheme|Scheme)', cand, re.I):
                            extracted_title = cand
            except Exception:
                pass
                
        file_info_list.append({
            "file": f,
            "fn": fn,
            "ftype": ftype,
            "course_code": extracted_cc,
            "qp_code": extracted_qp,
            "title": extracted_title
        })
        
    # Link schemes with QPs by QP code
    qp_to_code = {r["qp_code"]: r["course_code"] for r in file_info_list if r.get("qp_code") and r.get("course_code")}
    qp_to_title = {r["qp_code"]: r["title"] for r in file_info_list if r.get("qp_code") and r.get("title")}
    
    for r in file_info_list:
        if not r.get("course_code") and r.get("qp_code") in qp_to_code:
            r["course_code"] = qp_to_code[r["qp_code"]]
        if not r.get("title") and r.get("qp_code") in qp_to_title:
            r["title"] = qp_to_title[r["qp_code"]]
            
    # Group into papers by (course_code, qp_code)
    groups = {}
    for r in file_info_list:
        key = r.get("course_code") or r.get("qp_code") or r["fn"]
        if key not in groups:
            groups[key] = {
                "course_code": r.get("course_code"),
                "qp_code": r.get("qp_code"),
                "title": r.get("title") or known_titles.get(r.get("course_code"), ""),
                "files": []
            }
        groups[key]["files"].append(r["file"])
        if r.get("title") and not groups[key]["title"]:
            groups[key]["title"] = r["title"]
        if r.get("course_code") and not groups[key]["course_code"]:
            groups[key]["course_code"] = r["course_code"]
        if r.get("qp_code") and not groups[key]["qp_code"]:
            groups[key]["qp_code"] = r["qp_code"]
            
    print(f"Disassembled exam31 into {len(groups)} distinct course/QP groups.")
    for k, g in list(groups.items())[:10]:
        print(f"  Group {k}: Code: {g['course_code']} | QP: {g['qp_code']} | Title: {g['title']} | Files: {len(g['files'])}")

print("Simulation finished.")

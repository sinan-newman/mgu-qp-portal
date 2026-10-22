import json
import re
import os
import pypdf

STORAGE_DIR = r"C:\Users\Navirex\.gemini\antigravity\scratch\mgu-qp-storage\pdf"
PORTAL_DIR = r"C:\Users\Navirex\.gemini\antigravity\scratch\mgu-qp-portal"

with open(os.path.join(PORTAL_DIR, "data", "papers.json"), "r", encoding="utf-8") as f:
    papers = json.load(f)

e31 = [p for p in papers if p.get("id") == "exam31_1792678404"][0]
files = e31.get("files", [])

print(f"Exam 31 total files: {len(files)}")

results = []
for f in files:
    url = f.get("url", "")
    ftype = f.get("type", "QP")
    fn = os.path.basename(url)
    fpath = os.path.join(STORAGE_DIR, fn)
    
    extracted = {"fn": fn, "type": ftype, "url": url}
    if os.path.exists(fpath):
        try:
            reader = pypdf.PdfReader(fpath)
            txt = ""
            for p in reader.pages[:2]:
                txt += p.extract_text() or ""
            
            # Find course code
            m_cc = re.search(r'\b(MG3(?:DSC|DSE|SEC|MDC|VAC|CCR|AEC|MDE|SDC|MPC|HON|MIN|MDE)[A-Z]{2,5}(?:A\d{2}|\d{3}))\b', txt, re.I)
            if not m_cc:
                m_cc = re.search(r'\b(MG[1-8](?:DSC|DSE|SEC|MDC|VAC|CCR|AEC|MDE|SDC|MPC|HON|MIN|MDE)[A-Z]{2,5}(?:A\d{2}|\d{3}))\b', txt, re.I)
                
            # Find QP code
            m_qp = re.search(r'\b(2[4-6]\d{6})\b', txt)
            
            # Find title
            title = None
            if m_cc:
                cc = m_cc.group(1).upper()
                m_title = re.search(re.escape(cc) + r'[\s–\-:]+([A-Za-z0-9\s,\(\)&\'\-]{3,80})', txt)
                if m_title:
                    cand = m_title.group(1).splitlines()[0].strip()
                    cand = re.split(r'\(202\d|Duration|Time|Maximum|Answer|Part|Total', cand, flags=re.I)[0].strip()
                    if len(cand) > 3 and not re.match(r'^(Course|Question|Answer Scheme|Scheme)', cand, re.I):
                        title = cand
            
            extracted["course_code"] = m_cc.group(1).upper() if m_cc else None
            extracted["qp_code"] = m_qp.group(1) if m_qp else None
            extracted["title"] = title
        except Exception as e:
            extracted["error"] = str(e)
            
    results.append(extracted)

print(f"Parsed {len(results)} files.")
with_code = [r for r in results if r.get("course_code")]
print(f"Files with course code: {len(with_code)} / {len(results)}")
print(f"Files with QP code: {len([r for r in results if r.get('qp_code')])} / {len(results)}")

print("\nSample 20 extracted:")
for r in results[:20]:
    print(f"  {r.get('fn'):26} | Type: {r.get('type'):6} | Code: {str(r.get('course_code')):14} | QP: {str(r.get('qp_code')):8} | Title: {str(r.get('title'))[:30]}")

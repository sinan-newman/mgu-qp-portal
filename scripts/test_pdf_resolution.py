import json
import re
import os
import pypdf

STORAGE_DIR = r"C:\Users\Navirex\.gemini\antigravity\scratch\mgu-qp-storage\pdf"
PORTAL_DIR = r"C:\Users\Navirex\.gemini\antigravity\scratch\mgu-qp-portal"

with open(os.path.join(PORTAL_DIR, "data", "papers.json"), "r", encoding="utf-8") as f:
    papers = json.load(f)

print(f"Total papers in database: {len(papers)}")

def is_ambiguous(p):
    cc = (p.get("course_code") or "").strip().upper()
    title = (p.get("title") or "").strip()
    dept = (p.get("dept_code") or "").strip().upper()
    
    if dept == "GEN":
        return True
    if not cc or not re.match(r'^MG[1-8][A-Z]{5,10}[A-Z0-9]{3}$', cc):
        return True
    title_lower = title.lower()
    if title_lower.startswith("course ") or title_lower in ("question paper", "general studies", "evaluation scheme", "", "scheme", "model question paper") or title_lower == cc.lower():
        return True
    return False

ambiguous_papers = [p for p in papers if is_ambiguous(p)]
print(f"Ambiguous papers to inspect: {len(ambiguous_papers)}")

# Try to extract course code and title from PDFs
def extract_from_pdf(pdf_path):
    if not os.path.exists(pdf_path):
        return None
    try:
        reader = pypdf.PdfReader(pdf_path)
        full_text = ""
        for page in reader.pages[:2]:
            full_text += page.extract_text() or ""
        
        # 1. Look for course code
        # Pattern: MG[1-8](DSC|DSE|SEC|MDC|VAC|CCR|AEC|MDE|SDC|MPC|HON|MIN|MDE)[A-Z]{2,5}(A\d{2}|\d{3})
        code_match = re.search(r'\b(MG[1-8](?:DSC|DSE|SEC|MDC|VAC|CCR|AEC|MDE|SDC|MPC|HON|MIN|MDE)[A-Z]{2,5}(?:A\d{2}|\d{3}))\b', full_text, re.IGNORECASE)
        
        # 2. Look for QP code
        qp_match = re.search(r'\b(2[4-6]\d{6})\b', full_text)
        
        # 3. Look for course title around course code or header
        title_found = None
        if code_match:
            cc = code_match.group(1).upper()
            # Try to find text after course code, e.g. "MG3DSECHE201 - Introduction to Nanoscience"
            m_title = re.search(re.escape(cc) + r'[\s–\-:]+([A-Za-z0-9\s,\(\)&\'\-]{3,80})', full_text)
            if m_title:
                cand = m_title.group(1).splitlines()[0].strip()
                # Clean up trailing instructions
                cand = re.split(r'\(202\d|Duration|Time|Maximum|Answer|Part|Total', cand, flags=re.IGNORECASE)[0].strip()
                if len(cand) > 3 and not re.match(r'^(Course|Question|Answer Scheme|Scheme)', cand, re.I):
                    title_found = cand
                    
        return {
            "course_code": code_match.group(1).upper() if code_match else None,
            "qp_code": qp_match.group(1) if qp_match else None,
            "title": title_found,
            "text_sample": full_text[:400]
        }
    except Exception as e:
        return {"error": str(e)}

resolvable = []
still_ambiguous = []

for p in ambiguous_papers:
    # Check all attached files
    all_pdf_names = []
    if p.get("qp_url"):
        all_pdf_names.append(os.path.basename(p["qp_url"]))
    if p.get("scheme_url"):
        all_pdf_names.append(os.path.basename(p["scheme_url"]))
    for f in p.get("files", []):
        fn = os.path.basename(f.get("url", ""))
        if fn and fn not in all_pdf_names:
            all_pdf_names.append(fn)
    for m in p.get("model_papers", []):
        fn = os.path.basename(m.get("cdn_url") or m.get("url") or "")
        if fn and fn not in all_pdf_names:
            all_pdf_names.append(fn)
            
    extracted = None
    for fn in all_pdf_names:
        pdf_path = os.path.join(STORAGE_DIR, fn)
        res = extract_from_pdf(pdf_path)
        if res and res.get("course_code"):
            extracted = res
            extracted["file_used"] = fn
            break
            
    if extracted and extracted.get("course_code"):
        resolvable.append((p, extracted))
    else:
        still_ambiguous.append((p, all_pdf_names))

print(f"\nAuto-Resolvable from PDF: {len(resolvable)}")
print(f"Still Ambiguous (needs admin review): {len(still_ambiguous)}")

print("\n--- Samples of Auto-Resolvable ---")
for p, res in resolvable[:15]:
    print(f"Original Code: '{p.get('course_code')}' -> Extracted: '{res.get('course_code')}' | Title: '{res.get('title')}' | QP: '{res.get('qp_code')}' | File: {res.get('file_used')}")

print("\n--- Samples of Still Ambiguous ---")
for p, fns in still_ambiguous[:15]:
    print(f"ID: {p.get('id')} | Current Code: '{p.get('course_code')}' | Dept: {p.get('dept_code')} | Title: '{p.get('title')}' | Files: {fns}")

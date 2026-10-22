import os
import re

sync_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts", "sync_engine.py"))
with open(sync_path, "r", encoding="utf-8") as f:
    content = f.read()

# Add extract_metadata_from_pdf function if not present
if "def extract_metadata_from_pdf" not in content:
    pdf_func = '''def extract_metadata_from_pdf(pdf_path):
    if not os.path.exists(pdf_path):
        return None, None
    try:
        from pypdf import PdfReader
        reader = PdfReader(pdf_path)
        if len(reader.pages) == 0:
            return None, None
        page1 = reader.pages[0].extract_text() or ""
        m_code = re.search(r'\\b(MG[1-8](?:DSC|DSE|SEC|MDC|VAC|CCR|AEC|DEC|MDE|SDC|MPC|HON|MIN|MDE)[A-Z]{2,5}(?:A\\d{2}|\\d{3}))\\b', page1, re.IGNORECASE)
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

'''
    parse_marker = 'def parse_header_text(raw_header):'
    if parse_marker in content:
        content = content.replace(parse_marker, pdf_func + parse_marker, 1)
        print("Inserted extract_metadata_from_pdf")
    else:
        print("parse_header_text not found")

# Update course creation to handle ambiguity & PDF fallback
old_block = '''        qp_code, course_code, title = parse_header_text(raw_header)
        meta_course = parse_course_metadata(course_code, sem_default=sem_num)'''

new_block = '''        qp_code, course_code, title = parse_header_text(raw_header)
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

        is_ambiguous = bool(not course_code or meta_course["dept_code"] == "GEN")'''

if old_block in content and "is_ambiguous =" not in content:
    content = content.replace(old_block, new_block, 1)
    print("Updated course resolution with PDF fallback")

# Update target_paper creation dict to include review flags
old_target = '''                "is_signature": meta_course["is_signature"],
                "model_papers": []
            }'''
new_target = '''                "is_signature": meta_course["is_signature"],
                "model_papers": [],
                "needs_review": is_ambiguous,
                "status": "pending_review" if is_ambiguous else "published",
                "review_reason": "Ambiguous course code or General Studies categorization" if is_ambiguous else ""
            }'''
if old_target in content:
    content = content.replace(old_target, new_target, 1)
    print("Updated target_paper dictionary with review flags")

with open(sync_path, "w", encoding="utf-8") as f:
    f.write(content)
print("sync_engine.py patch finished.")

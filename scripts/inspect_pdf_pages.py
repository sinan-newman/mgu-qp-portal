import sys
import pypdf
import os
import re

sys.stdout.reconfigure(encoding='utf-8')

pdf_path = r"temp_model\bba_sem1.pdf"
reader = pypdf.PdfReader(pdf_path)

print(f"Total pages in {pdf_path}: {len(reader.pages)}")
for idx, page in enumerate(reader.pages):
    txt = page.extract_text() or ""
    lines = [l.strip() for l in txt.split("\n") if l.strip()]
    header = " // ".join(lines[:6])
    
    # Look for Course code or QP headers
    course_match = re.search(r'([A-Z0-9]{8,15})', txt)
    code_found = course_match.group(1) if course_match else "No Code"
    
    # Check if page is start of new question paper
    is_start = any(k in txt.upper() for k in ["MAXIMUM MARKS", "TIME: 3 HOURS", "TIME : 3 HOURS", "TIME: 1.5 HOURS", "TIME: 2 HOURS", "FIRST SEMESTER EXAMINATION", "MODEL QUESTION PAPER"])
    
    print(f"Page {idx+1:2d} | Start: {str(is_start):5s} | Code: {code_found:15s} | {header[:90]}")

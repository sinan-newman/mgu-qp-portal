import sys
import pypdf
import os
import re

sys.stdout.reconfigure(encoding='utf-8')

pdf_path = r"temp_model\bca_sem1.pdf"
if not os.path.exists(pdf_path):
    import urllib.request
    req = urllib.request.Request("https://www.mgu.ac.in/uploads/2024/11/BCA-THEORY-COMBINED.pdf", headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as resp, open(pdf_path, 'wb') as f:
        f.write(resp.read())

reader = pypdf.PdfReader(pdf_path)

print(f"Total pages in {pdf_path}: {len(reader.pages)}")
for idx, page in enumerate(reader.pages):
    txt = page.extract_text() or ""
    # Course code pattern: MG[1-8][A-Z]{3,6}[0-9]{3}
    m = re.findall(r'(MG[1-8][A-Z]{3,6}[0-9]{3}[A-Z0-9]*)', txt)
    lines = [l.strip() for l in txt.split("\n") if l.strip()]
    header = " // ".join(lines[:4])
    print(f"Page {idx+1:2d} | Codes: {str(m):30s} | {header[:80]}")

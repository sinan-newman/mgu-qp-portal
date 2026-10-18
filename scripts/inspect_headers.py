import sys
import pypdf

sys.stdout.reconfigure(encoding='utf-8')

pdf_path = r"temp_model\bba_sem1.pdf"
reader = pypdf.PdfReader(pdf_path)

for p_num in [1, 4, 7, 9]:
    print(f"\n==================== Page {p_num} Top Header ====================")
    txt = reader.pages[p_num - 1].extract_text()
    lines = [l.strip() for l in txt.split("\n") if l.strip()][:12]
    for l in lines:
        print("  >", l)

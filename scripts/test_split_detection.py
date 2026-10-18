import sys
import os
import re
import urllib.request
import pypdf
import json

sys.stdout.reconfigure(encoding='utf-8')

# Load all known course codes from papers.json
with open("data/papers.json", "r", encoding="utf-8") as f:
    papers = json.load(f)

known_courses = {}
for p in papers:
    code = (p.get("course_code") or "").strip().upper()
    if code:
        known_courses[code] = p

print(f"Loaded {len(known_courses)} distinct known courses from database.")

# Test URLs
test_urls = [
    ("BBA_Sem1", "https://www.mgu.ac.in/uploads/2024/11/BBA-1.pdf"),
    ("BCA_Sem1", "https://www.mgu.ac.in/uploads/2024/11/BCA-THEORY-COMBINED.pdf"),
    ("Arabic_Sem1", "https://www.mgu.ac.in/uploads/2024/11/Arabic.pdf"),
    ("Biotech_Sem1", "https://www.mgu.ac.in/uploads/2024/11/Biotechnology.pdf"),
    ("Economics_Sem1", "https://www.mgu.ac.in/uploads/2024/11/Economics.pdf")
]

os.makedirs("temp_test_split", exist_ok=True)
os.makedirs("temp_test_output", exist_ok=True)

for name, u in test_urls:
    raw_pdf = os.path.join("temp_test_split", f"{name}.pdf")
    if not os.path.exists(raw_pdf):
        print(f"\nDownloading {name}...")
        req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as resp, open(raw_pdf, "wb") as f:
            f.write(resp.read())
    
    reader = pypdf.PdfReader(raw_pdf)
    num_pages = len(reader.pages)
    print(f"\n==========================================")
    print(f"Inspecting {name} ({num_pages} pages)")
    print(f"==========================================")
    
    # Detect start pages of individual papers
    paper_starts = []  # list of (start_page_idx, detected_code, detected_title)
    
    for idx, page in enumerate(reader.pages):
        txt = page.extract_text() or ""
        txt_upper = txt.upper()
        
        # Check if page is the beginning of a question paper
        is_header = any(k in txt_upper for k in [
            "MAHATMA GANDHI UNIVERSITY", 
            "MAXIMUM MARKS", 
            "MAX. MARKS", 
            "TIME : 3", 
            "TIME: 3", 
            "TIME: 2", 
            "TIME: 1.5", 
            "TIME: 1 . 30", 
            "DURATION:", 
            "MODEL QUESTION PAPER"
        ])
        
        # Find potential course codes on this page
        codes = re.findall(r'\b(MG[1-8][A-Z0-9_]{5,14})\b', txt)
        # Normalize codes (remove trailing hyphen or underscore)
        codes = [c.rstrip('_-') for c in codes]
        
        # Check against known courses
        matched_known = [c for c in codes if c in known_courses]
        
        # If is_header and (has code or idx == 0)
        if (is_header or idx == 0) and (matched_known or codes or is_header):
            # If the previous start was on the same page, don't duplicate
            if not paper_starts or paper_starts[-1][0] != idx:
                best_code = matched_known[0] if matched_known else (codes[0] if codes else None)
                
                # Try to extract title line from top 5 lines
                top_lines = [l.strip() for l in txt.split("\n") if l.strip()][:8]
                title = "Unknown"
                for l in top_lines:
                    if best_code and best_code in l:
                        title = l.replace(best_code, "").replace("–", "").replace("-", "").strip()
                        break
                    elif any(w in l.upper() for w in ["ACCOUNTING", "MANAGEMENT", "MATHEMATICS", "PROGRAMMING", "ECONOMICS", "HISTORY"]):
                        title = l.strip()
                        break
                
                paper_starts.append((idx, best_code, title))
    
    # Calculate page ranges
    split_items = []
    for i, (start_idx, code, title) in enumerate(paper_starts):
        end_idx = paper_starts[i+1][0] if i+1 < len(paper_starts) else num_pages
        split_items.append({
            "code": code,
            "title": title,
            "start_page": start_idx + 1,
            "end_page": end_idx,
            "page_count": end_idx - start_idx
        })
    
    print(f"Detected {len(split_items)} question papers:")
    for item in split_items:
        match_info = f"MATCHED: {known_courses[item['code']]['title']}" if item['code'] in known_courses else "UNMATCHED"
        print(f"  Pages {item['start_page']:2d}-{item['end_page']:2d} ({item['page_count']} pp) | Code: {str(item['code']):15s} | {match_info} ({item['title'][:40]})")

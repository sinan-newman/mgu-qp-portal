import os
import glob
import pypdf
import re
import json

files = glob.glob(r"C:\Users\Navirex\.gemini\antigravity\scratch\mgu-qp-storage\pdf\MODEL_SEM*")
print(f"Analyzing {len(files)} MODEL_SEM files...")

results = []
for f in files:
    try:
        reader = pypdf.PdfReader(f)
        text = ""
        for p in reader.pages:
            text += p.extract_text() or ""
        
        # Course code pattern
        # Look for MG..., 24MG..., or course code patterns
        m = re.search(r'(?:24)?(MG[1-8][A-Z0-9_]{5,14})', text)
        code = m.group(1) if m else None
        
        # Look for course title
        title_m = re.search(r'Course\s*:\s*(?:24)?(?:MG[1-8][A-Z0-9_]{5,14})?\s*[-–:]\s*([^\n\r]+)', text, re.IGNORECASE)
        title = title_m.group(1).strip() if title_m else None
        
        # Check if practical
        is_practical = bool(re.search(r'practical|experiment|conduct one|demonstrate', text, re.IGNORECASE))
        
        results.append({
            'filename': os.path.basename(f),
            'pages': len(reader.pages),
            'detected_code': code,
            'detected_title': title,
            'is_practical': is_practical,
            'snippet': " ".join(text[:250].split())
        })
    except Exception as e:
        print(f"Error {f}: {e}")

detected_count = len([r for r in results if r['detected_code']])
print(f"\nDetected code in {detected_count}/{len(results)} files!")

for r in results:
    if r['detected_code']:
        print(f"  [AUTO-DETECT] {r['filename']} -> {r['detected_code']} ({'Practical' if r['is_practical'] else 'Theory'}, {r['pages']} pgs)")
    else:
        print(f"  [NEEDS ADMIN] {r['filename']} -> {r['pages']} pgs | {r['snippet'][:100]}")

with open('data/untagged_model_analysis.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2)

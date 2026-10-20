import os
import sys
import re
import json
import pypdf

sys.stdout.reconfigure(encoding='utf-8')

folder = r'c:\Users\Navirex\Desktop\Semester5'
pdf_files = sorted([f for f in os.listdir(folder) if f.lower().endswith('.pdf')])

with open('data/departments.json', 'r', encoding='utf-8') as f:
    depts = json.load(f)
dept_dict = {d['code']: d['name'] for d in depts}
dept_names = set([d['name'].strip().lower() for d in depts] + [d['code'].strip().lower() for d in depts])

with open('data/papers.json', 'r', encoding='utf-8') as f:
    catalog = json.load(f)
catalog_by_code = {p['course_code'].strip().upper(): p for p in catalog if p.get('course_code')}

def clean_spaced_text(text):
    # Fix 'C ourse C ode : M G 5 D S E B O T 3 0 3'
    return re.sub(r'(?<=\b[A-Za-z0-9])\s+(?=[A-Za-z0-9]\b)', '', text)

def is_department_name(title):
    if not title:
        return True
    t = title.strip().lower()
    return t in dept_names or t in [d.lower() for d in dept_dict.keys()]

for fname in pdf_files:
    fpath = os.path.join(folder, fname)
    reader = pypdf.PdfReader(fpath)
    print(f'==============================================')
    print(f'FILE: {fname} ({len(reader.pages)} pages)')
    print(f'==============================================')
    for p_idx, page in enumerate(reader.pages):
        text = page.extract_text() or ''
        clean = ' '.join(text.split())
        
        is_start = any(k in clean.upper() for k in [
            'MGU-UGP (HONOURS)', 'MGU-UGP(HONOURS)', 'FIFTH SEMESTER', 'SEMESTER V',
            'MODEL QUESTION PAPER', 'MAXIMUM MARKS', 'MAX. MARKS', 'TOTAL MARKS', 'DURATION:'
        ])
        
        t_for_code = clean
        if 'C ourse' in t_for_code or 'M G ' in t_for_code:
            t_for_code = clean_spaced_text(clean)
            
        found_codes = re.findall(r'(?:MG[1-8]?(?:DSC|DSE|SEC|MDC|VAC|CCR|AEC|MDE|SDC|MPC|HON|MIN|MDE)[A-Z]{2,5}(?:A\d{2}|\d{3}))', t_for_code, re.IGNORECASE)
        found_codes_alt = re.findall(r'\b(MG[1-8][A-Z]{3,8}(?:A\d{2}|\d{3}))\b', t_for_code, re.IGNORECASE)
        
        all_c = list(dict.fromkeys([c.upper() for c in found_codes + found_codes_alt]))
        # Normalize code semester if 'MGDSEPSY300' or 'MG1DSCENG301'
        norm_codes = []
        for c in all_c:
            if c.startswith('MG') and not c.startswith('MG5') and 'FIFTH SEMESTER' in clean.upper():
                if c.startswith('MGDSE') or c.startswith('MGDSC') or c.startswith('MGSEC'):
                    c = 'MG5' + c[2:]
                elif re.match(r'^MG[1-46-8]', c):
                    c = 'MG5' + c[3:]
            norm_codes.append(c)
        norm_codes = list(dict.fromkeys(norm_codes))

        title = ''
        m_title = re.search(r'(?:COURSE TITLE|TITLE OF (?:THE )?COURSE|PAPER NAME)\s*[:\-–—\s]+([A-Za-z0-9\s,&\'\/-]{3,80})', clean, re.IGNORECASE)
        if m_title:
            title = m_title.group(1).strip()
        else:
            for c in norm_codes:
                esc = re.escape(c)
                m_hyphen = re.search(esc + r'\s*[:\-–—]+\s*([A-Za-z0-9\s,&\'\/-]{3,80})', clean, re.IGNORECASE)
                if m_hyphen:
                    title = m_hyphen.group(1).strip()
                    break

        if norm_codes or is_start:
            print(f'  P.{p_idx+1:2d}: codes={norm_codes} | title="{title[:40]}" | start={is_start}')

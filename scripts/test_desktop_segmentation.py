import os
import sys
import pypdf
import re
import json

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

def collapse_spaced_words(text):
    return re.sub(r'(?<=\b[A-Za-z0-9])\s+(?=[A-Za-z0-9]\b)', '', text)

def extract_page_info(page_text, sem_default=5):
    if not page_text:
        return {'is_start': False, 'codes': [], 'title': '', 'is_practical': False}
    clean = ' '.join(page_text.split())
    collapsed = collapse_spaced_words(clean)
    upper = clean.upper()
    collapsed_upper = collapsed.upper()
    
    # 1. Course Code Detection
    raw_codes = []
    for txt in [clean, collapsed]:
        m_explicit = re.findall(r'(?:COURSE\s*(?:CODE|NO\.?)|PAPER\s*CODE)\s*[:\-–\s]+\s*([A-Z0-9_\-,\s]{6,60})', txt, re.IGNORECASE)
        for m in m_explicit:
            parts = re.split(r'[,;\/]+', m)
            for p in parts:
                p_clean = re.sub(r'\s+', '', p).upper()
                if p_clean: raw_codes.append(p_clean)
                
    for txt in [clean, collapsed]:
        pat = r'(?:MG\s*[1-8Il]?\s*(?:DSC|DSE|SEC|MDC|VAC|CCR|DEC|MDE|SDC|MPC|HON|MIN)\s*[A-Z]{2,5}\s*(?:A\d{2}|\d{3}))'
        for m in re.findall(pat, txt, re.IGNORECASE):
            raw_codes.append(re.sub(r'\s+', '', m).upper())
        for m in re.findall(r'\b(MG[1-8][A-Z]{3,8}(?:A\d{2}|\d{3}))\b', txt, re.IGNORECASE):
            raw_codes.append(re.sub(r'\s+', '', m).upper())
            
    valid_codes = []
    for c in raw_codes:
        c = c.replace('MGS5', 'MG5').replace('DEC', 'DSE')
        if c.startswith('MGDSE') or c.startswith('MGDSC') or c.startswith('MGSEC'):
            c = 'MG5' + c[2:]
        elif re.match(r'^MG[1-46-8]', c) and ('FIFTH' in upper or sem_default == 5):
            c = 'MG5' + c[3:]
        if re.search(r'\d$', c) and len(c) >= 8 and c.startswith('MG'):
            if c not in valid_codes:
                valid_codes.append(c)

    # 2. Check if page is Exam Start
    hasUniv = any(k in upper or k in collapsed_upper for k in ['MAHATMA GANDHI UNIVERSITY', 'MGU-UGP', 'MGU UGP', 'M.G. UNIVERSITY'])
    hasExam = any(k in upper or k in collapsed_upper for k in ['EXAMINATION', 'EXAM', 'MODEL QUESTION PAPER', 'MODEL QP', 'MODEL EXAMINATION'])
    hasMarks = any(k in upper or k in collapsed_upper for k in ['MAXIMUM MARKS', 'MAX. MARKS', 'TOTAL MARKS', 'MARKS:'])
    hasTime = any(k in upper or k in collapsed_upper for k in ['TIME:', 'DURATION:', 'TIME :', 'DURATION :'])
    hasSem = any(k in upper or k in collapsed_upper for k in ['SEMESTER', 'FIFTH SEMESTER', 'SEMESTER V', 'V SEMESTER'])
    
    is_start = (hasUniv and hasExam and (hasTime or hasMarks or hasSem)) or (len(valid_codes) > 0 and (hasTime or hasMarks or hasExam))
    
    # 3. Practical vs Theory
    is_practical = bool(re.search(r'(?:PRACTICAL\s*(?:EXAMINATION|MODEL|QP|EXAM)|EXPERIMENT\s*NO|CONDUCT\s*ONE\s*EXPERIMENT|LAB\s*EXAMINATION)', upper))
    
    # 4. Title Extraction
    title = ''
    for txt in [clean, collapsed]:
        m_title = re.search(r'(?:COURSE\s*TITLE|TITLE\s*OF\s*(?:THE\s*)?COURSE|PAPER\s*NAME)\s*[:\-–—\s]+([A-Za-z0-9\s,&\'\/-]{3,90})', txt, re.IGNORECASE)
        if m_title:
            cand = m_title.group(1).strip()
            cand = re.sub(r'\s*(?:Time|Duration|Max|Part|Section|Marks|MGU|Admission).*$', '', cand, flags=re.IGNORECASE).strip()
            if cand and cand.lower() not in dept_names and cand.lower() not in [d.lower() for d in dept_dict.keys()]:
                title = cand
                break
                
    if not title:
        for c in valid_codes:
            esc = re.escape(c)
            for txt in [clean, collapsed]:
                m_hyphen = re.search(esc + r'\s*[:\-–—]+\s*([A-Za-z0-9\s,&\'\/-]{3,90})', txt, re.IGNORECASE)
                if m_hyphen:
                    cand = m_hyphen.group(1).strip()
                    cand = re.sub(r'\s*(?:Time|Duration|Max|Part|Section|Marks|MGU|Admission).*$', '', cand, flags=re.IGNORECASE).strip()
                    if cand and cand.lower() not in dept_names and cand.lower() not in [d.lower() for d in dept_dict.keys()]:
                        title = cand
                        break
            if title: break
            
    matched_cat = None
    for c in valid_codes:
        if c in catalog_by_code:
            matched_cat = catalog_by_code[c]
            break
            
    if matched_cat and matched_cat.get('title'):
        cat_t = matched_cat['title'].strip()
        if cat_t.lower() not in dept_names and cat_t.lower() not in [d.lower() for d in dept_dict.keys()]:
            if not title or title.isupper() or len(title) < 5 or title.lower() in dept_names:
                title = cat_t
                
    if not title and valid_codes:
        title = f'Course {valid_codes[0]}'
        
    return {
        'is_start': is_start,
        'codes': valid_codes,
        'title': title,
        'is_practical': is_practical,
        'matched_cat': matched_cat
    }

total_detected_papers = 0
all_extracted = []

for fname in pdf_files:
    fpath = os.path.join(folder, fname)
    reader = pypdf.PdfReader(fpath)
    num_pages = len(reader.pages)
    
    page_infos = [extract_page_info(p.extract_text() or '') for p in reader.pages]
    
    segments = []
    cur_start = 0
    cur_codes = page_infos[0]['codes']
    
    for i in range(1, num_pages):
        pi = page_infos[i]
        c_codes = pi['codes']
        is_s = pi['is_start']
        elapsed = i - cur_start
        
        is_new = False
        if c_codes and cur_codes and (c_codes[0] != cur_codes[0]) and elapsed >= 1:
            is_new = True
        elif is_s and elapsed >= 1:
            is_new = True
        elif False and elapsed >= 15:
            is_new = True
            
        if is_new:
            segments.append((cur_start + 1, i, cur_codes, page_infos[cur_start]['title'], page_infos[cur_start]['is_practical']))
            cur_start = i
            cur_codes = c_codes
        else:
            if not cur_codes and c_codes:
                cur_codes = c_codes
                
    segments.append((cur_start + 1, num_pages, cur_codes, page_infos[cur_start]['title'], page_infos[cur_start]['is_practical']))
    
    print(f'=== {fname}: {len(segments)} papers ===')
    for s_start, s_end, scodes, stitle, is_prac in segments:
        total_detected_papers += 1
        ptype = 'PRACTICAL' if is_prac else 'THEORY'
        print(f'   P.{s_start:2d}-{s_end:2d} ({s_end-s_start+1}p) | Codes={scodes} | Type={ptype} | Title="{stitle}"')
        all_extracted.append({
            'file': fname,
            'start': s_start,
            'end': s_end,
            'codes': scodes,
            'title': stitle,
            'type': ptype
        })

print(f'\nTOTAL MODEL PAPERS DETECTED ACROSS ALL 16 FILES: {total_detected_papers}')

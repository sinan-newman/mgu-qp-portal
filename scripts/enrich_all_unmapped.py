import json
import urllib.request
import pypdf
import io
import re
import sys
import time
import os
import concurrent.futures
from parse_user_csv import code_to_entry

sys.stdout.reconfigure(encoding='utf-8')

COURSE_TYPE_NAMES = {
    'DSC': 'Discipline Specific Core',
    'DSE': 'Discipline Specific Elective',
    'SEC': 'Skill Enhancement Course',
    'VAC': 'Value Added Course',
    'MDC': 'Multi-Disciplinary Course',
    'AEC': 'Ability Enhancement Course',
    'CCR': 'Core Course',
    'MDE': 'Multidisciplinary Elective',
    'MIN': 'Minor Course',
    'SDC': 'Skill Development Course'
}

TYPO_FIXES = {
    r'\bHist\s+Ory\b': 'History',
    r'\bDair\s+Y\b': 'Dairy',
    r'\bRelev\s+Ant\b': 'Relevant',
    r'\bMa\s+Terial\b': 'Material',
    r'\bDa\s+Ta\b': 'Data',
    r'\bTheor\s+Y\b': 'Theory',
    r'\bRa\s+Tionalism\b': 'Rationalism',
    r'\bKhandaka\s+Vya\b': 'Khandakavya',
    r'\bBhaga\s+Vad\b': 'Bhagavad',
    r'\bThaddhit\s+A\b': 'Thaddhita',
    r'\bT\s+Ourism\b': 'Tourism',
    r'\bTechnolog\s+Y\b': 'Technology',
    r'\bDigit\s+Al\b': 'Digital',
    r'\bMa\s+Thematics\b': 'Mathematics',
    r'\bObser\s+Vational\b': 'Observational',
    r'\bNov\s+Alsahithyam\b': 'Novalsahithyam',
}

def clean_title(title):
    if not title:
        return ''
    title = re.sub(r'\(202\d\s+ADMISSION(?:\s+ONWARDS|\s+ONLY)?\)', '', title, flags=re.I)
    title = re.sub(r'Duration:.*', '', title, flags=re.I)
    title = re.sub(r'Maximum Marks:.*', '', title, flags=re.I)
    title = re.sub(r'Time:.*', '', title, flags=re.I)
    title = re.sub(r'(?:Discipline Specific (?:Core|Elective)\s*\([A-Z]+\)\s*[-–—:]*\s*)+', '', title, flags=re.I)
    title = re.sub(r'(?:Value Addition Course\s*\([A-Z]+\)\s*[-–—:]*\s*)+', '', title, flags=re.I)
    title = re.sub(r'(?:Skill Development Components?\s*\([A-Z]+\)\s*[-–—:]*\s*)+', '', title, flags=re.I)
    title = re.sub(r'\bMG[1-8][A-Z0-9]+\b\s*[-–—:]*\s*', '', title, flags=re.I)
    for pat, repl in TYPO_FIXES.items():
        title = re.sub(pat, repl, title, flags=re.I)
    title = re.sub(r'^[\s,–—\-:]*(?:MG[1-8][A-Z0-9]+[\s,–—\-:]*)+', '', title, flags=re.I)
    title = re.sub(r'\s+', ' ', title).strip(' -–—:,')
    
    words = title.split()
    if len(words) >= 4 and len(words) % 2 == 0:
        half = len(words) // 2
        if ' '.join(words[:half]).lower() == ' '.join(words[half:]).lower():
            title = ' '.join(words[:half])

    if title.isupper() or title.islower():
        title = title.title()
    return title

def extract_from_pdf(url):
    data = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = resp.read()
            break
        except Exception:
            time.sleep(1.5)
            
    if not data:
        return None
    
    reader = pypdf.PdfReader(io.BytesIO(data))
    page0 = reader.pages[0]
    
    try:
        text_layout = page0.extract_text(extraction_mode='layout') or ''
    except Exception:
        text_layout = ''
    text_plain = page0.extract_text() or ''
    
    m_code = re.search(r'\b(MG[1-8][A-Z]{3}[A-Z]{2,4}\d+)\b', text_layout) or \
             re.search(r'\b(MG[1-8][A-Z]{3}[A-Z]{2,4}\d+)\b', text_plain)
             
    if not m_code:
        return None
        
    course_code = m_code.group(1)
    
    m_parts = re.match(r'^MG([1-8])([A-Z]{3})([A-Z]{2,4})(\d+)$', course_code)
    sem = int(m_parts.group(1)) if m_parts else 1
    ctype = m_parts.group(2) if m_parts else 'DSC'
    raw_dept = m_parts.group(3) if m_parts else ''
    
    target_text = text_layout if course_code in text_layout else text_plain
    lines = [l.strip() for l in target_text.split('\n') if l.strip()]
    
    idx = -1
    for i, l in enumerate(lines):
        if course_code in l:
            idx = i
            break
            
    title_parts = []
    if idx != -1:
        code_line = lines[idx]
        remainder = code_line[code_line.index(course_code) + len(course_code):].strip()
        remainder = re.sub(r'^[\s\-–—:]+', '', remainder).strip()
        if remainder:
            title_parts.append(remainder)
            
        for next_l in lines[idx+1:idx+6]:
            if re.search(r'\b(202\d|Duration|Maximum Marks|Max Marks|Time:|Marks:|Part\s+[A-Z]|Remember|MAHATMA GANDHI|REGULAR EXAMINATION)\b', next_l, re.I):
                break
            if re.match(r'^(?:\[CO|\d+\.|\(?[a-d]\))', next_l.strip()):
                break
            cleaned = next_l.strip()
            if cleaned:
                title_parts.append(cleaned)
                
    full_title = clean_title(' '.join(title_parts))
    
    return {
        'course_code': course_code,
        'semester': sem,
        'course_type': ctype,
        'course_type_name': COURSE_TYPE_NAMES.get(ctype, ctype),
        'dept_code': raw_dept,
        'title': full_title
    }

def get_dept_info(code, depts):
    code = code.strip().upper()
    
    # Specific override for REM
    if code == 'REM':
        return {
            'parent_dept': 'PHY',
            'parent_dept_name': 'Physics',
            'dept_code': 'REM',
            'dept_name': 'Renewable Energy Management',
            'is_minor': False,
            'minor_name': None
        }

    for d in depts:
        if d['code'].upper() == code:
            return {
                'parent_dept': d['code'],
                'parent_dept_name': d['name'],
                'dept_code': d['code'],
                'dept_name': d['name'],
                'is_minor': False,
                'minor_name': None
            }
        for m in d.get('minors', []):
            if m['code'].upper() == code:
                return {
                    'parent_dept': d['code'],
                    'parent_dept_name': d['name'],
                    'dept_code': m['code'],
                    'dept_name': m['name'],
                    'is_minor': True,
                    'minor_name': m['name']
                }

    if code in code_to_entry:
        entry = code_to_entry[code]
        dept_name = entry['department'].strip()
        is_minor = entry['is_minor']
        prog_name = entry['programme'].strip()
        
        matched_dept = next((d for d in depts if d['name'].strip().lower() == dept_name.lower()), None)
        parent_code = matched_dept['code'] if matched_dept else code
        parent_name = matched_dept['name'] if matched_dept else dept_name
        
        return {
            'parent_dept': parent_code,
            'parent_dept_name': parent_name,
            'dept_code': code,
            'dept_name': prog_name,
            'is_minor': is_minor,
            'minor_name': prog_name if is_minor else None
        }

    return {
        'parent_dept': code,
        'parent_dept_name': code,
        'dept_code': code,
        'dept_name': code,
        'is_minor': False,
        'minor_name': None
    }

def process_single(p, depts):
    url = p.get('qp_url')
    if not url:
        return None, p.get('id'), "No URL"
    try:
        res = extract_from_pdf(url)
        if not res:
            return None, p.get('id'), "No course code found"
        dept_info = get_dept_info(res['dept_code'], depts)
        return (res, dept_info), p.get('id'), "OK"
    except Exception as e:
        return None, p.get('id'), str(e)

def main():
    with open('data/papers.json', 'r', encoding='utf-8') as f:
        papers = json.load(f)
    with open('data/departments.json', 'r', encoding='utf-8') as f:
        depts = json.load(f)

    # Filter out empty placeholder records without files
    valid_papers = [p for p in papers if p.get('has_files') or p.get('qp_url') or p.get('scheme_url')]
    removed = len(papers) - len(valid_papers)
    print(f"Removed {removed} empty placeholder records without files.")

    unmapped = [
        p for p in valid_papers 
        if not p.get('course_code') or p.get('dept_code') == 'GEN' or not p.get('dept_code') or p.get('title') == p.get('qp_code')
    ]
    print(f"Total unmapped papers needing enrichment: {len(unmapped)}")

    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_map = {executor.submit(process_single, p, depts): p for p in unmapped}
        for future in concurrent.futures.as_completed(future_map):
            p = future_map[future]
            data, pid, status = future.result()
            if data:
                res, dept_info = data
                results[pid] = (res, dept_info)
                print(f"Enriched: {pid} -> {res['course_code']} | {res['title']} ({dept_info['parent_dept_name']})")
            else:
                print(f"Failed: {pid} -> {status}")

    print(f"\nSuccessfully enriched: {len(results)} / {len(unmapped)}")

    # Apply updates
    updated = 0
    for p in valid_papers:
        if p['id'] in results:
            res, dept_info = results[p['id']]
            p['course_code'] = res['course_code']
            p['title'] = res['title']
            p['raw_header'] = f"{p.get('qp_code', '')} - {res['course_code']} - {res['title']}"
            p['course_type'] = res['course_type']
            p['course_type_name'] = res['course_type_name']
            p['semester'] = res['semester']
            p['dept_code'] = dept_info['dept_code']
            p['dept_name'] = dept_info['dept_name']
            p['parent_dept'] = dept_info['parent_dept']
            p['parent_dept_name'] = dept_info['parent_dept_name']
            p['is_minor'] = dept_info['is_minor']
            p['minor_name'] = dept_info['minor_name']
            updated += 1

    # Save to data/ and public/data/
    for folder in ['data', 'public/data']:
        with open(os.path.join(folder, 'papers.json'), 'w', encoding='utf-8') as f:
            json.dump(valid_papers, f, indent=2, ensure_ascii=False)

    print(f"Updated {updated} papers. Saved to data/papers.json and public/data/papers.json!")

if __name__ == '__main__':
    main()

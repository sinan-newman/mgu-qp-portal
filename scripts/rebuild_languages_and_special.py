import os
import sys
import json
import glob
import re
import pdfplumber

sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = "data/ai_notes"
PAPERS_JSON = "data/papers.json"
PDF_STORAGE_DIR = r"C:\Users\Navirex\.gemini\antigravity\scratch\mgu-qp-storage\pdf"

CID_MAP = {
    3105: '∂', 3087: 'θ', 3095: 'π', 2878: '+', 2879: '-', 2883: '/',
    2885: '=', 2888: '<', 2890: '>', 3429: '[', 3433: ']',
    4672: '(', 4673: ')', 3021: 'T', 3045: 'r', 3051: 'x', 3052: 'y', 3053: 'z',
    3118: '^2', 3119: '^3', 3120: '^4', 3121: '^5',
    2943: 'c', 2946: 'f', 2948: 'h', 2950: 'j', 2951: 'k', 2952: 'l', 2954: 'n',
    2956: 'p', 2958: 'r', 2959: 's', 2960: 't', 2961: 'u', 2962: 'v', 2963: 'w',
    2964: 'x', 2965: 'y', 2966: 'z'
}

def decode_cid(text):
    if not text:
        return ""
    def rep(m):
        code = int(m.group(1))
        if code in CID_MAP:
            return CID_MAP[code]
        if 2868 <= code <= 2877:
            return str(code - 2868)
        if 2931 <= code <= 2956:
            return chr(ord('a') + (code - 2931))
        return f"(cid:{code})"
    return re.sub(r'\(cid:(\d+)\)', rep, text)

def clean_tags(s):
    if not s:
        return ""
    s = s.replace('\x00', '').replace('\ufffd', '—')
    s = re.sub(r'\[\s*\d+\s*[xX*×]\s*\d+\s*=\s*\d+\s*\]', '', s)
    s = re.sub(r'\(\s*\d+\s*[xX*×]\s*\d+\s*=\s*\d+\s*\)', '', s)
    s = re.sub(r'\[\s*(?:Understand|Remember|Apply|Analyse|Analyze|Evaluate|Create|Skill|Knowledge|Application|Comprehension)[^\]]*\]', '', s, flags=re.I)
    s = re.sub(r'\[\s*T\s*:\s*[^\]]+\]', '', s, flags=re.I)
    s = re.sub(r'\[\s*CO[\s\d,:A-Za-z\-]+\]?', '', s, flags=re.I)
    s = re.sub(r'\[\s*Learning\s+Domain\s*\]', '', s, flags=re.I)
    s = re.sub(r'\[\s*CO\s*No\(s\)\s*\]', '', s, flags=re.I)
    s = re.sub(r'\[\s*[UKAAEnCSIAPap\d\s,/]+\s*\]', '', s)
    s = re.sub(r'[\s/,]+\s*\[[^\]]*\]?', '', s)
    s = re.sub(r'[\s/,:-]+$', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def format_stage_marks(text):
    if not text:
        return ""
    m_re = re.compile(r'[\(\[]?\s*(\d+(?:\.\d+)?)\s*(?:Marks?|M)\s*[\)\]]?', re.I)
    def repl(m):
        return f'<span class="font-bold text-emerald-700 dark:text-emerald-400">({m.group(1)} mark)</span>'
    return m_re.sub(repl, text)

def parse_qp_pdf(pdf_path):
    if not pdf_path or not os.path.exists(pdf_path):
        return []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            raw = '\n'.join(p.extract_text(layout=False) or '' for p in pdf.pages)
    except Exception:
        return []

    decoded = decode_cid(raw)
    lines = [l.strip() for l in decoded.splitlines() if l.strip()]

    sections = []
    cur_sec = {'id': 'PART_A', 'title': 'Part A — Short Answer Questions', 'marks': 2, 'questions': {}}
    cur_num = None

    q_re = re.compile(r'^(?:Q\.?\s*)?(\d{1,2})\s*[\.:\)\-]\s*(.*)', re.I)
    q_re2 = re.compile(r'^(\d{1,2})\s+([^\d\s].*)')
    q_bare = re.compile(r'^(\d{1,2})$')

    skip_headers = [
        "qp code", "reg no", "maximum marks", "duration:", "mahatma gandhi university",
        "remember (k)", "students should attempt", "[learning domain]",
        "multiple choice questions", "short answer type", "short essay", "essay type",
        "end of the question paper", "ശെരിയായ ഉത്തരം", "രചടാ െൂചന്നാ"
    ]

    for l in lines:
        lower = l.lower()
        if any(h in lower for h in skip_headers) and len(l) < 140:
            continue

        if re.search(r'\bpart\s+b\b|\bsection\s+b\b', lower):
            if cur_sec['questions']: sections.append(cur_sec)
            cur_sec = {'id': 'PART_B', 'title': 'Part B — Short Essay Questions', 'marks': 6, 'questions': {}}
            cur_num = None
            continue
        elif re.search(r'\bpart\s+c\b|\bsection\s+c\b', lower):
            if cur_sec['questions']: sections.append(cur_sec)
            cur_sec = {'id': 'PART_C', 'title': 'Part C — Essay Questions', 'marks': 10, 'questions': {}}
            cur_num = None
            continue
        elif re.search(r'\bpart\s+d\b|\bsection\s+d\b', lower):
            if cur_sec['questions']: sections.append(cur_sec)
            cur_sec = {'id': 'PART_D', 'title': 'Part D — Long Essay Questions', 'marks': 10, 'questions': {}}
            cur_num = None
            continue

        if lower.startswith('answer any') or lower.startswith('each question carries'):
            continue
        if re.search(r'^\(\s*\d+\s*[xX*×]\s*\d+\s*=\s*\d+\s*\)', l):
            continue

        bm = q_bare.match(l)
        if bm and 1 <= int(bm.group(1)) <= 45:
            cur_num = int(bm.group(1))
            if cur_num not in cur_sec['questions']: cur_sec['questions'][cur_num] = []
            continue

        qm = q_re.match(l) or q_re2.match(l)
        if qm and 1 <= int(qm.group(1)) <= 45:
            cur_num = int(qm.group(1))
            rest = qm.group(2).strip()
            if cur_num not in cur_sec['questions']: cur_sec['questions'][cur_num] = []
            if rest: cur_sec['questions'][cur_num].append(rest)
            continue

        if cur_num and cur_num in cur_sec['questions']:
            cur_sec['questions'][cur_num].append(l)

    if cur_sec['questions']:
        sections.append(cur_sec)
    return sections

def parse_scheme_pdf(pdf_path):
    if not pdf_path or not os.path.exists(pdf_path):
        return {}
    try:
        with pdfplumber.open(pdf_path) as pdf:
            raw = '\n'.join(p.extract_text(layout=False) or '' for p in pdf.pages)
    except Exception:
        return {}

    decoded = decode_cid(raw)
    lines = [l.strip() for l in decoded.splitlines() if l.strip()]

    skip_headers = [
        "qp code", "reg no:", "maximum marks:", "duration:", "mahatma gandhi university",
        "mgu-ugp", "regular examination", "scheme of valua", "answer any",
        "(2024 admission", "remember (k)", "students should attempt", "[learning domain]"
    ]

    q_re = re.compile(r'^(?:Q\.?\s*)?(\d{1,2})\s*[\.:\)\-]\s*(.*)', re.I)
    q_re2 = re.compile(r'^(\d{1,2})\s+([^\d\s].*)')
    q_bare = re.compile(r'^(\d{1,2})$')
    q_rtl = re.compile(r'^(.*?)\s+[\.:\)\-](\d{1,2})$')

    items = {}
    cur = None

    for l in lines:
        lower = l.lower()
        if any(sh in lower for sh in skip_headers) and len(l) < 140:
            continue
        if lower.startswith("part ") or lower.startswith("each question carries"):
            continue
        if re.search(r'^\(\s*\d+\s*[xX*×]\s*\d+\s*=\s*\d+\s*\)', l):
            continue

        bm = q_bare.match(l)
        if bm and 1 <= int(bm.group(1)) <= 45:
            cur = int(bm.group(1))
            if cur not in items: items[cur] = []
            continue

        qm = q_re.match(l) or q_re2.match(l)
        if qm and 1 <= int(qm.group(1)) <= 45:
            cur = int(qm.group(1))
            rest = qm.group(2).strip()
            if cur not in items: items[cur] = []
            if rest: items[cur].append(rest)
            continue

        rm = q_rtl.match(l)
        if rm and 1 <= int(rm.group(2)) <= 45:
            cur = int(rm.group(2))
            rest = rm.group(1).strip()
            if cur not in items: items[cur] = []
            if rest: items[cur].append(rest)
            continue

        if cur and cur in items:
            items[cur].append(l)

    parsed = {}
    for num, l_list in items.items():
        if not l_list: continue
        first_line = clean_tags(l_list[0])
        is_q = (
            "?" in first_line or
            any(first_line.lower().startswith(w) for w in ["what", "why", "how", "define", "explain", "discuss", "state", "differentiate", "distinguish", "write", "name", "identify", "evaluate", "illustrate", "describe"]) or
            re.search(r'\[[A-Za-z0-9,\s]+\]\s*$', first_line)
        )
        if is_q and len(l_list) > 1:
            q_text = first_line
            ans_lines = l_list[1:]
        else:
            q_text = ""
            ans_lines = l_list

        clean_ans_lines = [clean_tags(al) for al in ans_lines if clean_tags(al)]
        parsed[num] = {
            'question': q_text,
            'solution_lines': clean_ans_lines
        }
    return parsed

def format_solution(scheme_lines, q_text="", marks=2):
    if not scheme_lines:
        return "", ""

    cleaned = []
    for l in scheme_lines:
        cl = clean_tags(l)
        if not cl or any(h in cl.lower() for h in ['scheme of valuation', 'qp code', 'answer any', 'part a', 'part b', 'part c', 'maximum marks']):
            continue
        cl = format_stage_marks(cl)
        cleaned.append(cl)

    if not cleaned:
        return "", ""

    # MCQ detection
    is_mcq_q = bool(re.search(r'\b[a-d]\s*[\)\.]', q_text, re.I)) or marks == 1
    mcq_ans = None
    if is_mcq_q:
        for l in cleaned:
            m = re.search(r'(?:Ans(?:wer)?\.?\s*)?(?:Option\s+)?\b([a-d])\s*[\)\.\-:]\s*(.+)', l, re.I)
            if m:
                mcq_ans = f"Option ({m.group(1).lower()}) {m.group(2).strip()}"
                break
            m2 = re.search(r'^\s*([a-d])\s*[\)\.\-:]\s*(.+)', l, re.I)
            if m2:
                mcq_ans = f"Option ({m2.group(1).lower()}) {m2.group(2).strip()}"
                break

    final_ans = mcq_ans
    if not final_ans:
        cand = cleaned[0] if len(cleaned) <= 2 else cleaned[-1]
        cand = re.sub(r'<[^>]+>', '', cand).strip()
        cand = re.sub(r'\(?\b\d+(?:\.\d+)?\s*Marks?\b\)?', '', cand, flags=re.I).strip()
        cand = re.sub(r'[\s/,:—\.-]+$', '', cand).strip()
        if cand and len(cand) > 1 and not any(k in cand.lower() for k in ['scheme', 'verified', 'valuation', 'rubric']):
            final_ans = cand
        else:
            final_ans = ""

    if mcq_ans and len(cleaned) == 1:
        sol_html = f'<div class="p-2.5 rounded bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 font-medium text-xs sm:text-sm text-slate-800 dark:text-slate-200"><span class="font-bold text-indigo-700 dark:text-indigo-400">Correct Option:</span> {mcq_ans}</div>'
    elif len(cleaned) == 1:
        sol_html = f'<p class="leading-relaxed text-xs sm:text-sm text-slate-800 dark:text-slate-200">{cleaned[0]}</p>'
    else:
        lis = "".join(f"<li class=\"leading-relaxed text-xs sm:text-sm text-slate-700 dark:text-slate-300\">{line}</li>" for line in cleaned)
        sol_html = f"<ul class=\"list-disc list-inside space-y-1.5 my-1 text-xs sm:text-sm text-slate-700 dark:text-slate-300\">{lis}</ul>"

    return sol_html, final_ans

def reprocess_course(course_code, papers_list):
    if not papers_list:
        return None

    # Don't overwrite manually perfected courses unless needed
    sample_p = papers_list[0]
    title = clean_tags(sample_p.get('title', 'Course'))
    dept_name = sample_p.get('dept_name', 'General')
    sem = sample_p.get('semester', 1)
    course_type = sample_p.get('course_type', 'DSC')
    max_marks = sample_p.get('max_marks', 70)

    course_papers = []
    flat_questions = []
    total_solved = 0
    global_q_idx = 1

    for p_idx, p_data in enumerate(papers_list):
        exam_name = p_data.get('exam_name', f'EXAMINATION PAPER {p_idx+1}')
        paper_title = f"EXAMINATION PAPER {p_idx+1}: {exam_name.upper()}"

        sch_url = p_data.get('scheme_url') or p_data.get('scheme_path') or ''
        qp_url = p_data.get('qp_url') or p_data.get('pdf_path') or ''

        sch_fn = os.path.basename(sch_url) if sch_url else ''
        qp_fn = os.path.basename(qp_url) if qp_url else ''

        sch_path = os.path.join(PDF_STORAGE_DIR, sch_fn) if sch_fn else ''
        qp_path = os.path.join(PDF_STORAGE_DIR, qp_fn) if qp_fn else ''

        scheme_items = parse_scheme_pdf(sch_path)
        qp_sections = parse_qp_pdf(qp_path)

        paper_sections = []

        if qp_sections:
            for sec in qp_sections:
                sec_id = sec['id']
                sec_title = sec['title']
                sec_marks = 2 if sec_id == 'PART_A' else (6 if sec_id == 'PART_B' else 10)
                sec_qs = []

                sorted_nums = sorted(sec['questions'].keys())
                for q_num in sorted_nums:
                    if sec_id == 'PART_A' and q_num > 15: continue
                    if sec_id == 'PART_B' and (q_num < 5 or q_num > 25): continue
                    if sec_id in ('PART_C', 'PART_D') and q_num < 12: continue

                    raw_lines = sec['questions'][q_num]
                    q_text = clean_tags(" ".join(raw_lines))
                    if not q_text or len(q_text) < 3: continue

                    sol_html = ""
                    final_ans = ""

                    if q_num in scheme_items:
                        s_data = scheme_items[q_num]
                        sol_html, final_ans = format_solution(s_data['solution_lines'], q_text, sec_marks)

                    if sol_html:
                        total_solved += 1

                    q_obj = {
                        "id": f"P{p_idx+1}_Q{q_num}",
                        "number": q_num,
                        "global_number": global_q_idx,
                        "part": sec_id,
                        "marks": sec_marks,
                        "question": q_text,
                        "solution_html": sol_html,
                        "final_answer": final_ans,
                        "paper_id": f"paper_{p_idx+1}",
                        "has_official_scheme": bool(q_num in scheme_items)
                    }
                    sec_qs.append(q_obj)
                    flat_questions.append(q_obj)
                    global_q_idx += 1

                if sec_qs:
                    paper_sections.append({
                        "section_id": sec_id,
                        "section_title": sec_title,
                        "marks_per_question": sec_marks,
                        "questions": sec_qs
                    })
        elif scheme_items:
            sec_a, sec_b, sec_c = [], [], []
            for q_num in sorted(scheme_items.keys()):
                s_data = scheme_items[q_num]
                q_text = s_data['question'] or f"Question {q_num}"
                marks = 2 if q_num <= 10 else (6 if q_num <= 18 else 10)
                sec_id = "PART_A" if q_num <= 10 else ("PART_B" if q_num <= 18 else "PART_C")
                sol_html, final_ans = format_solution(s_data['solution_lines'], q_text, marks)

                if sol_html: total_solved += 1

                q_obj = {
                    "id": f"P{p_idx+1}_Q{q_num}",
                    "number": q_num,
                    "global_number": global_q_idx,
                    "part": sec_id,
                    "marks": marks,
                    "question": q_text,
                    "solution_html": sol_html,
                    "final_answer": final_ans,
                    "paper_id": f"paper_{p_idx+1}",
                    "has_official_scheme": True
                }
                if sec_id == "PART_A": sec_a.append(q_obj)
                elif sec_id == "PART_B": sec_b.append(q_obj)
                else: sec_c.append(q_obj)

                flat_questions.append(q_obj)
                global_q_idx += 1

            if sec_a: paper_sections.append({"section_id": "PART_A", "section_title": "Part A — Short Answer Questions", "marks_per_question": 2, "questions": sec_a})
            if sec_b: paper_sections.append({"section_id": "PART_B", "section_title": "Part B — Short Essay Questions", "marks_per_question": 6, "questions": sec_b})
            if sec_c: paper_sections.append({"section_id": "PART_C", "section_title": "Part C — Essay Questions", "marks_per_question": 10, "questions": sec_c})

        if paper_sections:
            course_papers.append({
                "paper_id": f"paper_{p_idx+1}",
                "paper_title": paper_title,
                "sections": paper_sections
            })

    if not course_papers:
        return None

    course_doc = {
        "course_code": course_code,
        "title": title,
        "dept_name": dept_name,
        "semester": sem,
        "course_type": course_type,
        "max_marks": max_marks,
        "total_questions": len(flat_questions),
        "total_solved": total_solved,
        "repeating_skipped": 0,
        "sources_used": [p.get('exam_name') for p in papers_list if p.get('exam_name')],
        "has_official_scheme": any(p.get('has_scheme') for p in papers_list),
        "syllabus_url": f"https://syllabusservice.mgu.ac.in/syllabus/{course_code}.pdf",
        "papers": course_papers,
        "questions": flat_questions
    }

    out_file = os.path.join(DATA_DIR, f"{course_code}.json")
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(course_doc, f, ensure_ascii=False, indent=2)

    pub_file = os.path.join("public/data/ai_notes", f"{course_code}.json")
    with open(pub_file, 'w', encoding='utf-8') as f:
        json.dump(course_doc, f, ensure_ascii=False, indent=2)

    return course_code, len(flat_questions), total_solved

def main():
    print("Loading papers.json...")
    papers = json.load(open(PAPERS_JSON, 'r', encoding='utf-8'))
    course_map = {}
    for p in papers:
        cc = p.get('course_code')
        if cc:
            if cc not in course_map: course_map[cc] = []
            course_map[cc].append(p)

    target_depts = {'MAL', 'HIN', 'TAM', 'ARB', 'SAN', 'FRE', 'GER', 'LSC', 'LST', 'JMC', 'PJM'}
    special_codes = {'MG1CCRBBA103', 'MG2CCRBBA101', 'MG2CCRBBA102', 'MG3CCRBBA202', 'MG3DSCGEO201', 'MG3SECBBA200'}

    targets = []
    for cc, plist in course_map.items():
        if cc == 'MG2DSCMAT100':
            continue # Preserve master manual
        dept = plist[0].get('dept_code', '')
        if dept in target_depts or cc in special_codes:
            targets.append((cc, plist))

    print(f"Targeting {len(targets)} language and special courses for enhanced extraction...")
    success = 0
    for idx, (cc, plist) in enumerate(targets, 1):
        res = reprocess_course(cc, plist)
        if res:
            success += 1
            if idx % 20 == 0 or idx == len(targets):
                print(f"[{idx}/{len(targets)}] Processed {res[0]}: {res[1]} Qs ({res[2]} solved)")

    print(f"Completed enhanced extraction for {success} courses!")

if __name__ == '__main__':
    main()

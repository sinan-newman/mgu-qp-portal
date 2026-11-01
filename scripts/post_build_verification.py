import os
import sys
import glob
import json
import re
import time

sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = "data/ai_notes"
PUBLIC_DIR = "public/data/ai_notes"

def clean_text_thoroughly(s):
    if not s: return ""
    s = s.replace('\x00', '').replace('\ufffd', '—')
    # Strip marks rubrics
    s = re.sub(r'\[\s*\d+\s*[xX*×]\s*\d+\s*=\s*\d+\s*\]', '', s)
    s = re.sub(r'\(\s*\d+\s*[xX*×]\s*\d+\s*=\s*\d+\s*\)', '', s)
    # Strip Bloom's terms
    s = re.sub(r'[\(\[]\s*(?:Understand|Remember|Apply|Analyse|Analyze|Evaluate|Create|Skill|Knowledge|Application|Comprehension)[^\]\)]*[\)\]]?', '', s, flags=re.I)
    s = re.sub(r'[\(\[]\s*T\s*:\s*[^\]\)]+[\)\]]?', '', s, flags=re.I)
    # Strip CO tags in both () and []
    s = re.sub(r'[\(\[]\s*CO[\s\d,:A-Za-z\-]+[\)\]]?', '', s, flags=re.I)
    s = re.sub(r'[\(\[]\s*Learning\s+Domain\s*[\)\]]?', '', s, flags=re.I)
    s = re.sub(r'[\(\[]\s*CO\s*No\(s\)\s*[\)\]]?', '', s, flags=re.I)
    # Strip standalone bloom/CO tags like [K], [U], [1], [2], (1), (2), [K] / [CO1]
    s = re.sub(r'[\(\[]\s*[UKAAEnCSIAPap\d\s,/]+\s*[\)\]]', '', s)
    s = re.sub(r'[\s/,]+\s*\[[^\]]*\]?', '', s)
    s = re.sub(r'[\s/,:-]+$', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def fix_title(t):
    if not t: return ""
    t = t.replace('\ufffd', '—').replace('\x00', '')
    t = re.sub(r'Part A\s*[\ufffd\?—\-–]\s*', 'Part A — ', t)
    t = re.sub(r'Part B\s*[\ufffd\?—\-–]\s*', 'Part B — ', t)
    t = re.sub(r'Part C\s*[\ufffd\?—\-–]\s*', 'Part C — ', t)
    t = re.sub(r'Part D\s*[\ufffd\?—\-–]\s*', 'Part D — ', t)
    return t

def sanitize_course_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            d = json.load(f)

        changed = False

        # Clean course metadata
        title = clean_text_thoroughly(d.get('title', ''))
        if title != d.get('title'):
            d['title'] = title
            changed = True

        # Check papers
        papers = d.get('papers', [])
        for p in papers:
            pt = fix_title(p.get('paper_title', ''))
            if pt != p.get('paper_title'):
                p['paper_title'] = pt
                changed = True

            for s in p.get('sections', []):
                st = fix_title(s.get('section_title', ''))
                if st != s.get('section_title'):
                    s['section_title'] = st
                    changed = True

                for q in s.get('questions', []):
                    old_q = q.get('question', '')
                    new_q = clean_text_thoroughly(old_q)
                    if new_q != old_q:
                        q['question'] = new_q
                        changed = True

                    sol = q.get('solution_html', '')
                    if sol:
                        if any(k in sol for k in ['Official Valuation Rubric:', 'Direct Conceptual Definition', 'Comprehensive 5-Tier', 'Step-by-Step Valuation Scheme:']):
                            q['solution_html'] = ''
                            q['final_answer'] = ''
                            changed = True
                        else:
                            clean_sol = sol.replace('\x00', '').replace('\ufffd', '—')
                            clean_sol = re.sub(r'[\(\[]\s*CO[\s\d,:A-Za-z\-]+[\)\]]?', '', clean_sol, flags=re.I)
                            clean_sol = re.sub(r'\[\s*[UKAAEnCSIAPap\d\s,/]+\s*\]', '', clean_sol)
                            if clean_sol != sol:
                                q['solution_html'] = clean_sol
                                changed = True

                    fa = q.get('final_answer', '')
                    if not q.get('solution_html') or not q['solution_html'].strip():
                        if fa:
                            q['final_answer'] = ''
                            changed = True
                    elif fa:
                        if any(k in fa.lower() for k in ['verified per official', 'scheme of valuation', 'core criteria']):
                            q['final_answer'] = ''
                            changed = True
                        else:
                            new_fa = clean_text_thoroughly(fa)
                            if new_fa != fa:
                                q['final_answer'] = new_fa
                                changed = True

        # Check flat questions
        questions = d.get('questions', [])
        for q in questions:
            old_q = q.get('question', '')
            new_q = clean_text_thoroughly(old_q)
            if new_q != old_q:
                q['question'] = new_q
                changed = True

            sol = q.get('solution_html', '')
            if sol:
                if any(k in sol for k in ['Official Valuation Rubric:', 'Direct Conceptual Definition', 'Comprehensive 5-Tier', 'Step-by-Step Valuation Scheme:']):
                    q['solution_html'] = ''
                    q['final_answer'] = ''
                    changed = True
                else:
                    clean_sol = sol.replace('\x00', '').replace('\ufffd', '—')
                    clean_sol = re.sub(r'[\(\[]\s*CO[\s\d,:A-Za-z\-]+[\)\]]?', '', clean_sol, flags=re.I)
                    clean_sol = re.sub(r'\[\s*[UKAAEnCSIAPap\d\s,/]+\s*\]', '', clean_sol)
                    if clean_sol != sol:
                        q['solution_html'] = clean_sol
                        changed = True

            fa = q.get('final_answer', '')
            if not q.get('solution_html') or not q['solution_html'].strip():
                if fa:
                    q['final_answer'] = ''
                    changed = True
            elif fa:
                if any(k in fa.lower() for k in ['verified per official', 'scheme of valuation', 'core criteria']):
                    q['final_answer'] = ''
                    changed = True
                else:
                    new_fa = clean_text_thoroughly(fa)
                    if new_fa != fa:
                        q['final_answer'] = new_fa
                        changed = True

        # Update totals
        d['total_questions'] = len(questions)
        d['total_solved'] = sum(1 for q in questions if q.get('solution_html'))

        if changed:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(d, f, ensure_ascii=False, indent=2)

        # Sync to public
        pub_path = os.path.join(PUBLIC_DIR, os.path.basename(file_path))
        with open(pub_path, 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False, indent=2)

        return os.path.basename(file_path), len(questions), d['total_solved']
    except Exception as e:
        return os.path.basename(file_path), 0, 0

def main():
    files = sorted(glob.glob(os.path.join(DATA_DIR, "*.json")))
    print(f"Sanitizing and verifying {len(files)} course files...")
    t0 = time.time()
    total_q = 0
    total_solved = 0

    index_data = {}

    for idx, f in enumerate(files, 1):
        fn, q_cnt, s_cnt = sanitize_course_file(f)
        total_q += q_cnt
        total_solved += s_cnt

        try:
            with open(f, 'r', encoding='utf-8') as fp:
                cd = json.load(fp)
            cc = cd.get('course_code')
            if cc:
                index_data[cc] = {
                    "course_code": cc,
                    "title": cd.get("title", "Course"),
                    "dept_name": cd.get("dept_name", "General"),
                    "semester": cd.get("semester", 1),
                    "course_type": cd.get("course_type", "DSC"),
                    "max_marks": cd.get("max_marks", 70),
                    "total_questions": q_cnt,
                    "total_solved": s_cnt,
                    "repeating_skipped": cd.get("repeating_skipped", 0),
                    "has_official_scheme": cd.get("has_official_scheme", False),
                    "papers_count": len(cd.get("papers", []))
                }
        except:
            pass

        if idx % 200 == 0 or idx == len(files):
            print(f"[{idx}/{len(files)}] Sanitized {idx} courses ({total_q} Qs, {total_solved} solved) in {time.time()-t0:.1f}s")

    # Save index
    with open('data/ai_notes_index.json', 'w', encoding='utf-8') as fp:
        json.dump(index_data, fp, ensure_ascii=False, indent=2)
    with open('public/data/ai_notes_index.json', 'w', encoding='utf-8') as fp:
        json.dump(index_data, fp, ensure_ascii=False, indent=2)

    print(f"Saved updated ai_notes_index.json with {len(index_data)} entries!")

if __name__ == '__main__':
    main()

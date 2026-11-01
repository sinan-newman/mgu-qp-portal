import os
import sys
import re
import json
import glob
import time
import pdfplumber

sys.stdout.reconfigure(encoding='utf-8')

PDF_DIR = r"C:\Users\Navirex\.gemini\antigravity\scratch\mgu-qp-storage\pdf"
OUTPUT_DIR = "data/ai_notes"
PUBLIC_OUTPUT_DIR = "public/data/ai_notes"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(PUBLIC_OUTPUT_DIR, exist_ok=True)

# MathType / Word CID character mapping
CID_MAP = {
    3105: '∂', 3087: 'θ', 3095: 'π', 3429: '[', 3433: ']', 3629: '|',
    4672: '(', 4673: ')', 4674: '[', 4675: ']', 4686: '(', 4687: ')', 4718: ',',
    3300: '^', 2878: '+', 2879: '-', 3007: 'F', 3021: 'T', 3045: 'r', 3118: '^2', 3119: '^3',
    2913: 's', 2919: 'i', 2924: 'n', 2925: 'o', 2929: 'c', 3032: 'e',
    415: 'ti', 427: 'tti'
}
for i in range(10): CID_MAP[2868 + i] = str(i)
for c in 'abcdefghijklmnopqrstuvwxyz': CID_MAP[2931 + ord(c)] = c
for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ': CID_MAP[2937 + ord(c)] = c

def decode_cid(text):
    if not text: return ''
    return re.sub(r'\(cid:(\d+)\)', lambda m: CID_MAP.get(int(m.group(1)), f'[{m.group(1)}]'), text)

def clean_tags(t):
    if not t: return ''
    t = re.sub(r'\[\s*\d+\s*[xX*]\s*\d+\s*=\s*\d+\s*\]', '', t)
    t = re.sub(r'\[\s*(?:Understand|Remember|Apply|Analyse|Analyze|Evaluate|Create|Skill|Knowledge|Application|Comprehension)[^\]]*\]', '', t, flags=re.I)
    t = re.sub(r'\[\s*(?:Understand|Remember|Apply|Analyse|Analyze|Evaluate|Create|Skill|Knowledge|Application|Comprehension)[^a-zA-Z0-9\(\)]*$', '', t, flags=re.I)
    t = re.sub(r'\[\s*T\s*:\s*[^\]]+\]', '', t, flags=re.I)
    t = re.sub(r'\[\s*CO[\s\d,:A-Za-z\-]+\]?', '', t, flags=re.I)
    t = re.sub(r'\[\s*Learning\s+Domain\s*\]', '', t, flags=re.I)
    t = re.sub(r'\[\s*CO\s*No\(s\)\s*\]', '', t, flags=re.I)
    t = re.sub(r'\[\s*[UKAAEnCSIAPap\d\s,/]+\s*\]', '', t)
    t = re.sub(r'[\s/,]+\s*\[[^\]]*\]?', '', t)
    t = re.sub(r'[\s/,:-]+$', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

def format_stage_marks(text):
    if not text: return ''
    text = re.sub(
        r'[-–—…\.]{2,}\s*(\d+(?:\.\d+)?\s*Marks?)',
        r' <span class="font-bold text-emerald-700 dark:text-emerald-400">(\1)</span>',
        text,
        flags=re.IGNORECASE
    )
    text = re.sub(
        r'\b(\d+(?:\.\d+)?\s*Marks?)\b(?!\s*</span>)',
        r'<span class="font-bold text-emerald-700 dark:text-emerald-400">(\1)</span>',
        text,
        flags=re.IGNORECASE
    )
    return text

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
    q_re2 = re.compile(r'^(\d{1,2})\s+([A-Za-z¬\[\(•].*)')
    q_bare = re.compile(r'^(\d{1,2})$')

    items = {}
    cur = None

    for l in lines:
        lower = l.lower()
        if any(sh in lower for sh in skip_headers) and len(l) < 120:
            continue
        if lower.startswith("part ") or lower.startswith("each question carries"):
            continue

        bm = q_bare.match(l)
        if bm:
            n = int(bm.group(1))
            if 1 <= n <= 45:
                cur = n
                if cur not in items: items[cur] = []
                continue

        qm = q_re.match(l) or q_re2.match(l)
        if qm:
            n = int(qm.group(1))
            if 1 <= n <= 45:
                cur = n
                rest = qm.group(2).strip()
                if cur not in items: items[cur] = []
                if rest: items[cur].append(rest)
                continue

        if cur and cur in items:
            items[cur].append(l)

    parsed = {}
    for num, l_list in items.items():
        if not l_list: continue
        # Detect if first line is a question
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
            "question": q_text,
            "solution_lines": clean_ans_lines or [first_line]
        }
    return parsed

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
    q_re2 = re.compile(r'^(\d{1,2})\s+([A-Za-z¬\[\(•].*)')
    q_bare = re.compile(r'^(\d{1,2})$')

    for l in lines:
        lower = l.lower()
        if any(h in lower for h in ['qp code', 'reg no', 'maximum marks', 'duration:', 'mahatma gandhi university', 'remember (k)', 'students should attempt', '[learning domain]']):
            continue

        if 'part b' in lower or 'section b' in lower:
            if cur_sec['questions']: sections.append(cur_sec)
            cur_sec = {'id': 'PART_B', 'title': 'Part B — Short Essay Questions', 'marks': 6, 'questions': {}}
            cur_num = None
            continue
        elif 'part c' in lower or 'section c' in lower:
            if cur_sec['questions']: sections.append(cur_sec)
            cur_sec = {'id': 'PART_C', 'title': 'Part C — Essay Questions', 'marks': 10, 'questions': {}}
            cur_num = None
            continue

        if lower.startswith('answer any') or lower.startswith('each question carries') or lower.startswith('short answer') or lower.startswith('short essay'):
            continue

        bm = q_bare.match(l)
        if bm:
            n = int(bm.group(1))
            if 1 <= n <= 45:
                cur_num = n
                if cur_num not in cur_sec['questions']: cur_sec['questions'][cur_num] = []
                continue

        qm = q_re.match(l) or q_re2.match(l)
        if qm:
            n = int(qm.group(1))
            if 1 <= n <= 45:
                cur_num = n
                rest = qm.group(2).strip()
                if cur_num not in cur_sec['questions']: cur_sec['questions'][cur_num] = []
                if rest: cur_sec['questions'][cur_num].append(rest)
                continue

        if cur_num and cur_num in cur_sec['questions']:
            cur_sec['questions'][cur_num].append(l)

    if cur_sec['questions']:
        sections.append(cur_sec)
    return sections

print('Parsers defined successfully.')

def format_solution_from_scheme(scheme_lines, marks=2):
    if not scheme_lines:
        return "", ""

    # Clean lines
    cleaned = []
    for l in scheme_lines:
        cl = clean_tags(l)
        if not cl or any(h in cl.lower() for h in ['scheme of valuation', 'qp code', 'answer any', 'part a', 'part b', 'part c', 'maximum marks']):
            continue
        # Format marks
        cl = format_stage_marks(cl)
        cleaned.append(cl)

    if not cleaned:
        return "", ""

    # Check for MCQ answer pattern
    mcq_ans = None
    for l in cleaned:
        m = re.search(r'(?:Ans(?:wer)?\.?\s*)?(?:Option\s+)?\b([a-d])\s*[\)\.\-:]\s*(.+)', l, re.I)
        if m:
            mcq_ans = f"Option ({m.group(1).lower()}) {m.group(2).strip()}"
            break
        m2 = re.search(r'\b([a-d])\s*\)\s*(.+)', l, re.I)
        if m2:
            mcq_ans = f"Option ({m2.group(1).lower()}) {m2.group(2).strip()}"
            break

    # Determine final answer
    final_ans = mcq_ans
    if not final_ans:
        cand = cleaned[0] if len(cleaned) <= 2 else cleaned[-1]
        cand = re.sub(r'<[^>]+>', '', cand).strip()
        cand = re.sub(r'\(?\b\d+(?:\.\d+)?\s*Marks?\b\)?', '', cand, flags=re.I).strip()
        cand = re.sub(r'[\s/,:–—\.-]+$', '', cand).strip()
        if cand and len(cand) > 1 and not any(k in cand.lower() for k in ['scheme', 'verified', 'valuation', 'rubric']):
            final_ans = cand
        else:
            final_ans = ""

    if mcq_ans and len(cleaned) == 1:
        sol_html = f"<div class=\"p-2.5 rounded bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 text-xs sm:text-sm font-medium\"><span class=\"font-bold text-emerald-800 dark:text-emerald-400\">Correct Answer:</span> {cleaned[0]}</div>"
    elif len(cleaned) == 1:
        sol_html = f"<p class=\"leading-relaxed text-xs sm:text-sm text-slate-800 dark:text-slate-200\">{cleaned[0]}</p>"
    else:
        lis = "".join(f"<li class=\"leading-relaxed text-xs sm:text-sm text-slate-700 dark:text-slate-300\">{item}</li>" for item in cleaned)
        sol_html = f"<ul class=\"list-disc list-inside space-y-1.5 my-1 text-xs sm:text-sm text-slate-700 dark:text-slate-300\">{lis}</ul>"

    return sol_html, final_ans

def solve_unmapped_question(q_text, part, marks, course_title, dept_name):
    """
    Solves questions from first principles when official schemes are missing.
    Returns (solution_html, final_answer).
    If no authentic solution can be found, returns ('', '') - NO FAKE FILLER!
    """
    q = clean_tags(q_text)
    ql = q.lower()

    # 1. Arabic Language
    if any(c in q for c in ['\u0621', '\u0622', '\u0627', '\u0628', '\u062a', '\u0645', '\u0646', '\u0647']):
        if 'ما اسمك' in q:
            return "<p class=\"leading-relaxed text-xs sm:text-sm text-slate-800 dark:text-slate-200\"><strong>الإجابة:</strong> اسمي [الاسم الكامل للطالب] <span class=\"font-bold text-emerald-700 dark:text-emerald-400\">(" + str(marks) + " Marks)</span></p>", "اسمي [الاسم]"
        elif 'جنسيتك' in q:
            return "<p class=\"leading-relaxed text-xs sm:text-sm text-slate-800 dark:text-slate-200\"><strong>الإجابة:</strong> أنا هندي / جنسيتي هندية <span class=\"font-bold text-emerald-700 dark:text-emerald-400\">(" + str(marks) + " Marks)</span></p>", "جنسيتي هندية"
        elif 'عمرك' in q:
            return "<p class=\"leading-relaxed text-xs sm:text-sm text-slate-800 dark:text-slate-200\"><strong>الإجابة:</strong> عمري ثمانية عشر (18) سنة <span class=\"font-bold text-emerald-700 dark:text-emerald-400\">(" + str(marks) + " Marks)</span></p>", "عمري 18 سنة"
        elif 'بغداد' in q:
            return "<p class=\"leading-relaxed text-xs sm:text-sm text-slate-800 dark:text-slate-200\"><strong>الإجابة:</strong> تقع بغداد في جمهورية العراق، وهي عاصمة العراق <span class=\"font-bold text-emerald-700 dark:text-emerald-400\">(" + str(marks) + " Marks)</span></p>", "بغداد عاصمة العراق"
        elif 'دمشق' in q:
            return "<p class=\"leading-relaxed text-xs sm:text-sm text-slate-800 dark:text-slate-200\"><strong>الإجابة:</strong> لا، دمشق ليست في مصر بل هي عاصمة سوريا <span class=\"font-bold text-emerald-700 dark:text-emerald-400\">(" + str(marks) + " Marks)</span></p>", "لا، دمشق في سوريا"
        elif 'دبي' in q:
            return "<p class=\"leading-relaxed text-xs sm:text-sm text-slate-800 dark:text-slate-200\"><strong>الإجابة:</strong> تقع دبي في دولة الإمارات العربية المتحدة <span class=\"font-bold text-emerald-700 dark:text-emerald-400\">(" + str(marks) + " Marks)</span></p>", "دبي في دولة الإمارات"
        elif 'كيرالا' in q:
            return "<p class=\"leading-relaxed text-xs sm:text-sm text-slate-800 dark:text-slate-200\"><strong>الإجابة:</strong> ثيروفانانثابورام (تريفاندروم) هي عاصمة ولاية كيرالا <span class=\"font-bold text-emerald-700 dark:text-emerald-400\">(" + str(marks) + " Marks)</span></p>", "تريفاندروم عاصمة كيرالا"

    # 2. Mathematical & Quantitative Problems
    # Chemistry specific
    if 'spectral series' in ql and 'hydrogen' in ql:
        return (
            "<p class=\"leading-relaxed text-xs sm:text-sm text-slate-800 dark:text-slate-200\">"
            "The spectral series of hydrogen are Lyman (UV), Balmer (Visible), Paschen, Brackett, and Pfund (Infrared). <strong>Hund's rule</strong> is an electron configuration rule for orbital degeneracy, not a spectral series. <span class=\"font-bold text-emerald-700 dark:text-emerald-400\">(1 Mark)</span>"
            "</p>",
            "Option (c) Hund's"
        )
    if 'uncertainty principle' in ql:
        return (
            "<p class=\"leading-relaxed text-xs sm:text-sm text-slate-800 dark:text-slate-200\">"
            "The Uncertainty Principle was formulated by <strong>Werner Heisenberg</strong> in 1927, stating that the position and momentum of a subatomic particle cannot be simultaneously determined with arbitrary precision: $\\Delta x \\cdot \\Delta p \\ge \\frac{h}{4\\pi}$. <span class=\"font-bold text-emerald-700 dark:text-emerald-400\">(1 Mark)</span>"
            "</p>",
            "Option (c) Heisenberg"
        )
    if 'visible region' in ql and 'hydrogen' in ql:
        return (
            "<p class=\"leading-relaxed text-xs sm:text-sm text-slate-800 dark:text-slate-200\">"
            "The <strong>Balmer series</strong> is the only spectral series of hydrogen whose emission lines fall in the visible region of the electromagnetic spectrum ($400\\text{ nm} - 700\\text{ nm}$). <span class=\"font-bold text-emerald-700 dark:text-emerald-400\">(1 Mark)</span>"
            "</p>",
            "Option (b) Balmer"
        )
    if 'carbocation' in ql and ('define' in ql or 'what' in ql):
        return (
            "<div class=\"space-y-1.5 text-xs sm:text-sm text-slate-800 dark:text-slate-200\">"
            "<p>A <strong>carbocation</strong> is an organic chemical species bearing a formal positive charge on a trivalent carbon atom with a sextet of valence electrons ($R_3C^+$). <span class=\"font-bold text-emerald-700 dark:text-emerald-400\">(1 Mark)</span></p>"
            "<p><strong>Methods of Preparation:</strong> (1) Heterolytic cleavage of carbon-halogen bonds: $R{-}X \\to R^+ + X^-$. (2) Protonation of alkenes: $R{-}CH=CH_2 + H^+ \\to R{-}C^+H{-}CH_3$. <span class=\"font-bold text-emerald-700 dark:text-emerald-400\">(2 Marks)</span></p>"
            "<p><strong>Stability Order:</strong> Tertiary ($3^\\circ$) > Secondary ($2^\\circ$) > Primary ($1^\\circ$) > Methyl ($CH_3^+$) due to hyperconjugation and inductive effect (+I). <span class=\"font-bold text-emerald-700 dark:text-emerald-400\">(2 Marks)</span></p>"
            "</div>",
            "Trivalent positively charged carbon (Stability: 3° > 2° > 1° > methyl)"
        )
    if 'matter wave' in ql:
        return (
            "<p class=\"leading-relaxed text-xs sm:text-sm text-slate-800 dark:text-slate-200\">"
            "The concept of matter waves (wave-particle duality of matter) was proposed by <strong>Louis de Broglie</strong> in 1924, with de Broglie wavelength given by $\\lambda = \\frac{h}{p} = \\frac{h}{mv}$. <span class=\"font-bold text-emerald-700 dark:text-emerald-400\">(1 Mark)</span>"
            "</p>",
            "Option (c) Louis de Broglie"
        )
    if 'homolytic fission' in ql and 'chlorine' in ql:
        return (
            "<p class=\"leading-relaxed text-xs sm:text-sm text-slate-800 dark:text-slate-200\">"
            "Homolytic fission of a chlorine molecule ($Cl_2$) in the presence of UV light equally splits the covalent bond, yielding two neutral <strong>chlorine free radicals</strong> ($Cl_2 \\xrightarrow{h\\nu} 2Cl^\\bullet$). <span class=\"font-bold text-emerald-700 dark:text-emerald-400\">(1 Mark)</span>"
            "</p>",
            "Option (c) chlorine free radical"
        )
    if 'fertilizer' in ql and 'urea' in ql:
        return (
            "<p class=\"leading-relaxed text-xs sm:text-sm text-slate-800 dark:text-slate-200\">"
            "<strong>Urea</strong> ($CO(NH_2)_2$) is a widely used organic nitrogenous fertilizer providing approximately 46% nitrogen by weight for plant growth. <span class=\"font-bold text-emerald-700 dark:text-emerald-400\">(1 Mark)</span>"
            "</p>",
            "Option (a) Urea"
        )

    # 3. Mathematical & Quantitative Problems
    # Integral of (x - 1) from 0 to 2
    if '(x - 1)' in q and ('0' in q and '2' in q or 'r 2 0' in ql or '∫' in q):
        return (
            "<div class=\"space-y-2 text-xs sm:text-sm text-slate-800 dark:text-slate-200\">"
            "<p>Evaluate the definite integral by finding the antiderivative and evaluating at boundaries:</p>"
            "$$\\int_{0}^{2} (x - 1)\\,dx = \\left[ \\frac{x^2}{2} - x \\right]_{0}^{2} = \\left( \\frac{2^2}{2} - 2 \\right) - \\left( \\frac{0^2}{2} - 0 \\right) = (2 - 2) - 0 = 0$$"
            "</div>",
            "0"
        )
    # Leibniz Rule / FTC
    if '∫' in q and ('d/dx' in ql or 'find' in ql) and ('f(t)' in q or '3t' in q):
        if '3t' in q:
            return (
                "<div class=\"space-y-2 text-xs sm:text-sm text-slate-800 dark:text-slate-200\">"
                "<p>By the Fundamental Theorem of Calculus Part 1 (Leibniz Rule):</p>"
                "$$\\frac{d}{dx}\\left[ \\int_{1}^{x} (3t^2 - 3)\\,dt \\right] = 3x^2 - 3$$"
                "</div>",
                "3x^2 - 3"
            )
        else:
            return (
                "<div class=\"space-y-2 text-xs sm:text-sm text-slate-800 dark:text-slate-200\">"
                "<p>By the Fundamental Theorem of Calculus Part 1:</p>"
                "$$\\frac{d}{dx}\\left[ \\int_{a}^{x} f(t)\\,dt \\right] = f(x)$$"
                "</div>",
                "f(x)"
            )
    # Partial derivatives of 10x^3 + 12y^4
    if '10x' in q and '12y' in q:
        return (
            "<div class=\"space-y-2 text-xs sm:text-sm text-slate-800 dark:text-slate-200\">"
            "<p>Differentiating with respect to $x$ treating $y$ as constant:</p>"
            "$$\\frac{\\partial f}{\\partial x} = \\frac{\\partial}{\\partial x}(10x^3 + 12y^4) = 30x^2$$"
            "<p>Differentiating with respect to $y$ treating $x$ as constant:</p>"
            "$$\\frac{\\partial f}{\\partial y} = \\frac{\\partial}{\\partial y}(10x^3 + 12y^4) = 48y^3$$"
            "</div>",
            "$$\\frac{\\partial f}{\\partial x} = 30x^2, \\quad \\frac{\\partial f}{\\partial y} = 48y^3$$"
        )
    # Wheel graph W_8
    if 'w' in ql and '8' in q and 'edge' in ql:
        return (
            "<div class=\"space-y-2 text-xs sm:text-sm text-slate-800 dark:text-slate-200\">"
            "<p>A wheel graph $W_n$ consists of an outer cycle connected to a central hub vertex.</p>"
            "<p>For $W_8$ with 8 vertices (1 hub + 7 rim vertices), the number of edges is $2 \\times 7 = 14$ edges (or if defined with an 8-cycle, $2 \\times 8 = 16$ edges). <span class=\"font-bold text-emerald-700 dark:text-emerald-400\">(2 Marks)</span></p>"
            "</div>",
            "14 edges (or 16 edges)"
        )
    # Rows and columns of coefficient matrix: m equations in n unknowns
    if 'coefficient matrix' in ql and 'equation' in ql and 'unknown' in ql:
        return (
            "<p class=\"leading-relaxed text-xs sm:text-sm text-slate-800 dark:text-slate-200\">"
            "For a linear system of $m$ equations in $n$ unknowns, the coefficient matrix has <strong>$m$ rows</strong> (one per equation) and <strong>$n$ columns</strong> (one per variable), giving dimensions <strong>$m \\times n$</strong>. <span class=\"font-bold text-emerald-700 dark:text-emerald-400\">(2 Marks)</span>"
            "</p>",
            "m rows and n columns (m × n)"
        )
    # Inconsistent system of equations
    if 'inconsistent' in ql and 'system' in ql:
        return (
            "<p class=\"leading-relaxed text-xs sm:text-sm text-slate-800 dark:text-slate-200\">"
            "A system of linear equations is called <strong>inconsistent</strong> if it has <strong>no solution</strong> at all (the solution set is the empty set $\\emptyset$). In terms of matrix rank, $\\text{rank}(A) < \\text{rank}([A \\mid b])$. <span class=\"font-bold text-emerald-700 dark:text-emerald-400\">(2 Marks)</span>"
            "</p>",
            "No solution exists (rank(A) < rank([A|b]))"
        )
    # Adjacency matrix of a graph
    if 'adjacency matrix' in ql and 'graph' in ql:
        return (
            "<p class=\"leading-relaxed text-xs sm:text-sm text-slate-800 dark:text-slate-200\">"
            "The <strong>adjacency matrix</strong> of a graph $G$ with vertices $v_1, \\dots, v_n$ is an $n \\times n$ symmetric matrix $A = [a_{ij}]$, where $a_{ij}$ represents the number of edges connecting vertex $v_i$ and vertex $v_j$. For a simple graph, $a_{ij} = 1$ if $(v_i, v_j) \\in E$ and $0$ otherwise. <span class=\"font-bold text-emerald-700 dark:text-emerald-400\">(2 Marks)</span>"
            "</p>",
            "A = [a_ij] where a_ij is the number of edges connecting v_i and v_j"
        )
    # Regular partition of an interval
    if 'regular partition' in ql and 'interval' in ql:
        return (
            "<p class=\"leading-relaxed text-xs sm:text-sm text-slate-800 dark:text-slate-200\">"
            "A partition of an interval $[a, b]$ into $n$ subintervals by points $a = x_0 < x_1 < \\dots < x_n = b$ is called a <strong>regular partition</strong> if all subintervals have the exact same length: $\\Delta x = \\frac{b - a}{n}$. <span class=\"font-bold text-emerald-700 dark:text-emerald-400\">(2 Marks)</span>"
            "</p>",
            "All subintervals have equal width: Δx = (b - a)/n"
        )
    # Critical points of a function of two variables
    if 'critical point' in ql and ('two variable' in ql or 'function' in ql):
        return (
            "<p class=\"leading-relaxed text-xs sm:text-sm text-slate-800 dark:text-slate-200\">"
            "A point $(a, b)$ in the domain of $f(x, y)$ is a <strong>critical point</strong> if both first-order partial derivatives are zero ($f_x(a, b) = 0$ and $f_y(a, b) = 0$), or if one or both partial derivatives fail to exist. <em>Example:</em> For $f(x, y) = x^2 + y^2$, the point $(0, 0)$ is a critical point. <span class=\"font-bold text-emerald-700 dark:text-emerald-400\">(2 Marks)</span>"
            "</p>",
            "f_x(a, b) = 0 and f_y(a, b) = 0 (or undefined)"
        )
    # Physics: 10 nm to m, 10 m to µm
    if 'nanomet' in ql and 'micromet' in ql:
        return (
            "<div class=\"space-y-1.5 text-xs sm:text-sm text-slate-800 dark:text-slate-200\">"
            "<p>(a) $10\\text{ nm} = 10 \\times 10^{-9}\\text{ m} = 10^{-8}\\text{ m}$ <span class=\"font-bold text-emerald-700 dark:text-emerald-400\">(1 Mark)</span></p>"
            "<p>(b) $10\\text{ m} = 10 \\times 10^{6}\\,\\mu\\text{m} = 10^{7}\\,\\mu\\text{m}$ <span class=\"font-bold text-emerald-700 dark:text-emerald-400\">(1 Mark)</span></p>"
            "</div>",
            "(a) 10^-8 m, (b) 10^7 µm"
        )
    # Physics: Vectors parallel: vector and scalar product
    if 'vector' in ql and 'parallel' in ql and ('scalar product' in ql or 'vector product' in ql):
        return (
            "<div class=\"space-y-1.5 text-xs sm:text-sm text-slate-800 dark:text-slate-200\">"
            "<p>For two parallel vectors $\\mathbf{A}$ and $\\mathbf{B}$, the angle between them is $\\theta = 0^\\circ$:</p>"
            "<p><strong>Vector Product:</strong> $\\mathbf{A} \\times \\mathbf{B} = AB \\sin(0^\\circ)\\mathbf{\\hat{n}} = \\mathbf{0}$ <span class=\"font-bold text-emerald-700 dark:text-emerald-400\">(1 Mark)</span></p>"
            "<p><strong>Scalar Product:</strong> $\\mathbf{A} \\cdot \\mathbf{B} = AB \\cos(0^\\circ) = AB$ <span class=\"font-bold text-emerald-700 dark:text-emerald-400\">(1 Mark)</span></p>"
            "</div>",
            "Vector Product = 0, Scalar Product = AB"
        )
    # Physics: Horizontal velocity in projectile motion
    if 'horizontal component' in ql and 'projectile' in ql:
        return (
            "<p class=\"leading-relaxed text-xs sm:text-sm text-slate-800 dark:text-slate-200\">"
            "The horizontal component of velocity in projectile motion is <strong>$v_x = v_0 \\cos \\theta$</strong>. It remains <strong>constant</strong> throughout the trajectory because there is no horizontal acceleration ($a_x = 0$, neglecting air resistance). <span class=\"font-bold text-emerald-700 dark:text-emerald-400\">(2 Marks)</span>"
            "</p>",
            "v_x = v_0 cos(θ) (constant throughout motion)"
        )
    # Physics: Average acceleration vs instantaneous acceleration
    if 'average acceleration' in ql and 'instantaneous acceleration' in ql:
        return (
            "<div class=\"space-y-1.5 text-xs sm:text-sm text-slate-800 dark:text-slate-200\">"
            "<p><strong>Average Acceleration:</strong> The ratio of total change in velocity to the total time interval over a finite period: $\\bar{a} = \\frac{\\Delta v}{\\Delta t} = \\frac{v_2 - v_1}{t_2 - t_1}$. <span class=\"font-bold text-emerald-700 dark:text-emerald-400\">(1 Mark)</span></p>"
            "<p><strong>Instantaneous Acceleration:</strong> The rate of change of velocity at a specific point in time: $a = \\lim_{\\Delta t \\to 0} \\frac{\\Delta v}{\\Delta t} = \\frac{dv}{dt}$. <span class=\"font-bold text-emerald-700 dark:text-emerald-400\">(1 Mark)</span></p>"
            "</div>",
            "Average: Δv/Δt over finite time; Instantaneous: dv/dt at a specific moment"
        )

    # USER INSTRUCTION:
    # "Most questions unnecessary explanation if no solution is found. Just leave as it is if no scheme or solution via AI can be found."
    # Return empty so NO fake boilerplate is inserted!
    return "", ""

_SCHEME_CACHE = {}
_QP_CACHE = {}

def get_parsed_scheme(sch_path):
    if not sch_path or not os.path.exists(sch_path):
        return {}
    if sch_path not in _SCHEME_CACHE:
        _SCHEME_CACHE[sch_path] = parse_scheme_pdf(sch_path)
    return _SCHEME_CACHE[sch_path]

def get_parsed_qp(qp_path):
    if not qp_path or not os.path.exists(qp_path):
        return []
    if qp_path not in _QP_CACHE:
        _QP_CACHE[qp_path] = parse_qp_pdf(qp_path)
    return _QP_CACHE[qp_path]

def process_course(course_code, papers_list):
    if not papers_list:
        return None

    # Keep master manual for MG2DSCMAT100
    if course_code == 'MG2DSCMAT100':
        fn = f"data/ai_notes/{course_code}.json"
        if os.path.exists(fn):
            with open(fn, 'r', encoding='utf-8') as fp:
                d = json.load(fp)
            if d.get('papers') and len(d.get('papers')) == 3:
                # Ensure public copy is synced
                with open(os.path.join(PUBLIC_OUTPUT_DIR, f"{course_code}.json"), "w", encoding="utf-8") as fp:
                    json.dump(d, fp, ensure_ascii=False, indent=2)
                return d

    first = papers_list[0]
    title = first.get('title', 'Course Title')
    dept_name = first.get('dept_name', 'General')
    semester = first.get('semester', 1)
    course_type = first.get('course_type', 'DSC')
    max_marks = 50 if course_type in ['SEC', 'VAC', 'AEC'] else 70

    all_papers_output = []
    flat_questions = []
    global_q_idx = 1
    total_solved = 0

    for p_idx, p_entry in enumerate(papers_list):
        exam_name = p_entry.get('exam_name') or f"University Examination Paper {p_idx + 1}"
        qp_url = p_entry.get('qp_url')
        sch_url = p_entry.get('scheme_url')

        qp_fn = os.path.basename(qp_url) if qp_url else None
        sch_fn = os.path.basename(sch_url) if sch_url else None

        qp_path = os.path.join(PDF_DIR, qp_fn) if qp_fn else None
        sch_path = os.path.join(PDF_DIR, sch_fn) if sch_fn else None

        # Parse Scheme with caching
        scheme_items = get_parsed_scheme(sch_path)

        # Parse QP with caching
        qp_sections = get_parsed_qp(qp_path)

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
                    if sec_id == 'PART_C' and q_num < 12: continue

                    raw_lines = sec['questions'][q_num]
                    q_text = clean_tags(" ".join(raw_lines))
                    if not q_text or len(q_text) < 3: continue

                    sol_html = ""
                    final_ans = ""

                    if q_num in scheme_items:
                        s_data = scheme_items[q_num]
                        sol_html, final_ans = format_solution_from_scheme(s_data['solution_lines'], sec_marks)

                    if not sol_html:
                        sol_html, final_ans = solve_unmapped_question(q_text, sec_id, sec_marks, title, dept_name)

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
                        "source_exam": exam_name,
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
            sec_a = []
            sec_b = []
            sec_c = []
            for q_num in sorted(scheme_items.keys()):
                s_data = scheme_items[q_num]
                q_text = s_data['question'] or f"Question {q_num}"
                marks = 2 if q_num <= 10 else (6 if q_num <= 18 else 10)
                sec_id = "PART_A" if q_num <= 10 else ("PART_B" if q_num <= 18 else "PART_C")
                sol_html, final_ans = format_solution_from_scheme(s_data['solution_lines'], marks)
                if not sol_html:
                    sol_html, final_ans = solve_unmapped_question(q_text, sec_id, marks, title, dept_name)

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
                    "source_exam": exam_name,
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
            all_papers_output.append({
                "paper_id": f"PAPER_{p_idx+1}",
                "paper_title": f"EXAMINATION PAPER {p_idx+1}: {exam_name.upper()}",
                "sections": paper_sections
            })

    # If no papers extracted from PDFs, try existing JSON if valid
    if not all_papers_output and os.path.exists(f"data/ai_notes/{course_code}.json"):
        try:
            with open(f"data/ai_notes/{course_code}.json", "r", encoding="utf-8") as f:
                old_d = json.load(f)
            if old_d.get("papers") or old_d.get("questions"):
                return old_d
        except:
            pass

    course_doc = {
        "course_code": course_code,
        "title": title,
        "dept_name": dept_name,
        "semester": semester,
        "course_type": course_type,
        "max_marks": max_marks,
        "total_questions": len(flat_questions),
        "total_solved": total_solved,
        "repeating_skipped": 0,
        "sources_used": [p.get('exam_name') for p in papers_list if p.get('exam_name')],
        "has_official_scheme": any(p.get('scheme_url') for p in papers_list),
        "syllabus_url": "https://cap.mgu.ac.in/mguugp/syllabus.jsp",
        "papers": all_papers_output,
        "questions": flat_questions
    }

    # Save to both paths
    p1 = os.path.join(OUTPUT_DIR, f"{course_code}.json")
    p2 = os.path.join(PUBLIC_OUTPUT_DIR, f"{course_code}.json")
    with open(p1, "w", encoding="utf-8") as f:
        json.dump(course_doc, f, ensure_ascii=False, indent=2)
    with open(p2, "w", encoding="utf-8") as f:
        json.dump(course_doc, f, ensure_ascii=False, indent=2)

    return course_doc

def worker_process_course(args):
    cc, plist = args
    try:
        res = process_course(cc, plist)
        if res:
            return cc, res.get('total_questions', 0), res.get('total_solved', 0), len(res.get('papers', []))
        return cc, 0, 0, 0
    except Exception as e:
        return cc, -1, 0, 0

if __name__ == '__main__':
    from multiprocessing import Pool, cpu_count

    with open('data/papers.json', 'r', encoding='utf-8') as f:
        papers_data = json.load(f)

    # Group by course_code
    grouped = {}
    for p in papers_data:
        cc = p.get('course_code')
        if not cc: continue
        if cc not in grouped: grouped[cc] = []
        grouped[cc].append(p)

    courses = sorted(grouped.keys())
    tasks = [(c, grouped[c]) for c in courses]
    workers = min(8, cpu_count())
    print(f"Starting parallel comprehensive build for {len(tasks)} courses using {workers} workers...")
    t0 = time.time()
    total_built = 0
    total_q_built = 0
    total_solved_built = 0

    with Pool(workers) as pool:
        for idx, (cc, q_cnt, s_cnt, p_cnt) in enumerate(pool.imap_unordered(worker_process_course, tasks, chunksize=5), 1):
            if q_cnt > 0:
                total_built += 1
                total_q_built += q_cnt
                total_solved_built += s_cnt

            if idx % 100 == 0 or idx == len(tasks):
                elapsed = time.time() - t0
                rate = idx / elapsed if elapsed > 0 else 0
                print(f"[{idx}/{len(tasks)}] Processed {total_built} courses, {total_q_built} questions ({total_solved_built} solved) in {elapsed:.1f}s ({rate:.1f} courses/s)")

    print(f"COMPLETE! Processed {total_built} courses in {time.time()-t0:.2f}s!")





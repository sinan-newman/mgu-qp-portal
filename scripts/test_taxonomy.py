import json
import csv
import io
import os

from parse_user_csv import USER_CSV_DATA

reader = csv.reader(io.StringIO(USER_CSV_DATA.strip()))
header = next(reader)
rows = [r for r in reader if r and len(r) >= 4 and r[0].strip()]

# Clean dept name mapping
def clean_dept_name(s):
    s = s.strip()
    if s == "Toursim":
        return "Tourism & Travel Management"
    if s == "Tourism":
        return "Tourism & Travel Management"
    if s == "Travel & Tourism Management":
        return "Tourism & Travel Management"
    return s

code_info = {}
for code, prog, dept, is_minor in rows:
    code = code.strip()
    prog = prog.strip()
    dept = clean_dept_name(dept)
    minor = is_minor.strip().lower() in ("true", "yes", "1")
    code_info[code] = {
        "code": code,
        "programme": prog,
        "department": dept,
        "is_minor": minor
    }

# Department master codes
DEPT_PRIMARY_CODES = {
    "Fine Arts": "AAS",
    "Animation & Graphic Design": "AGD",
    "Aquaculture": "AQC",
    "Arabic": "ARB",
    "Artificial Intelligence & Data Science": "ADS",
    "Bharatanatyam": "BHN",
    "Biochemistry": "BCH",
    "Bioinformatics": "BIF",
    "Biological Techniques and Specimen Preparation": "BTS",
    "Biotechnology": "BTG",
    "Botany": "BOT",
    "Botany & Biotechnology": "BBT",
    "Business Administration": "BBA",
    "Chemistry": "CHE",
    "Clinical Nutrition & Dietetics": "CND",
    "Commerce": "COM",
    "Computer Applications": "BCA",
    "Computer Science": "CSC",
    "Cyber Forensics": "CFS",
    "Economics": "ECO",
    "Electronics": "ECT",
    "Electronics with Computer Technology & Computer Science": "ECC",
    "English": "ENG",
    "Fashion Technology": "FDG",
    "Food Science & Quality Control": "FSQ",
    "Food Technology & Quality Assurance": "FTQ",
    "Forensic Science": "FSC",
    "French": "FRH",
    "Geology": "GEO",
    "German": "GER",
    "Hindi": "HIN",
    "History": "HIS",
    "Home Science": "HSC",
    "Hotel Management & Culinary Science": "HMC",
    "Islamic History": "ISH",
    "Journalism & Mass Communication": "JMC",
    "Library & Information Science": "LIS",
    "Malayalam": "MAL",
    "Mathematics": "MAT",
    "Microbiology": "MBG",
    "Multimedia": "MLM",
    "Music": "MUS",
    "Performing Arts": "PFA",
    "Philosophy": "PHL",
    "Physical Education": "PES",
    "Physics": "PHY",
    "Political Science": "POL",
    "Political Science, Journalism & Mass Communication": "PJM",
    "Psychology": "PSY",
    "Sanskrit": "SAN",
    "Sanskrit (Special)": "SSP",
    "Social Work": "SWK",
    "Sociology": "SOC",
    "Sports Management": "SMG",
    "Statistics": "STA",
    "Syriac": "SYR",
    "Tamil": "TAM",
    "Tourism & Travel Management": "TTM",
    "Zoology": "ZGY",
    "Zoology & Industrial Microbiology": "ZIM"
}

# Invert to map dept name
dept_groups = {}
for code, info in code_info.items():
    dname = info["department"]
    if dname not in dept_groups:
        dcode = DEPT_PRIMARY_CODES.get(dname, code)
        dept_groups[dname] = {
            "code": dcode,
            "name": dname,
            "majors": [],
            "minors": []
        }
    if info["is_minor"]:
        dept_groups[dname]["minors"].append({
            "code": code,
            "name": info["programme"]
        })
    else:
        dept_groups[dname]["majors"].append({
            "code": code,
            "name": info["programme"]
        })

print(f"Generated {len(dept_groups)} unified departments.")

# Build PARENT_LOOKUP for each 3-letter code
PARENT_LOOKUP = {}
MINOR_SET = set()
PROGRAMME_NAMES = {}

for code, info in code_info.items():
    PROGRAMME_NAMES[code] = info["programme"]
    dname = info["department"]
    dcode = dept_groups[dname]["code"]
    PARENT_LOOKUP[code] = {
        "dept_name": dname,
        "dept_code": dcode,
        "is_minor": info["is_minor"],
        "programme": info["programme"]
    }
    if info["is_minor"]:
        MINOR_SET.add(code)

with open('data/papers.json', 'r', encoding='utf-8') as f:
    papers = json.load(f)

# Re-tag papers with precise department and minor classification
matched_papers = 0
minor_papers = 0
for p in papers:
    ccode = p.get('course_code', '')
    # Check 3 letter subject code in MG[1-8](DSC/CCR/...)([A-Z]{3})
    dept_part = p.get('dept_code', '')
    if len(ccode) >= 9:
        # e.g. MG1DSCMAT100 -> MAT
        sub3 = ccode[5:8] if ccode.startswith('MG') and len(ccode) >= 8 else dept_part
        if sub3 in PARENT_LOOKUP:
            dept_part = sub3

    if dept_part in PARENT_LOOKUP:
        info = PARENT_LOOKUP[dept_part]
        p['parent_dept'] = info['dept_code']
        p['parent_dept_name'] = info['dept_name']
        p['dept_code'] = dept_part
        p['dept_name'] = info['programme']
        p['is_minor'] = info['is_minor']
        p['minor_name'] = info['programme'] if info['is_minor'] else ""
        matched_papers += 1
        if info['is_minor']:
            minor_papers += 1

print(f"Total papers: {len(papers)}")
print(f"Matched with user taxonomy: {matched_papers}")
print(f"Tagged as Minor papers: {minor_papers}")

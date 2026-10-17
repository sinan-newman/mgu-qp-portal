"""
Rebuilds departments.json and papers.json with the full 116 user-specified course codes,
60 academic departments, complete minor programs hierarchy, and CCR/MDE course types.
"""

import os
import json
import re
import csv
import io

PROJECT_DIR = r"C:\Users\Navirex\.gemini\antigravity\scratch\mgu-qp-portal"
DATA_DIR = os.path.join(PROJECT_DIR, "data")
PUBLIC_DATA_DIR = os.path.join(PROJECT_DIR, "public", "data")
SCRATCH_DIR = r"C:\Users\Navirex\.gemini\antigravity\scratch"

# Clean department name mapping
def clean_dept_name(s):
    s = s.strip()
    if s in ("Toursim", "Tourism", "Travel & Tourism Management"):
        return "Tourism & Travel Management"
    return s

# 116 User-uploaded codes CSV data
USER_CSV_DATA = """Code,Programme (Major/Minor),Department,Minor (Yes /No)
AAS,Applied Arts,Fine Arts ,False
ADS,Artificial Intelligence & Data Science,Artificial Intelligence & Data Science,False
ADN,Art & Design,Fine Arts ,True
AGD,Animation & Graphic Design,Animation & Graphic Design,False
AHY,Art History,Fine Arts ,True
AQC,Aquaculture,Aquaculture,False
ARB,Arabic,Arabic,False
AVE,Animation & VFX,Animation & Graphic Design,False
BBA,Business Administration,Business Administration,False
BBT,Botany & Biotechnology,Botany & Biotechnology,False
BCA,Computer Applications,Computer Applications,False
BCH,Biochemistry,Biochemistry,False
BHN,Bharatanatyam,Bharatanatyam,False
BIF,Bioinformatics,Bioinformatics,False
BSM,Sports Management,Sports Management,False
BLW,Business Laws,Commerce,True
BOT,Botany,Botany,False
BST,Business Studies,Commerce,True
BTG,Biotechnology,Biotechnology,False
BTS,Biological Techniques and Specimen Preparation,Biological Techniques and Specimen Preparation,False
CDG,Communication Design,Fine Arts ,True
CFS,Cyber Forensics,Cyber Forensics,False
CHE,Chemistry,Chemistry,False
CMA,Computer Applications ,Computer Applications ,True
CND,Clinical Nutrition & Dietetics,Clinical Nutrition & Dietetics,False
COM,Commerce,Commerce,False
CSC,Computer Science,Computer Science,False
CST,Cultural Studies in Tamil,Tamil,True
CVM,Computer Knowledge,Malayalam,True
DMD,Digital Media ,Animation & Graphic Design,True
DMP,Digital Media Production,Journalism & Mass Communication,True
DVC,Devolopment Communication,Tamil,True
ECC,Electronics with Computer Technology & Computer Science,Electronics with Computer Technology & Computer Science,False
ECO,Economics,Economics,False
ECT,Electronics with Computer Technology,Electronics ,False
ENG,English,English,False
EVS,Environmental Studies,Botany,True
FDG,Fashion Design,Fashion Technology,False
FHI,Functional Hindi,Hindi,True
FIM,Fitness Management,Physical Education,True
FNN,Food Nutrition,Tourism,True
FRH,French,French,False
FSC,Forensic Science,Forensic Science,False
FSQ,Food Science & Quality Control,Food Science & Quality Control,False
FTQ,Food Technology & Quality Assurance,Food Technology & Quality Assurance,False
GEO,Geology,Geology,False
GER,German,German,False
GMF,Garment Manufacturing,Fashion Technology,True
GRA,Graphic Art,Animation & Graphic Design,True
HBM,Hospitality Business Management,Toursim,True
HIN,Hindi,Hindi,False
HIS,History,History,False
HMC,Hotel Management & Culinary Science,Hotel Management & Culinary Science,False
HPY,Human Physiology,Clinical Nutrition & Dietetics,True
HSC,Home Science,Home Science,False
HTC,Horticulture,Botany,True
IAA,Interior Architecture and Artistry,Animation & Graphic Design,False
IAM,Industrial Automation,Electronics,True
ICH,Industrial Chemistry,Chemistry,True
ISH,Islamic History,Islamic History,False
JMC,Journalism & Mass Communication,Journalism & Mass Communication,False
KCN,Kathakali Chenda,Performing Arts,False
KMD,Kathakali Maddalam,Performing Arts,False
KSN,Kathakali Sangeetham,Performing Arts,False
KVS,Kathakali Vesham,Performing Arts,False
LGS,Linguistics,Hindi,True
LIH,English Literary History,English,True
LIS,Library & Information Science,Library & Information Science,True
LSC,Language Science,Arabic ,True
LST,Language Studies ,Arabic,True
MAL,Malayalam,Malayalam,False
MAT,Mathematics,Mathematics,False
MBG,Microbiology,Microbiology,False
MHN,Mohiniyattam,Performing Arts,False
MLM,Multimedia,Multimedia,False
MMD,Mridangam,Music,False
MOS,Mobile System,Electronics,True
MVL,Violin ,Music,False
MVN,Veena,Music,False
MVO,Vocal ,Music,False
NBC,Nutritional Biochemistry,Clinical Nutrition & Dietetics,True
PAI,Painting,Fine Arts ,False
PEG,Petroleum Engineering,Chemistry,True
PEJ,Print & Electronic Journalism,Journalism & Mass Communication,True
PES,Physical Education,Physical Education,False
PHL,Philosophy,Philosophy,False
PHY,Physics,Physics,False
PJM,"Political Science, Journalism & Mass Communication","Political Science, Journalism & Mass Communication",False
POL,Political Science,Political Science,False
PSY,Psychology,Psychology,False
PTP,Heritage Studies,Malayalam,True
SAC,Strength & Conditioning,Physical Education,True
SAN,Sanskrit,Sanskrit,False
SAT,Sequential Art,Animation & Graphic Design,True
SCL,Sculpture,Fine Arts ,False
SDV,Sound Design & Visual Editing,Multimedia,False
SHP,Literature Studies,Malayalam,True
SMG,Sports Management,Sports Management,False
SOC,Sociology,Sociology,False
SSD,Sanskrit (Vedanta),Sanskrit (Special),False
SSJ,Sanskrit (Jyotisha),Sanskrit (Special),False
SSN,Sanskrit (Nyaya),Sanskrit (Special),False
SSS,Sanskrit (Sahitya),Sanskrit (Special),False
SSV,Sanskrit (Vyakarana),Sanskrit (Special),False
STA,Statistics,Statistics,False
SWK,Social Work,Social Work,False
SYR,Syriac,Syriac,False
TAM,Tamil,Tamil,False
TRS,Translation Studies,English,True
TTM,Travel & Tourism Management,Travel & Tourism Management,False
TTP,Comparative Study,Malayalam ,True
TXL,Textiles,Fashion Technology,True
VCN,Visual Communication,Multimedia,False
VID,Visual Design ,Animation & Graphic Design,True
ZGY,Zoology,Zoology,False
ZIM,Zoology & Industrial Microbiology,Zoology & Industrial Microbiology,False
"""

# Department primary code mapping
DEPT_PRIMARY_CODES = {
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
    "Fine Arts": "AAS",
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

DEPT_ICONS = {
    "Commerce": "bi-briefcase",
    "English": "bi-book",
    "Malayalam": "bi-translate",
    "Mathematics": "bi-calculator",
    "Physics": "bi-lightning-charge",
    "Chemistry": "bi-eyedropper",
    "Botany": "bi-flower1",
    "Zoology": "bi-bug",
    "Computer Science": "bi-laptop",
    "Computer Applications": "bi-pc-display",
    "Economics": "bi-graph-up-arrow",
    "History": "bi-hourglass-split",
    "Political Science": "bi-bank",
    "Psychology": "bi-heart-pulse",
    "Hindi": "bi-quote",
    "Arabic": "bi-globe2",
    "Fine Arts": "bi-palette",
    "Music": "bi-music-note-beamed",
    "Performing Arts": "bi-mask",
    "Physical Education": "bi-activity",
    "Statistics": "bi-bar-chart",
    "Biochemistry": "bi-virus",
    "Biotechnology": "bi-dna",
    "Bioinformatics": "bi-cpu",
    "Geology": "bi-compass",
    "Electronics": "bi-broadcast",
    "Fashion Technology": "bi-scissors",
    "Journalism & Mass Communication": "bi-newspaper",
    "Tourism & Travel Management": "bi-airplane",
    "Business Administration": "bi-building",
    "Social Work": "bi-people",
    "Sociology": "bi-diagram-3",
    "Philosophy": "bi-lightbulb",
    "Sanskrit": "bi-feather",
    "Tamil": "bi-card-text",
    "French": "bi-translate",
    "German": "bi-translate",
    "Syriac": "bi-book-half"
}

TYPE_NAMES = {
    "DSC": "Discipline Specific Core",
    "DSE": "Discipline Specific Elective",
    "SEC": "Skill Enhancement Course",
    "VAC": "Value Added Course",
    "MDC": "Multidisciplinary Course",
    "AEC": "Ability Enhancement Course",
    "CCR": "Core Course (BBA/BCA)",
    "MDE": "Multidisciplinary Elective (BBA/BCA)",
    "MIN": "Minor Course"
}

def parse_user_metadata():
    reader = csv.reader(io.StringIO(USER_CSV_DATA.strip()))
    header = next(reader)
    rows = [r for r in reader if r and len(r) >= 4 and r[0].strip()]

    code_info = {}
    dept_groups = {}

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

        if dept not in dept_groups:
            dcode = DEPT_PRIMARY_CODES.get(dept, code)
            dept_groups[dept] = {
                "code": dcode,
                "name": dept,
                "icon": DEPT_ICONS.get(dept, "bi-mortarboard"),
                "description": f"Curriculum and question papers for {dept}.",
                "majors": [],
                "minors": []
            }

        if minor:
            dept_groups[dept]["minors"].append({"code": code, "name": prog})
        else:
            dept_groups[dept]["majors"].append({"code": code, "name": prog})

    # Sort departments alphabetically
    sorted_departments = sorted(dept_groups.values(), key=lambda d: d["name"])
    
    # Save departments.json
    for out_dir in [DATA_DIR, PUBLIC_DATA_DIR]:
        with open(os.path.join(out_dir, "departments.json"), "w", encoding="utf-8") as f:
            json.dump(sorted_departments, f, indent=2)

    print(f"Saved {len(sorted_departments)} departments to departments.json")
    return code_info, dept_groups

def parse_course_code_rich(code, code_info, dept_groups):
    if not code:
        return None

    # Matches MG[1-8](DSC|DSE|SEC|VAC|MDC|AEC|CCR|MDE|MIN)([A-Z]{3})([A-Z0-9]+)
    m = re.match(r'^MG([1-8])([A-Z]{3})([A-Z]{3})([A-Z0-9]+)$', code, re.IGNORECASE)
    if m:
        sem = int(m.group(1))
        ctype = m.group(2).upper()
        dept_code = m.group(3).upper()
        cnum = m.group(4).upper()

        info = code_info.get(dept_code)
        if info:
            dname = info["department"]
            pdept_code = dept_groups[dname]["code"] if dname in dept_groups else dept_code
            is_minor = info["is_minor"] or (ctype == "MIN")
            prog_name = info["programme"]
            return {
                "semester": sem,
                "course_type": ctype,
                "course_type_name": TYPE_NAMES.get(ctype, ctype),
                "dept_code": dept_code,
                "dept_name": prog_name,
                "parent_dept": pdept_code,
                "parent_dept_name": dname,
                "is_minor": is_minor,
                "minor_name": prog_name if is_minor else "",
                "course_number": cnum
            }
        else:
            return {
                "semester": sem,
                "course_type": ctype,
                "course_type_name": TYPE_NAMES.get(ctype, ctype),
                "dept_code": dept_code,
                "dept_name": dept_code,
                "parent_dept": dept_code,
                "parent_dept_name": dept_code,
                "is_minor": (ctype == "MIN"),
                "minor_name": "" if ctype != "MIN" else "Minor Course",
                "course_number": cnum
            }

    return None

def rebuild_database():
    code_info, dept_groups = parse_user_metadata()

    # Load existing papers
    with open(os.path.join(DATA_DIR, "papers.json"), "r", encoding="utf-8") as f:
        existing_papers = json.load(f)

    updated_papers = []
    minor_count = 0

    for p in existing_papers:
        # Exclude CBCS strictly
        if p.get("batch") == "CBCS" or p.get("course_type") == "CBCS":
            continue

        ccode = p.get("course_code", "").upper()
        parsed = parse_course_code_rich(ccode, code_info, dept_groups)

        if parsed:
            p["semester"] = parsed["semester"]
            p["semester_label"] = f"Semester {parsed['semester']}"
            p["course_type"] = parsed["course_type"]
            p["course_type_name"] = parsed["course_type_name"]
            p["dept_code"] = parsed["dept_code"]
            p["dept_name"] = parsed["dept_name"]
            p["parent_dept"] = parsed["parent_dept"]
            p["parent_dept_name"] = parsed["parent_dept_name"]
            p["is_minor"] = parsed["is_minor"]
            p["minor_name"] = parsed["minor_name"]
        else:
            # Fallback to existing or check dept_code
            d_code = p.get("dept_code", "").upper()
            if d_code in code_info:
                info = code_info[d_code]
                dname = info["department"]
                p["parent_dept"] = dept_groups[dname]["code"] if dname in dept_groups else d_code
                p["parent_dept_name"] = dname
                p["dept_name"] = info["programme"]
                p["is_minor"] = info["is_minor"]
                p["minor_name"] = info["programme"] if info["is_minor"] else ""

        if p.get("is_minor"):
            minor_count += 1

        updated_papers.append(p)

    # Save to data/ and public/data/
    for out_dir in [DATA_DIR, PUBLIC_DATA_DIR]:
        with open(os.path.join(out_dir, "papers.json"), "w", encoding="utf-8") as f:
            json.dump(updated_papers, f, indent=2)

    # Update stats
    with_files = [p for p in updated_papers if p["has_files"]]
    qps = [p for p in updated_papers if p["has_qp"]]
    schemes = [p for p in updated_papers if p["has_scheme"]]
    
    unique_parent_depts = set(p["parent_dept"] for p in updated_papers if p["parent_dept"] != "GEN")

    stats = {
        "total_records": len(updated_papers),
        "records_with_files": len(with_files),
        "total_question_papers": len(qps),
        "total_schemes": len(schemes),
        "departments_count": len(dept_groups),
        "minor_papers_count": minor_count,
        "batch_scope": "FYUGP (MGU-UGP Honours) Only",
        "last_sync": "2026-10-17 13:50 UTC"
    }

    for out_dir in [DATA_DIR, PUBLIC_DATA_DIR]:
        with open(os.path.join(out_dir, "stats.json"), "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2)

    print(f"Rebuilt papers.json: {len(updated_papers)} FYUGP papers.")
    print(f"Tagged {minor_count} papers as Minor with their specific minor headings!")
    print(f"Total departments in stats: {len(dept_groups)}")

if __name__ == "__main__":
    rebuild_database()

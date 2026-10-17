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

import csv
import io
import json
import os

reader = csv.reader(io.StringIO(USER_CSV_DATA.strip()))
header = next(reader)
rows = [r for r in reader if r and len(r) >= 4 and r[0].strip()]

print(f"Total rows parsed: {len(rows)}")

# Group by Department
dept_map = {}
code_to_entry = {}

# Clean dept name mapping (standardize e.g. "Toursim" -> "Tourism", trailing spaces)
def clean_name(s):
    s = s.strip()
    if s == "Toursim":
        return "Tourism"
    return s

for code, prog, dept, is_minor in rows:
    code = code.strip()
    prog = prog.strip()
    dept = clean_name(dept)
    minor = is_minor.strip().lower() in ("true", "yes", "1")
    code_to_entry[code] = {
        "code": code,
        "programme": prog,
        "department": dept,
        "is_minor": minor
    }
    if dept not in dept_map:
        dept_map[dept] = {"majors": [], "minors": []}
    if minor:
        dept_map[dept]["minors"].append({"code": code, "name": prog})
    else:
        dept_map[dept]["majors"].append({"code": code, "name": prog})

print(f"Total departments: {len(dept_map)}")
print("\nDepartments and their minors:")
for d, info in sorted(dept_map.items()):
    minors = [f"{m['name']} ({m['code']})" for m in info["minors"]]
    majors = [f"{m['name']} ({m['code']})" for m in info["majors"]]
    print(f"- {d}: Majors={majors} | Minors={minors}")

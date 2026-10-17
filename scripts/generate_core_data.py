# Python script to generate departments.json and model_courses.json
import json
import os
import re

DEPARTMENTS = [
    {
        "code": "ENG",
        "name": "English",
        "category": "Humanities & Languages",
        "icon": "bi-book",
        "description": "English Language, Literature, Translation Studies and Historical Literary Studies.",
        "minors": [
            {"code": "LIH", "name": "Literature in History (English)"},
            {"code": "TRS", "name": "Translation Studies (English)"}
        ]
    },
    {
        "code": "MAL",
        "name": "Malayalam",
        "category": "Humanities & Languages",
        "icon": "bi-translate",
        "description": "Malayalam Language, Literature, Culture and Kerala Heritage Studies.",
        "minors": [
            {"code": "PTP", "name": "Kerala Samskaram & Heritage (PTP)"}
        ]
    },
    {
        "code": "COM",
        "name": "Commerce",
        "category": "Commerce & Management",
        "icon": "bi-briefcase",
        "description": "Commerce, Corporate Accounting, Finance, Marketing, Business Law & Studies.",
        "minors": [
            {"code": "BST", "name": "Business Studies & Sustainable Development"},
            {"code": "BLW", "name": "Business Law & Corporate Regulations"}
        ]
    },
    {
        "code": "MAT",
        "name": "Mathematics",
        "category": "Science",
        "icon": "bi-calculator",
        "description": "Calculus, Linear Algebra, Real Analysis, Number Theory & Applied Mathematics.",
        "minors": []
    },
    {
        "code": "PHY",
        "name": "Physics",
        "category": "Science",
        "icon": "bi-lightning-charge",
        "description": "Classical & Modern Physics, Quantum Mechanics, Electronics and Optics.",
        "minors": []
    },
    {
        "code": "CHE",
        "name": "Chemistry",
        "category": "Science",
        "icon": "bi-eyedropper",
        "description": "Organic, Inorganic, Physical, Food and Environmental Chemistry.",
        "minors": []
    },
    {
        "code": "BOT",
        "name": "Botany",
        "category": "Science",
        "icon": "bi-flower1",
        "description": "Plant Sciences, Systematics, Molecular Biology and Ecology.",
        "minors": []
    },
    {
        "code": "ZGY",
        "name": "Zoology",
        "category": "Science",
        "icon": "bi-bug",
        "description": "Animal Diversity, Genetics, Cell Biology and Wildlife Management.",
        "minors": []
    },
    {
        "code": "BCH",
        "name": "Biochemistry",
        "category": "Science",
        "icon": "bi-virus",
        "description": "Molecular Biochemistry, Metabolism, Nutrition and Forensic Science.",
        "minors": []
    },
    {
        "code": "BTG",
        "name": "Biotechnology",
        "category": "Science",
        "icon": "bi-dna",
        "description": "Applied Biotechnology, Molecular Biology, Tissue Culture.",
        "minors": [
            {"code": "BTS", "name": "Biological Techniques & Services"}
        ]
    },
    {
        "code": "BIF",
        "name": "Bioinformatics",
        "category": "Science",
        "icon": "bi-diagram-3",
        "description": "Sequence Informatics, Computational Biology, Biological Databases.",
        "minors": []
    },
    {
        "code": "CSC",
        "name": "Computer Science & IT",
        "category": "Computer Science & Tech",
        "icon": "bi-laptop",
        "description": "Programming, Web Tech, Green Computing, Security and Software Systems.",
        "minors": [
            {"code": "BCA", "name": "Computer Applications"},
            {"code": "DAT", "name": "Data Analytics"}
        ]
    },
    {
        "code": "ECO",
        "name": "Economics",
        "category": "Social Sciences",
        "icon": "bi-graph-up",
        "description": "Micro & Macro Economics, Econometrics, Quantitative Economics and Fintech.",
        "minors": []
    },
    {
        "code": "HIS",
        "name": "History",
        "category": "Social Sciences",
        "icon": "bi-hourglass-split",
        "description": "Indian History, Global History, Historiography and Archaeology.",
        "minors": [
            {"code": "AHY", "name": "Art History"}
        ]
    },
    {
        "code": "POL",
        "name": "Political Science",
        "category": "Social Sciences",
        "icon": "bi-shield-shaded",
        "description": "Indian Constitution, Everyday Politics, International Relations & Human Rights.",
        "minors": []
    },
    {
        "code": "PSY",
        "name": "Psychology",
        "category": "Social Sciences",
        "icon": "bi-heart-pulse",
        "description": "Foundations of Psychology, Child Development, Cognitive Operations & Health.",
        "minors": []
    },
    {
        "code": "STA",
        "name": "Statistics",
        "category": "Science",
        "icon": "bi-bar-chart",
        "description": "Fundamentals of Statistics, Data Visualization, Statistical Modelling & R.",
        "minors": []
    },
    {
        "code": "HIN",
        "name": "Hindi",
        "category": "Humanities & Languages",
        "icon": "bi-chat-quote",
        "description": "Hindi Literature, Communicative Hindi, Cinema and Translation.",
        "minors": []
    },
    {
        "code": "PES",
        "name": "Physical Education",
        "category": "Health & Sports",
        "icon": "bi-activity",
        "description": "Physical Fitness, Health, Sports Science and Weight Management.",
        "minors": []
    },
    {
        "code": "ARB",
        "name": "Arabic",
        "category": "Humanities & Languages",
        "icon": "bi-globe2",
        "description": "Arabic Heritage, Literature and Communication.",
        "minors": []
    },
    {
        "code": "GEO",
        "name": "Geology",
        "category": "Science",
        "icon": "bi-compass",
        "description": "Earth Sciences, Petrology, Field Training and Mineralogy.",
        "minors": []
    },
    {
        "code": "SAN",
        "name": "Sanskrit",
        "category": "Humanities & Languages",
        "icon": "bi-feather",
        "description": "Sanskrit Literature, Grammar and Indian Philosophy.",
        "minors": [
            {"code": "SKT", "name": "Sanskrit"}
        ]
    },
    {
        "code": "MUS",
        "name": "Music & Performing Arts",
        "category": "Fine Arts",
        "icon": "bi-music-note-beamed",
        "description": "Musicology, Bharathanatyam and Performing Arts.",
        "minors": [
            {"code": "BHN", "name": "Bharathanatyam"}
        ]
    }
]

# Raw CSV content provided in the prompt
RAW_CSV = """Course Code,Note
MG1AECENG100,English for Science part I
MG1AECENG101,English for Arts and Humanities part I
MG1AECENG102,English for Commerce Part I
MG1AECHIN100,Environment in Hindi Literature – For Science
MG1AECHIN101,New Media in Hindi Stories – For Humanities
MG1AECHIN102,Drama And Communicative Hindi – For Commerce
MG1AECMAL100,Sahithemalika(Science)
MG1AECMAL101,Sargasahiti(Humanities)
MG1AECMAL102,Bhashasahiti(Commerce)
MG1DSCBCH100,Biochemistry-The Science of Life
MG1DSCBLW100,Corporate Regulations and Compliance
MG1DSCBOT100,Fascinating World of Plant Sciences
MG1DSCBST100,Marketing Management
MG1DSCBTG100,Fundamentals for Biotechnology
MG1DSCCHE100,Fundamentals of Chemistry-I
MG1DSCCOM100,Basic Finance for Daily Life
MG1DSCECO100,Essentials of Economics - I
MG1DSCENG100,"Literary Genres: Poetry, Fiction and Folktales"
MG1DSCHIN100,"Learn, Write, Go Ahead"
MG1DSCHIS100,Introducing History
MG1DSCLIH100,Anglo-Saxon Aesthetics to Renaissance Rhetoric: Makers of English Literature
MG1DSCMAL100,Kadhanuroopanam
MG1DSCMAT100,Ground Roots of Mathematics
MG1DSCPHY100,Foundations of Physics
MG1DSCPOL100,Everyday Politics
MG1DSCPSY100,Psychology for Personal Growth
MG1DSCPTP100,Kerala Samskaram - Poorvakhattam
MG1DSCSTA100,Fundamentals of Statistics and Data Visualisation
MG1DSCTRS100,Malayalam Literature in English Translation
MG1DSCZGY100,Introduction to Zoology
MG1DSCZGY101,Biological Basis of Behaviour-I
MG1MDCBCH100,Sports Biochemistry: The Science of Exercise and Human Performance
MG1MDCBOT100,Ecotourism
MG1MDCBTG100,Ecology and Environmental Science
MG1MDCCHE100,Food Chemistry and Nutrition
MG1MDCCOM100,Business Organisation and Entrepreneurship
MG1MDCCSC101,Internet and Web Technologies
MG1MDCECO100,Economics and Finance in Everyday Life
MG1MDCENG100,Folk Tales and Songs from India
MG1MDCENG101,Narratives of Humour
MG1MDCENG102,Content Writing
MG1MDCHIN100,Lovely Hindi
MG1MDCHIS101,Science and Society
MG1MDCMAL101,Cinemayum Sahityavum
MG1MDCPES101,Physical Fitness and Healthy Living
MG1MDCPHY100,Physics Around You
MG1MDCPOL100,Introduction to India’s Foreign Policy
MG1MDCPSY100,Communicate with Confidence
MG1MDCSTA101,Data Analysis Using Libre Calc
MG2AECENG100,English for Science - Part II
MG2AECENG101,English for Arts and Humanities - Part II
MG2AECENG102,English for Commerce - Part II
MG2AECHIN100,New Text New Aesthetics (Science)
MG2AECHIN101,Harmony of Festivals (Humanities)
MG2AECHIN102,Modern Hindi Prose and Translation (Commerce)
MG2AECMAL100,Kalamanjari (Science)
MG2AECMAL101,Drishyapadham (Humanities)
MG2AECMAL102,Gadyaraji (Commerce)
MG2DSCBCH100,"Essentials of Biochemistry: Vitamins, Hormones, Enzymes and Neurotransmitters"
MG2DSCBLW100,Business Regulatory Framework
MG2DSCBOT100,Plant Resources and Ventures in Botany
MG2DSCBST100,Business and Sustainable Development
MG2DSCBTG100,Applied Biotechnology
MG2DSCCHE100,Fundamentals of Chemistry - II
MG2DSCCOM100,Indian Securities Market : Structure and Operations
MG2DSCECO100,Essentials of Economics - II
MG2DSCENG100,"Literary Genres: Prose, Drama and Film"
MG2DSCHIN100,Writing Process
MG2DSCHIS100,Themes in Global History
MG2DSCLIH100,From Restoration Rationalism to Romantic Rhapsodies: Makers of English Literature
MG2DSCMAL100,Kavyabhavana
MG2DSCMAT100,A Gateway to Mathematics
MG2DSCPHY100,Modern Physics
MG2DSCPOL100,Introduction to Indian Constitution
MG2DSCPSY100,Psychology as a Profession
MG2DSCPTP100,Keralasamskaram - Utharaghattam
MG2DSCSTA100,Introduction to Statistical Modelling
MG2DSCTRS100,Indian Literatures in English Translation
MG2DSCZGY100,Environmental Biology
MG2DSCZGY101,Biological Basis of Behavior II
MG2MDCBCH100,Biochemistry in Entrepreneurship
MG2MDCBOT100,Gardening and Landscaping
MG2MDCBTG100,Tools and Techniques in Biotechnology
MG2MDCCHE100,Dairy Chemistry
MG2MDCCOM100,Fundamentals of Accounting
MG2MDCCOM101,Event Management
MG2MDCCSC101,Mastering Spreadsheets
MG2MDCECO100,Understanding Indian Economy
MG2MDCENG100,Narratives of Love and Friendship
MG2MDCENG101,Sports Literature and Cinema
MG2MDCENG102,Fundamentals of Advertising and Public Relations
MG2MDCHIN102,Women in Contemporary Hindi Cinema
MG2MDCHIS101,Human and Environment
MG2MDCMAL101,Janapriya Samskaram
MG2MDCPES100,Physical Education - Foundation & Career prospect
MG2MDCPHY100,Observational Astronomy
MG2MDCPOL101,Politics of Human Security
MG2MDCPSY100,Psychology of Friendship and Love
MG2MDCSTA101,Data Analysis using JAMOVI and Introduction to R
MG3DSCBCH202,Techniques in Biochemistry and Forensic Science
MG3DSCBLW200,GST Laws : Fundamentals
MG3DSCBOT200,Microbiology and Phycology
MG3DSCBOT201,Mycology and Plant Pathology
MG3DSCBOT202,Thallophytes and Archegoniates
MG3DSCBTG202,Fundamentals of Molecular Biology
MG3DSCCHE200,Inorganic Chemistry - I
MG3DSCCHE201,Organic Chemistry - I
MG3DSCCHE202,Inorganic and Organic Chemistry
MG3DSCCOM200,Financial Accounting
MG3DSCCOM201,Quantitative Techniques for Business
MG3DSCECO200,Microeconomics - I
MG3DSCECO201,Quantitative Economics - I
MG3DSCECO202,Basics of Fintech Entrepreneurship
MG3DSCENG200,An Introduction to Phonetics
MG3DSCENG201,Appreciating Poetry
MG3DSCENG202,Detective Fiction
MG3DSCHIN202,Children’s Play in Hindi
MG3DSCHIS200,Society in Pre-Modern Kerala
MG3DSCHIS201,Understanding Early India
MG3DSCHIS202,Origins of the Modern World
MG3DSCLIH200,Victorian Vistas and Imperial Imaginings : Makers of English Literature
MG3DSCMAL200,Naveenakavitha
MG3DSCMAL201,Vaikom Muhammad Basheer
MG3DSCMAL202,Novalsahithyam
MG3DSCMAT200,Perspectives of Mathematics
MG3DSCMAT201,Building Blocks for Higher Mathematics
MG3DSCMAT202,Essentials of Applied Mathematics
MG3DSCPHY200,Principles of Mechanics
MG3DSCPHY201,Essential Mathematics for Physics
MG3DSCPHY202,Atomic and Molecular Spectroscopy
MG3DSCPOL203,Human Rights in India
MG3DSCPSY200,Foundations of Psychology
MG3DSCPSY201,Child Development
MG3DSCPSY202,Psychological First Aid
MG3DSCPTP200,Nattarivupadanam
MG3DSCSTA203,Statistical Research Techniques using Softwares
MG3DSCTRS200,World Literatures in English Translation
MG3DSCZGY200,Protistan Diversity and Animal Diversity - Non Chordata - I
MG3DSCZGY201,Animal Diversity - Non Chordata - II
MG3DSCZGY203,Biological Basis of Behavior - III
MG3DSEBOT200,Ethnobotany and Intellectual Property Rights
MG3DSECHE201,Introduction to Nanoscience
MG3DSECOM202,Services Marketing
MG3DSECOM203,Financial Services
MG3DSECOM204,Public Finance
MG3DSEECO203,Monetary Economics
MG3DSEENG201,"Reading Culture: Food, Travel and Music"
MG3DSEHIS200,The Ancient Social Formations from Hunter Gatherers to the Classical Antiquity
MG3DSEMAL200,Sancharasahithyam
MG3DSEMAT202,Numerical Methods
MG3DSEPHY200,Basic Semiconductor Physics
MG3DSEPSY201,Positive Psychology
MG3DSEZGY200,Ethology
MG3DSEZGY201,Value Added Products of Animals
MG3MDCENG200,Literature and Kerala Renaissance
MG3MDCHIN200,"Equality, Freedom and Brotherhood"
MG3MDCMAL200,Keralapadanam
MG3VACBOT200,Bioethics and IPR
MG3VACBTG200,Environmental Biotechnology and Human Rights
MG3VACCHE200,Forensic Chemistry
MG3VACCSC200,White Hat Hacking
MG3VACENG200,Literature and Gender
MG3VACENG201,"Literature, Technology and AI"
MG3VACHIN200,We are One
MG3VACMAL200,Athijeevanapadangal
MG3VACMAL201,Paristhithipadangal
MG3VACPES201,Lifestyle Diseases & Physical Activity
MG3VACPHY200,Science and Society
MG3VACPOL200,Secularism and Cultural Diversity
MG3VACSTA200,"Applied Statistical Analysis : Ethical Data Collection, Interpretation and Decision Making in Society"
MG4DSCBCH202,"Metabolism of Carbohydrates, Proteins and Lipids"
MG4DSCBOT200,Archegoniates
MG4DSCBOT201,Plant Anatomy and Reproductive Botany
MG4DSCBOT202,Introduction to Flowering Plants and their Economic Importance
MG4DSCBST200,Digital and Social Media Marketing and Brand Communication
MG4DSCBTG202,Tissue Culture Techniques
MG4DSCCHE200,Organic Chemistry - 2
MG4DSCCHE201,Physical Chemistry - 1
MG4DSCCHE202,Fundamentals of Physical Chemistry
MG4DSCCOM200,Corporate Accounting
MG4DSCCOM201,Quantitative Techniques for Business Decisions
MG4DSCECO200,Macroeconomics - I
MG4DSCECO201,Quantitative Economics - II
MG4DSCECO202,Economics of Marketing
MG4DSCENG200,Indian Writing in English
MG4DSCENG201,Reading Prose and Fiction
MG4DSCHIS200,History of Modern Kerala
MG4DSCHIS201,Perspectives on Pre-Colonial India
MG4DSCHIS202,Understanding the Modern World
MG4DSCLIH200,Moods of Modernism and Poetics of the Postmodern: Makers of English Literature
MG4DSCMAL200,Malayalakavitha - Kavithrayamvare
MG4DSCMAL201,"Cherukatha, Novel"
MG4DSCMAL202,S. K. Pottakkat
MG4DSCMAT200,Matrix Algebra and Number Theory
MG4DSCMAT201,Fundamentals of Analysis
MG4DSCMAT202,Applied Mathematical Methods
MG4DSCPHY200,Wave Optics
MG4DSCPHY201,Electromagnetic Theory
MG4DSCPHY202,Basic Electronics and Electricity
MG4DSCPOL203,Global Affairs: Concepts and Contemporary Issues in International Relations
MG4DSCPSY200,Fundamentals of Cognitive Operations
MG4DSCPSY201,Self and Social Interactions
MG4DSCPSY202,Psychology of Marketing and Advertisements
MG4DSCPTP200,Keraleeyadrusyakala
MG4DSCSTA203,Applied Statistical Methods
MG4DSCTRS200,Translation for the Media
MG4DSCZGY200,Animal Diversity Chordata - I
MG4DSCZGY201,Biological Chemistry
MG4DSCZGY203,Biological Basis of Behavior - IV
MG4DSEBOT200,Food Science and Quality Control
MG4DSECHE201,Food Chemistry
MG4DSECOM201,Co-operative Legislations
MG4DSECOM204,Trends and Innovations in Banking
MG4DSECOM205,Essentials of Supply Chain Management
MG4DSEECO204,Agricultural Economics
MG4DSEENG201,"Reading Culture: Comics, Cartoons and Fairy Tales"
MG4DSEHIS200,World History from Early Medieval to Early Modern Period
MG4DSEMAL200,Jeevithamezhuthth
MG4DSEMAT201,Transforms and Fourier Series
MG4DSEPHY202,"Exploring the Cosmos: Observations, Celestial Bodies, and Cosmic Evolution"
MG4DSEPSY200,Exploring Health Psychology
MG4DSEZGY201,"Health, Nutrition and Wellness"
MG4SECENG200,English for International Careers
MG4SECENG201,English for Professional Purposes
MG4SECENG202,English for the Financial Sector
MG4SECHIN200,Let's Speak Hindi
MG4SECMAL201,Malsarapareekshakalile Malayalam
MG4SECMAT200,Document Preparation using LaTeX
MG4SECPES201,Exercise and Weight Management
MG4VACBTG200,Human Resource Management in Biotechnology
MG4VACCHE200,Basic Environmental Chemistry
MG4VACCSC200,Green Computing Techniques
MG4VACENG200,Literature and Environment
MG4VACENG201,Literature and Law
MG4VACHIN200,Let Gandhi Live Let Peace Prevail
MG4VACMAL201,Samoohyaneethipadanam
MG4VACMAT200,Business Mathematics
MG4VACPOL200,Legal Literacy and Legal Awareness
MG4VACPSY200,Social Values for Enhancing Human Dignity
MG5DSCBOT300,Angiosperm Systematics and Economic Botany
MG5DSCBOT301,Plant Cell and Molecular Biology
MG5DSCCHE300,Organic Chemistry – 3
MG5DSCCHE301,Physical Chemistry – 2
MG5DSCCOM300,Income Tax – I
MG5DSCCOM301,Cost Accounting
MG5DSCCOM302,Financial Management
MG5DSCECO300,Econometrics -I
MG5DSCECO301,International Economics
MG5DSCENG300,American Literature
MG5DSCENG301,An Introduction to Literary Criticism
MG5DSCENG302,Reading Shakespeare
MG5DSCHIS300,India: Making of the Nation
MG5DSCHIS301,Historiography I – The Inheritances
MG5DSCHIS302,History of Capitalism
MG5DSCMAL300,Bhashaasasthram
MG5DSCMAL301,Pracheenasahithyam
MG5DSCMAL302,Natakapadanam
MG5DSCMAT300,A First Course in Complex Analysis
MG5DSCMAT301,Limits and Convergence
MG5DSCMAT302,Fundamentals of Groups and Rings
MG5DSCPHY300,Classical Mechanics
MG5DSCPHY301,Introduction to Quantum Mechanics
MG5DSCPHY302,Atomic and Molecular Physics
MG5DSCPSY300,Dynamics of Research in Psychology
MG5DSCPSY301,Individual Behavior in Organization
MG5DSCPSY302,Fundamentals of Abnormal Psychology
MG5DSCZGY300,Animal Diversity Chordata - II
MG5DSCZGY301,Cell Biology and Molecular Biology
MG5DSCZGY302,Fundamentals of Genetics
MG5DSEBOT301,"Phytogeography, Forestry and Ecotourism"
MG5DSEBOT302,Plant Biotechnology
MG5DSEBOT304,Analytical Techniques in Plant Science
MG5DSECHE300,"Quantum Mechanics, Spectroscopy & Group Theory"
MG5DSECHE302,Environmental Chemistry
MG5DSECHE305,Main Group Elements
MG5DSECOM301,Administration and Management of Co-operative Societies
MG5DSECOM302,Brand Management
MG5DSECOM303,Legal Framework for Financial Markets
MG5DSECOM304,Advanced GST Laws
MG5DSECOM305,Procurement and Global Sourcing
MG5DSEECO301,Financial Regulation and Supervision
MG5DSEECO304,Public Economics -I
MG5DSEECO306,Business Economics
MG5DSEENG302,Literature and Ecology
MG5DSEENG303,Reading Culture: Literature and Fine Arts
MG5DSEHIS300,Gender and Indian History
MG5DSEHIS303,Transition to Contemporary Times
MG5DSEMAL300,Samakalikasahithyam
MG5DSEMAL301,Bharatheeyasahithyasidhanthangal
MG5DSEMAT300,Differential Equations and Applications
MG5DSEMAT302,An Invitation to Fuzzy Mathematics
MG5DSEPHY301,Computational Physics: Python
MG5DSEPHY302,Physics of Atmosphere
MG5DSEPSY301,Blooming Through Adolescence
MG5DSEPSY302,Indian Psychology
MG5DSEZGY300,Biotechnology - Principles and Practices
MG5DSEZGY301,Wildlife Management
MG5SECBOT300,Mushroom Production and Value Addition
MG5SECCHE300,Analytical Techniques and Chemistry of Cosmetics
MG5SECCOM300,Computerised Accounting
MG5SECECO301,Economics of Rural Entrepreneurship
MG5SECENG300,Critical Thinking and Academic Writing
MG5SECHIS300,Doing Oral History
MG5SECMAL300,Madhyamarachana
MG5SECMAT300,Introduction to Python for Mathematical Computation
MG5SECPHY300,Solar Cell Technology: From Fundamentals to Applications
MG5SECPSY300,Writing and Formatting Skills
MG5SECZGY300,Food and Water Quality Management
"""

# Major/Minor department mapping lookup
PARENT_DEPT_LOOKUP = {}
DEPT_NAMES = {}
for d in DEPARTMENTS:
    DEPT_NAMES[d["code"]] = d["name"]
    PARENT_DEPT_LOOKUP[d["code"]] = d["code"]
    for m in d.get("minors", []):
        PARENT_DEPT_LOOKUP[m["code"]] = d["code"]
        DEPT_NAMES[m["code"]] = m["name"]

TYPE_NAMES = {
    "DSC": "Discipline Specific Core",
    "DSE": "Discipline Specific Elective",
    "SEC": "Skill Enhancement Course",
    "VAC": "Value Added Course",
    "MDC": "Multi-Disciplinary Course",
    "AEC": "Ability Enhancement Course",
    "MIN": "Minor Course"
}

def parse_course_code(code):
    # Regex: MG(\d)(DSC|DSE|SEC|VAC|MDC|AEC|MIN)([A-Z]{3})(\d{3}[A-Z]?)
    m = re.match(r'MG([1-8])([A-Z]{3})([A-Z]{3})(\d+.*)', code)
    if m:
        sem = int(m.group(1))
        ctype = m.group(2)
        dept_code = m.group(3)
        cnum = m.group(4)
        parent_dept = PARENT_DEPT_LOOKUP.get(dept_code, dept_code)
        return {
            "semester": sem,
            "course_type": ctype,
            "course_type_name": TYPE_NAMES.get(ctype, ctype),
            "dept_code": dept_code,
            "dept_name": DEPT_NAMES.get(dept_code, dept_code),
            "parent_dept": parent_dept,
            "parent_dept_name": DEPT_NAMES.get(parent_dept, parent_dept),
            "is_minor": dept_code != parent_dept,
            "course_number": cnum
        }
    return None

import csv
import io

def generate_datasets():
    reader = csv.reader(io.StringIO(RAW_CSV.strip()))
    header = next(reader)
    
    model_courses = []
    for row in reader:
        if not row or not row[0].strip():
            continue
        code = row[0].strip()
        title = row[1].strip() if len(row) > 1 else ""
        parsed = parse_course_code(code)
        entry = {
            "course_code": code,
            "title": title,
            **(parsed if parsed else {
                "semester": 1,
                "course_type": "DSC",
                "course_type_name": "Discipline Specific Core",
                "dept_code": "GEN",
                "dept_name": "General",
                "parent_dept": "GEN",
                "parent_dept_name": "General",
                "is_minor": False,
                "course_number": "100"
            })
        }
        model_courses.append(entry)
        
    out_dir = r"C:\Users\Navirex\.gemini\antigravity\scratch\mgu-qp-portal\data"
    os.makedirs(out_dir, exist_ok=True)
    
    with open(os.path.join(out_dir, "departments.json"), "w", encoding="utf-8") as f:
        json.dump(DEPARTMENTS, f, indent=2)
        
    with open(os.path.join(out_dir, "model_courses.json"), "w", encoding="utf-8") as f:
        json.dump(model_courses, f, indent=2)
        
    print(f"Generated departments.json with {len(DEPARTMENTS)} departments.")
    print(f"Generated model_courses.json with {len(model_courses)} courses.")

if __name__ == "__main__":
    generate_datasets()

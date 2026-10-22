import json
import re
import os

PORTAL_DIR = r"C:\Users\Navirex\.gemini\antigravity\scratch\mgu-qp-portal"

papers_path = os.path.join(PORTAL_DIR, "data", "papers.json")
public_papers_path = os.path.join(PORTAL_DIR, "public", "data", "papers.json")

with open(papers_path, "r", encoding="utf-8") as f:
    papers = json.load(f)

# Comprehensive title fixes dictionary
title_fixes = {
    "MG2MDCSTA100": ("Time Series Methods and Their Applications", "STA", "Statistics"),
    "MG1MDCMAL01": ("സിനിമയും സാഹിത്യവും (Cinema and Literature)", "MAL", "Malayalam"),
    "MG3DSEHIN200": ("आधुनिक हिन्दी नाटक (Modern Hindi Drama)", "HIN", "Hindi"),
    "MG5DSEBCA301": ("Time Series Analysis", "BCA", "Computer Applications"),
    "MG5DSEPHY301": ("Computational Physics: Python", "PHY", "Physics"),
    "MG5DSEHIN306": ("Special Author: Chithra Mudgal", "HIN", "Hindi"),
    "MG5DSEPES301": ("Community Coaching", "PES", "Physical Education & Sports"),
    "MG5DSEPES303": ("Sports Marketing", "PES", "Physical Education & Sports"),
    "MG5DSEPES305": ("Sports Nutrition Essentials", "PES", "Physical Education & Sports"),
    "MG5DSEMAL300": ("Samakalika Sahityam (Contemporary Literature)", "MAL", "Malayalam"),
    "MG5DSEMAL302": ("പരസ്യകല - നവസാധ്യതകൾ (Advertising Art)", "MAL", "Malayalam"),
    "MG5DSEMAL303": ("Media Studies - Preshepanakala", "MAL", "Malayalam"),
    "MG5DSEMAL304": ("Multimedia Nirmanam (Multimedia Production)", "MAL", "Malayalam"),
    "MG5SECMAL300": ("Madhyama Rachana (Media Writing)", "MAL", "Malayalam"),
    "MG3VACBHN200": ("Bharathanatyam as a Cultural Source of South India", "BHN", "Bharathanatyam"),
    "MG4VACBHN200": ("Bharathanatyam and Yoga", "BHN", "Bharathanatyam"),
    "MG4VACMHN200": ("Mohiniyattam and Yoga", "MHN", "Mohiniyattam"),
    "MG4VACMMD200": ("Fundamental Lessons of Prominent Mridangam Schools in South India", "MMD", "Mridangam"),
    "MG4VACMMDA00": ("Major Laya Intricacies of Popular Concert Talas and Thani Avarthanam", "MMD", "Mridangam"),
    "MG3DCSESSV202": ("वेदाङ्गपरिचयः (Introduction to Vedangas)", "SSV", "Sanskrit Sahitya"),
    "MG3DSESSV201": ("संस्कृतनाट्यसाहित्यम् (Sanskrit Dramatic Literature)", "SSV", "Sanskrit Sahitya"),
    "MG3MDCMAL201": ("കേരളീയ വിജ്ഞാന വ്യവസ്ഥകൾ (Kerala Knowledge Systems)", "MAL", "Malayalam"),
    "MG2MDCSSS100": ("History of Sanskrit Literature", "SSS", "Sanskrit Sahitya")
}

# Clean titles that have prefix "Course Title: " or "COURSE NAME: "
def clean_prefix(t):
    if not t: return t
    cleaned = re.sub(r'^(Course\s*Title\s*[:\-–\ufffd]*|Course\s*Name\s*[:\-–\ufffd]*|Course\s*[:\-–\ufffd]*)', '', t.strip(), flags=re.I).strip()
    if cleaned and not cleaned.lower().startswith('course ') and not cleaned.lower().startswith('mg') and len(cleaned) > 4:
        # Title case if uppercase
        if cleaned.isupper() and len(cleaned) > 5:
            cleaned = cleaned.title()
        return cleaned
    return t

fixed_count = 0
for p in papers:
    cc = (p.get("course_code") or "").strip().upper()
    if cc in title_fixes:
        new_title, dept_c, dept_n = title_fixes[cc]
        p["title"] = new_title
        p["dept_code"] = dept_c
        p["dept_name"] = dept_n
        p["parent_dept"] = dept_c
        p["parent_dept_name"] = dept_n
        p["needs_review"] = False
        p["status"] = "published"
        p.pop("ambiguity_reason", None)
        fixed_count += 1
    else:
        orig = p.get("title", "")
        cleaned = clean_prefix(orig)
        if cleaned != orig:
            p["title"] = cleaned
            p["needs_review"] = False
            p["status"] = "published"
            p.pop("ambiguity_reason", None)
            fixed_count += 1

# Check final state
pending_review = [p for p in papers if p.get("needs_review") or p.get("status") == "pending_review" or p.get("dept_code") == "GEN"]
published = [p for p in papers if not (p.get("needs_review") or p.get("status") == "pending_review" or p.get("dept_code") == "GEN")]

print(f"Applied fixes to {fixed_count} papers.")
print(f"Total papers: {len(papers)}")
print(f"Published (visible to normal users): {len(published)}")
print(f"Pending review (quarantined): {len(pending_review)}")

for p in pending_review:
    print(f"  Pending: {p.get('id')} | Code: {p.get('course_code')} | Dept: {p.get('dept_code')} | Title: {p.get('title')}")

with open(papers_path, "w", encoding="utf-8") as f:
    json.dump(papers, f, indent=2, ensure_ascii=False)
with open(public_papers_path, "w", encoding="utf-8") as f:
    json.dump(papers, f, indent=2, ensure_ascii=False)

print("Saved papers.json successfully.")

# Also update model_papers.json
model_path = os.path.join(PORTAL_DIR, "data", "model_papers.json")
public_model_path = os.path.join(PORTAL_DIR, "public", "data", "model_papers.json")

with open(model_path, "r", encoding="utf-8") as f:
    models = json.load(f)

for m in models:
    cc = (m.get("course_code") or "").strip().upper()
    if cc in title_fixes:
        new_title, dept_c, dept_n = title_fixes[cc]
        m["title"] = new_title
        m["dept_code"] = dept_c
        m["dept_name"] = dept_n
    else:
        orig = m.get("title", "")
        cleaned = clean_prefix(orig)
        if cleaned != orig:
            m["title"] = cleaned

with open(model_path, "w", encoding="utf-8") as f:
    json.dump(models, f, indent=2, ensure_ascii=False)
with open(public_model_path, "w", encoding="utf-8") as f:
    json.dump(models, f, indent=2, ensure_ascii=False)

print("Saved model_papers.json successfully.")

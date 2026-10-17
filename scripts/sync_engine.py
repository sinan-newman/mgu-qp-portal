"""
sync_engine.py
==============
Unified Autonomous MGU FYUGP Sync Engine.
Designed to run either locally or inside GitHub Actions scheduled workflows:
1. Checks assist.mgu.ac.in for new FYUGP question papers / schemes.
2. Extracts course code from PDF headers if missing.
3. Downloads any new PDFs and mirrors them to mgu-qp-storage.
4. Updates data/papers.json and stats.json.
"""

import os
import sys
import re
import json
import time
import urllib.request
import urllib.parse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
DATA_FILE = os.path.join(PROJECT_DIR, "data", "papers.json")
STATS_FILE = os.path.join(PROJECT_DIR, "data", "stats.json")
PUBLIC_DATA_FILE = os.path.join(PROJECT_DIR, "public", "data", "papers.json")
PUBLIC_STATS_FILE = os.path.join(PROJECT_DIR, "public", "data", "stats.json")
DEPTS_FILE = os.path.join(PROJECT_DIR, "data", "departments.json")

STORAGE_DIR = os.path.abspath(os.path.join(PROJECT_DIR, "..", "mgu-qp-storage"))
PDF_DIR = os.path.join(STORAGE_DIR, "pdf")

BASE_URL = "https://assist.mgu.ac.in/schema/"
CDN_BASE = "https://cdn.jsdelivr.net/gh/sinancc1729/mgu-qp-storage@main/pdf"
RAW_BASE = "https://raw.githubusercontent.com/sinancc1729/mgu-qp-storage/main/pdf"

FYUGP_EXAMS = [
    {"id": "35", "semester": 5, "label": "Semester 5", "exam_name": "V Semester MGU UGP (Honours) - 2024 Admission regular Examination October 2026"},
    {"id": "34", "semester": 1, "label": "Semester 1", "exam_name": "First Semester MGU-UGP (HONOURS) Special Examination July 2026"},
    {"id": "31", "semester": 3, "label": "Semester 3", "exam_name": "III Semester MGU-UGP-(Hons) 2024 Admission Regular(Special Examination) Examination July 2026"},
    {"id": "27", "semester": 2, "label": "Semester 2", "exam_name": "Second semester BA/BSc/BVocFYUGP April 2026"},
    {"id": "21", "semester": 4, "label": "Semester 4", "exam_name": "MGU-UGP (HONOURS) 2024 Admission Regular Exam Sem 4, March 2026"},
    {"id": "7",  "semester": 1, "label": "Semester 1", "exam_name": "First Semester MGU-UGP/MGU-BBA/MGU-BCA Honours Examinations November 2025"},
    {"id": "6",  "semester": 3, "label": "Semester 3", "exam_name": "Third Semester MGU-UGP(Hons.) Regular Exam Oct 2025"},
    {"id": "4",  "semester": 2, "label": "Semester 2", "exam_name": "II Semester MGU UGP25 - March - 2025"},
    {"id": "1",  "semester": 1, "label": "Semester 1", "exam_name": "MGU-UGP (HONOURS) Regular Exam Sem 1, Nov 2024"},
]

def clean_html(text):
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&#039;', "'").replace('&quot;', '"')
    return re.sub(r'\s+', ' ', text).strip()

def fetch_exam_html(exam_id):
    data = urllib.parse.urlencode({"options": str(exam_id)}).encode("utf-8")
    req = urllib.request.Request(
        BASE_URL,
        data=data,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MGU-Portal-Sync/1.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=35) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"[Sync] Warning: Failed to fetch exam {exam_id}: {e}")
        return ""

def main():
    print(f"[Sync] Starting autonomous sync at {datetime.utcnow().isoformat()}Z...")
    
    # Load existing database
    if not os.path.exists(DATA_FILE):
        print("[Sync] Error: data/papers.json not found.")
        sys.exit(1)
        
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        existing_papers = json.load(f)
        
    existing_ids = {p["id"]: p for p in existing_papers}
    existing_file_urls = set()
    for p in existing_papers:
        for fl in p.get("files", []):
            u = fl.get("mgu_url") or fl.get("url", "")
            if u:
                existing_file_urls.add(u)
                
    print(f"[Sync] Current database has {len(existing_papers)} papers and {len(existing_file_urls)} tracked URLs.")
    
    # Check all FYUGP exam sessions
    new_papers_found = 0
    new_files_found = 0
    
    panel_pattern = re.compile(r'<div class="panel-heading"[^>]*>(.*?)</div>\s*<div[^>]*class="panel-collapse[^"]*"[^>]*>(.*?)</div>\s*</div>', re.DOTALL | re.IGNORECASE)
    btn_pattern = re.compile(r'<a[^>]*class="accordion-toggle"[^>]*>(.*?)</a>', re.DOTALL | re.IGNORECASE)
    file_pattern = re.compile(r'<a\s+href="([^"]+)"[^>]*>(.*?)</a>', re.DOTALL | re.IGNORECASE)
    
    for exam in FYUGP_EXAMS:
        html = fetch_exam_html(exam["id"])
        if not html:
            continue
            
        for m in panel_pattern.finditer(html):
            head_html = m.group(1)
            body_html = m.group(2)
            
            btn_m = btn_pattern.search(head_html)
            raw_header = clean_html(btn_m.group(1) if btn_m else head_html)
            if not raw_header:
                continue
                
            # Extract files
            files = []
            for fm in file_pattern.finditer(body_html):
                furl = fm.group(1).strip()
                ftype_raw = clean_html(fm.group(2)).upper()
                if not furl.startswith("http"):
                    furl = "https://assist.mgu.ac.in/schema/" + furl.lstrip("/")
                if furl.lower().endswith(".pdf"):
                    files.append((furl, ftype_raw))
                    if furl not in existing_file_urls:
                        new_files_found += 1
                        
    print(f"[Sync] Audit complete: Found {new_files_found} new PDF files on MGU portal.")
    if new_files_found == 0:
        print("[Sync] Database is already 100% up to date with MGU database.")
        sys.exit(0)
    else:
        print(f"[Sync] Found {new_files_found} new files to ingest and mirror!")
        # Trigger full pipeline rebuild if new files exist
        import subprocess
        subprocess.run(["python", os.path.join(SCRIPT_DIR, "build_papers_db.py")], check=True)
        subprocess.run(["python", os.path.join(SCRIPT_DIR, "enrich_all_unmapped.py")], check=True)
        subprocess.run(["python", os.path.join(SCRIPT_DIR, "backup_all_pdfs.py")], check=True)
        print("[Sync] Pipeline successfully synchronized all new files!")

if __name__ == "__main__":
    main()

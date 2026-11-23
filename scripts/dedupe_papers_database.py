import json
import shutil
import os
from collections import defaultdict

DATA_PATH = "data/papers.json"
PUB_DATA_PATH = "public/data/papers.json"
BACKUP_PATH = "data/papers.json.bak"

def dedupe_database():
    print("=== MGU Question Papers Database Deduplication Engine ===")
    
    # 1. Backup
    shutil.copy2(DATA_PATH, BACKUP_PATH)
    print(f"[Backup] Created backup at {BACKUP_PATH}")
    
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        papers = json.load(f)
        
    initial_count = len(papers)
    print(f"[Initial] Total paper records: {initial_count}")
    
    # 2. Clean Exam 6 files (remove erroneously injected CR31 files)
    cr31_cleaned_files = 0
    for p in papers:
        if str(p.get("exam_id")) == "6":
            old_files = p.get("files", [])
            new_files = [fl for fl in old_files if "DOC-CR31" not in fl.get("url", "")]
            if len(new_files) != len(old_files):
                cr31_cleaned_files += (len(old_files) - len(new_files))
                p["files"] = new_files
                qp_f = next((fl for fl in new_files if fl.get("type") == "QP"), None)
                sch_f = next((fl for fl in new_files if fl.get("type") == "SCHEME"), None)
                p["has_qp"] = qp_f is not None
                p["qp_url"] = qp_f["url"] if qp_f else ""
                p["has_scheme"] = sch_f is not None
                p["scheme_url"] = sch_f["url"] if sch_f else ""
    print(f"[Exam 6] Cleaned {cr31_cleaned_files} cross-injected Exam 31 files from Exam 6 records.")
    
    # 3. Remove 5 empty course code records
    empty_ids = {
        "exam34_1793102190",
        "exam31_1793102190",
        "exam7_1793102190",
        "exam4_1793102190",
        "exam35_1793226423"
    }
    before_empty = len(papers)
    papers = [p for p in papers if p.get("id") not in empty_ids]
    print(f"[Empty Records] Removed {before_empty - len(papers)} orphan records with empty course code.")
    
    # 4. Remove 40 redundant exam31_MG... records where exam31_<qp_code> exists
    e31_to_remove = set()
    for p in papers:
        pid = p.get("id", "")
        if pid.startswith("exam31_MG"):
            cc = p.get("course_code")
            partner = next((op for op in papers if op.get("id") != pid and str(op.get("exam_id")) == "31" and op.get("course_code") == cc), None)
            if partner:
                e31_to_remove.add(pid)
                
    papers = [p for p in papers if p.get("id") not in e31_to_remove]
    print(f"[Exam 31] Removed {len(e31_to_remove)} redundant exam31_MG... records.")
    
    # 5. Deduplicate any remaining duplicate records for the SAME course_code and SAME exam_id
    by_ce = defaultdict(list)
    for p in papers:
        cc = (p.get("course_code") or "").strip().upper()
        eid = str(p.get("exam_id", ""))
        by_ce[(cc, eid)].append(p)
        
    merged_papers = []
    other_dupes_merged = 0
    
    for (cc, eid), plist in by_ce.items():
        if not cc or len(plist) == 1:
            merged_papers.extend(plist)
            continue
            
        # Check if they are distinct examination sets (e.g., Set A and Set B)
        has_set_a = any("(Set A)" in (p.get("exam_name") or "") for p in plist)
        has_set_b = any("(Set B)" in (p.get("exam_name") or "") for p in plist)
        if has_set_a and has_set_b:
            merged_papers.extend(plist)
            continue
            
        other_dupes_merged += (len(plist) - 1)
        # Select best canonical record
        plist.sort(key=lambda p: (
            1 if p.get("qp_code") and not str(p.get("qp_code")).startswith("AWAITED") else 0,
            len(p.get("title") or ""),
            len(p.get("files") or [])
        ), reverse=True)
        
        primary = plist[0]
        existing_urls = set(f.get("url") for f in primary.get("files", []))
        for other in plist[1:]:
            for f in other.get("files", []):
                u = f.get("url")
                if u and u not in existing_urls:
                    primary.setdefault("files", []).append(f)
                    existing_urls.add(u)
            for m in other.get("model_papers", []):
                mu = m.get("url") or m.get("cdn_url")
                if mu and not any((em.get("url") or em.get("cdn_url")) == mu for em in primary.get("model_papers", [])):
                    primary.setdefault("model_papers", []).append(m)
                    
        # Update primary flags
        qp_f = next((fl for fl in primary.get("files", []) if fl.get("type") == "QP"), None)
        sch_f = next((fl for fl in primary.get("files", []) if fl.get("type") == "SCHEME"), None)
        if qp_f and not primary.get("has_qp"):
            primary["has_qp"] = True
            primary["qp_url"] = qp_f["url"]
        if sch_f and not primary.get("has_scheme"):
            primary["has_scheme"] = True
            primary["scheme_url"] = sch_f["url"]
            
        merged_papers.append(primary)
        
    print(f"[Merge] Merged {other_dupes_merged} other duplicate records.")
    print(f"[Result] Total records in deduplicated database: {len(merged_papers)} (pruned {initial_count - len(merged_papers)} redundant records).")
    
    # 6. Save to data/papers.json and public/data/papers.json
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(merged_papers, f, indent=2, ensure_ascii=False)
    with open(PUB_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(merged_papers, f, indent=2, ensure_ascii=False)
        
    print(f"[Saved] Successfully updated {DATA_PATH} and {PUB_DATA_PATH}!")

if __name__ == "__main__":
    dedupe_database()

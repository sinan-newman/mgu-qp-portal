from count_all_model_pdfs import all_entries
import re

# Filter only genuine model QP links from mgu uploads
valid_model_pdfs = []
seen_urls = set()

for e in all_entries:
    u = e["url"]
    label = e["label"]
    sem = e["semester"]
    
    # Exclude institutional policy / general docs
    if any(k in u.lower() for k in ["institutional-development-plan", "ugc-approval", "fee-refund", "admin.pdf", "right-to-public"]):
        continue
    
    if u in seen_urls:
        continue
    seen_urls.add(u)
    
    valid_model_pdfs.append({
        "semester": sem,
        "label": label,
        "url": u,
        "filename": u.split("/")[-1]
    })

print(f"Total valid unique model QP PDF files: {len(valid_model_pdfs)}")

# Group by semester
by_sem = {}
for item in valid_model_pdfs:
    by_sem.setdefault(item["semester"], []).append(item)

for sem, items in sorted(by_sem.items()):
    print(f"  Semester {sem}: {len(items)} PDF files")

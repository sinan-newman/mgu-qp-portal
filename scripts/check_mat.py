import json

with open("data/model_papers.json", "r", encoding="utf-8") as f:
    models = json.load(f)

mat_models = [m for m in models if m.get("dept_code") == "MAT" or "MAT" in m.get("course_code", "")]
print(f"Total Mathematics (MAT) Model Question Papers: {len(mat_models)}")
by_sem = {}
for m in mat_models:
    s = m.get("semester")
    by_sem[s] = by_sem.get(s, 0) + 1

for s in sorted(by_sem.keys()):
    print(f"\nSemester {s} ({by_sem[s]} model papers):")
    for m in mat_models:
        if m.get("semester") == s:
            print(f"  [{m.get('course_code')}] ({m.get('paper_type')}) {m.get('title')}")

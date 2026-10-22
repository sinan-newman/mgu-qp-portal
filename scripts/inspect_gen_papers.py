import json

with open("data/papers.json", "r", encoding="utf-8") as f:
    papers = json.load(f)

gen_papers = [p for p in papers if p.get("dept_code") == "GEN" or p.get("parent_dept") == "GEN"]
print(f"Total GEN papers: {len(gen_papers)}\n")

for p in gen_papers:
    qp = bool(p.get("qp_url"))
    sch = bool(p.get("scheme_url"))
    mods = len(p.get("model_papers", []))
    pdf = p.get("qp_url") or p.get("scheme_url") or (p.get("model_papers", [{}])[0].get("cdn_url") if p.get("model_papers") else "")
    raw = p.get("raw_header", "")
    print(f"ID: {p.get('id')}")
    print(f"  Code: {p.get('course_code')} | QP Code: {p.get('qp_code')} | Sem: {p.get('semester')}")
    print(f"  Title: {p.get('title')}")
    print(f"  Raw: {raw}")
    print(f"  Files: QP={qp}, Scheme={sch}, Models={mods}")
    print(f"  PDF: {pdf}\n")

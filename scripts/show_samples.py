from count_all_model_pdfs import all_entries

print("Sample Semester 1 entries:")
sem1 = [e for e in all_entries if e["semester"] == 1]
for x in sem1[:12]:
    print(f"  {x['label']:35} | {x['url']}")

print("\nSample Semester 2 entries:")
sem2 = [e for e in all_entries if e["semester"] == 2]
for x in sem2[:12]:
    print(f"  {x['label']:35} | {x['url']}")

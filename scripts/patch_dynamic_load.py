import os

server_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "server.py"))
with open(server_path, "r", encoding="utf-8") as f:
    text = f.read()

target1 = '''    def handle_admin_pending_papers(self):
        papers = CACHE.get("papers") or []'''

replacement1 = '''    def handle_admin_pending_papers(self):
        load_data()
        papers = CACHE.get("papers") or []'''

target2 = '''            papers = CACHE.get("papers") or []
            target_paper = next((p for p in papers if p.get("id") == paper_id), None)'''

replacement2 = '''            papers = CACHE.get("papers") or []
            target_paper = next((p for p in papers if p.get("id") == paper_id), None)
            if not target_paper:
                load_data()
                papers = CACHE.get("papers") or []
                target_paper = next((p for p in papers if p.get("id") == paper_id), None)'''

if target1 in text:
    text = text.replace(target1, replacement1, 1)
    print("Updated target 1")
if target2 in text:
    text = text.replace(target2, replacement2, 1)
    print("Updated target 2")

with open(server_path, "w", encoding="utf-8") as f:
    f.write(text)
print("Finished patching dynamic load.")

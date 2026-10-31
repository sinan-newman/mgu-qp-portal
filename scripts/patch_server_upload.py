import os

portal_dir = r'C:\Users\Navirex\.gemini\antigravity\scratch\mgu-qp-portal'
server_path = os.path.join(portal_dir, 'server.py')

with open(server_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Update handle_feedback_post
old_feedback_post = """            else:
                reports.insert(0, data)"""

new_feedback_post = """            else:
                file_data = data.pop("fileData", None)
                file_name = data.get("fileName")
                if file_data and file_name:
                    import base64, re
                    try:
                        if "," in file_data:
                            file_data = file_data.split(",", 1)[1]
                        file_bytes = base64.b64decode(file_data)
                        rep_id = data.get("id", str(int(time.time())))
                        safe_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", file_name)
                        saved_filename = f"REPORT_{rep_id}_{safe_name}"
                        for udir in [os.path.join(BASE_DIR, "uploads", "missing_reports"), os.path.join(BASE_DIR, "public", "uploads", "missing_reports")]:
                            os.makedirs(udir, exist_ok=True)
                            with open(os.path.join(udir, saved_filename), "wb") as out_f:
                                out_f.write(file_bytes)
                        data["fileUrl"] = f"uploads/missing_reports/{saved_filename}"
                    except Exception as ex:
                        print("Error saving attached report file:", ex)
                reports.insert(0, data)"""

if old_feedback_post in content:
    content = content.replace(old_feedback_post, new_feedback_post)
    print("Patched handle_feedback_post in server.py")
else:
    print("old_feedback_post not found in server.py")

# Ensure public/uploads is also checked in clean_path.startswith("uploads/")
old_uploads_check = """        if clean_path.startswith("uploads/"):
            fname = clean_path.replace("uploads/", "")
            for udir in [os.path.join(BASE_DIR, "uploads"), os.path.join(DATA_DIR, "uploads")]:"""

new_uploads_check = """        if clean_path.startswith("uploads/"):
            fname = clean_path.replace("uploads/", "")
            for udir in [os.path.join(BASE_DIR, "uploads"), os.path.join(BASE_DIR, "public", "uploads"), os.path.join(DATA_DIR, "uploads")]:"""

if old_uploads_check in content:
    content = content.replace(old_uploads_check, new_uploads_check)
    print("Patched clean_path check in server.py")

with open(server_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Saved server.py")

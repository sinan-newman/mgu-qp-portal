import os
import re

server_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "server.py"))
with open(server_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update do_POST if not already updated
if "/api/admin/resolve-paper" not in content:
    old_post = 'if parsed.path in ("/api/admin/delete-paper", "/api/admin/papers/delete"):'
    new_post = '''if parsed.path in ("/api/admin/resolve-paper", "/api/admin/papers/resolve"):
            self.handle_admin_resolve_paper()
            return
        if parsed.path in ("/api/admin/discard-pending-paper", "/api/admin/papers/discard"):
            self.handle_admin_discard_paper()
            return
        if parsed.path in ("/api/admin/delete-paper", "/api/admin/papers/delete"):'''
    if old_post in content:
        content = content.replace(old_post, new_post, 1)
        print("Updated do_POST")
    else:
        print("Failed to find do_POST target")
else:
    print("do_POST already contains /api/admin/resolve-paper")

# 2. Update /api/papers filter if not already updated
if "needs_review" not in content:
    old_filter = 'if only_with_files and not (p.get("has_files") or (p.get("model_papers") and len(p.get("model_papers")) > 0)):'
    new_filter = '''# Exclude unverified or ambiguous papers needing manual admin review
                if p.get("needs_review") or p.get("status") == "pending_review" or p.get("dept_code") == "GEN" or not p.get("course_code") or p.get("course_code") == "GEN":
                    continue

                if only_with_files and not (p.get("has_files") or (p.get("model_papers") and len(p.get("model_papers")) > 0)):'''
    if old_filter in content:
        content = content.replace(old_filter, new_filter, 1)
        print("Updated /api/papers filter")
    else:
        print("Failed to find /api/papers filter target")
else:
    print("/api/papers filter already contains needs_review")

# 3. Add handler methods
if "def handle_admin_resolve_paper" not in content:
    methods_code = '''    def handle_admin_pending_papers(self):
        papers = CACHE.get("papers") or []
        pending = [
            p for p in papers
            if p.get("needs_review") or p.get("status") == "pending_review" or p.get("dept_code") == "GEN" or not p.get("course_code") or p.get("course_code") == "GEN"
        ]
        self.send_json_response({
            "total": len(pending),
            "papers": pending
        })

    def handle_admin_resolve_paper(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body)

            paper_id = data.get("paper_id") or data.get("id")
            course_code = (data.get("course_code") or "").strip().upper()
            title = (data.get("title") or data.get("course_title") or "").strip()
            
            if not paper_id:
                self.send_json_response({"success": False, "error": "Missing paper ID"}, status=400)
                return

            if not course_code:
                self.send_json_response({"success": False, "error": "Course code is required"}, status=400)
                return

            # Sanitize & validate course code
            import re
            m = re.match(r'^MG([1-8])(DSC|DSE|SEC|MDC|VAC|CCR|AEC|MDE|SDC|MPC|HON|MIN|MDE)([A-Z]{2,5})(A\d{2}|\d{3})$', course_code)
            if not m:
                m_broad = re.match(r'^MG([1-8])[A-Z]{5,10}(A\d{2}|\d{3})$', course_code)
                if not m_broad:
                    self.send_json_response({"success": False, "error": f"Invalid course code format: '{course_code}'. Must follow MG[1-8][TYPE][DEPT][NUM] structure (e.g. MG5DSCBCA301)."}, status=400)
                    return
                sem = int(m_broad.group(1))
                ctype = "DSC"
                dept_c = course_code[5:-3] or "GEN"
                lvl = m_broad.group(2)
            else:
                sem = int(m.group(1))
                ctype = m.group(2).upper()
                dept_c = m.group(3).upper()
                lvl = m.group(4).upper()

            is_sig = lvl.startswith("A")
            user_sem = data.get("semester")
            if user_sem and str(user_sem).isdigit():
                sem = int(user_sem)

            # Department lookup
            dept_dict = {}
            for d in (CACHE.get("departments") or []):
                code = (d.get("code") or "").upper()
                name = d.get("name") or code
                if code:
                    dept_dict[code] = name
                for maj in d.get("majors", []):
                    m_code = (maj.get("code") or "").upper()
                    m_name = maj.get("name") or name
                    if m_code:
                        dept_dict[m_code] = m_name

            dept_n = data.get("dept_name") or dept_dict.get(dept_c, dept_c)
            parent_dept = data.get("parent_dept") or dept_c
            parent_dept_name = data.get("parent_dept_name") or dept_n

            COURSE_TYPE_NAMES = {
                "DSC": "Discipline Specific Core",
                "DSE": "Discipline Specific Elective",
                "MDC": "Multidisciplinary Course",
                "AEC": "Ability Enhancement Course",
                "SEC": "Skill Enhancement Course",
                "VAC": "Value Added Course",
                "CCR": "Common Core",
                "SDC": "Skill Development Course",
                "MPC": "Minor Pathway Course",
                "MDE": "Multidisciplinary Elective",
                "HON": "Honours Course",
                "MIN": "Minor Course"
            }

            papers = CACHE.get("papers") or []
            target_paper = next((p for p in papers if p.get("id") == paper_id), None)
            if not target_paper:
                self.send_json_response({"success": False, "error": f"Target paper '{paper_id}' not found"}, status=404)
                return

            # DEDUPLICATION CHECK: Look for another paper with the same (course_code, semester)
            existing_duplicate = next(
                (p for p in papers if p.get("id") != paper_id and p.get("course_code", "").upper() == course_code and p.get("semester") == sem),
                None
            )

            if existing_duplicate:
                # Merge target paper's files and details into existing canonical paper
                existing_files = existing_duplicate.setdefault("files", [])
                existing_urls = set(f.get("url") or f.get("mgu_url") for f in existing_files)

                merged_count = 0
                for f in target_paper.get("files", []):
                    f_url = f.get("url") or f.get("mgu_url")
                    if f_url and f_url not in existing_urls:
                        existing_files.append(f)
                        existing_urls.add(f_url)
                        merged_count += 1

                if target_paper.get("qp_url") and not existing_duplicate.get("qp_url"):
                    existing_duplicate["qp_url"] = target_paper["qp_url"]
                    existing_duplicate["has_qp"] = True

                if target_paper.get("scheme_url") and not existing_duplicate.get("scheme_url"):
                    existing_duplicate["scheme_url"] = target_paper["scheme_url"]
                    existing_duplicate["has_scheme"] = True

                if target_paper.get("model_papers"):
                    existing_models = existing_duplicate.setdefault("model_papers", [])
                    existing_model_ids = set(m.get("id") for m in existing_models)
                    for m in target_paper["model_papers"]:
                        if m.get("id") not in existing_model_ids:
                            existing_models.append(m)
                            existing_model_ids.add(m.get("id"))

                existing_duplicate["has_files"] = bool(existing_duplicate.get("files") or existing_duplicate.get("model_papers"))

                # Strict requirement: REMOVE target paper from database since duplicate exists!
                papers = [p for p in papers if p.get("id") != paper_id]
                CACHE["papers"] = papers

                for fpath in [os.path.join(DATA_DIR, "papers.json"), os.path.join(BASE_DIR, "public", "data", "papers.json")]:
                    if os.path.exists(os.path.dirname(fpath)):
                        with open(fpath, "w", encoding="utf-8") as f_out:
                            json.dump(papers, f_out, indent=2)

                self.update_stats()
                self.send_json_response({
                    "success": True,
                    "action": "merged",
                    "message": f"Duplicate found for {course_code}! Merged {merged_count} file(s) into existing course record ({existing_duplicate.get('title')}) and deleted duplicate record from database.",
                    "duplicate_id": existing_duplicate.get("id"),
                    "deleted_id": paper_id
                })
                return

            # No duplicate found -> Update target paper and publish
            target_paper["course_code"] = course_code
            target_paper["title"] = title or f"Course {course_code}"
            target_paper["raw_header"] = f"{target_paper.get('qp_code', '')} - {course_code} {target_paper['title']}".strip(" -")
            target_paper["semester"] = sem
            target_paper["semester_label"] = f"Semester {sem}"
            target_paper["course_type"] = ctype
            target_paper["course_type_name"] = COURSE_TYPE_NAMES.get(ctype, ctype)
            target_paper["dept_code"] = dept_c
            target_paper["dept_name"] = dept_n
            target_paper["parent_dept"] = parent_dept
            target_paper["parent_dept_name"] = parent_dept_name
            target_paper["is_signature"] = is_sig
            target_paper["needs_review"] = False
            target_paper["status"] = "published"
            if "review_reason" in target_paper:
                del target_paper["review_reason"]

            CACHE["papers"] = papers
            for fpath in [os.path.join(DATA_DIR, "papers.json"), os.path.join(BASE_DIR, "public", "data", "papers.json")]:
                if os.path.exists(os.path.dirname(fpath)):
                    with open(fpath, "w", encoding="utf-8") as f_out:
                        json.dump(papers, f_out, indent=2)

            self.update_stats()
            self.send_json_response({
                "success": True,
                "action": "published",
                "message": f"Course {course_code} successfully verified and published to public portal!",
                "paper": target_paper
            })
        except Exception as e:
            self.send_json_response({"success": False, "error": str(e)}, status=500)

    def handle_admin_discard_paper(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body)

            paper_id = data.get("paper_id") or data.get("id")
            if not paper_id:
                self.send_json_response({"success": False, "error": "Missing paper ID"}, status=400)
                return

            papers = CACHE.get("papers") or []
            init_len = len(papers)
            papers = [p for p in papers if p.get("id") != paper_id]

            if len(papers) == init_len:
                self.send_json_response({"success": False, "error": "Paper not found"}, status=404)
                return

            CACHE["papers"] = papers
            for fpath in [os.path.join(DATA_DIR, "papers.json"), os.path.join(BASE_DIR, "public", "data", "papers.json")]:
                if os.path.exists(os.path.dirname(fpath)):
                    with open(fpath, "w", encoding="utf-8") as f_out:
                        json.dump(papers, f_out, indent=2)

            self.update_stats()
            self.send_json_response({
                "success": True,
                "action": "discarded",
                "message": f"Pending paper {paper_id} discarded and permanently removed from database.",
                "deleted_id": paper_id
            })
        except Exception as e:
            self.send_json_response({"success": False, "error": str(e)}, status=500)
'''

    del_marker = '    def handle_admin_delete(self):'
    if del_marker in content:
        content = content.replace(del_marker, methods_code + "\n" + del_marker, 1)
        print("Inserted admin review methods")
    else:
        print("handle_admin_delete marker not found")
else:
    print("handle_admin_resolve_paper already exists")

with open(server_path, "w", encoding="utf-8") as f:
    f.write(content)
print("server.py patch completed.")

"""
MGU Question Papers Portal - Backend Server
Provides static file serving, REST API, PDF proxying, and sync trigger.
Dependency-free (Python 3 standard library).
"""

import http.server
import socketserver
import urllib.request
import urllib.parse
import json
import os
import sys
import mimetypes
import threading
import time

PORT = 8080
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PUBLIC_DIR = BASE_DIR if os.path.exists(os.path.join(BASE_DIR, "index.html")) else os.path.join(BASE_DIR, "public")
DATA_DIR = os.path.join(BASE_DIR, "data")
VISITORS_FILE = os.path.join(DATA_DIR, "visitors.json")
VISITORS_LOCK = threading.Lock()

# In-memory cache for fast search
CACHE = {
    "papers": None,
    "departments": None,
    "model_courses": None,
    "model_papers": None,
    "stats": None,
    "visitors": None
}

def get_initial_visitors():
    import time
    today_str = time.strftime("%Y-%m-%d")
    return {
        "total_pageviews": 0,
        "total_unique_visitors": 0,
        "today_date": today_str,
        "today_pageviews": 0,
        "today_unique_visitors": 0,
        "device_breakdown": {
            "mobile": 0,
            "desktop": 0
        },
        "daily_history": {},
        "recent_visits": [],
        "seen_today_vids": [],
        "all_time_vids": []
    }

def load_visitors():
    if os.path.exists(VISITORS_FILE):
        try:
            with open(VISITORS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading visitors.json: {e}")
    return get_initial_visitors()

def save_visitors():
    import copy
    with VISITORS_LOCK:
        data = copy.deepcopy(CACHE.get("visitors") or get_initial_visitors())
    for fpath in [VISITORS_FILE, os.path.join(BASE_DIR, "public", "data", "visitors.json")]:
        try:
            os.makedirs(os.path.dirname(fpath), exist_ok=True)
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving visitors to {fpath}: {e}")

def load_data():
    try:
        with open(os.path.join(DATA_DIR, "papers.json"), "r", encoding="utf-8") as f:
            CACHE["papers"] = json.load(f)
    except Exception as e:
        print(f"Error loading papers.json: {e}")
        CACHE["papers"] = []

    try:
        with open(os.path.join(DATA_DIR, "departments.json"), "r", encoding="utf-8") as f:
            CACHE["departments"] = json.load(f)
    except Exception as e:
        print(f"Error loading departments.json: {e}")
        CACHE["departments"] = []

    try:
        with open(os.path.join(DATA_DIR, "model_courses.json"), "r", encoding="utf-8") as f:
            CACHE["model_courses"] = json.load(f)
    except Exception as e:
        print(f"Error loading model_courses.json: {e}")
        CACHE["model_courses"] = []

    try:
        with open(os.path.join(DATA_DIR, "model_papers.json"), "r", encoding="utf-8") as f:
            CACHE["model_papers"] = json.load(f)
    except Exception as e:
        print(f"Error loading model_papers.json: {e}")
        CACHE["model_papers"] = []

    try:
        with open(os.path.join(DATA_DIR, "stats.json"), "r", encoding="utf-8") as f:
            CACHE["stats"] = json.load(f)
    except Exception as e:
        print(f"Error loading stats.json: {e}")
        CACHE["stats"] = {}

    CACHE["visitors"] = load_visitors()

load_data()

class PortalRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Enable CORS for local dev / client integrations
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)

        if path.startswith("/api/"):
            self.handle_api_get(path, params)
            return

        # Serve static assets from public/ or data/
        if path == "/" or path == "":
            self.serve_file(os.path.join(PUBLIC_DIR, "index.html"), "text/html; charset=utf-8")
            return

        # Check if file exists in public/
        clean_path = path.lstrip("/")
        full_public = os.path.join(PUBLIC_DIR, clean_path)
        if os.path.isfile(full_public):
            mime_type, _ = mimetypes.guess_type(full_public)
            self.serve_file(full_public, mime_type or "application/octet-stream")
            return

        # Check if file exists in data/ (e.g. /data/papers.json)
        full_data = os.path.join(DATA_DIR, clean_path.replace("data/", ""))
        if os.path.isfile(full_data):
            self.serve_file(full_data, "application/json; charset=utf-8")
            return

        # Check if file exists in uploads/ (custom admin uploads)
        if clean_path.startswith("uploads/"):
            fname = clean_path.replace("uploads/", "")
            for udir in [os.path.join(BASE_DIR, "uploads"), os.path.join(BASE_DIR, "public", "uploads"), os.path.join(DATA_DIR, "uploads")]:
                full_up = os.path.join(udir, fname)
                if os.path.isfile(full_up):
                    self.serve_file(full_up, "application/pdf")
                    return

        # Default fallback to index.html for SPA routes
        self.serve_file(os.path.join(PUBLIC_DIR, "index.html"), "text/html; charset=utf-8")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/visit":
            self.handle_visit_post()
            return
        if parsed.path == "/api/sync":
            self.handle_sync_trigger()
            return
        if parsed.path == "/api/sync-model":
            self.handle_model_sync_trigger()
            return
        if parsed.path in ("/api/admin/upload-paper", "/api/admin/papers"):
            self.handle_admin_upload()
            return
        if parsed.path in ("/api/admin/resolve-paper", "/api/admin/papers/resolve"):
            self.handle_admin_resolve_paper()
            return
        if parsed.path in ("/api/admin/discard-pending-paper", "/api/admin/papers/discard"):
            self.handle_admin_discard_paper()
            return
        if parsed.path in ("/api/admin/delete-paper", "/api/admin/papers/delete"):
            self.handle_admin_delete()
            return
        if parsed.path == "/api/feedback":
            self.handle_feedback_post()
            return
        self.send_json_response({"error": "Endpoint not found"}, status=404)

    def handle_api_get(self, path, params):
        if path == "/api/admin/pending-papers":
            self.handle_admin_pending_papers()
            return
        if path == "/api/visitors":
            self.handle_visitors_get()
            return
        if path == "/api/feedback":
            self.handle_feedback_get()
            return
        if path == "/api/crawl-history":
            history_file = os.path.join(DATA_DIR, "crawl_history.json")
            if os.path.exists(history_file):
                try:
                    with open(history_file, "r", encoding="utf-8") as f:
                        self.send_json_response(json.load(f))
                        return
                except Exception:
                    pass
            self.send_json_response([])
            return
        if path == "/api/stats":
            self.send_json_response(CACHE["stats"] or {})
            return

        if path == "/api/departments":
            self.send_json_response(CACHE["departments"] or [])
            return

        if path == "/api/model-courses":
            query = params.get("search", [""])[0].lower()
            dept = params.get("dept", [""])[0].upper()
            sem = params.get("semester", [""])[0]
            
            courses = CACHE["model_courses"] or []
            if query:
                courses = [c for c in courses if query in c["course_code"].lower() or query in c["title"].lower() or query in c["dept_name"].lower()]
            if dept:
                courses = [c for c in courses if c["parent_dept"] == dept or c["dept_code"] == dept]
            if sem and sem.isdigit():
                courses = [c for c in courses if c["semester"] == int(sem)]
            self.send_json_response(courses)
            return

        if path == "/api/model-papers":
            self.send_json_response(CACHE["model_papers"] or [])
            return

        if path == "/api/papers":
            search_query = params.get("search", [""])[0].strip().lower()
            dept = params.get("dept", [""])[0].strip().upper()
            sem = params.get("semester", [""])[0].strip()
            ctype = params.get("course_type", [""])[0].strip().upper()
            only_with_files = params.get("has_files", ["true"])[0].lower() == "true"
            page = int(params.get("page", ["1"])[0])
            limit = int(params.get("limit", ["24"])[0])

            papers = CACHE["papers"] or []

            # Filter papers
            filtered = []
            for p in papers:
                # Exclude unverified or ambiguous papers needing manual admin review
                if p.get("needs_review") or p.get("status") == "pending_review" or p.get("dept_code") == "GEN" or not p.get("course_code") or p.get("course_code") == "GEN":
                    continue

                if only_with_files and not (p.get("has_files") or (p.get("model_papers") and len(p.get("model_papers")) > 0)):
                    continue

                if sem and sem.isdigit() and p["semester"] != int(sem):
                    continue

                if ctype and ctype != "ALL":
                    if ctype == "MIN":
                        if not p["is_minor"]:
                            continue
                    elif p["course_type"] != ctype:
                        continue

                if dept and dept != "ALL":
                    if p["parent_dept"] != dept and p["dept_code"] != dept:
                        continue

                if search_query:
                    searchable = f"{p['course_code']} {p['qp_code']} {p['title']} {p['raw_header']} {p['dept_name']} {p['parent_dept_name']} {p['course_type_name']}".lower()
                    if search_query not in searchable:
                        continue

                filtered.append(p)

            # Pagination
            total_matches = len(filtered)
            start = (page - 1) * limit
            end = start + limit
            paged_results = filtered[start:end]

            response = {
                "total": total_matches,
                "page": page,
                "limit": limit,
                "total_pages": (total_matches + limit - 1) // limit if limit else 1,
                "papers": paged_results
            }
            self.send_json_response(response)
            return

        if path == "/api/proxy-pdf":
            # Proxy PDF to allow seamless inline iframe preview
            pdf_url = params.get("url", [""])[0].strip()

            # Handle local uploads directly
            clean_local = pdf_url.lstrip("/")
            if clean_local.startswith("uploads/"):
                for candidate_root in [BASE_DIR, os.path.join(BASE_DIR, "public")]:
                    local_target = os.path.join(candidate_root, clean_local.replace("/", os.sep))
                    if os.path.exists(local_target) and os.path.isfile(local_target):
                        try:
                            with open(local_target, "rb") as f_pdf:
                                data = f_pdf.read()
                            self.send_response(200)
                            self.send_header("Content-Type", "application/pdf")
                            self.send_header("Content-Length", str(len(data)))
                            self.send_header("Content-Disposition", 'inline; filename="preview.pdf"')
                            self.send_header("Cache-Control", "public, max-age=86400")
                            self.end_headers()
                            self.wfile.write(data)
                            return
                        except Exception as e:
                            self.send_json_response({"error": f"Failed to read local PDF: {str(e)}"}, status=500)
                            return

            is_valid_source = pdf_url and (
                pdf_url.startswith("https://assist.mgu.ac.in/") or
                "mgu.ac.in" in pdf_url or
                "cdn.jsdelivr.net" in pdf_url or
                "raw.githubusercontent.com" in pdf_url
            )
            if not is_valid_source:
                self.send_json_response({"error": "Invalid or unauthorized URL"}, status=400)
                return

            try:
                # Safely encode URL for external request
                import urllib.parse
                parts = urllib.parse.urlsplit(pdf_url)
                encoded_path = urllib.parse.quote(parts.path, safe='/@:')
                safe_pdf_url = urllib.parse.urlunsplit((parts.scheme, parts.netloc, encoded_path, parts.query, parts.fragment))

                req = urllib.request.Request(
                    safe_pdf_url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MGU-Portal-Proxy/1.0"}
                )
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = resp.read()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/pdf")
                    self.send_header("Content-Length", str(len(data)))
                    # Remove restrictive framing headers so iframe preview works
                    self.send_header("Content-Disposition", "inline; filename=\"preview.pdf\"")
                    self.send_header("Cache-Control", "public, max-age=86400")
                    self.end_headers()
                    self.wfile.write(data)
                    return
            except Exception as e:
                self.send_json_response({"error": f"Failed to fetch PDF: {str(e)}"}, status=502)
                return

        self.send_json_response({"error": "Unknown API endpoint"}, status=404)

    def handle_sync_trigger(self):
        def sync_worker():
            try:
                import scripts.sync_engine as sync_engine
                sync_engine.run_sync(trigger_type="manual")
                load_data()
                print("Background assist.mgu.ac.in manual sync completed.")
            except Exception as e:
                print(f"Background sync error: {e}")

        threading.Thread(target=sync_worker, daemon=True).start()
        self.send_json_response({
            "status": "started",
            "message": "Background sync with https://assist.mgu.ac.in/schema/ initiated."
        })

    def handle_model_sync_trigger(self):
        def model_sync_worker():
            try:
                import scripts.scrape_mgu_model_papers as model_scraper
                model_scraper.run_scraper(force=False)
                load_data()
                print("Background MGU Model Question Papers resync completed.")
            except Exception as e:
                print(f"Background model resync error: {e}")

        threading.Thread(target=model_sync_worker, daemon=True).start()
        self.send_json_response({
            "status": "started",
            "message": "Background sync for MGU FYUGP Model Question Papers initiated."
        })

    def handle_admin_upload(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body)

            import time
            import base64

            import re
            course_code = data.get("course_code", "").strip().upper()
            title = data.get("title", "").strip()
            semester = int(data.get("semester", 1))
            dept_code = data.get("dept_code", "").strip().upper()
            parent_dept = data.get("parent_dept", dept_code).strip().upper()
            dept_name = data.get("dept_name", dept_code).strip()
            parent_dept_name = data.get("parent_dept_name", dept_name).strip()
            course_type = data.get("course_type", "DSC").strip().upper()
            is_minor = bool(data.get("is_minor", False))
            minor_name = data.get("minor_name", "").strip()
            exam_name = data.get("exam_name", "MGU-UGP (Honours) 2024 Admission Regular Examination").strip()
            qp_code = data.get("qp_code", "").strip()
            qp_url = data.get("qp_url", "").strip()
            scheme_url = data.get("scheme_url", "").strip()
            qp_file_b64 = data.get("qp_file_b64", "")
            scheme_file_b64 = data.get("scheme_file_b64", "")

            # Sanitize course code: strip trailing letters that bled into course code (e.g. MG4DSEMAT201TRANS -> MG4DSEMAT201)
            if course_code:
                m_strip = re.match(r'^(MG[1-8](?:DSC|DSE|SEC|MDC|VAC|CCR|AEC|MDE|SDC|MPC|HON|MIN|MDE)[A-Z]{2,5}(?:A\d{2}|[1-5][0-9]{2}))[A-Z]+$', course_code)
                if m_strip:
                    course_code = m_strip.group(1)

                if not course_code[-1].isdigit():
                    self.send_json_response({"success": False, "error": f"Invalid course code '{course_code}': Course codes must always end with a number."}, status=400)
                    return

            # Strict rule: Title of paper must never be the same as department name or department code
            if title and dept_name and title.strip().lower() in (dept_name.strip().lower(), parent_dept_name.strip().lower(), dept_code.strip().lower(), parent_dept.strip().lower()):
                title = f"Course {course_code}" if course_code else ""

            is_signature = bool(re.search(r'A\d{2}$', course_code.strip().upper())) if course_code else bool(data.get("is_signature", False))

            uploads_dir = os.path.join(BASE_DIR, "uploads")
            os.makedirs(uploads_dir, exist_ok=True)
            public_uploads_dir = os.path.join(BASE_DIR, "public", "uploads")
            os.makedirs(public_uploads_dir, exist_ok=True)

            ts = int(time.time())
            if qp_file_b64:
                qp_fname = f"QP_{course_code or 'CUSTOM'}_{qp_code or 'paper'}_{ts}.pdf"
                qp_data_bytes = base64.b64decode(qp_file_b64.split(",")[-1])
                for udir in [uploads_dir, public_uploads_dir]:
                    with open(os.path.join(udir, qp_fname), "wb") as f:
                        f.write(qp_data_bytes)
                qp_url = f"uploads/{qp_fname}"

            if scheme_file_b64:
                sch_fname = f"SCHEME_{course_code or 'CUSTOM'}_{qp_code or 'scheme'}_{ts}.pdf"
                sch_data_bytes = base64.b64decode(scheme_file_b64.split(",")[-1])
                for udir in [uploads_dir, public_uploads_dir]:
                    with open(os.path.join(udir, sch_fname), "wb") as f:
                        f.write(sch_data_bytes)
                scheme_url = f"uploads/{sch_fname}"

            files = []
            if qp_url:
                files.append({"type": "QP", "label": "QUESTION PAPER", "url": qp_url})
            if scheme_url:
                files.append({"type": "SCHEME", "label": "SCHEME", "url": scheme_url})

            paper_id = f"custom_{course_code or 'qp'}_{ts}"
            is_model_paper = bool(data.get("is_model_paper", False))

            if is_model_paper:
                model_obj = {
                    "id": f"model_{course_code or 'qp'}_{ts}",
                    "title": title or f"Model Question Paper - {course_code}",
                    "paper_type": data.get("paper_type", "THEORY"),
                    "url": qp_url,
                    "pages": 3,
                    "source": "Admin Ingestion"
                }
                papers = CACHE.get("papers") or []
                found = False
                new_paper = None
                for p in papers:
                    if p.get("course_code", "").strip().upper() == course_code:
                        if "model_papers" not in p or not isinstance(p["model_papers"], list):
                            p["model_papers"] = []
                        # Enforce rule: course can have at most 1 Theory and at most 1 Practical
                        m_ptype = model_obj.get("paper_type", "THEORY").upper()
                        p["model_papers"] = [m for m in p["model_papers"] if m.get("paper_type", "THEORY").upper() != m_ptype]
                        p["model_papers"].append(model_obj)
                        p["has_files"] = True
                        if is_signature:
                            p["is_signature"] = True
                        found = True
                        new_paper = p
                        break
                if not found:
                    new_paper = {
                        "id": f"custom_model_{course_code}_{ts}",
                        "qp_code": qp_code,
                        "course_code": course_code,
                        "title": title or f"Course {course_code}",
                        "raw_header": f"{course_code} {title}".strip(),
                        "semester": semester,
                        "semester_label": f"Semester {semester}",
                        "course_type": course_type,
                        "course_type_name": data.get("course_type_name", course_type),
                        "dept_code": dept_code,
                        "dept_name": dept_name,
                        "parent_dept": parent_dept,
                        "parent_dept_name": parent_dept_name,
                        "is_minor": is_minor,
                        "minor_name": minor_name,
                        "is_signature": is_signature,
                        "exam_id": "model_qp",
                        "exam_name": "FYUGP Model Question Paper",
                        "batch": "2024 Admission",
                        "is_fyugp": True,
                        "has_qp": False,
                        "has_scheme": False,
                        "files": [],
                        "has_files": True,
                        "model_papers": [model_obj],
                        "is_custom_upload": True
                    }
                    papers.insert(0, new_paper)
                CACHE["papers"] = papers
            else:
                new_paper = {
                    "id": paper_id,
                    "qp_code": qp_code,
                    "course_code": course_code,
                    "title": title or f"Course {course_code}",
                    "raw_header": f"{qp_code} - {course_code} {title}".strip(" -"),
                    "semester": semester,
                    "semester_label": f"Semester {semester}",
                    "course_type": course_type,
                    "course_type_name": data.get("course_type_name", course_type),
                    "dept_code": dept_code,
                    "dept_name": dept_name,
                    "parent_dept": parent_dept,
                    "parent_dept_name": parent_dept_name,
                    "is_minor": is_minor,
                    "minor_name": minor_name,
                    "is_signature": is_signature,
                    "exam_id": "custom",
                    "exam_name": exam_name,
                    "batch": "2024 Admission",
                    "is_fyugp": True,
                    "has_qp": bool(qp_url),
                    "qp_url": qp_url,
                    "has_scheme": bool(scheme_url),
                    "scheme_url": scheme_url,
                    "files": files,
                    "has_files": len(files) > 0,
                    "is_custom_upload": True
                }

                papers = CACHE.get("papers") or []
                papers.insert(0, new_paper)
                CACHE["papers"] = papers

            for fpath in [os.path.join(DATA_DIR, "papers.json"), os.path.join(BASE_DIR, "public", "data", "papers.json")]:
                if os.path.exists(os.path.dirname(fpath)):
                    with open(fpath, "w", encoding="utf-8") as f:
                        json.dump(papers, f, indent=2)

            self.update_stats()
            self.send_json_response({"success": True, "message": "Paper uploaded and published successfully!", "paper": new_paper})
        except Exception as e:
            self.send_json_response({"success": False, "error": str(e)}, status=500)

    def handle_admin_pending_papers(self):
        load_data()
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
                load_data()
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

    def handle_admin_delete(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body)
            paper_id = data.get("id")

            if not paper_id:
                self.send_json_response({"success": False, "error": "Missing paper ID"}, status=400)
                return

            papers = CACHE.get("papers") or []
            initial_len = len(papers)
            papers = [p for p in papers if p.get("id") != paper_id]

            if len(papers) == initial_len:
                self.send_json_response({"success": False, "error": "Paper not found"}, status=404)
                return

            CACHE["papers"] = papers

            for fpath in [os.path.join(DATA_DIR, "papers.json"), os.path.join(BASE_DIR, "public", "data", "papers.json")]:
                if os.path.exists(os.path.dirname(fpath)):
                    with open(fpath, "w", encoding="utf-8") as f:
                        json.dump(papers, f, indent=2)

            self.update_stats()
            self.send_json_response({"success": True, "message": f"Paper deleted successfully!", "deleted_id": paper_id})
        except Exception as e:
            self.send_json_response({"success": False, "error": str(e)}, status=500)

    def handle_feedback_get(self):
        reports_file = os.path.join(DATA_DIR, "reports.json")
        reports = []
        if os.path.exists(reports_file):
            try:
                with open(reports_file, "r", encoding="utf-8") as f:
                    reports = json.load(f)
            except Exception:
                reports = []
        self.send_json_response(reports)

    def handle_feedback_post(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body)
            reports_file = os.path.join(DATA_DIR, "reports.json")
            reports = []
            if os.path.exists(reports_file):
                try:
                    with open(reports_file, "r", encoding="utf-8") as f:
                        reports = json.load(f)
                except Exception:
                    reports = []

            action = data.get("action")
            if action == "update_status":
                rep_id = data.get("id")
                new_status = data.get("status")
                for r in reports:
                    if r.get("id") == rep_id:
                        r["status"] = new_status
            elif action == "delete":
                rep_id = data.get("id")
                reports = [r for r in reports if r.get("id") != rep_id]
            elif action == "clear_resolved":
                reports = [r for r in reports if r.get("status") != "resolved"]
            elif action == "sync_all":
                reports = data.get("reports", reports)
            else:
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
                reports.insert(0, data)

            for fpath in [reports_file, os.path.join(BASE_DIR, "public", "data", "reports.json")]:
                if os.path.exists(os.path.dirname(fpath)):
                    with open(fpath, "w", encoding="utf-8") as f:
                        json.dump(reports, f, indent=2, ensure_ascii=False)
            self.send_json_response({"success": True, "message": "Feedback operation successful", "reports_count": len(reports)})
        except Exception as e:
            self.send_json_response({"success": False, "error": str(e)}, status=500)

    def handle_visit_post(self):
        import time
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            payload = json.loads(body) if body else {}

            visitor_id = str(payload.get("visitor_id") or "").strip()
            device = str(payload.get("device") or "desktop").strip().lower()
            page = str(payload.get("page") or "/").strip()
            dev_key = "mobile" if "mobile" in device else "desktop"

            today_str = time.strftime("%Y-%m-%d")
            now_time_str = time.strftime("%I:%M %p, %b %d")

            with VISITORS_LOCK:
                vdata = CACHE.get("visitors") or get_initial_visitors()

                # Daily rollover check
                if vdata.get("today_date") != today_str:
                    prev_date = vdata.get("today_date")
                    if prev_date:
                        if "daily_history" not in vdata:
                            vdata["daily_history"] = {}
                        vdata["daily_history"][prev_date] = {
                            "pageviews": vdata.get("today_pageviews", 0),
                            "unique": vdata.get("today_unique_visitors", 0)
                        }
                    vdata["today_date"] = today_str
                    vdata["today_pageviews"] = 0
                    vdata["today_unique_visitors"] = 0
                    vdata["seen_today_vids"] = []

                # Increment pageviews
                vdata["total_pageviews"] = vdata.get("total_pageviews", 0) + 1
                vdata["today_pageviews"] = vdata.get("today_pageviews", 0) + 1

                # Unique today check
                if "seen_today_vids" not in vdata:
                    vdata["seen_today_vids"] = []
                if visitor_id and visitor_id not in vdata["seen_today_vids"]:
                    vdata["seen_today_vids"].append(visitor_id)
                    vdata["today_unique_visitors"] = vdata.get("today_unique_visitors", 0) + 1
                elif not visitor_id:
                    vdata["today_unique_visitors"] = vdata.get("today_unique_visitors", 0) + 1

                # All-time unique check
                if "all_time_vids" not in vdata:
                    vdata["all_time_vids"] = []
                if visitor_id and visitor_id not in vdata["all_time_vids"]:
                    vdata["all_time_vids"].append(visitor_id)
                    vdata["total_unique_visitors"] = vdata.get("total_unique_visitors", 0) + 1
                elif not visitor_id:
                    vdata["total_unique_visitors"] = vdata.get("total_unique_visitors", 0) + 1

                # Device breakdown
                if "device_breakdown" not in vdata:
                    vdata["device_breakdown"] = {"mobile": 0, "desktop": 0}
                vdata["device_breakdown"][dev_key] = vdata["device_breakdown"].get(dev_key, 0) + 1

                # Recent visits log
                if "recent_visits" not in vdata:
                    vdata["recent_visits"] = []

                friendly_page = page
                if friendly_page.startswith("#/department/"):
                    friendly_page = "Dept " + friendly_page.replace("#/department/", "")
                elif friendly_page.startswith("#/papers"):
                    friendly_page = "All Question Papers"
                elif friendly_page.startswith("#/bookmarks"):
                    friendly_page = "Saved Papers"
                elif friendly_page == "#/departments" or friendly_page == "#/":
                    friendly_page = "Academic Departments"

                vdata["recent_visits"].insert(0, {
                    "time": now_time_str,
                    "device": "Mobile" if dev_key == "mobile" else "Desktop",
                    "page": friendly_page[:60]
                })
                vdata["recent_visits"] = vdata["recent_visits"][:25]
                CACHE["visitors"] = vdata

            save_visitors()

            self.send_json_response({
                "success": True,
                "total_unique": vdata.get("total_unique_visitors", 0),
                "today_unique": vdata.get("today_unique_visitors", 0)
            })
        except Exception as e:
            self.send_json_response({"success": False, "error": str(e)}, status=500)

    def handle_visitors_get(self):
        with VISITORS_LOCK:
            vdata = CACHE.get("visitors") or get_initial_visitors()
            summary = {
                "total_pageviews": vdata.get("total_pageviews", 0),
                "total_unique_visitors": vdata.get("total_unique_visitors", 0),
                "today_date": vdata.get("today_date", ""),
                "today_pageviews": vdata.get("today_pageviews", 0),
                "today_unique_visitors": vdata.get("today_unique_visitors", 0),
                "device_breakdown": vdata.get("device_breakdown", {"mobile": 0, "desktop": 0}),
                "daily_history": vdata.get("daily_history", {}),
                "recent_visits": vdata.get("recent_visits", [])
            }
        self.send_json_response(summary)

    def update_stats(self):
        import time
        papers = CACHE.get("papers") or []
        with_files = [p for p in papers if p.get("has_files")]
        qps = [p for p in papers if p.get("has_qp")]
        schemes = [p for p in papers if p.get("has_scheme")]
        minor_count = sum(1 for p in papers if p.get("is_minor"))
        stats = {
            "total_records": len(papers),
            "records_with_files": len(with_files),
            "total_question_papers": len(qps),
            "total_schemes": len(schemes),
            "departments_count": len(CACHE.get("departments") or []),
            "minor_papers_count": minor_count,
            "batch_scope": "FYUGP (MGU-UGP Honours) Only",
            "last_sync": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
        }
        CACHE["stats"] = stats
        for fpath in [os.path.join(DATA_DIR, "stats.json"), os.path.join(BASE_DIR, "public", "data", "stats.json")]:
            if os.path.exists(os.path.dirname(fpath)):
                with open(fpath, "w", encoding="utf-8") as f:
                    json.dump(stats, f, indent=2)

    def serve_file(self, full_path, content_type):
        if not os.path.exists(full_path):
            self.send_error(404, "File not found")
            return
        try:
            with open(full_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            if "html" in content_type or "javascript" in content_type or "json" in content_type:
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.send_header("Pragma", "no-cache")
                self.send_header("Expires", "0")
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, f"Error reading file: {e}")

    def send_json_response(self, data, status=200):
        try:
            body = json.dumps(data).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            self.send_error(500, f"JSON Error: {e}")

def start_background_scheduler():
    def scheduler_loop():
        INTERVAL_SECONDS = 6 * 3600  # 6 hours
        while True:
            time.sleep(INTERVAL_SECONDS)
            try:
                print("[Scheduled 6-Hr Auto-Sync] Starting background crawl...", flush=True)
                import scripts.sync_engine as sync_engine
                sync_engine.run_sync(trigger_type="automatic")
                load_data()
                print("[Scheduled 6-Hr Auto-Sync] Completed successfully.", flush=True)
            except Exception as e:
                print(f"[Scheduled 6-Hr Auto-Sync] Error: {e}", flush=True)

    t = threading.Thread(target=scheduler_loop, daemon=True)
    t.start()

def run_server():
    socketserver.TCPServer.allow_reuse_address = True
    start_background_scheduler()
    with socketserver.TCPServer(("", PORT), PortalRequestHandler) as httpd:
        print(f"============================================================")
        print(f" MGU Previous Year Question Papers & Schemes Portal")
        print(f" Running at: http://localhost:{PORT}")
        print(f"============================================================")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")

if __name__ == "__main__":
    run_server()

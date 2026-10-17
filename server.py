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

PORT = 8080
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PUBLIC_DIR = BASE_DIR if os.path.exists(os.path.join(BASE_DIR, "index.html")) else os.path.join(BASE_DIR, "public")
DATA_DIR = os.path.join(BASE_DIR, "data")

# In-memory cache for fast search
CACHE = {
    "papers": None,
    "departments": None,
    "model_courses": None,
    "model_papers": None,
    "stats": None
}

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

        # Default fallback to index.html for SPA routes
        self.serve_file(os.path.join(PUBLIC_DIR, "index.html"), "text/html; charset=utf-8")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/sync":
            self.handle_sync_trigger()
            return
        self.send_json_response({"error": "Endpoint not found"}, status=404)

    def handle_api_get(self, path, params):
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
                if only_with_files and not p["has_files"]:
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
            pdf_url = params.get("url", [""])[0]
            if not pdf_url or not pdf_url.startswith("https://assist.mgu.ac.in/"):
                self.send_json_response({"error": "Invalid or unauthorized URL"}, status=400)
                return

            try:
                req = urllib.request.Request(
                    pdf_url,
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
                import scripts.scraper as scraper
                scraper.run_sync(use_cache=False)
                load_data()
                print("Background resync completed.")
            except Exception as e:
                print(f"Background resync error: {e}")

        threading.Thread(target=sync_worker, daemon=True).start()
        self.send_json_response({
            "status": "started",
            "message": "Background sync with https://assist.mgu.ac.in/schema/ initiated."
        })

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

def run_server():
    socketserver.TCPServer.allow_reuse_address = True
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

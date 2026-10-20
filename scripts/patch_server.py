import os

server_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server.py")
with open(server_path, "r", encoding="utf-8") as f:
    content = f.read()

target = '''        if path == "/api/proxy-pdf":
            # Proxy PDF to allow seamless inline iframe preview
            pdf_url = params.get("url", [""])[0]
            is_valid_source = pdf_url and (
                pdf_url.startswith("https://assist.mgu.ac.in/") or
                "mgu.ac.in" in pdf_url or
                "cdn.jsdelivr.net" in pdf_url or
                "raw.githubusercontent.com" in pdf_url
            )
            if not is_valid_source:
                self.send_json_response({"error": "Invalid or unauthorized URL"}, status=400)
                return'''

replacement = '''        if path == "/api/proxy-pdf":
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
                return'''

if target in content:
    content = content.replace(target, replacement, 1)
    with open(server_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("server.py updated successfully!")
else:
    print("Target not found or already updated.")

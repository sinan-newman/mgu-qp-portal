"""
backup_all_pdfs.py
==================
Downloads all valid FYUGP question paper and scheme PDFs from MGU server,
mirrors them to the dedicated repository 'sinan-newman/mgu-qp-storage',
and updates papers.json with permanent high-speed CDN URLs.
"""

import os
import json
import time
import urllib.request
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

STORAGE_DIR = os.path.abspath("../mgu-qp-storage")
PDF_DIR = os.path.join(STORAGE_DIR, "pdf")
GIT_EXE = os.path.abspath("../mingit/cmd/git.exe")
PAT = os.environ.get("GITHUB_PAT", "")
REMOTE_REPO = "sinan-newman/mgu-qp-storage"

CDN_BASE = "https://cdn.jsdelivr.net/gh/sinan-newman/mgu-qp-storage@main/pdf"
RAW_BASE = "https://raw.githubusercontent.com/sinan-newman/mgu-qp-storage/main/pdf"


def get_all_pdf_urls():
    with open("data/papers.json", "r", encoding="utf-8") as f:
        papers = json.load(f)

    url_map = {}  # filename -> full_url
    for p in papers:
        for f in p.get("files", []):
            u = f.get("url", "")
            if u.startswith("http") and u.lower().endswith(".pdf"):
                fname = u.split("/")[-1]
                url_map[fname] = u

    return url_map


def download_single(fname, url):
    dest = os.path.join(PDF_DIR, fname)
    if os.path.exists(dest) and os.path.getsize(dest) > 1000:
        return True, fname, 0  # Already downloaded

    for attempt in range(3):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()
                if len(data) > 500:
                    with open(dest, "wb") as out:
                        out.write(data)
                    return True, fname, len(data)
        except Exception:
            time.sleep(0.5 * (attempt + 1))

    return False, fname, 0


def push_batch(batch_num, total_batches, batch_files):
    print(f"\n[Git] Staging & pushing batch {batch_num}/{total_batches} ({len(batch_files)} files)...")
    try:
        # Add files in this batch
        for bf in batch_files:
            rel_path = os.path.join("pdf", bf)
            subprocess.run([GIT_EXE, "-C", STORAGE_DIR, "add", rel_path], check=True)

        msg = f"Add FYUGP PDF archive batch {batch_num}/{total_batches} ({len(batch_files)} files)"
        subprocess.run([GIT_EXE, "-C", STORAGE_DIR, "commit", "-m", msg], check=True)

        # Set authenticated remote
        auth_url = f"https://sinan-newman:{PAT}@github.com/{REMOTE_REPO}.git"
        subprocess.run([GIT_EXE, "-C", STORAGE_DIR, "remote", "set-url", "origin", auth_url], check=True)

        # Push with retry
        pushed = False
        for push_try in range(3):
            res = subprocess.run([GIT_EXE, "-C", STORAGE_DIR, "push", "origin", "main"], capture_output=True, text=True)
            if res.returncode == 0:
                pushed = True
                print(f"[Git] Batch {batch_num}/{total_batches} pushed successfully!")
                break
            else:
                print(f"[Git] Push attempt {push_try+1} failed: {res.stderr.strip()}. Retrying...")
                time.sleep(3)

        if not pushed:
            print(f"[Git ERROR] Failed to push batch {batch_num}")
            return False
        return True
    finally:
        clean_url = f"https://github.com/{REMOTE_REPO}.git"
        subprocess.run([GIT_EXE, "-C", STORAGE_DIR, "remote", "set-url", "origin", clean_url], capture_output=True)


def update_database_urls():
    print("\n[DB] Updating papers.json with CDN and permanent mirror URLs...")
    with open("data/papers.json", "r", encoding="utf-8") as f:
        papers = json.load(f)

    for p in papers:
        # Update qp_url
        if p.get("qp_url") and p["qp_url"].lower().endswith(".pdf"):
            fname = p["qp_url"].split("/")[-1]
            p["mgu_qp_url"] = p["qp_url"]
            p["qp_url"] = f"{CDN_BASE}/{fname}"
            p["raw_qp_url"] = f"{RAW_BASE}/{fname}"

        # Update scheme_url
        if p.get("scheme_url") and p["scheme_url"].lower().endswith(".pdf"):
            fname = p["scheme_url"].split("/")[-1]
            p["mgu_scheme_url"] = p["scheme_url"]
            p["scheme_url"] = f"{CDN_BASE}/{fname}"
            p["raw_scheme_url"] = f"{RAW_BASE}/{fname}"

        # Update files array
        for fl in p.get("files", []):
            u = fl.get("url", "")
            if u.lower().endswith(".pdf"):
                fname = u.split("/")[-1]
                fl["mgu_url"] = u
                fl["url"] = f"{CDN_BASE}/{fname}"
                fl["raw_url"] = f"{RAW_BASE}/{fname}"

    with open("data/papers.json", "w", encoding="utf-8") as f:
        json.dump(papers, f, indent=2, ensure_ascii=False)

    with open("public/data/papers.json", "w", encoding="utf-8") as f:
        json.dump(papers, f, indent=2, ensure_ascii=False)

    print("[DB] papers.json updated and mirrored to public/data/papers.json!")


def main():
    os.makedirs(PDF_DIR, exist_ok=True)

    print("[Step 1] Gathering PDF URLs from papers.json...")
    url_map = get_all_pdf_urls()
    total_files = len(url_map)
    print(f"Total unique PDFs to backup: {total_files}")

    print("\n[Step 2] Concurrent download with 16 workers...")
    t0 = time.time()
    success_count = 0
    fail_count = 0
    downloaded_bytes = 0

    with ThreadPoolExecutor(max_workers=16) as executor:
        future_map = {executor.submit(download_single, fname, url): fname for fname, url in url_map.items()}
        for i, fut in enumerate(as_completed(future_map), 1):
            ok, fname, b = fut.result()
            if ok:
                success_count += 1
                downloaded_bytes += b
            else:
                fail_count += 1

            if i % 250 == 0 or i == total_files:
                elapsed = time.time() - t0
                print(f"Progress: {i}/{total_files} ({i/total_files*100:.1f}%) | Success: {success_count} | Fail: {fail_count} | Elapsed: {elapsed:.1f}s")

    print(f"\nDownload completed in {time.time() - t0:.1f}s. Success: {success_count}/{total_files}.")

    print("\n[Step 3] Batch commit & push to GitHub repository...")
    all_files = sorted(os.listdir(PDF_DIR))
    batch_size = 500
    batches = [all_files[i:i + batch_size] for i in range(0, len(all_files), batch_size)]
    total_batches = len(batches)

    for idx, batch in enumerate(batches, 1):
        push_batch(idx, total_batches, batch)

    print("\n[Step 4] Updating website database with permanent mirror URLs...")
    update_database_urls()

    print("\nALL TASKS COMPLETED SUCCESSFULLY!")


if __name__ == "__main__":
    main()

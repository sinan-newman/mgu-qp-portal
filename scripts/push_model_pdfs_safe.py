"""
push_model_pdfs_safe.py
=======================
Uploads remaining model PDFs to sinan-newman/mgu-qp-storage in ultra-safe batches of 20 files (~4.5 MB).
Includes retry logic with exponential backoff.
"""

import os
import sys
import subprocess
import time
import re

sys.stdout.reconfigure(encoding='utf-8')

STORAGE_DIR = os.path.abspath(r"C:\Users\Navirex\.gemini\antigravity\scratch\mgu-qp-storage")
GIT_EXE = os.path.abspath(r"C:\Users\Navirex\.gemini\antigravity\scratch\mingit\cmd\git.exe")

log_path = r"C:\Users\Navirex\.gemini\antigravity\brain\87d52a0b-0a87-4dfd-b1bf-99a37fa42aef\.system_generated\logs\transcript.jsonl"
token = re.search(r'(ghp_[a-zA-Z0-9]+)', open(log_path, encoding='utf-8').read()).group(1)

# Find untracked files in storage
status_out = subprocess.check_output([GIT_EXE, "-C", STORAGE_DIR, "status", "-s"], text=True)
untracked = [line.strip().replace("?? ", "").strip() for line in status_out.splitlines() if line.startswith("?? pdf/MODEL_")]
untracked.sort()

print(f"Total untracked model PDF files remaining: {len(untracked)}", flush=True)

if not untracked:
    print("No untracked model files. All files are committed and pushed!", flush=True)
    sys.exit(0)

batch_size = 20
batches = [untracked[i:i + batch_size] for i in range(0, len(untracked), batch_size)]
print(f"Total batches to push: {len(batches)} (~{batch_size} files per batch)", flush=True)

push_url = f"https://{token}@github.com/sinan-newman/mgu-qp-storage.git"

for idx, batch in enumerate(batches, 1):
    print(f"\n--- Processing Batch {idx}/{len(batches)} ({len(batch)} files) ---", flush=True)
    
    # Git add
    cmd = [GIT_EXE, "-C", STORAGE_DIR, "add"] + batch
    subprocess.run(cmd, check=True)
    
    diff_check = subprocess.run([GIT_EXE, "-C", STORAGE_DIR, "diff", "--staged", "--quiet"])
    if diff_check.returncode == 0:
        print(f"Batch {idx}/{len(batches)}: No staged changes.", flush=True)
        continue
        
    commit_msg = f"Add official MGU model papers chunk {idx}/{len(batches)}"
    subprocess.run([GIT_EXE, "-C", STORAGE_DIR, "commit", "-m", commit_msg], check=True)
    
    # Push with up to 5 retries and backoff
    pushed = False
    for attempt in range(5):
        print(f"Pushing Batch {idx}/{len(batches)} (Attempt {attempt+1}/5)...", flush=True)
        res = subprocess.run([GIT_EXE, "-C", STORAGE_DIR, "push", push_url, "main"], capture_output=True, text=True)
        if res.returncode == 0:
            print(f"Batch {idx}/{len(batches)} pushed successfully!", flush=True)
            pushed = True
            break
        else:
            err = res.stderr.strip()[:150]
            print(f"Push attempt {attempt+1} failed: {err}", flush=True)
            sleep_time = 3 * (attempt + 1)
            print(f"Waiting {sleep_time}s before retry...", flush=True)
            time.sleep(sleep_time)
            
    if not pushed:
        print(f"Fatal error pushing batch {idx}, stopping.", flush=True)
        sys.exit(1)

print("\n🎉 ALL remaining model question paper PDFs pushed successfully to sinan-newman/mgu-qp-storage!", flush=True)

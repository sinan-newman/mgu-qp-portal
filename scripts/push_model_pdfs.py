"""
push_model_pdfs.py
==================
Stages, commits, and pushes all newly split model question papers
to https://github.com/sinan-newman/mgu-qp-storage in batches.
"""

import os
import sys
import subprocess
import glob
import re

STORAGE_DIR = os.path.abspath(r"C:\Users\Navirex\.gemini\antigravity\scratch\mgu-qp-storage")
GIT_EXE = os.path.abspath(r"C:\Users\Navirex\.gemini\antigravity\scratch\mingit\cmd\git.exe")

log_path = r"C:\Users\Navirex\.gemini\antigravity\brain\87d52a0b-0a87-4dfd-b1bf-99a37fa42aef\.system_generated\logs\transcript.jsonl"
token = re.search(r'(ghp_[a-zA-Z0-9]+)', open(log_path, encoding='utf-8').read()).group(1)

model_files = glob.glob(os.path.join(STORAGE_DIR, "pdf", "MODEL_*.pdf"))
print(f"Total model PDF files to push: {len(model_files)}")

# Batch in chunks of 300 files
batch_size = 300
batches = [model_files[i:i + batch_size] for i in range(0, len(model_files), batch_size)]

push_url = f"https://{token}@github.com/sinan-newman/mgu-qp-storage.git"

for idx, batch in enumerate(batches, 1):
    print(f"\n--- Processing Batch {idx}/{len(batches)} ({len(batch)} files) ---")
    
    # Stage files
    rel_paths = [os.path.relpath(p, STORAGE_DIR) for p in batch]
    # Add files in chunks of 50 to avoid cmd length limit
    for chunk_start in range(0, len(rel_paths), 50):
        chunk = rel_paths[chunk_start:chunk_start + 50]
        cmd = [GIT_EXE, "-C", STORAGE_DIR, "add"] + chunk
        subprocess.run(cmd, check=True)
        
    # Check if there is anything staged
    diff_check = subprocess.run([GIT_EXE, "-C", STORAGE_DIR, "diff", "--staged", "--quiet"])
    if diff_check.returncode == 0:
        print(f"Batch {idx} already committed or no changes.")
        continue
        
    commit_msg = f"Add official MGU FYUGP model question papers (batch {idx}/{len(batches)})"
    subprocess.run([GIT_EXE, "-C", STORAGE_DIR, "commit", "-m", commit_msg], check=True)
    
    # Push
    print(f"Pushing batch {idx} to remote...")
    push_res = subprocess.run([GIT_EXE, "-C", STORAGE_DIR, "push", push_url, "main"], capture_output=True, text=True)
    if push_res.returncode != 0:
        print(f"Push error on batch {idx}: {push_res.stderr}")
    else:
        print(f"Batch {idx} pushed successfully!")

print("\nAll model question papers pushed to sinan-newman/mgu-qp-storage!")

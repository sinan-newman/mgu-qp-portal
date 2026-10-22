import pypdf
import os
import sys

STORAGE_DIR = r"C:\Users\Navirex\.gemini\antigravity\scratch\mgu-qp-storage\pdf"
files = [
    'MODEL_MG5DSEHIN306.pdf',
    'MODEL_MG5DSEMAL300.pdf',
    'MODEL_MG5DSEMAL304.pdf',
    'MODEL_MG5DSEPES301.pdf',
    'MODEL_MG5DSEPES303.pdf',
    'MODEL_MG5DSEPES305.pdf',
    'MODEL_MG5DSEMAL302.pdf',
    'MODEL_MG5DSEMAL303.pdf',
    'MODEL_MG5SECMAL300.pdf',
    'MODEL_MG3VACBHN200.pdf',
    'MODEL_MG4VACBHN200_PRACTICAL.pdf',
    'MODEL_MG4VACMHN200_PRACTICAL.pdf',
    'MODEL_MG4VACMMD200_PRACTICAL.pdf',
    'MODEL_MG4VACMMDA00_PRACTICAL.pdf',
    'MODEL_MG3DCSESSV202.pdf',
    'MODEL_MG3DSESSV201.pdf',
    'MODEL_MG3MDCMAL201.pdf',
    'MODEL_MG2MDCSSS100.pdf'
]

for fn in files:
    p = os.path.join(STORAGE_DIR, fn)
    print("="*50)
    print(fn)
    if os.path.exists(p):
        try:
            reader = pypdf.PdfReader(p)
            txt = reader.pages[0].extract_text() or ""
            for line in txt.splitlines()[:10]:
                sys.stdout.buffer.write((line + '\n').encode('utf-8', errors='replace'))
        except Exception as e:
            print("Error:", e)
    else:
        print("File not found on disk")

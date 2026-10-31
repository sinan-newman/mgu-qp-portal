import os

portal_dir = r'C:\Users\Navirex\.gemini\antigravity\scratch\mgu-qp-portal'

correct_candidates_js = """        // Candidate 1: Direct same-origin uploads path (most reliable when deployed on GitHub Pages or local)
        if (filename && filename.endsWith('.pdf')) {
            if (cleanRaw.includes('model_papers') || filename.startsWith('MODEL_')) {
                candidates.push('uploads/model_papers/' + filename);
                candidates.push('public/uploads/model_papers/' + filename);
            } else {
                candidates.push('uploads/' + filename);
                candidates.push('public/uploads/' + filename);
            }
            if (window.location.origin) {
                const pathname = window.location.pathname;
                const basePath = pathname.substring(0, pathname.lastIndexOf('/') + 1);
                if (cleanRaw.includes('model_papers') || filename.startsWith('MODEL_')) {
                    candidates.push(window.location.origin + basePath + 'uploads/model_papers/' + filename);
                } else {
                    candidates.push(window.location.origin + basePath + 'uploads/' + filename);
                }
            }
        }

        // Candidate 2: Primary URL as provided
        if (cleanRaw.startsWith('http://') || cleanRaw.startsWith('https://')) {
            candidates.push(cleanRaw);
        }

        // Candidate 3: GitHub Raw CDN (direct upstream source, guaranteed immediate sync)
        if (matchingFile && matchingFile.raw_url) {
            candidates.push(matchingFile.raw_url);
        } else if (filename && filename.endsWith('.pdf')) {
            candidates.push('https://raw.githubusercontent.com/sinan-newman/mgu-qp-storage/main/pdf/' + filename);
        }

        // Candidate 4: jsDelivr CDN (fast edge distribution)
        if (filename && filename.endsWith('.pdf')) {
            candidates.push('https://cdn.jsdelivr.net/gh/sinan-newman/mgu-qp-storage@main/pdf/' + filename);
            candidates.push('https://fastly.jsdelivr.net/gh/sinan-newman/mgu-qp-storage@main/pdf/' + filename);
        }"""

for rel in ['js/pdf-viewer.js', 'public/js/pdf-viewer.js']:
    path = os.path.join(portal_dir, rel)
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    start_idx = None
    end_idx = None
    for i, line in enumerate(lines):
        if '// Candidate 1: Direct same-origin uploads path' in line:
            start_idx = i
        if '// Candidate 5: Local server proxy' in line:
            end_idx = i
            break

    if start_idx is not None and end_idx is not None:
        lines[start_idx:end_idx] = [correct_candidates_js + '\n\n']
        with open(path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        print(f"Fixed {rel}")
    else:
        print(f"Failed to find range in {rel}")

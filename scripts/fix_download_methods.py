import os

portal_dir = r'C:\Users\Navirex\.gemini\antigravity\scratch\mgu-qp-portal'

correct_download_methods = """    async download(doc, activeType = 'QP') {
        const candidates = this.getCandidateUrls(doc, activeType);
        const code = (doc.course_code || doc.qp_code || 'Document').replace(/[^a-zA-Z0-9_-]/g, '_');
        const filename = code + '_' + activeType + '.pdf';
        return this._triggerDownload(candidates, filename);
    },

    async downloadDirect(url, title = 'Document', code = '') {
        const dummyDoc = {
            title: title,
            course_code: code,
            qp_url: url,
            files: [{ type: 'QP', url: url }]
        };
        const candidates = this.getCandidateUrls(dummyDoc, 'QP');
        const safeName = (code || title || 'Document').replace(/[^a-zA-Z0-9_-]/g, '_');
        const filename = safeName.toLowerCase().endsWith('.pdf') ? safeName : (safeName + '.pdf');
        return this._triggerDownload(candidates, filename);
    },"""

for rel in ['js/pdf-viewer.js', 'public/js/pdf-viewer.js']:
    path = os.path.join(portal_dir, rel)
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    start_idx = None
    end_idx = None
    for i, line in enumerate(lines):
        if 'async download(doc, activeType' in line:
            start_idx = i
        if 'async _triggerDownload(candidates, filename)' in line:
            end_idx = i
            break

    if start_idx is not None and end_idx is not None:
        lines[start_idx:end_idx] = [correct_download_methods + '\n\n']
        with open(path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        print(f"Fixed download methods in {rel}")
    else:
        print(f"Failed to find download range in {rel}")

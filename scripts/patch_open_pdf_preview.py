import os

for path in [
    os.path.join(os.path.dirname(__file__), '..', 'js', 'app.js'),
    os.path.join(os.path.dirname(__file__), '..', 'public', 'js', 'app.js')
]:
    abs_p = os.path.abspath(path)
    with open(abs_p, 'r', encoding='utf-8') as f:
        content = f.read()

    target = '''    previewDirect(btn, url, title, code) {
        if (btn) this.setButtonLoading(btn, true, 'Opening...');
        try {
            PDFViewer.openDirect(url, title, code);
        } finally {
            if (btn) {
                setTimeout(() => this.setButtonLoading(btn, false), 450);
            }
        }
    },'''

    replacement = '''    previewDirect(btn, url, title, code) {
        if (btn) this.setButtonLoading(btn, true, 'Opening...');
        try {
            PDFViewer.openDirect(url, title, code);
        } finally {
            if (btn) {
                setTimeout(() => this.setButtonLoading(btn, false), 450);
            }
        }
    },

    openPdfPreview(url, title = 'Document Preview') {
        if (window.PDFViewer) {
            window.PDFViewer.openDirect(url, title);
        }
    },'''

    if 'openPdfPreview(url,' not in content and target in content:
        content = content.replace(target, replacement, 1)
        with open(abs_p, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'Added openPdfPreview to {abs_p}')
    else:
        print(f'openPdfPreview already in {abs_p} or target not found')

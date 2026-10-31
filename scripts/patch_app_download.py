import os

portal_dir = r'C:\Users\Navirex\.gemini\antigravity\scratch\mgu-qp-portal'

download_methods = """    async downloadPaper(btn, doc, type = 'QP') {
        if (!doc) return;
        if (btn) this.setButtonLoading(btn, true, '');
        try {
            if (window.PDFViewer && window.PDFViewer.download) {
                await window.PDFViewer.download(doc, type);
            } else {
                const url = type === 'QP' ? doc.qp_url : doc.scheme_url;
                if (url) window.open(url, '_blank');
            }
        } finally {
            if (btn) {
                setTimeout(() => this.setButtonLoading(btn, false), 450);
            }
        }
    },

    async downloadDirect(btn, url, title = 'Document', code = '') {
        if (!url) return;
        if (btn) this.setButtonLoading(btn, true, '');
        try {
            if (window.PDFViewer && window.PDFViewer.downloadDirect) {
                await window.PDFViewer.downloadDirect(url, title, code);
            } else {
                window.open(url, '_blank');
            }
        } finally {
            if (btn) {
                setTimeout(() => this.setButtonLoading(btn, false), 450);
            }
        }
    },

    openPdfPreview(url, title = 'Document Preview') {"""

for rel in ['js/app.js', 'public/js/app.js']:
    path = os.path.join(portal_dir, rel)
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    if "openPdfPreview(url, title = 'Document Preview') {" in content and "async downloadPaper(btn, doc," not in content:
        content = content.replace("    openPdfPreview(url, title = 'Document Preview') {", download_methods)
        print(f"Added download methods to {rel}")

    # Replace raw download anchors in renderGroupedCourseCard
    old_qp_anchor = """<a href="${p.qp_url}" target="_blank" download class="p-1 text-xs rounded-lg bg-slate-200/80 dark:bg-slate-600 hover:bg-slate-300 dark:hover:bg-slate-500 text-slate-700 dark:text-slate-200 transition" title="Download Question Paper">
                                                <i class="bi bi-download"></i>
                                            </a>"""
    new_qp_anchor = """<button onclick="App.downloadPaper(this, ${JSON.stringify(p).replace(/\"/g, '&quot;')}, 'QP')" class="p-1 text-xs rounded-lg bg-slate-200/80 dark:bg-slate-600 hover:bg-slate-300 dark:hover:bg-slate-500 text-slate-700 dark:text-slate-200 transition" title="Download Question Paper">
                                                <i class="bi bi-download"></i>
                                            </button>"""
    content = content.replace(old_qp_anchor, new_qp_anchor)

    old_sch_anchor = """<a href="${p.scheme_url}" target="_blank" download class="p-1 text-xs rounded-lg bg-slate-200/80 dark:bg-slate-600 hover:bg-slate-300 dark:hover:bg-slate-500 text-slate-700 dark:text-slate-200 transition" title="Download Evaluation Scheme">
                                                <i class="bi bi-download"></i>
                                            </a>"""
    new_sch_anchor = """<button onclick="App.downloadPaper(this, ${JSON.stringify(p).replace(/\"/g, '&quot;')}, 'SCHEME')" class="p-1 text-xs rounded-lg bg-slate-200/80 dark:bg-slate-600 hover:bg-slate-300 dark:hover:bg-slate-500 text-slate-700 dark:text-slate-200 transition" title="Download Evaluation Scheme">
                                                <i class="bi bi-download"></i>
                                            </button>"""
    content = content.replace(old_sch_anchor, new_sch_anchor)

    old_m_anchor = """<a href="${m.cdn_url || m.url}" target="_blank" download class="p-1 text-xs rounded-lg bg-slate-200/80 dark:bg-slate-600 hover:bg-slate-300 dark:hover:bg-slate-500 text-slate-700 dark:text-slate-200 transition" title="Download Model Question Paper">
                                            <i class="bi bi-download"></i>
                                        </a>"""
    new_m_anchor = """<button onclick="App.downloadDirect(this, '${m.cdn_url || m.url}', '${m.title ? m.title.replace(/'/g, \"\\\\'\") : 'Model_Paper'}', '${course.course_code || ''}')" class="p-1 text-xs rounded-lg bg-slate-200/80 dark:bg-slate-600 hover:bg-slate-300 dark:hover:bg-slate-500 text-slate-700 dark:text-slate-200 transition" title="Download Model Question Paper">
                                            <i class="bi bi-download"></i>
                                        </button>"""
    content = content.replace(old_m_anchor, new_m_anchor)

    # In single card / table row
    old_table_qp = """<a href="${p.qp_url}" target="_blank" download class="p-1.5 text-xs rounded-lg bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 transition" title="Download Question Paper">
                                            <i class="bi bi-download"></i>
                                        </a>"""
    new_table_qp = """<button onclick="App.downloadPaper(this, ${JSON.stringify(p).replace(/\"/g, '&quot;')}, 'QP')" class="p-1.5 text-xs rounded-lg bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 transition" title="Download Question Paper">
                                            <i class="bi bi-download"></i>
                                        </button>"""
    content = content.replace(old_table_qp, new_table_qp)

    old_table_sch = """<a href="${p.scheme_url}" target="_blank" download class="p-1.5 text-xs rounded-lg bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 transition" title="Download Evaluation Scheme">
                                            <i class="bi bi-download"></i>
                                        </a>"""
    new_table_sch = """<button onclick="App.downloadPaper(this, ${JSON.stringify(p).replace(/\"/g, '&quot;')}, 'SCHEME')" class="p-1.5 text-xs rounded-lg bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 transition" title="Download Evaluation Scheme">
                                            <i class="bi bi-download"></i>
                                        </button>"""
    content = content.replace(old_table_sch, new_table_sch)

    old_table_m = """<a href="${m.cdn_url || m.url}" target="_blank" download class="p-1 text-xs rounded-lg bg-slate-200/80 dark:bg-slate-600 hover:bg-slate-300 dark:hover:bg-slate-500 text-slate-700 dark:text-slate-200 transition" title="Download Model QP">
                                        <i class="bi bi-download"></i>
                                    </a>"""
    new_table_m = """<button onclick="App.downloadDirect(this, '${m.cdn_url || m.url}', '${m.title ? m.title.replace(/'/g, \"\\\\'\") : 'Model_Paper'}', '${course.course_code || ''}')" class="p-1 text-xs rounded-lg bg-slate-200/80 dark:bg-slate-600 hover:bg-slate-300 dark:hover:bg-slate-500 text-slate-700 dark:text-slate-200 transition" title="Download Model QP">
                                        <i class="bi bi-download"></i>
                                    </button>"""
    content = content.replace(old_table_m, new_table_m)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Successfully saved {rel}")

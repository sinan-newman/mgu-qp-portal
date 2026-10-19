/**
 * PDF Viewer Modal Controller
 * Provides seamless in-browser preview, tab switching between QP & Scheme, download and fullscreen.
 */

const PDFViewer = {
    currentDoc: null,
    activeType: 'QP', // 'QP' or 'SCHEME'

    init() {
        // Modal DOM elements
        this.modal = document.getElementById('pdfModal');
        this.frame = document.getElementById('pdfIframe');
        this.titleEl = document.getElementById('modalTitle');
        this.metaEl = document.getElementById('modalMeta');
        this.qpTabBtn = document.getElementById('modalQpTab');
        this.schemeTabBtn = document.getElementById('modalSchemeTab');
        this.downloadBtn = document.getElementById('modalDownloadBtn');
        this.openExternalBtn = document.getElementById('modalExternalBtn');
        this.loadingSpinner = document.getElementById('modalLoading');

        // Close on escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && !this.modal.classList.contains('hidden')) {
                this.close();
            }
        });

        // Close on backdrop click (clicking outside the modal dialog)
        if (this.modal) {
            this.modal.addEventListener('click', (e) => {
                if (e.target === this.modal) {
                    this.close();
                }
            });
        }

        // Tab click listeners
        if (this.qpTabBtn) {
            this.qpTabBtn.addEventListener('click', () => this.switchTab('QP'));
        }
        if (this.schemeTabBtn) {
            this.schemeTabBtn.addEventListener('click', () => this.switchTab('SCHEME'));
        }
    },

    open(doc, defaultType = 'QP') {
        this.currentDoc = doc;
        this.activeType = defaultType;

        // Set Title & Meta
        this.titleEl.textContent = doc.title || doc.course_code || 'Document Preview';
        
        const qpTag = doc.qp_code ? `<span class="bg-blue-100 text-blue-800 dark:bg-blue-900/60 dark:text-blue-200 text-xs px-2 py-0.5 rounded font-mono font-medium">QP: ${doc.qp_code}</span>` : '';
        const codeTag = doc.course_code ? `<span class="bg-indigo-100 text-indigo-800 dark:bg-indigo-900/60 dark:text-indigo-200 text-xs px-2 py-0.5 rounded font-mono font-semibold">${doc.course_code}</span>` : '';
        const semTag = `<span class="text-xs text-slate-500 dark:text-slate-400 font-medium">${doc.semester_label || ('Semester ' + doc.semester)}</span>`;
        const deptTag = `<span class="text-xs text-slate-600 dark:text-slate-300">${doc.dept_name || doc.parent_dept_name}</span>`;

        this.metaEl.innerHTML = `${qpTag} ${codeTag} ${semTag} • ${deptTag}`;

        // Configure Tabs
        const hasQP = Boolean(doc.qp_url || doc.has_qp);
        const hasScheme = Boolean(doc.scheme_url || doc.has_scheme);

        if (hasQP) {
            this.qpTabBtn.classList.remove('hidden');
        } else {
            this.qpTabBtn.classList.add('hidden');
        }

        if (hasScheme) {
            this.schemeTabBtn.classList.remove('hidden');
        } else {
            this.schemeTabBtn.classList.add('hidden');
        }

        // If requested tab is not available, default to what is available
        if (defaultType === 'QP' && !hasQP && hasScheme) {
            this.activeType = 'SCHEME';
        } else if (defaultType === 'SCHEME' && !hasScheme && hasQP) {
            this.activeType = 'QP';
        } else {
            this.activeType = defaultType;
        }

        this.renderViewer();
        this.modal.classList.remove('hidden');
        document.body.classList.add('overflow-hidden');
    },

    switchTab(type) {
        this.activeType = type;
        this.renderViewer();
    },

    renderViewer() {
        const isQP = this.activeType === 'QP';
        const url = isQP ? this.currentDoc.qp_url : this.currentDoc.scheme_url;

        // Update active tab styles
        if (isQP) {
            this.qpTabBtn.className = 'px-2.5 sm:px-3 py-1 text-xs font-semibold rounded-md bg-blue-600 text-white shadow-xs flex items-center gap-1 sm:gap-1.5 transition';
            this.schemeTabBtn.className = 'px-2.5 sm:px-3 py-1 text-xs font-medium rounded-md text-slate-700 dark:text-slate-200 hover:bg-slate-300 dark:hover:bg-slate-600 flex items-center gap-1 sm:gap-1.5 transition';
        } else {
            this.schemeTabBtn.className = 'px-2.5 sm:px-3 py-1 text-xs font-semibold rounded-md bg-emerald-600 text-white shadow-xs flex items-center gap-1 sm:gap-1.5 transition';
            this.qpTabBtn.className = 'px-2.5 sm:px-3 py-1 text-xs font-medium rounded-md text-slate-700 dark:text-slate-200 hover:bg-slate-300 dark:hover:bg-slate-600 flex items-center gap-1 sm:gap-1.5 transition';
        }

        if (!url) {
            this.frame.src = 'about:blank';
            return;
        }

        // Show spinner
        this.loadingSpinner.classList.remove('hidden');

        // Proxy vs Direct/Google Docs Viewer detection
        // If served from local backend server, use /api/proxy-pdf
        // If hosted on GitHub Pages or static server, use Google Docs Viewer embed or direct URL
        let viewerSrc = url;
        const isLocalBackend = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') && window.location.port !== '';
        
        if (url.startsWith('blob:') || url.startsWith('data:')) {
            viewerSrc = url;
        } else if (isLocalBackend) {
            viewerSrc = `/api/proxy-pdf?url=${encodeURIComponent(url)}`;
        } else {
            // For GitHub Pages / static hosting, Google Docs Viewer ensures cross-origin PDF renders seamlessly
            viewerSrc = `https://docs.google.com/viewer?url=${encodeURIComponent(url)}&embedded=true`;
        }

        if (this._spinnerTimeout) clearTimeout(this._spinnerTimeout);
        this.frame.onload = () => {
            this.loadingSpinner.classList.add('hidden');
            if (this._spinnerTimeout) clearTimeout(this._spinnerTimeout);
        };
        // 3-second safety fallback if iframe onload does not fire
        this._spinnerTimeout = setTimeout(() => {
            this.loadingSpinner.classList.add('hidden');
        }, 3000);

        this.frame.src = viewerSrc;

        // Update Download & External open buttons with visual feedback
        this.downloadBtn.onclick = () => {
            const origHtml = this.downloadBtn.innerHTML;
            this.downloadBtn.innerHTML = '<i class="bi bi-arrow-repeat spinner-icon text-xs"></i> <span>Downloading...</span>';
            this.downloadBtn.classList.add('opacity-75');
            
            const a = document.createElement('a');
            a.href = url;
            a.target = '_blank';
            a.download = `${this.currentDoc.course_code || 'MGU'}_${this.activeType}.pdf`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);

            setTimeout(() => {
                this.downloadBtn.innerHTML = origHtml;
                this.downloadBtn.classList.remove('opacity-75');
            }, 1000);
        };

        this.openExternalBtn.onclick = () => {
            window.open(url, '_blank');
        };
    },

    openDirect(url, title = 'Model Question Paper', code = '') {
        const dummyDoc = {
            title: title,
            course_code: code,
            dept_name: 'Official MGU Model Question Paper (FYUGP 2024)',
            semester_label: 'Model Paper',
            qp_url: url,
            has_qp: true,
            has_scheme: false
        };
        this.open(dummyDoc, 'QP');
    },

    close() {
        this.modal.classList.add('hidden');
        document.body.classList.remove('overflow-hidden');
        this.frame.src = 'about:blank';
        this.currentDoc = null;
    }
};

window.PDFViewer = PDFViewer;

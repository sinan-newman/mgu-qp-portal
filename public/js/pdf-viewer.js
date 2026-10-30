/**
 * PDF Viewer Modal Controller - Enterprise Edition
 * High-performance, client-side PDF rendering using PDF.js.
 * Features:
 * - Direct multi-mirror fallback engine (Local uploads -> jsDelivr CDN -> Raw GitHub -> CORS Proxies -> MGU)
 * - Zero dependency on third-party viewer iframes (eliminates Google Docs "No preview available" errors completely)
 * - Smooth multi-page continuous vertical scroll with retina-sharp canvas rendering
 * - Responsive fit-to-width auto-scaling for mobile, tablet, and desktop
 * - Full toolbar controls: Zoom In/Out, Fit Width, 90° Page Rotation, Previous/Next jump
 * - Instant offline/cached blob downloads with clean academic filenames
 * - Graceful error states with direct university fallback links
 */

const PDFViewer = {
    currentDoc: null,
    activeType: 'QP', // 'QP' or 'SCHEME'
    pdfDoc: null,
    zoomScale: 1.0,
    rotation: 0,
    fitToWidthMode: true,
    currentPage: 1,
    totalPages: 1,
    activeBlob: null,
    activeBlobUrl: null,
    activeWorkingUrl: null,
    isLoading: false,

    init() {
        this.modal = document.getElementById('pdfModal');
        this.pagesContainer = document.getElementById('pdfPagesContainer');
        this.viewerContainer = document.getElementById('pdfViewerContainer');
        this.toolbar = document.getElementById('pdfToolbar');
        this.loadingSpinner = document.getElementById('modalLoading');
        this.loadingStatus = document.getElementById('modalLoadingStatus');
        this.errorCard = document.getElementById('pdfErrorCard');
        this.errorTitle = document.getElementById('pdfErrorTitle');
        this.errorMessage = document.getElementById('pdfErrorMessage');
        this.directMguLink = document.getElementById('pdfDirectMguLink');

        this.currentPageEl = document.getElementById('pdfCurrentPage');
        this.totalPagesEl = document.getElementById('pdfTotalPages');
        this.zoomLevelEl = document.getElementById('pdfZoomLevel');

        this.titleEl = document.getElementById('modalTitle');
        this.metaEl = document.getElementById('modalMeta');
        this.qpTabBtn = document.getElementById('modalQpTab');
        this.schemeTabBtn = document.getElementById('modalSchemeTab');
        this.downloadBtn = document.getElementById('modalDownloadBtn');
        this.openExternalBtn = document.getElementById('modalExternalBtn');
        this.iframe = document.getElementById('pdfIframe');

        // Configure PDF.js worker
        if (window.pdfjsLib) {
            window.pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
        }

        // Close on escape key
        document.addEventListener('keydown', (e) => {
            if (this.modal && !this.modal.classList.contains('hidden')) {
                if (e.key === 'Escape') {
                    this.close();
                } else if (e.key === '+' || e.key === '=') {
                    e.preventDefault();
                    this.zoomIn();
                } else if (e.key === '-' || e.key === '_') {
                    e.preventDefault();
                    this.zoomOut();
                } else if (e.key === '0') {
                    e.preventDefault();
                    this.zoomReset();
                } else if (e.key === 'r' || e.key === 'R') {
                    e.preventDefault();
                    this.rotate();
                }
            }
        });

        // Close on backdrop click (outside modal dialog)
        if (this.modal) {
            this.modal.addEventListener('click', (e) => {
                if (e.target === this.modal) {
                    this.close();
                }
            });
        }

        // Scroll spy to update current page number
        if (this.viewerContainer) {
            let scrollTimer = null;
            this.viewerContainer.addEventListener('scroll', () => {
                if (scrollTimer) clearTimeout(scrollTimer);
                scrollTimer = setTimeout(() => this.updateCurrentPageOnScroll(), 60);
            }, { passive: true });
        }

        // Tab click listeners
        if (this.qpTabBtn) {
            this.qpTabBtn.addEventListener('click', () => this.switchTab('QP'));
        }
        if (this.schemeTabBtn) {
            this.schemeTabBtn.addEventListener('click', () => this.switchTab('SCHEME'));
        }

        // Window resize re-fits width
        window.addEventListener('resize', () => {
            if (this.modal && !this.modal.classList.contains('hidden') && this.fitToWidthMode && this.pdfDoc) {
                if (this._resizeTimeout) clearTimeout(this._resizeTimeout);
                this._resizeTimeout = setTimeout(() => this.renderAllPages(), 150);
            }
        });
    },

    open(doc, defaultType = 'QP') {
        if (!doc) return;
        this.currentDoc = doc;
        this.activeType = defaultType;
        this.zoomScale = 1.0;
        this.rotation = 0;
        this.fitToWidthMode = true;

        // Set Title & Meta
        if (this.titleEl) {
            this.titleEl.textContent = doc.title || doc.course_code || 'Document Preview';
        }

        if (this.metaEl) {
            const qpTag = doc.qp_code ? `<span class="bg-blue-100 text-blue-800 dark:bg-blue-900/60 dark:text-blue-200 text-xs px-2 py-0.5 rounded font-mono font-medium">QP: ${doc.qp_code}</span>` : '';
            const codeTag = doc.course_code ? `<span class="bg-indigo-100 text-indigo-800 dark:bg-indigo-900/60 dark:text-indigo-200 text-xs px-2 py-0.5 rounded font-mono font-semibold">${doc.course_code}</span>` : '';
            const semTag = `<span class="text-xs text-slate-500 dark:text-slate-400 font-medium">${doc.semester_label || ('Semester ' + (doc.semester || 1))}</span>`;
            const deptTag = `<span class="text-xs text-slate-600 dark:text-slate-300">${doc.dept_name || doc.parent_dept_name || 'MGU FYUGP'}</span>`;
            this.metaEl.innerHTML = `${qpTag} ${codeTag} ${semTag} • ${deptTag}`;
        }

        // Check availability of QP vs Scheme
        const hasQP = Boolean(doc.qp_url || doc.has_qp || (doc.files && doc.files.some(f => f.type === 'QP')));
        const hasScheme = Boolean(doc.scheme_url || doc.has_scheme || (doc.files && doc.files.some(f => f.type === 'SCHEME')));

        if (this.qpTabBtn) this.qpTabBtn.classList.toggle('hidden', !hasQP);
        if (this.schemeTabBtn) this.schemeTabBtn.classList.toggle('hidden', !hasScheme);

        // Auto-select available tab if requested is missing
        if (defaultType === 'QP' && !hasQP && hasScheme) {
            this.activeType = 'SCHEME';
        } else if (defaultType === 'SCHEME' && !hasScheme && hasQP) {
            this.activeType = 'QP';
        } else {
            this.activeType = defaultType;
        }

        if (this.modal) {
            this.modal.classList.remove('hidden');
        }
        document.body.classList.add('overflow-hidden');

        this.renderViewer();

        try {
            if (window.App && typeof window.App.trackPortalVisit === 'function') {
                window.App.trackPortalVisit('Paper: ' + (doc.course_code || doc.title || 'Document'));
            }
        } catch (e) {}
    },

    switchTab(type) {
        if (this.activeType === type) return;
        this.activeType = type;
        this.renderViewer();
    },

    getCandidateUrls(doc, activeType) {
        const isQP = activeType === 'QP';
        let primaryUrl = isQP ? doc.qp_url : doc.scheme_url;
        
        // Find matching file object from files array
        const matchingFile = (doc.files || []).find(f => {
            const ftype = (f.type || '').toUpperCase();
            const flabel = (f.label || '').toUpperCase();
            if (isQP) {
                return ftype === 'QP' || flabel.includes('QP') || flabel.includes('QUESTION');
            } else {
                return ftype === 'SCHEME' || flabel.includes('SCHEME') || flabel.includes('VALUATION');
            }
        });

        if (matchingFile) {
            primaryUrl = primaryUrl || matchingFile.url;
        }

        // If no exam paper, check model papers
        if (!primaryUrl && doc.model_papers && doc.model_papers.length > 0) {
            const m = doc.model_papers[0];
            primaryUrl = m.cdn_url || m.url;
        }

        if (!primaryUrl) return [];

        const cleanRaw = primaryUrl.trim();
        const filename = cleanRaw.split('/').pop().split('?')[0];
        const candidates = [];

        // Candidate 1: Direct same-origin uploads path (most reliable when deployed on GitHub Pages or local)
        if (filename && filename.endsWith('.pdf')) {
            candidates.push(`uploads/${filename}`);
            candidates.push(`public/uploads/${filename}`);
            if (window.location.origin) {
                const pathname = window.location.pathname;
                const basePath = pathname.substring(0, pathname.lastIndexOf('/') + 1);
                candidates.push(`${window.location.origin}${basePath}uploads/${filename}`);
            }
        }

        // Candidate 2: Primary URL as provided
        if (cleanRaw.startsWith('http://') || cleanRaw.startsWith('https://')) {
            candidates.push(cleanRaw);
        }

        // Candidate 3: jsDelivr CDN
        if (filename && filename.endsWith('.pdf')) {
            candidates.push(`https://cdn.jsdelivr.net/gh/sinan-newman/mgu-qp-storage@main/pdf/${filename}`);
            candidates.push(`https://fastly.jsdelivr.net/gh/sinan-newman/mgu-qp-storage@main/pdf/${filename}`);
        }

        // Candidate 4: GitHub Raw CDN
        if (matchingFile && matchingFile.raw_url) {
            candidates.push(matchingFile.raw_url);
        } else if (filename && filename.endsWith('.pdf')) {
            candidates.push(`https://raw.githubusercontent.com/sinan-newman/mgu-qp-storage/main/pdf/${filename}`);
        }

        // Candidate 5: Local server proxy if running on localhost / dev server
        const isLocal = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') && window.location.port !== '';
        const mguUrl = (matchingFile && matchingFile.mgu_url) ? matchingFile.mgu_url : (cleanRaw.includes('mgu.ac.in') ? cleanRaw : '');
        if (isLocal && mguUrl) {
            candidates.push(`/api/proxy-pdf?url=${encodeURIComponent(mguUrl)}`);
        } else if (isLocal && cleanRaw.startsWith('http')) {
            candidates.push(`/api/proxy-pdf?url=${encodeURIComponent(cleanRaw)}`);
        }

        // Candidate 6: Direct MGU URL
        if (mguUrl) {
            candidates.push(mguUrl);
        }

        // Candidate 7: Public reliable CORS proxies for direct MGU fallback on GitHub Pages
        if (mguUrl && !isLocal) {
            candidates.push(`https://api.allorigins.win/raw?url=${encodeURIComponent(mguUrl)}`);
        }

        // Return deduplicated list
        return [...new Set(candidates.filter(Boolean))];
    },

    async fetchPdfBuffer(candidates) {
        let lastError = null;
        for (let i = 0; i < candidates.length; i++) {
            const candUrl = candidates[i];
            try {
                if (this.loadingStatus) {
                    this.loadingStatus.textContent = `Attempting secure connection (Source ${i + 1}/${candidates.length})...`;
                }

                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 6500);

                const resp = await fetch(candUrl, { signal: controller.signal });
                clearTimeout(timeoutId);

                if (resp.ok) {
                    const buf = await resp.arrayBuffer();
                    if (buf && buf.byteLength > 100) {
                        const header = new Uint8Array(buf.slice(0, 5));
                        const headerStr = String.fromCharCode(...header);
                        if (headerStr.startsWith('%PDF')) {
                            return { buffer: buf, workingUrl: candUrl };
                        }
                    }
                }
            } catch (err) {
                lastError = err;
            }
        }
        throw new Error(lastError ? lastError.message : 'All mirror sources failed to return valid PDF');
    },

    async renderViewer() {
        const isQP = this.activeType === 'QP';

        // Update tab styles
        if (this.qpTabBtn && this.schemeTabBtn) {
            if (isQP) {
                this.qpTabBtn.className = 'px-2.5 sm:px-3 py-1 text-xs font-semibold rounded-md bg-blue-600 text-white shadow-xs flex items-center gap-1 sm:gap-1.5 transition';
                this.schemeTabBtn.className = 'px-2.5 sm:px-3 py-1 text-xs font-medium rounded-md text-slate-700 dark:text-slate-200 hover:bg-slate-300 dark:hover:bg-slate-600 flex items-center gap-1 sm:gap-1.5 transition';
            } else {
                this.schemeTabBtn.className = 'px-2.5 sm:px-3 py-1 text-xs font-semibold rounded-md bg-emerald-600 text-white shadow-xs flex items-center gap-1 sm:gap-1.5 transition';
                this.qpTabBtn.className = 'px-2.5 sm:px-3 py-1 text-xs font-medium rounded-md text-slate-700 dark:text-slate-200 hover:bg-slate-300 dark:hover:bg-slate-600 flex items-center gap-1 sm:gap-1.5 transition';
            }
        }

        // Show loading spinner & reset view containers
        if (this.loadingSpinner) this.loadingSpinner.classList.remove('hidden');
        if (this.loadingStatus) this.loadingStatus.textContent = 'Resolving document source...';
        if (this.pagesContainer) {
            this.pagesContainer.innerHTML = '';
            this.pagesContainer.classList.remove('hidden');
        }
        if (this.toolbar) this.toolbar.classList.remove('hidden');
        if (this.errorCard) this.errorCard.classList.add('hidden');
        if (this.iframe) {
            this.iframe.src = 'about:blank';
            this.iframe.classList.add('hidden');
        }

        const candidates = this.getCandidateUrls(this.currentDoc, this.activeType);

        if (!candidates || candidates.length === 0) {
            this.showError('No PDF URL registered for this paper category.');
            return;
        }

        try {
            const { buffer, workingUrl } = await this.fetchPdfBuffer(candidates);
            this.activeWorkingUrl = workingUrl;
            this.activeBlob = new Blob([buffer], { type: 'application/pdf' });
            if (this.activeBlobUrl) {
                try { URL.revokeObjectURL(this.activeBlobUrl); } catch (e) {}
            }
            this.activeBlobUrl = URL.createObjectURL(this.activeBlob);

            // Configure Download & New Tab actions
            this.setupActions(this.activeBlob, workingUrl, this.currentDoc, this.activeType);

            // Render PDF.js
            if (window.pdfjsLib) {
                if (this.loadingStatus) this.loadingStatus.textContent = 'Rendering document pages...';
                const loadingTask = window.pdfjsLib.getDocument({
                    data: buffer,
                    cMapUrl: 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/cmaps/',
                    cMapPacked: true
                });

                this.pdfDoc = await loadingTask.promise;
                this.totalPages = this.pdfDoc.numPages;
                this.currentPage = 1;

                if (this.currentPageEl) this.currentPageEl.textContent = '1';
                if (this.totalPagesEl) this.totalPagesEl.textContent = String(this.totalPages);

                await this.renderAllPages();
            } else {
                // Secondary fallback: Native object / embed
                this.fallbackToIframe(this.activeBlobUrl);
            }

            if (this.loadingSpinner) this.loadingSpinner.classList.add('hidden');
        } catch (err) {
            console.warn('[PDFViewer] Fetch buffer error:', err);
            // If direct PDF.js fetch failed, try fallback iframe before showing error
            const directMgu = this.currentDoc.qp_url || this.currentDoc.scheme_url || '';
            this.showError('This paper is listed in the examination portal, but the digital PDF is temporarily unreachable or undergoing university digitization.', directMgu);
        }
    },

    async renderAllPages() {
        if (!this.pdfDoc || !this.pagesContainer) return;
        this.pagesContainer.innerHTML = '';

        const containerWidth = this.viewerContainer ? (this.viewerContainer.clientWidth || 800) : 800;
        const dpr = Math.min(window.devicePixelRatio || 1, 2.0);

        for (let num = 1; num <= this.pdfDoc.numPages; num++) {
            const page = await this.pdfDoc.getPage(num);
            const baseViewport = page.getViewport({ scale: 1.0, rotation: this.rotation });

            let finalScale = this.zoomScale;
            if (this.fitToWidthMode) {
                const isMobile = window.innerWidth < 640;
                const sidePadding = isMobile ? 16 : 48;
                const availableWidth = Math.max(containerWidth - sidePadding, 280);
                const maxWidth = isMobile ? availableWidth : Math.min(availableWidth, 900);
                finalScale = maxWidth / baseViewport.width;
                this.zoomScale = finalScale;
            }

            const renderViewport = page.getViewport({ scale: finalScale * dpr, rotation: this.rotation });
            const cssWidth = renderViewport.width / dpr;
            const cssHeight = renderViewport.height / dpr;

            const pageWrapper = document.createElement('div');
            pageWrapper.className = 'pdf-page-wrapper relative bg-white dark:bg-slate-900 shadow-lg rounded-sm sm:rounded-md overflow-hidden border border-slate-300 dark:border-slate-700/80 my-2 transition-all duration-150';
            pageWrapper.dataset.pageNum = String(num);
            pageWrapper.style.width = `${cssWidth}px`;
            pageWrapper.style.maxWidth = '100%';

            const canvas = document.createElement('canvas');
            canvas.width = renderViewport.width;
            canvas.height = renderViewport.height;
            canvas.style.width = `${cssWidth}px`;
            canvas.style.height = `${cssHeight}px`;
            canvas.style.maxWidth = '100%';
            canvas.className = 'block mx-auto';

            const ctx = canvas.getContext('2d', { alpha: false });
            ctx.imageSmoothingEnabled = true;
            ctx.imageSmoothingQuality = 'high';

            pageWrapper.appendChild(canvas);
            this.pagesContainer.appendChild(pageWrapper);

            await page.render({
                canvasContext: ctx,
                viewport: renderViewport
            }).promise;
        }

        this.updateZoomLabel();
    },

    updateCurrentPageOnScroll() {
        if (!this.viewerContainer || !this.currentPageEl || this.totalPages <= 1) return;
        const wrappers = this.viewerContainer.querySelectorAll('.pdf-page-wrapper');
        const containerTop = this.viewerContainer.scrollTop;
        const containerHeight = this.viewerContainer.clientHeight;
        const middleY = containerTop + (containerHeight / 3);

        for (const wrap of wrappers) {
            const top = wrap.offsetTop;
            const height = wrap.offsetHeight;
            if (top <= middleY && (top + height) >= middleY) {
                const pageNum = wrap.dataset.pageNum;
                if (pageNum && this.currentPage !== parseInt(pageNum, 10)) {
                    this.currentPage = parseInt(pageNum, 10);
                    this.currentPageEl.textContent = String(this.currentPage);
                }
                break;
            }
        }
    },

    zoomIn() {
        this.fitToWidthMode = false;
        this.zoomScale = Math.min(this.zoomScale * 1.2, 3.5);
        this.renderAllPages();
    },

    zoomOut() {
        this.fitToWidthMode = false;
        this.zoomScale = Math.max(this.zoomScale / 1.2, 0.4);
        this.renderAllPages();
    },

    zoomReset() {
        this.fitToWidthMode = false;
        this.zoomScale = 1.0;
        this.renderAllPages();
    },

    fitWidth() {
        this.fitToWidthMode = true;
        this.renderAllPages();
    },

    rotate() {
        this.rotation = (this.rotation + 90) % 360;
        this.renderAllPages();
    },

    prevPage() {
        if (this.currentPage > 1) {
            this.scrollToPage(this.currentPage - 1);
        }
    },

    nextPage() {
        if (this.currentPage < this.totalPages) {
            this.scrollToPage(this.currentPage + 1);
        }
    },

    scrollToPage(num) {
        if (!this.viewerContainer) return;
        const target = this.viewerContainer.querySelector(`.pdf-page-wrapper[data-page-num="${num}"]`);
        if (target) {
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            this.currentPage = num;
            if (this.currentPageEl) this.currentPageEl.textContent = String(num);
        }
    },

    updateZoomLabel() {
        if (this.zoomLevelEl) {
            const pct = Math.round(this.zoomScale * 100);
            this.zoomLevelEl.textContent = this.fitToWidthMode ? 'Fit Width' : `${pct}%`;
        }
    },

    setupActions(blob, workingUrl, doc, activeType) {
        if (this.downloadBtn) {
            this.downloadBtn.onclick = () => {
                const safeCode = (doc.course_code || 'MGU').replace(/[^a-zA-Z0-9_-]/g, '');
                const safeType = activeType === 'QP' ? 'Question_Paper' : 'Valuation_Scheme';
                const filename = `${safeCode}_${safeType}.pdf`;

                if (blob) {
                    const a = document.createElement('a');
                    const bUrl = URL.createObjectURL(blob);
                    a.href = bUrl;
                    a.download = filename;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    setTimeout(() => URL.revokeObjectURL(bUrl), 2000);
                } else if (workingUrl) {
                    const a = document.createElement('a');
                    a.href = workingUrl;
                    a.target = '_blank';
                    a.download = filename;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                }
            };
        }

        if (this.openExternalBtn) {
            this.openExternalBtn.onclick = () => {
                if (this.activeBlobUrl) {
                    window.open(this.activeBlobUrl, '_blank');
                } else if (workingUrl) {
                    window.open(workingUrl, '_blank');
                } else {
                    const direct = doc.qp_url || doc.scheme_url;
                    if (direct) window.open(direct, '_blank');
                }
            };
        }
    },

    fallbackToIframe(url) {
        if (!this.iframe) return;
        if (this.pagesContainer) this.pagesContainer.classList.add('hidden');
        if (this.toolbar) this.toolbar.classList.add('hidden');
        this.iframe.src = url;
        this.iframe.classList.remove('hidden');
    },

    showError(msg, directUrl = '') {
        if (this.loadingSpinner) this.loadingSpinner.classList.add('hidden');
        if (this.pagesContainer) this.pagesContainer.classList.add('hidden');
        if (this.toolbar) this.toolbar.classList.add('hidden');
        if (this.iframe) this.iframe.classList.add('hidden');

        if (this.errorCard) {
            this.errorCard.classList.remove('hidden');
            if (this.errorTitle) {
                this.errorTitle.textContent = 'Document Pending University Upload';
            }
            if (this.errorMessage) {
                this.errorMessage.textContent = msg || 'This paper is listed in the examination database, but the official PDF document is not yet available.';
            }
            if (this.directMguLink) {
                const targetUrl = directUrl || (this.currentDoc ? (this.currentDoc.qp_url || this.currentDoc.scheme_url) : '');
                if (targetUrl && targetUrl.startsWith('http')) {
                    this.directMguLink.href = targetUrl;
                    this.directMguLink.classList.remove('hidden');
                } else {
                    this.directMguLink.classList.add('hidden');
                }
            }
        }
    },

    retry() {
        this.renderViewer();
    },

    openDirect(url, title = 'Document Preview', code = '') {
        const dummyDoc = {
            title: title,
            course_code: code,
            dept_name: 'Official Mahatma Gandhi University Examination Asset',
            semester_label: 'FYUGP',
            qp_url: url,
            has_qp: true,
            has_scheme: false,
            files: [{ type: 'QP', url: url, label: 'Question Paper' }]
        };
        this.open(dummyDoc, 'QP');
    },

    close() {
        if (this.modal) {
            this.modal.classList.add('hidden');
        }
        document.body.classList.remove('overflow-hidden');
        if (this.pagesContainer) {
            this.pagesContainer.innerHTML = '';
        }
        if (this.iframe) {
            this.iframe.src = 'about:blank';
        }
        if (this.activeBlobUrl) {
            try { URL.revokeObjectURL(this.activeBlobUrl); } catch (e) {}
            this.activeBlobUrl = null;
        }
        this.activeBlob = null;
        this.pdfDoc = null;
    }
};

// Global export
window.PDFViewer = PDFViewer;

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => PDFViewer.init());
} else {
    PDFViewer.init();
}

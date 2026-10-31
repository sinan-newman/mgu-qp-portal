/**
 * Main Application Logic for MGU Question Papers Portal (FYUGP)
 * Features:
 * - Department-Wise Navigation as Primary (Tab 1)
 * - All Question Papers & Schemes (Tab 2)
 * - Saved Question Papers (Tab 3)
 * - Alphabetical Department Cards (A-Z) with Instant Filter
 * - Department Detail: Semester 1-8 Tabs + All Semesters + Year-Wise Grouping
 * - Ultra-Fast Multi-Term Tokenized Search with Code Normalization & Aliases
 * - In-Browser PDF Preview Modal & Direct Download
 * - Save / Bookmark with Star Icon & Text
 */

// IndexedDB Storage for Missing Paper Upload Attachments
const MissingFileStorage = {
    dbName: 'mgu_missing_reports_db',
    dbVersion: 1,
    storeName: 'files',

    async getDb() {
        return new Promise((resolve, reject) => {
            if (!window.indexedDB) return reject(new Error('IndexedDB not supported'));
            const req = indexedDB.open(this.dbName, this.dbVersion);
            req.onupgradeneeded = (e) => {
                const db = e.target.result;
                if (!db.objectStoreNames.contains(this.storeName)) {
                    db.createObjectStore(this.storeName, { keyPath: 'id' });
                }
            };
            req.onsuccess = () => resolve(req.result);
            req.onerror = () => reject(req.error);
        });
    },

    async saveFile(id, fileBlob, fileName) {
        try {
            const db = await this.getDb();
            return new Promise((resolve, reject) => {
                const tx = db.transaction(this.storeName, 'readwrite');
                const store = tx.objectStore(this.storeName);
                store.put({ id, blob: fileBlob, fileName, savedAt: Date.now() });
                tx.oncomplete = () => resolve(true);
                tx.onerror = () => reject(tx.error);
            });
        } catch (e) {
            console.warn('IndexedDB save failed:', e);
            return false;
        }
    },

    async getFile(id) {
        try {
            const db = await this.getDb();
            return new Promise((resolve, reject) => {
                const tx = db.transaction(this.storeName, 'readonly');
                const store = tx.objectStore(this.storeName);
                const req = store.get(id);
                req.onsuccess = () => resolve(req.result);
                req.onerror = () => reject(req.error);
            });
        } catch (e) {
            console.warn('IndexedDB get failed:', e);
            return null;
        }
    },

    async deleteFile(id) {
        try {
            const db = await this.getDb();
            return new Promise((resolve) => {
                const tx = db.transaction(this.storeName, 'readwrite');
                const store = tx.objectStore(this.storeName);
                store.delete(id);
                tx.oncomplete = () => resolve(true);
            });
        } catch (e) {
            return false;
        }
    }
};

const App = {
    // Data stores
    papers: [],
    departments: [],
    stats: {},
    bookmarks: new Set(),
    filteredPapers: [],
    feedbackReports: [],
    inboxFilter: 'all',
    currentCrawlModalRecord: null,
    currentCrawlModalFilter: 'all',

    modelState: {
        searchQuery: '',
        selectedSemester: 'all',
        selectedDept: '',
        selectedType: '',
        currentPage: 1,
        itemsPerPage: 24
    },
    modelCatalog: [],

    // Department & Search Aliases Dictionary
    ALIASES: {
        'maths': ['mat', 'mathematics', 'maths', 'math'],
        'math': ['mat', 'mathematics', 'maths', 'math'],
        'calculus': ['mat', 'calculus'],
        'algebra': ['mat', 'algebra'],
        'cs': ['csc', 'computer science', 'computer', 'bca', 'information technology'],
        'comp': ['csc', 'computer science'],
        'computer': ['csc', 'computer science'],
        'it': ['csc', 'information technology'],
        'bca': ['csc', 'bca', 'computer application'],
        'bba': ['bba', 'business administration'],
        'comm': ['com', 'commerce', 'bcom', 'corporate', 'finance'],
        'commerce': ['com', 'commerce', 'bcom'],
        'bcom': ['com', 'commerce'],
        'accounting': ['com', 'accounting'],
        'stats': ['sta', 'statistics'],
        'stat': ['sta', 'statistics'],
        'statistics': ['sta', 'statistics'],
        'eng': ['eng', 'english', 'literature'],
        'english': ['eng', 'english', 'literature'],
        'mal': ['mal', 'malayalam'],
        'malayalam': ['mal', 'malayalam'],
        'hin': ['hin', 'hindi'],
        'hindi': ['hin', 'hindi'],
        'arb': ['arb', 'arabic'],
        'arabic': ['arb', 'arabic'],
        'san': ['san', 'sanskrit', 'skt'],
        'sanskrit': ['san', 'sanskrit'],
        'phy': ['phy', 'physics'],
        'physics': ['phy', 'physics'],
        'chem': ['che', 'chemistry'],
        'chemistry': ['che', 'chemistry'],
        'bot': ['bot', 'botany', 'plant'],
        'botany': ['bot', 'botany'],
        'zoo': ['zgy', 'zoology', 'animal'],
        'zoology': ['zgy', 'zoology'],
        'biotech': ['btg', 'biotechnology'],
        'biotechnology': ['btg', 'biotechnology'],
        'biochem': ['bch', 'biochemistry'],
        'biochemistry': ['bch', 'biochemistry'],
        'bioinfo': ['bif', 'bioinformatics'],
        'bioinformatics': ['bif', 'bioinformatics'],
        'bio': ['btg', 'bch', 'bif', 'bot', 'zgy'],
        'eco': ['eco', 'economics'],
        'economics': ['eco', 'economics'],
        'hist': ['his', 'history'],
        'history': ['his', 'history'],
        'pol': ['pol', 'politics', 'political science'],
        'politics': ['pol', 'political science'],
        'political': ['pol', 'political science'],
        'psych': ['psy', 'psychology'],
        'psychology': ['psy', 'psychology'],
        'pe': ['pes', 'physical education', 'sports'],
        'sports': ['pes', 'physical education'],
        'physical': ['pes', 'physical education'],
        'geo': ['geo', 'geology', 'earth'],
        'geology': ['geo', 'geology'],
        'music': ['mus', 'music'],
        'bsw': ['bsw', 'social work'],
        'bhn': ['bhn', 'bharatanatyam', 'bharathanatyam', 'pfa', 'performing arts'],
        'bharatanatyam': ['bhn', 'bharatanatyam', 'bharathanatyam', 'pfa', 'performing arts'],
        'bharathanatyam': ['bhn', 'bharatanatyam', 'bharathanatyam', 'pfa', 'performing arts'],
        'pfa': ['pfa', 'performing arts', 'bhn', 'kcn', 'kmd', 'ksn', 'kvs', 'mhn'],
        'performing': ['pfa', 'performing arts', 'bhn']
    },

    // Main Filters State
    state: {
        activeTab: 'departments', // Primary: 'departments' | 'papers' | 'bookmarks'
        searchQuery: '',
        selectedDept: 'ALL',
        selectedSemester: 'ALL',
        selectedCourseType: 'ALL',
        onlyWithFiles: true,
        viewMode: 'grid', // 'grid' | 'table'
        currentPage: 1,
        pageSize: 24,
        isDarkMode: false
    },

    // Department Detail & Cards State
    deptState: {
        activeDept: null,
        selectedSemester: 'ALL', // 'ALL' | 1..8
        searchQuery: '',         // In-department paper search
        deptSearchQuery: '',     // Department list quick filter
        signatureExpanded: false // Collapsible signature courses dropdown
    },

    // Routing & Navigation History State
    currentRoute: null,
    lastDeptListScrollY: 0,

    // Admin Smart Ingestion & Splitting State
    selectedSmartPdfFile: null,
    currentPaperCategory: 'QP',
    adminSplitPapers: [],
    splitCardsFilter: 'ALL',
    splitCardsSearchQuery: '',
    masterPdfUrl: null,

    async init() {
        this.loadBookmarks();
        this.initTheme();
        this.bindEvents();
        PDFViewer.init();

        // Load data
        await this.loadAllData();
        this.updateStatsUI();
        this.renderDepartmentsList();
        this.applyFilters();

        // Load reports & feedback
        await this.loadFeedbackReports();

        // Track portal visitor session
        this.trackPortalVisit();

        const isAuth = sessionStorage.getItem('mgu_admin_auth') === 'true';
        if (isAuth) {
            document.getElementById('adminNavBtn')?.classList.remove('hidden');
            document.getElementById('adminActiveBadge')?.classList.remove('hidden');
            const userDisplay = document.getElementById('adminUserDisplayName');
            if (userDisplay) {
                userDisplay.textContent = sessionStorage.getItem('mgu_admin_user') || 'sinan_cc';
            }
            this.populateAdminDeptDropdown();
            this.fetchVisitorStats();
        } else {
            document.getElementById('adminNavBtn')?.classList.add('hidden');
        }

        // Close feedback modal on Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeFeedbackModal();
            }
        });

        // Initialize Client-Side URL Routing
        this.handleRouting(window.location.hash);

        // Listen for browser navigation (Back, Forward, hash changes)
        window.addEventListener('hashchange', () => this.handleRouting(window.location.hash));
        window.addEventListener('popstate', () => this.handleRouting(window.location.hash));

        // Secret Admin URL query trigger: ?admin
        const hasAdminParam = new URLSearchParams(window.location.search).has('admin');
        if (hasAdminParam) {
            this.openAdminPage(true);
        }

        // Secret Keyboard Shortcut: Ctrl + Shift + A or Alt + A
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey && e.shiftKey && (e.key === 'A' || e.key === 'a')) || (e.altKey && (e.key === 'a' || e.key === 'A'))) {
                e.preventDefault();
                this.openAdminPage(true);
            }
        });
    },

    loadBookmarks() {
        try {
            const saved = localStorage.getItem('mgu_qp_bookmarks');
            if (saved) {
                this.bookmarks = new Set(JSON.parse(saved));
            }
        } catch (e) {
            this.bookmarks = new Set();
        }
        this.updateBookmarkCountBadge();
    },

    saveBookmarks() {
        try {
            localStorage.setItem('mgu_qp_bookmarks', JSON.stringify(Array.from(this.bookmarks)));
        } catch (e) {}
        this.updateBookmarkCountBadge();
    },

    toggleBookmark(paperId) {
        if (this.bookmarks.has(paperId)) {
            this.bookmarks.delete(paperId);
        } else {
            this.bookmarks.add(paperId);
        }
        this.saveBookmarks();

        // Re-render if on bookmarks tab
        if (this.state.activeTab === 'bookmarks') {
            this.renderPapers();
        } else {
            // Update all button instances for this paperId on screen
            const isBookmarked = this.bookmarks.has(paperId);
            document.querySelectorAll(`[data-bm-id="${paperId}"]`).forEach(btn => {
                btn.className = `px-2.5 py-1 text-xs font-semibold rounded-lg flex items-center gap-1.5 transition ${
                    isBookmarked 
                        ? 'bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-700' 
                        : 'bg-slate-100 dark:bg-slate-700 hover:bg-amber-50 dark:hover:bg-amber-950/40 text-slate-600 dark:text-slate-300 hover:text-amber-700 border border-slate-200 dark:border-slate-600'
                }`;
                btn.innerHTML = `
                    <i class="bi ${isBookmarked ? 'bi-star-fill text-amber-500' : 'bi-star'}"></i>
                    <span>${isBookmarked ? 'Saved' : 'Save'}</span>
                `;
            });
        }
    },

    updateBookmarkCountBadge() {
        const el = document.getElementById('bookmarkCountBadge');
        if (el) {
            el.textContent = this.bookmarks.size;
            el.classList.toggle('hidden', this.bookmarks.size === 0);
        }
    },

    setButtonLoading(btn, isLoading, loadingText = 'Processing...') {
        const el = typeof btn === 'string' ? document.getElementById(btn) : btn;
        if (!el) return;

        if (isLoading) {
            if (el.dataset.originalHtml) return;
            el.dataset.originalHtml = el.innerHTML;
            el.dataset.originalDisabled = el.disabled ? 'true' : 'false';
            el.disabled = true;
            el.classList.add('btn-loading');
            el.innerHTML = `<span class="spinner-icon mr-1.5 inline-block w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin"></span><span>${loadingText}</span>`;
        } else {
            if (el.dataset.originalHtml !== undefined) {
                el.innerHTML = el.dataset.originalHtml;
                delete el.dataset.originalHtml;
            }
            if (el.dataset.originalDisabled === 'false') {
                el.disabled = false;
            }
            delete el.dataset.originalDisabled;
            el.classList.remove('btn-loading');
        }
    },

    reportSelectedFile: null,

    formatFileSize(bytes) {
        if (!bytes || bytes <= 0) return '0 B';
        const units = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return (bytes / Math.pow(1024, i)).toFixed(1) + ' ' + units[i];
    },

    handleReportFileSelect(e) {
        const file = e.target?.files?.[0];
        if (!file) return;

        if (!file.name.toLowerCase().endsWith('.pdf') && file.type !== 'application/pdf') {
            alert('Please select a valid PDF file.');
            if (e.target) e.target.value = '';
            return;
        }

        if (file.size > 25 * 1024 * 1024) {
            alert('File size exceeds 25 MB limit. Please select a smaller PDF or provide a Google Drive link.');
            if (e.target) e.target.value = '';
            return;
        }

        this.reportSelectedFile = file;

        const promptEl = document.getElementById('reportDropzonePrompt');
        const previewEl = document.getElementById('reportFilePreview');
        const nameEl = document.getElementById('reportFileName');
        const sizeEl = document.getElementById('reportFileSize');

        if (nameEl) nameEl.textContent = file.name;
        if (sizeEl) sizeEl.textContent = this.formatFileSize(file.size);
        if (promptEl) promptEl.classList.add('hidden');
        if (previewEl) previewEl.classList.remove('hidden');
    },

    clearReportFile(e) {
        if (e) {
            e.preventDefault();
            e.stopPropagation();
        }
        this.reportSelectedFile = null;
        const fileInput = document.getElementById('reportFileInput');
        if (fileInput) fileInput.value = '';

        const promptEl = document.getElementById('reportDropzonePrompt');
        const previewEl = document.getElementById('reportFilePreview');
        if (previewEl) previewEl.classList.add('hidden');
        if (promptEl) promptEl.classList.remove('hidden');
    },

    async previewReportFile(id) {
        const report = (this.feedbackReports || []).find(r => r.id === id);
        if (!report) return;

        // 1. Try fileUrl if already hosted
        if (report.fileUrl) {
            if (window.PDFViewer) {
                window.PDFViewer.openDirect(report.fileUrl, `${report.courseCode || 'Paper'} - ${report.title || 'Missing Paper'}`, report.courseCode || '');
                return;
            }
        }

        // 2. Try IndexedDB
        const stored = await MissingFileStorage.getFile(id);
        if (stored && stored.blob) {
            const blobUrl = URL.createObjectURL(stored.blob);
            if (window.PDFViewer) {
                window.PDFViewer.openDirect(blobUrl, `${report.courseCode || 'Paper'} - ${report.title || 'Missing Paper'} (Uploaded)`, report.courseCode || '');
            } else {
                window.open(blobUrl, '_blank');
            }
            return;
        }

        // 3. Try driveLink if available
        if (report.driveLink) {
            window.open(report.driveLink, '_blank');
            return;
        }

        alert('Unable to load attached file. The file may need to be uploaded to the server or provided via Drive link.');
    },

    async downloadReportFile(id) {
        const report = (this.feedbackReports || []).find(r => r.id === id);
        if (!report) return;

        const downloadName = (report.fileName || `${report.courseCode || 'Missing'}_paper.pdf`).replace(/[^a-zA-Z0-9_.-]/g, '_');

        // 1. Try IndexedDB
        const stored = await MissingFileStorage.getFile(id);
        if (stored && stored.blob) {
            const blobUrl = URL.createObjectURL(stored.blob);
            const a = document.createElement('a');
            a.href = blobUrl;
            a.download = downloadName;
            document.body.appendChild(a);
            a.click();
            setTimeout(() => {
                document.body.removeChild(a);
                URL.revokeObjectURL(blobUrl);
            }, 200);
            return;
        }

        // 2. Try fileUrl
        if (report.fileUrl) {
            if (window.PDFViewer && window.PDFViewer.downloadDirect) {
                window.PDFViewer.downloadDirect(report.fileUrl, report.title, report.courseCode);
            } else {
                window.open(report.fileUrl, '_blank');
            }
            return;
        }

        // 3. Try driveLink
        if (report.driveLink) {
            window.open(report.driveLink, '_blank');
            return;
        }

        alert('File attachment not found.');
    },

    previewPaper(btn, doc, type = 'QP') {
        if (btn) this.setButtonLoading(btn, true, 'Opening...');
        try {
            PDFViewer.open(doc, type);
        } finally {
            if (btn) {
                setTimeout(() => this.setButtonLoading(btn, false), 450);
            }
        }
    },

    previewDirect(btn, url, title, code) {
        if (btn) this.setButtonLoading(btn, true, 'Opening...');
        try {
            PDFViewer.openDirect(url, title, code);
        } finally {
            if (btn) {
                setTimeout(() => this.setButtonLoading(btn, false), 450);
            }
        }
    },

    async downloadPaper(btn, doc, type = 'QP') {
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

    openPdfPreview(url, title = 'Document Preview') {
        if (window.PDFViewer) {
            window.PDFViewer.openDirect(url, title);
        }
    },

    initTheme() {
        const isUserSet = localStorage.getItem('mgu_theme_user_set') === 'true';
        let isDark = false;
        
        if (isUserSet) {
            isDark = localStorage.getItem('mgu_theme') === 'dark';
        } else {
            // Default to Day (Light) Mode unless mobile/system explicitly prefers dark
            isDark = Boolean(window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches);
        }

        this.applyTheme(isDark, false);

        // Listen for mobile/system theme switches (e.g. phone day/night schedule)
        if (window.matchMedia) {
            const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
            const listener = (e) => {
                if (localStorage.getItem('mgu_theme_user_set') !== 'true') {
                    this.applyTheme(e.matches, false);
                }
            };
            if (mediaQuery.addEventListener) {
                mediaQuery.addEventListener('change', listener);
            } else if (mediaQuery.addListener) {
                mediaQuery.addListener(listener);
            }
        }
    },

    applyTheme(isDark, saveAsUserChoice = false) {
        this.state.isDarkMode = isDark;
        if (isDark) {
            document.documentElement.classList.add('dark');
            const icon = document.getElementById('themeIcon');
            if (icon) icon.className = 'bi bi-sun text-amber-400';
        } else {
            document.documentElement.classList.remove('dark');
            const icon = document.getElementById('themeIcon');
            if (icon) icon.className = 'bi bi-moon-stars text-slate-600';
        }

        if (saveAsUserChoice) {
            localStorage.setItem('mgu_theme_user_set', 'true');
            localStorage.setItem('mgu_theme', isDark ? 'dark' : 'light');
        }
    },

    setTheme(isDark) {
        this.applyTheme(isDark, true);
    },

    toggleTheme() {
        this.applyTheme(!this.state.isDarkMode, true);
    },

    async fetchResource(apiUrl, staticUrl) {
        const isLocalBackend = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') && window.location.port !== '';
        if (isLocalBackend) {
            try {
                const res = await fetch(apiUrl);
                if (res.ok) return await res.json();
            } catch (e) {}
        }
        try {
            const resStatic = await fetch(staticUrl);
            if (resStatic.ok) return await resStatic.json();
        } catch (e) {
            console.error('Failed to load static resource:', staticUrl, e);
        }
        return null;
    },

    async loadAllData() {
        const fetchResource = (apiUrl, staticUrl) => this.fetchResource(apiUrl, staticUrl);

        const [papersData, deptsData, statsData, modelData, syllabiData] = await Promise.all([
            fetchResource('/api/papers?limit=10000&has_files=false', 'data/papers.json'),
            fetchResource('/api/departments', 'data/departments.json'),
            fetchResource('/api/stats', 'data/stats.json'),
            fetchResource('/api/model-papers', 'data/model_papers.json'),
            fetchResource('/api/syllabi', 'data/mgu_syllabi.json')
        ]);

        const rawPapers = (papersData && papersData.papers) ? papersData.papers : (Array.isArray(papersData) ? papersData : []);
        
        // Strict FYUGP restriction: filter out any CBCS records
        this.papers = rawPapers.filter(p => 
            p.batch !== 'CBCS' && 
            p.course_type !== 'CBCS' &&
            !p.needs_review &&
            p.status !== 'pending_review' &&
            p.dept_code !== 'GEN' &&
            p.course_code &&
            p.course_code !== 'GEN'
        );
        this.buildCourseCatalogIndex();
        
        // Sort departments strictly alphabetically (A-Z)
        const rawDepts = deptsData || [];
        this.departments = rawDepts.sort((a, b) => a.name.localeCompare(b.name));
        this.stats = statsData || {};
        this.modelCatalog = Array.isArray(modelData) ? modelData : [];
        this.syllabi = (syllabiData && syllabiData.programs) ? syllabiData.programs : [];
    },

    buildCourseCatalogIndex() {
        this._courseCatalogMap = {
            byCode: new Map(),
            byTitle: new Map()
        };
        (this.papers || []).forEach(p => {
            if (p.course_code) {
                const c = p.course_code.trim().toUpperCase();
                if (!this._courseCatalogMap.byCode.has(c)) {
                    this._courseCatalogMap.byCode.set(c, []);
                }
                this._courseCatalogMap.byCode.get(c).push(p);
            }
            if (p.title) {
                const t = p.title.trim().toUpperCase();
                if (!this._courseCatalogMap.byTitle.has(t)) {
                    this._courseCatalogMap.byTitle.set(t, []);
                }
                this._courseCatalogMap.byTitle.get(t).push(p);
            }
        });
    },

    getActiveDepartments() {
        return this.departments.filter(d => {
            const deptCodes = new Set([d.code, ...(d.majors || []).map(m => m.code), ...(d.minors || []).map(m => m.code)]);
            return this.papers.some(p => (deptCodes.has(p.parent_dept) || deptCodes.has(p.dept_code)) && (p.has_files || (p.model_papers && p.model_papers.length > 0)));
        });
    },


    crawlHistoryCache: [],

    async loadCrawlHistory(force = false) {
        const container = document.getElementById('crawlHistoryContainer');
        if (!container) return;

        if (force || !this.crawlHistoryCache || this.crawlHistoryCache.length === 0) {
            container.innerHTML = '<div class="p-4 text-center text-xs text-slate-400"><div class="animate-spin inline-block w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full mr-2"></div>Loading crawl audit logs...</div>';
        }

        try {
            const data = await this.fetchResource('/api/crawl-history', 'data/crawl_history.json');
            this.crawlHistoryCache = Array.isArray(data) ? data : (data?.history || []);
            this.renderCrawlHistory(this.crawlHistoryCache);
        } catch (e) {
            console.error("Error loading crawl history:", e);
            if (container) {
                container.innerHTML = `<div class="p-3 text-xs text-rose-500 rounded-xl bg-rose-50 dark:bg-rose-950/30">Failed to load crawl history: ${e.message}</div>`;
            }
        }
    },

    renderCrawlHistory(history) {
        const container = document.getElementById('crawlHistoryContainer');
        if (!container) return;

        if (!history || history.length === 0) {
            container.innerHTML = '<div class="p-6 text-center text-xs text-slate-400 border border-dashed border-slate-200 dark:border-slate-700 rounded-xl">No crawl records available yet. Click "Sync Now" to run a crawl.</div>';
            return;
        }

        // Update summary cards
        const latest = history[0];
        const lastTimeEl = document.getElementById('crawlStatLastTime');
        const lastTriggerEl = document.getElementById('crawlStatLastTrigger');
        const lastFilesEl = document.getElementById('crawlStatLastFiles');

        if (lastTimeEl) lastTimeEl.textContent = latest.timestamp_local || latest.timestamp?.split('T')[0] || '--';
        if (lastTriggerEl) {
            const isAuto = (latest.trigger_type || '').toLowerCase() === 'automatic';
            lastTriggerEl.innerHTML = isAuto
                ? '<span class="inline-flex items-center gap-1 text-blue-600 dark:text-blue-400"><i class="bi bi-clock-fill"></i> Automatic (6-hr)</span>'
                : '<span class="inline-flex items-center gap-1 text-emerald-600 dark:text-emerald-400"><i class="bi bi-hand-index-thumb-fill"></i> Manual Trigger</span>';
        }
        if (lastFilesEl) {
            const added = latest.new_files_added || 0;
            lastFilesEl.innerHTML = added > 0
                ? `<span class="text-emerald-600 dark:text-emerald-400 font-bold">+${added} files (${latest.new_qps_added || 0} QPs, ${latest.new_schemes_added || 0} Schemes)</span>`
                : '<span class="text-slate-400 font-semibold">0 (Up to date)</span>';
        }

        let html = '<div class="rounded-xl border border-slate-200 dark:border-slate-700 divide-y divide-slate-100 dark:divide-slate-700/60 overflow-hidden">';
        history.forEach((rec, idx) => {
            const isAuto = (rec.trigger_type || '').toLowerCase() === 'automatic';
            const added = rec.new_files_added || 0;
            const hasDetails = rec.new_items && rec.new_items.length > 0;

            html += `
                <div class="p-3.5 bg-white dark:bg-slate-800/80 hover:bg-slate-50 dark:hover:bg-slate-700/30 transition flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                    <div class="space-y-1">
                        <div class="flex items-center gap-2">
                            <span class="px-2 py-0.5 rounded-full text-[10px] font-bold ${isAuto ? 'bg-blue-100 dark:bg-blue-900/60 text-blue-700 dark:text-blue-300' : 'bg-emerald-100 dark:bg-emerald-900/60 text-emerald-700 dark:text-emerald-300'}">
                                ${isAuto ? '<i class="bi bi-robot mr-1"></i>Automatic (6-hr)' : '<i class="bi bi-person-fill mr-1"></i>Manual'}
                            </span>
                            <span class="font-bold text-slate-800 dark:text-slate-200">${rec.timestamp_local || rec.timestamp}</span>
                        </div>
                        <div class="text-[11px] text-slate-500 dark:text-slate-400">
                            ${rec.summary || (added > 0 ? `Ingested ${added} new files (${rec.new_qps_added || 0} QPs, ${rec.new_schemes_added || 0} Schemes)` : 'Database was already up to date with MGU')}
                        </div>
                    </div>
                    <div class="flex items-center gap-2 self-start sm:self-center shrink-0">
                        <span class="px-2.5 py-1 rounded-lg text-xs font-bold ${added > 0 ? 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800' : 'bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400'}">
                            ${added > 0 ? `+${added} files` : '0 new'}
                        </span>
                        ${hasDetails ? `
                            <button onclick="App.showCrawlDetailsModal(${idx})" class="px-3 py-1.5 text-xs font-bold rounded-lg bg-indigo-50 dark:bg-indigo-950/40 hover:bg-indigo-100 dark:hover:bg-indigo-900/50 text-indigo-600 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-800 transition flex items-center gap-1.5 shadow-2xs">
                                <i class="bi bi-list-check text-sm"></i> View All Files (${rec.new_items ? rec.new_items.length : (rec.new_files_added || 0)})
                            </button>
                        ` : ''}
                    </div>
                </div>
            `;
        });
        html += '</div>';

        container.innerHTML = html;
    },

    showCrawlDetailsModal(index) {
        const rec = this.crawlHistoryCache[index];
        if (!rec || !rec.new_items) return;

        this.currentCrawlModalRecord = rec;
        this.currentCrawlModalFilter = 'all';

        const modal = document.getElementById('crawlDetailsModal');
        const titleEl = document.getElementById('crawlModalTitle');
        const subtitleEl = document.getElementById('crawlModalSubtitle');
        const searchInput = document.getElementById('crawlModalSearchInput');
        const clearBtn = document.getElementById('crawlModalClearSearch');

        if (!modal) return;

        const isAuto = (rec.trigger_type || '').toLowerCase() === 'automatic';
        if (titleEl) {
            titleEl.innerHTML = `<i class="bi bi-file-earmark-check-fill text-emerald-600 shrink-0"></i> ${isAuto ? 'Automatic Crawl (6-hr)' : 'Manual Crawl'} — All ${rec.new_items.length} Files Added`;
        }
        if (subtitleEl) {
            subtitleEl.textContent = `Completed at ${rec.timestamp_local || rec.timestamp} across ${rec.total_exams_checked || 10} examination sessions`;
        }

        if (searchInput) {
            searchInput.value = '';
        }
        if (clearBtn) {
            clearBtn.classList.add('hidden');
        }

        this.renderCrawlModalFilters();
        this.renderCrawlModalFiles();

        modal.classList.remove('hidden');
    },

    renderCrawlModalFilters() {
        const pillsContainer = document.getElementById('crawlModalFilterPills');
        if (!pillsContainer || !this.currentCrawlModalRecord) return;

        const items = this.currentCrawlModalRecord.new_items || [];
        const totalCount = items.length;
        const qpCount = items.filter(x => (x.file_type || '').toUpperCase() === 'QP').length;
        const schemeCount = items.filter(x => (x.file_type || '').toUpperCase() === 'SCHEME').length;

        // Group by semester
        const semCounts = {};
        items.forEach(x => {
            const s = x.semester || 5;
            semCounts[s] = (semCounts[s] || 0) + 1;
        });

        // Sorted semesters descending: 5, 4, 3, 2, 1
        const sems = Object.keys(semCounts).map(Number).sort((a, b) => b - a);

        let pillsHtml = `
            <button type="button" onclick="App.setCrawlModalFilter('all')" class="crawl-filter-pill px-3 py-1 rounded-lg font-semibold shrink-0 transition text-xs ${this.currentCrawlModalFilter === 'all' ? 'bg-blue-600 text-white shadow-2xs' : 'bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 text-slate-600 dark:text-slate-300'}">
                All (${totalCount})
            </button>
        `;

        if (schemeCount > 0) {
            pillsHtml += `
                <button type="button" onclick="App.setCrawlModalFilter('SCHEME')" class="crawl-filter-pill px-3 py-1 rounded-lg font-semibold shrink-0 transition text-xs ${this.currentCrawlModalFilter === 'SCHEME' ? 'bg-emerald-600 text-white shadow-2xs' : 'bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 text-slate-600 dark:text-slate-300'}">
                    Schemes (${schemeCount})
                </button>
            `;
        }

        if (qpCount > 0) {
            pillsHtml += `
                <button type="button" onclick="App.setCrawlModalFilter('QP')" class="crawl-filter-pill px-3 py-1 rounded-lg font-semibold shrink-0 transition text-xs ${this.currentCrawlModalFilter === 'QP' ? 'bg-indigo-600 text-white shadow-2xs' : 'bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 text-slate-600 dark:text-slate-300'}">
                    Question Papers (${qpCount})
                </button>
            `;
        }

        sems.forEach(s => {
            const count = semCounts[s];
            const filterKey = `sem-${s}`;
            pillsHtml += `
                <button type="button" onclick="App.setCrawlModalFilter('${filterKey}')" class="crawl-filter-pill px-2.5 py-1 rounded-lg font-semibold shrink-0 transition text-xs ${this.currentCrawlModalFilter === filterKey ? 'bg-purple-600 text-white shadow-2xs' : 'bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 text-slate-600 dark:text-slate-300'}">
                    Sem ${s} (${count})
                </button>
            `;
        });

        pillsContainer.innerHTML = pillsHtml;
    },

    setCrawlModalFilter(filterKey) {
        this.currentCrawlModalFilter = filterKey;
        this.renderCrawlModalFilters();
        this.renderCrawlModalFiles();
    },

    clearCrawlModalSearch() {
        const input = document.getElementById('crawlModalSearchInput');
        if (input) {
            input.value = '';
            input.focus();
        }
        const clearBtn = document.getElementById('crawlModalClearSearch');
        if (clearBtn) clearBtn.classList.add('hidden');
        this.renderCrawlModalFiles();
    },

    filterCrawlModalFiles() {
        const input = document.getElementById('crawlModalSearchInput');
        const clearBtn = document.getElementById('crawlModalClearSearch');
        if (input && clearBtn) {
            if (input.value.trim().length > 0) {
                clearBtn.classList.remove('hidden');
            } else {
                clearBtn.classList.add('hidden');
            }
        }
        this.renderCrawlModalFiles();
    },

    renderCrawlModalFiles() {
        const listEl = document.getElementById('crawlModalFilesList');
        const counterEl = document.getElementById('crawlModalFileCounter');
        const footerSummaryEl = document.getElementById('crawlModalFooterSummary');
        const searchInput = document.getElementById('crawlModalSearchInput');

        if (!listEl || !this.currentCrawlModalRecord) return;

        const allItems = this.currentCrawlModalRecord.new_items || [];
        const query = (searchInput?.value || '').trim().toLowerCase();
        const activeFilter = this.currentCrawlModalFilter || 'all';

        const filtered = allItems.filter(item => {
            // Apply category / semester filter
            if (activeFilter === 'QP' && (item.file_type || '').toUpperCase() !== 'QP') return false;
            if (activeFilter === 'SCHEME' && (item.file_type || '').toUpperCase() !== 'SCHEME') return false;
            if (activeFilter.startsWith('sem-')) {
                const targetSem = parseInt(activeFilter.replace('sem-', ''), 10);
                if (parseInt(item.semester, 10) !== targetSem) return false;
            }

            // Apply search query
            if (query) {
                const text = `${item.course_code || ''} ${item.title || ''} ${item.qp_code || ''} ${item.filename || ''} ${item.label || ''} Sem ${item.semester || ''}`.toLowerCase();
                const terms = query.split(/\\s+/).filter(Boolean);
                return terms.every(t => text.includes(t));
            }

            return true;
        });

        // Update counter & summary
        if (counterEl) {
            counterEl.textContent = `Showing ${filtered.length} of ${allItems.length} files`;
        }
        if (footerSummaryEl) {
            footerSummaryEl.textContent = `Total ${allItems.length} files added in this crawl session`;
        }

        if (filtered.length === 0) {
            listEl.innerHTML = `
                <div class="py-12 text-center text-slate-400 dark:text-slate-500">
                    <i class="bi bi-search text-2xl mb-2 block"></i>
                    <p class="font-semibold text-xs">No files matching your search or filter.</p>
                    <p class="text-[11px] mt-1 text-slate-400">Try clearing the search or switching the filter tab.</p>
                </div>
            `;
            return;
        }

        let html = '';
        filtered.forEach((item) => {
            const isQp = (item.file_type || '').toUpperCase() === 'QP';
            const pdfUrl = item.url || (item.filename ? `https://cdn.jsdelivr.net/gh/sinan-newman/mgu-qp-storage@main/pdf/${item.filename}` : '#');
            const safeTitle = (item.title || item.course_code || 'Question Paper').replace(/'/g, "\\'");
            const safeCode = (item.course_code || '').replace(/'/g, "\\'");

            html += `
                <div class="p-3 bg-slate-50 dark:bg-slate-700/50 hover:bg-slate-100/70 dark:hover:bg-slate-700/80 rounded-xl border border-slate-200 dark:border-slate-600/70 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs transition">
                    <div class="space-y-1 min-w-0 flex-1">
                        <div class="flex items-center gap-1.5 flex-wrap">
                            <span class="px-2 py-0.5 rounded font-mono font-bold text-[10px] bg-slate-200 dark:bg-slate-600 text-slate-700 dark:text-slate-200">
                                Sem ${item.semester || 5}
                            </span>
                            <span class="px-2 py-0.5 rounded font-mono font-bold text-[10px] bg-blue-100 dark:bg-blue-900/60 text-blue-700 dark:text-blue-300">
                                ${item.course_code || 'N/A'}
                            </span>
                            ${item.qp_code ? `<span class="px-2 py-0.5 rounded font-mono text-[10px] bg-slate-200/80 dark:bg-slate-600/80 text-slate-700 dark:text-slate-300">QP: ${item.qp_code}</span>` : ''}
                            <span class="px-2 py-0.5 rounded-full text-[10px] font-bold ${isQp ? 'bg-indigo-100 dark:bg-indigo-900/60 text-indigo-700 dark:text-indigo-300' : 'bg-emerald-100 dark:bg-emerald-900/60 text-emerald-700 dark:text-emerald-300'}">
                                ${item.file_type || 'PDF'}
                            </span>
                            ${item.exam_id ? `<span class="text-[10px] text-slate-400 font-mono">Exam #${item.exam_id}</span>` : ''}
                        </div>
                        <div class="font-semibold text-slate-800 dark:text-slate-100 text-xs sm:text-[13px] leading-tight">
                            ${item.title || item.course_code || 'Question Paper'}
                        </div>
                        <div class="text-[10px] text-slate-400 font-mono truncate">
                            <i class="bi bi-file-earmark-pdf mr-0.5"></i> ${item.filename || ''}
                        </div>
                    </div>
                    <div class="shrink-0 flex items-center gap-2 self-start sm:self-center">
                        <button type="button" onclick="App.previewDirect(this, '${pdfUrl}', '${safeTitle}', '${safeCode}')" class="px-3 py-1.5 text-xs font-semibold rounded-lg bg-blue-600 hover:bg-blue-500 text-white flex items-center gap-1.5 shadow-2xs transition">
                            <i class="bi bi-eye text-[11px]"></i> Preview
                        </button>
                        <a href="${pdfUrl}" target="_blank" rel="noopener noreferrer" class="p-1.5 text-xs rounded-lg bg-slate-200/80 dark:bg-slate-600 hover:bg-slate-300 dark:hover:bg-slate-500 text-slate-700 dark:text-slate-200 transition" title="Open PDF in new tab">
                            <i class="bi bi-box-arrow-up-right"></i>
                        </a>
                    </div>
                </div>
            `;
        });

        listEl.innerHTML = html;
    },

    closeCrawlDetailsModal() {
        const modal = document.getElementById('crawlDetailsModal');
        if (modal) modal.classList.add('hidden');
    },


    updateStatsUI() {
        const totalPapersEl = document.getElementById('statTotalPapers');
        const totalSchemesEl = document.getElementById('statTotalSchemes');
        const totalDeptsEl = document.getElementById('statTotalDepartments');
        const lastSyncEl = document.getElementById('statLastSync');

        const totalQPs = this.papers.filter(p => p.has_qp).length;
        const totalSchemes = this.papers.filter(p => p.has_scheme).length;
        const activeDepts = this.getActiveDepartments();

        if (totalPapersEl) totalPapersEl.textContent = `${totalQPs.toLocaleString()}+`;
        if (totalSchemesEl) totalSchemesEl.textContent = `${totalSchemes.toLocaleString()}+`;
        if (totalDeptsEl) totalDeptsEl.textContent = `${activeDepts.length}`;
        if (lastSyncEl) lastSyncEl.textContent = '2024 Admission';
        const totalModels = (this.modelCatalog && this.modelCatalog.length > 0) ? this.modelCatalog.length : 1649;
        const statTotalModelEl = document.getElementById('statTotalModelPapers');
        if (statTotalModelEl) statTotalModelEl.textContent = `${totalModels.toLocaleString()}+`;
    },

    bindEvents() {
        // 1. Search Input in Filter Bar (All Question Papers Tab)
        const searchInput = document.getElementById('searchInput');
        const clearSearchBtn = document.getElementById('clearSearchBtn');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.state.searchQuery = e.target.value.trim().toLowerCase();
                this.state.currentPage = 1;
                if (clearSearchBtn) {
                    clearSearchBtn.classList.toggle('hidden', !this.state.searchQuery);
                }
                this.applyFilters();
            });

            // Focus on '/' key
            document.addEventListener('keydown', (e) => {
                if (e.key === '/' && document.activeElement !== searchInput && document.activeElement.tagName !== 'INPUT') {
                    e.preventDefault();
                    if (this.state.activeTab !== 'papers') {
                        this.switchTab('papers');
                    }
                    setTimeout(() => searchInput.focus(), 50);
                }
            });
        }

        if (clearSearchBtn) {
            clearSearchBtn.addEventListener('click', () => {
                if (searchInput) searchInput.value = '';
                this.state.searchQuery = '';
                clearSearchBtn.classList.add('hidden');
                this.state.currentPage = 1;
                this.applyFilters();
            });
        }

        // 2. Department Cards Quick Search Input with Live Autocomplete Dropdown
        const deptSearchInput = document.getElementById('deptSearchInput');
        const clearDeptSearchBtn = document.getElementById('clearDeptSearchBtn');
        if (deptSearchInput) {
            deptSearchInput.addEventListener('input', (e) => {
                this.handleLiveSearch(e.target.value.trim());
            });

            deptSearchInput.addEventListener('focus', (e) => {
                if (e.target.value.trim().length >= 1) {
                    this.handleLiveSearch(e.target.value.trim());
                }
            });
        }

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            const dropdown = document.getElementById('deptSearchDropdown');
            const searchInput = document.getElementById('deptSearchInput');
            if (dropdown && !dropdown.contains(e.target) && e.target !== searchInput) {
                dropdown.classList.add('hidden');
            }
        });

        if (clearDeptSearchBtn) {
            clearDeptSearchBtn.addEventListener('click', () => {
                this.clearDeptSearch();
            });
        }

        // 3. In-Department Paper Search Input
        const deptPaperSearch = document.getElementById('deptPaperSearchInput');
        if (deptPaperSearch) {
            deptPaperSearch.addEventListener('input', (e) => {
                this.deptState.searchQuery = e.target.value.trim().toLowerCase();
                this.renderDeptSemesterPapers();
            });
        }

        // 4. Semester Buttons (Sem 1 to 8)
        document.querySelectorAll('.sem-filter-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const sem = btn.dataset.sem;
                this.setSemester(sem);
            });
        });

        // 5. Course Type Buttons
        document.querySelectorAll('.ctype-filter-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const ctype = btn.dataset.ctype;
                this.setCourseType(ctype);
            });
        });

        // 6. Department Select Dropdown
        const deptSelect = document.getElementById('deptSelect');
        if (deptSelect) {
            deptSelect.addEventListener('change', (e) => {
                this.setDepartment(e.target.value);
            });
        }

        // 7. Navigation Tabs (Departments / Papers / Bookmarks)
        document.querySelectorAll('.nav-tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.switchTab(btn.dataset.tab, true);
            });
        });

        // 8. Files only toggle
        const filesOnlyCheckbox = document.getElementById('filesOnlyCheckbox');
        if (filesOnlyCheckbox) {
            filesOnlyCheckbox.addEventListener('change', (e) => {
                this.state.onlyWithFiles = e.target.checked;
                this.state.currentPage = 1;
                this.applyFilters();
            });
        }

        // 9. View Mode Toggles
        const gridViewBtn = document.getElementById('gridViewBtn');
        const tableViewBtn = document.getElementById('tableViewBtn');
        if (gridViewBtn && tableViewBtn) {
            gridViewBtn.addEventListener('click', () => {
                this.state.viewMode = 'grid';
                gridViewBtn.className = 'p-1 rounded text-blue-600 dark:text-blue-400 bg-white dark:bg-slate-800 shadow-2xs transition';
                tableViewBtn.className = 'p-1 rounded text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition';
                this.renderPapers();
            });
            tableViewBtn.addEventListener('click', () => {
                this.state.viewMode = 'table';
                tableViewBtn.className = 'p-1 rounded text-blue-600 dark:text-blue-400 bg-white dark:bg-slate-800 shadow-2xs transition';
                gridViewBtn.className = 'p-1 rounded text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition';
                this.renderPapers();
            });
        }

        // 10. Theme Toggle Button
        const themeBtn = document.getElementById('themeToggleBtn');
        if (themeBtn) {
            themeBtn.addEventListener('click', () => this.toggleTheme());
        }

        // 11. Admin Smart PDF Dropzone
        this.bindDropzoneEvents();
    },

    handleLiveSearch(query) {
        const dropdown = document.getElementById('deptSearchDropdown');
        const clearBtn = document.getElementById('clearDeptSearchBtn');
        const deptSearchIcon = document.getElementById('deptSearchIcon');
        if (deptSearchIcon) {
            deptSearchIcon.classList.remove('bi-search');
            deptSearchIcon.classList.add('bi-arrow-repeat', 'spinner-icon');
            setTimeout(() => {
                deptSearchIcon.classList.remove('bi-arrow-repeat', 'spinner-icon');
                deptSearchIcon.classList.add('bi-search');
            }, 250);
        }
        if (!dropdown) return;

        this.deptState.deptSearchQuery = query.toLowerCase();
        if (clearBtn) clearBtn.classList.toggle('hidden', !query);

        // Also filter the department cards below in real-time
        this.renderDepartmentsList();

        if (!query || query.length < 1) {
            dropdown.classList.add('hidden');
            dropdown.innerHTML = '';
            return;
        }

        const q = query.toLowerCase();

        // 1. Matched Departments
        const matchedDepts = this.departments.filter(d => 
            d.name.toLowerCase().includes(q) || 
            d.code.toLowerCase().includes(q)
        ).slice(0, 5);

        // 2. Matched Minors
        const matchedMinors = [];
        this.departments.forEach(d => {
            (d.minors || []).forEach(m => {
                if (m.name.toLowerCase().includes(q) || m.code.toLowerCase().includes(q)) {
                    matchedMinors.push({
                        ...m,
                        parent_dept_code: d.code,
                        parent_dept_name: d.name
                    });
                }
            });
        });

        // 3. Matched Courses / Question Papers
        const matchedPapers = [];
        const seenKeys = new Set();
        const tokens = q.split(/\s+/).filter(Boolean);
        let totalPaperMatches = 0;

        for (const p of this.papers) {
            if (this.matchPaper(p, tokens, q)) {
                totalPaperMatches++;
                const uniqueKey = `${p.id || ''}_${p.course_code || ''}_${p.exam_name || ''}`;
                if (!seenKeys.has(uniqueKey)) {
                    seenKeys.add(uniqueKey);
                    if (matchedPapers.length < 12) {
                        matchedPapers.push(p);
                    }
                }
            }
        }

        if (matchedDepts.length === 0 && matchedMinors.length === 0 && matchedPapers.length === 0) {
            dropdown.innerHTML = `
                <div class="p-4 text-center text-slate-400 text-xs">
                    No departments, minors, or courses match "<span class="font-semibold text-slate-600 dark:text-slate-300">${query}</span>".
                </div>
            `;
            dropdown.classList.remove('hidden');
            return;
        }

        let html = '';

        // Departments Group
        if (matchedDepts.length > 0) {
            html += `
                <div class="px-3.5 py-1.5 bg-slate-50 dark:bg-slate-700/60 text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
                    <i class="bi bi-mortarboard text-blue-600"></i> Departments (${matchedDepts.length})
                </div>
                ${matchedDepts.map(d => `
                    <div onclick="App.openDepartmentView('${d.code}'); App.closeSearchDropdown();" class="p-3 hover:bg-blue-50/70 dark:hover:bg-slate-700/70 cursor-pointer flex items-center justify-between gap-3 transition">
                        <div class="flex items-center gap-2.5 min-w-0">
                            <div class="w-7 h-7 rounded-lg bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 flex items-center justify-center text-xs shrink-0 font-bold">
                                <i class="bi ${d.icon || 'bi-mortarboard'}"></i>
                            </div>
                            <div class="truncate">
                                <span class="font-semibold text-slate-900 dark:text-slate-100">${d.name}</span>
                            </div>
                        </div>
                        <span class="font-mono text-[11px] font-bold px-2 py-0.5 rounded bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-900/40 shrink-0">
                            ${d.code}
                        </span>
                    </div>
                `).join('')}
            `;
        }

        // Minors Group
        if (matchedMinors.length > 0) {
            html += `
                <div class="px-3.5 py-1.5 bg-pink-50/50 dark:bg-pink-950/30 text-[10px] font-bold uppercase tracking-wider text-pink-600 dark:text-pink-400 flex items-center gap-1.5">
                    <i class="bi bi-bookmark-star-fill text-pink-500"></i> Minors (${matchedMinors.length})
                </div>
                ${matchedMinors.slice(0, 5).map(m => `
                    <div onclick="App.openDepartmentView('${m.parent_dept_code}'); App.closeSearchDropdown();" class="p-3 hover:bg-pink-50/70 dark:hover:bg-slate-700/70 cursor-pointer flex items-center justify-between gap-3 transition">
                        <div class="flex items-center gap-2.5 min-w-0">
                            <span class="w-2 h-2 rounded-full bg-pink-500 shrink-0"></span>
                            <div class="truncate">
                                <span class="font-semibold text-slate-900 dark:text-slate-100">${m.name}</span>
                                <span class="text-[11px] text-slate-400 ml-1.5">• under ${m.parent_dept_name}</span>
                            </div>
                        </div>
                        <span class="font-mono text-[11px] font-bold px-2 py-0.5 rounded-full bg-pink-100 dark:bg-pink-900/60 text-pink-800 dark:text-pink-200 shrink-0">
                            ${m.code}
                        </span>
                    </div>
                `).join('')}
            `;
        }

        // Courses / Papers Group
        if (matchedPapers.length > 0) {
            html += `
                <div class="px-3.5 py-1.5 bg-slate-50 dark:bg-slate-700/60 text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center justify-between">
                    <span class="flex items-center gap-1.5">
                        <i class="bi bi-file-earmark-text text-indigo-600"></i> Courses & Papers (${totalPaperMatches})
                    </span>
                    ${totalPaperMatches > matchedPapers.length ? `
                        <span class="text-[10px] text-slate-400 font-normal">Showing top ${matchedPapers.length} of ${totalPaperMatches}</span>
                    ` : ''}
                </div>
                ${matchedPapers.map(p => `
                    <div class="p-3 hover:bg-slate-50 dark:hover:bg-slate-700/70 flex items-center justify-between gap-3 transition">
                        <div class="min-w-0 flex-1">
                            <div class="flex items-center gap-1.5 flex-wrap">
                                <span class="font-mono font-bold text-xs text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/40 px-1.5 py-0.5 rounded">
                                    ${p.course_code || 'CODE N/A'}
                                </span>
                                <span class="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200">
                                    ${this.extractMonthYear(p.exam_name)}
                                </span>
                                ${p.is_minor ? `
                                    <span class="text-[10px] font-semibold px-1.5 py-0.5 rounded badge-minor">
                                        ${p.minor_name || p.dept_code} (Minor)
                                    </span>
                                ` : ''}
                            </div>
                            <div class="font-medium text-slate-900 dark:text-slate-100 truncate mt-0.5" title="${p.title}">
                                ${p.title}
                            </div>
                            <div class="text-[11px] text-slate-400 truncate">
                                ${p.parent_dept_name || p.dept_name || ''}
                            </div>
                        </div>

                        <div class="shrink-0 flex items-center gap-1.5">
                            ${p.has_qp ? `
                                <button onclick="App.previewPaper(this, ${JSON.stringify(p).replace(/"/g, '&quot;')}, 'QP'); App.closeSearchDropdown();" class="px-2.5 py-1 text-xs font-semibold rounded-lg bg-blue-600 hover:bg-blue-500 text-white shadow-xs flex items-center gap-1 transition" title="Preview Question Paper">
                                    <i class="bi bi-eye"></i> QP
                                </button>
                            ` : ''}
                            ${p.has_scheme ? `
                                <button onclick="App.previewPaper(this, ${JSON.stringify(p).replace(/"/g, '&quot;')}, 'SCHEME'); App.closeSearchDropdown();" class="px-2.5 py-1 text-xs font-semibold rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white shadow-xs flex items-center gap-1 transition" title="Preview Evaluation Scheme">
                                    <i class="bi bi-journal-check"></i> Scheme
                                </button>
                            ` : ''}
                            <button onclick="App.openDepartmentView('${p.parent_dept || p.dept_code}', ${p.semester}); App.closeSearchDropdown();" class="px-2 py-1 text-xs font-semibold rounded-lg bg-slate-100 hover:bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-200 transition" title="Go to Department">
                                <i class="bi bi-arrow-right"></i>
                            </button>
                        </div>
                    </div>
                `).join('')}
                ${totalPaperMatches > matchedPapers.length ? `
                    <div onclick="App.switchToAllPapersWithQuery('${q.replace(/'/g, "\\'")}'); App.closeSearchDropdown();" class="p-2.5 bg-slate-50 dark:bg-slate-700/50 hover:bg-blue-50 dark:hover:bg-slate-700 cursor-pointer text-center text-xs font-semibold text-blue-600 dark:text-blue-400 transition border-t border-slate-100 dark:border-slate-700">
                        View all ${totalPaperMatches} matching papers in All Question Papers →
                    </div>
                ` : ''}
            `;
        }

        dropdown.innerHTML = html;
        dropdown.classList.remove('hidden');
    },

    closeSearchDropdown() {
        const dropdown = document.getElementById('deptSearchDropdown');
        if (dropdown) dropdown.classList.add('hidden');
    },

    clearDeptSearch() {
        const input = document.getElementById('deptSearchInput');
        const btn = document.getElementById('clearDeptSearchBtn');
        const dropdown = document.getElementById('deptSearchDropdown');
        if (input) input.value = '';
        if (btn) btn.classList.add('hidden');
        if (dropdown) {
            dropdown.classList.add('hidden');
            dropdown.innerHTML = '';
        }
        this.deptState.deptSearchQuery = '';
        this.renderDepartmentsList();
    },

    switchToAllPapersWithQuery(q) {
        this.switchTab('papers');
        const searchInput = document.getElementById('searchQuery');
        if (searchInput) {
            searchInput.value = q;
            this.state.searchQuery = q;
            this.applyFilters();
        }
        window.scrollTo({ top: 0, behavior: 'smooth' });
    },

    clearDeptPaperSearch() {
        const input = document.getElementById('deptPaperSearchInput');
        if (input) input.value = '';
        this.deptState.searchQuery = '';
        this.renderDeptSemesterPapers();
    },

    handleRouting(rawHash) {
        const hash = (rawHash || window.location.hash || '').trim();
        this.trackPortalVisit(hash || '#/departments');

        // 0. AI Notes route: #/ai-notes or #/ai-notes/COURSE_CODE
        const aiMatch = hash.match(/^#\/?ai-notes(?:\/([A-Za-z0-9_\-\s%]+))?\/?$/i);
        if (aiMatch) {
            const rawCode = aiMatch[1] ? decodeURIComponent(aiMatch[1].trim()) : null;
            this.switchTab('ai-notes', false);
            if (rawCode && window.AiNotesStudio) {
                window.AiNotesStudio.selectCourse(rawCode);
            }
            return;
        }

        // 1. Department route: #/department/CODE or #/department/CODE/SEM or #dept=CODE
        const deptMatch = hash.match(/^#\/?(?:dept=|department\/)([A-Za-z0-9_]+)\/?(?:[\/?&](?:sem[\/=])?([0-9]+|ALL))?\/?$/i);
        if (deptMatch) {
            const deptCode = deptMatch[1].toUpperCase();
            const semParam = deptMatch[2] ? (deptMatch[2].toUpperCase() === 'ALL' ? 'ALL' : parseInt(deptMatch[2], 10)) : null;
            if (this.deptState.activeDept && this.deptState.activeDept.code.toUpperCase() === deptCode && (this.deptState.selectedSemester === semParam) && !document.getElementById('deptDetailContainer')?.classList.contains('hidden')) {
                return;
            }
            this.openDepartmentView(deptCode, semParam, false);
            return;
        }

        // 2. Papers route: #/papers or #/all-papers or #papers
        if (hash === '#/papers' || hash === '#/all-papers' || hash === '#papers') {
            if (this.state.activeTab !== 'papers' || !document.getElementById('deptDetailContainer')?.classList.contains('hidden')) {
                this.switchTab('papers', false);
            }
            return;
        }

        // 3. Bookmarks / Saved route: #/bookmarks or #/saved or #saved
        if (hash === '#/bookmarks' || hash === '#/saved' || hash === '#saved') {
            if (this.state.activeTab !== 'bookmarks' || !document.getElementById('deptDetailContainer')?.classList.contains('hidden')) {
                this.switchTab('bookmarks', false);
            }
            return;
        }

        // 4. Admin route: #admin or #/admin
        if (hash.toLowerCase() === '#admin' || hash.toLowerCase() === '#/admin') {
            this.openAdminPage(false);
            return;
        }

        // 5. Explicit Departments route: #/departments or #departments
        if (hash === '#/departments' || hash === '#departments') {
            if (this.state.activeTab !== 'departments' || !document.getElementById('deptDetailContainer')?.classList.contains('hidden')) {
                this.showDepartmentsList(false);
            }
            return;
        }

        // 6. Default fallback (e.g. empty hash or #/ or unrecognized)
        if (this.state.activeTab !== 'departments' || !document.getElementById('deptDetailContainer')?.classList.contains('hidden')) {
            this.showDepartmentsList(false);
        }
    },

    showDepartmentsList(updateHash = true) {
        this.switchTab('departments', updateHash);
        if (this.lastDeptListScrollY !== undefined && this.lastDeptListScrollY > 0) {
            window.scrollTo({ top: this.lastDeptListScrollY, behavior: 'instant' });
        } else {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
    },

    switchTab(tab, updateHash = true) {
        this.state.activeTab = tab;

        // Ensure hero and main nav tabs are visible on top-level tabs
        document.getElementById('heroSection')?.classList.remove('hidden');
        document.getElementById('mainNavTabsContainer')?.classList.remove('hidden');
        document.getElementById('deptDetailContainer')?.classList.add('hidden');
        document.getElementById('adminPageSection')?.classList.add('hidden');

        // Update nav button active classes
        document.querySelectorAll('.nav-tab-btn').forEach(btn => {
            const isActive = btn.dataset.tab === tab;
            if (isActive) {
                btn.className = 'nav-tab-btn px-4 py-2 font-semibold text-xs sm:text-sm rounded-xl bg-blue-600 text-white shadow-sm flex items-center gap-2 transition shrink-0 min-h-[38px]';
            } else {
                btn.className = 'nav-tab-btn px-4 py-2 font-medium text-xs sm:text-sm rounded-xl text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center gap-2 transition shrink-0 min-h-[38px]';
            }
        });

        // Hide/Show containers
        const papersSection = document.getElementById('papersSection');
        const departmentsSection = document.getElementById('departmentsSection');
        const filterControls = document.getElementById('filterControlsSection');
        const aiNotesSection = document.getElementById('aiNotesSection');

        if (tab === 'departments') {
            document.title = 'Mahatma Gandhi University • FYUGP Question Papers and Schemes';
            if (updateHash && window.location.hash !== '#/departments' && window.location.hash !== '') {
                this.currentRoute = '#/departments';
                window.location.hash = '#/departments';
            }
            if (papersSection) papersSection.classList.add('hidden');
            if (departmentsSection) departmentsSection.classList.remove('hidden');
            if (filterControls) filterControls.classList.add('hidden');
            if (aiNotesSection) aiNotesSection.classList.add('hidden');
            document.getElementById('deptListContainer')?.classList.remove('hidden');
            this.deptState.activeDept = null;
        } else if (tab === 'papers') {
            document.title = 'All Question Papers & Schemes - MGU FYUGP';
            if (updateHash && window.location.hash !== '#/papers') {
                this.currentRoute = '#/papers';
                window.location.hash = '#/papers';
            }
            if (papersSection) papersSection.classList.remove('hidden');
            if (departmentsSection) departmentsSection.classList.add('hidden');
            if (filterControls) filterControls.classList.remove('hidden');
            if (aiNotesSection) aiNotesSection.classList.add('hidden');
            this.state.currentPage = 1;
            this.applyFilters();
        } else if (tab === 'bookmarks') {
            document.title = 'Saved Question Papers - MGU FYUGP';
            if (updateHash && window.location.hash !== '#/bookmarks' && window.location.hash !== '#/saved') {
                this.currentRoute = '#/bookmarks';
                window.location.hash = '#/bookmarks';
            }
            if (papersSection) papersSection.classList.remove('hidden');
            if (departmentsSection) departmentsSection.classList.add('hidden');
            if (filterControls) filterControls.classList.remove('hidden');
            if (aiNotesSection) aiNotesSection.classList.add('hidden');
            this.state.currentPage = 1;
            this.applyFilters();
        } else if (tab === 'ai-notes') {
            document.title = 'AI Notes Studio • MGU FYUGP Question Papers & Revision Notes';
            if (updateHash && !window.location.hash.startsWith('#/ai-notes')) {
                this.currentRoute = '#/ai-notes';
                window.location.hash = '#/ai-notes';
            }
            if (papersSection) papersSection.classList.add('hidden');
            if (departmentsSection) departmentsSection.classList.add('hidden');
            if (filterControls) filterControls.classList.add('hidden');
            if (aiNotesSection) {
                aiNotesSection.classList.remove('hidden');
                if (window.AiNotesStudio) {
                    window.AiNotesStudio.renderSection();
                    if (!window.AiNotesStudio.state.activeCourse && window.AiNotesStudio.state.coursesList.length > 0) {
                        window.AiNotesStudio.selectCourse(window.AiNotesStudio.state.coursesList[0].course_code);
                    }
                }
            }
        }
    },

    openAiNotesForCourse(courseCode, courseTitle) {
        this.switchTab('ai-notes', false);
        const code = (courseCode || courseTitle || '').trim();
        if (code) {
            window.location.hash = `#/ai-notes/${encodeURIComponent(code)}`;
        } else {
            window.location.hash = '#/ai-notes';
        }
        if (window.AiNotesStudio) {
            window.AiNotesStudio.renderSection();
            if (code) {
                window.AiNotesStudio.selectCourse(code);
            }
        }
        window.scrollTo({ top: 0, behavior: 'smooth' });
    },

    setSemester(sem) {
        this.state.selectedSemester = sem;
        this.state.currentPage = 1;

        document.querySelectorAll('.sem-filter-btn').forEach(btn => {
            const isActive = btn.dataset.sem === sem;
            if (isActive) {
                btn.className = 'sem-filter-btn px-3 py-1 text-xs font-semibold rounded-lg bg-blue-600 text-white shadow-xs transition shrink-0';
            } else {
                btn.className = 'sem-filter-btn px-2.5 py-1 text-xs font-medium rounded-lg text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition shrink-0';
            }
        });

        this.applyFilters();
    },

    setCourseType(ctype) {
        this.state.selectedCourseType = ctype;
        this.state.currentPage = 1;

        document.querySelectorAll('.ctype-filter-btn').forEach(btn => {
            const isActive = btn.dataset.ctype === ctype;
            if (isActive) {
                btn.className = 'ctype-filter-btn px-3 py-1 text-xs font-semibold rounded-lg bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-xs transition shrink-0';
            } else {
                btn.className = 'ctype-filter-btn px-2.5 py-1 text-xs font-medium rounded-lg bg-slate-100/80 dark:bg-slate-800/80 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white border border-slate-200/60 dark:border-slate-700/50 transition shrink-0';
            }
        });

        this.applyFilters();
    },

    setQuickSearch(term) {
        const input = document.getElementById('searchInput');
        if (input) {
            input.value = term;
            this.state.searchQuery = term;
            const clearBtn = document.getElementById('clearSearchBtn');
            if (clearBtn) clearBtn.classList.remove('hidden');
            this.state.currentPage = 1;
            this.applyFilters();
        }
    },

    clearSearchQuery() {
        const input = document.getElementById('searchInput');
        if (input) input.value = '';
        const clearBtn = document.getElementById('clearSearchBtn');
        if (clearBtn) clearBtn.classList.add('hidden');
        this.state.searchQuery = '';
        this.state.currentPage = 1;
        this.applyFilters();
    },

    renderActiveFilterChips() {
        const tray = document.getElementById('activeFiltersTray');
        const container = document.getElementById('activeFilterChipsContainer');
        const countEl = document.getElementById('filterActiveCount');
        
        if (countEl) {
            const count = this.groupedCourses ? this.groupedCourses.length : (this.filteredPapers ? this.filteredPapers.length : 0);
            countEl.textContent = `${count.toLocaleString()} Courses`;
        }

        if (!tray || !container) return;

        const chips = [];

        if (this.state.searchQuery) {
            chips.push(`
                <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-xl text-xs font-semibold bg-blue-50 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300 border border-blue-200 dark:border-blue-900/50 shadow-2xs">
                    <i class="bi bi-search text-[10px]"></i> "${this.state.searchQuery}"
                    <button type="button" onclick="App.clearSearchQuery()" class="hover:text-blue-900 dark:hover:text-white ml-0.5 p-0.5 rounded hover:bg-blue-200/60 transition"><i class="bi bi-x"></i></button>
                </span>
            `);
        }

        if (this.state.selectedSemester !== 'ALL') {
            chips.push(`
                <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-xl text-xs font-semibold bg-indigo-50 text-indigo-700 dark:bg-indigo-950/60 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-900/50 shadow-2xs">
                    <i class="bi bi-calendar3 text-[10px]"></i> Sem ${this.state.selectedSemester}
                    <button type="button" onclick="App.setSemester('ALL')" class="hover:text-indigo-900 dark:hover:text-white ml-0.5 p-0.5 rounded hover:bg-indigo-200/60 transition"><i class="bi bi-x"></i></button>
                </span>
            `);
        }

        if (this.state.selectedCourseType !== 'ALL') {
            const label = this.state.selectedCourseType === 'MIN' ? 'Minor Only' : this.state.selectedCourseType;
            chips.push(`
                <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-xl text-xs font-semibold bg-purple-50 text-purple-700 dark:bg-purple-950/60 dark:text-purple-300 border border-purple-200 dark:border-purple-900/50 shadow-2xs">
                    <i class="bi bi-tag text-[10px]"></i> ${label}
                    <button type="button" onclick="App.setCourseType('ALL')" class="hover:text-purple-900 dark:hover:text-white ml-0.5 p-0.5 rounded hover:bg-purple-200/60 transition"><i class="bi bi-x"></i></button>
                </span>
            `);
        }

        if (this.state.selectedDept !== 'ALL') {
            const deptObj = this.departments.find(d => d.code === this.state.selectedDept);
            const dName = deptObj ? deptObj.name : this.state.selectedDept;
            chips.push(`
                <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-xl text-xs font-semibold bg-teal-50 text-teal-700 dark:bg-teal-950/60 dark:text-teal-300 border border-teal-200 dark:border-teal-900/50 shadow-2xs">
                    <i class="bi bi-mortarboard text-[10px]"></i> ${dName}
                    <button type="button" onclick="App.setDepartment('ALL')" class="hover:text-teal-900 dark:hover:text-white ml-0.5 p-0.5 rounded hover:bg-teal-200/60 transition"><i class="bi bi-x"></i></button>
                </span>
            `);
        }

        if (chips.length > 0) {
            container.innerHTML = chips.join('');
            tray.classList.remove('hidden');
        } else {
            container.innerHTML = '';
            tray.classList.add('hidden');
        }
    },

    setDepartment(deptCode) {
        this.state.selectedDept = deptCode;
        this.state.currentPage = 1;

        // Sync dropdown
        const deptSelect = document.getElementById('deptSelect');
        if (deptSelect && deptSelect.value !== deptCode) {
            deptSelect.value = deptCode;
        }

        this.applyFilters();
    },

    /**
     * Enhanced multi-term tokenized search matching function
     */
    matchPaper(p, tokens, rawQuery) {
        if (!tokens.length) return true;

        const pCodeRaw = (p.course_code || '').toLowerCase();
        const pCodeNorm = pCodeRaw.replace(/[^a-z0-9]/g, '');
        const pQp = (p.qp_code || '').toLowerCase();
        const pTitle = (p.title || '').toLowerCase();
        const pRawHeader = (p.raw_header || '').toLowerCase();
        const pDept = (p.dept_name || '').toLowerCase();
        const pParentDept = (p.parent_dept_name || '').toLowerCase();
        const pDeptCode = (p.dept_code || '').toLowerCase();
        const pParentDeptCode = (p.parent_dept || '').toLowerCase();
        const pType = (p.course_type || '').toLowerCase();
        const pTypeName = (p.course_type_name || '').toLowerCase();
        const pExam = (p.exam_name || '').toLowerCase();
        const pSemStr = `sem ${p.semester} sem${p.semester} semester ${p.semester} s${p.semester}`;

        const combined = `${pCodeRaw} ${pCodeNorm} ${pQp} ${pTitle} ${pRawHeader} ${pDept} ${pParentDept} ${pDeptCode} ${pParentDeptCode} ${pType} ${pTypeName} ${pExam} ${pSemStr}`;

        // Every token must match
        for (const token of tokens) {
            const normToken = token.replace(/[^a-z0-9]/g, '');
            
            // 1. Direct match in combined string
            if (combined.includes(token)) continue;
            
            // 2. Normalized course code match (strips spaces/dashes)
            if (normToken && pCodeNorm.includes(normToken)) continue;

            // 3. Department & keyword alias lookup
            const aliasList = App.ALIASES[token] || (normToken ? App.ALIASES[normToken] : null);
            if (aliasList) {
                const matchedAlias = aliasList.some(alias => combined.includes(alias));
                if (matchedAlias) continue;
            }

            // If token didn't match anything, paper is excluded
            return false;
        }

        return true;
    },

    applyFilters() {
        const searchIcon = document.getElementById('searchIcon');
        if (searchIcon) {
            searchIcon.classList.remove('bi-search');
            searchIcon.classList.add('bi-arrow-repeat', 'spinner-icon');
            setTimeout(() => {
                searchIcon.classList.remove('bi-arrow-repeat', 'spinner-icon');
                searchIcon.classList.add('bi-search');
            }, 250);
        }

        let results = this.papers;

        // If on bookmarks tab, filter only bookmarks
        if (this.state.activeTab === 'bookmarks') {
            results = results.filter(p => this.bookmarks.has(p.id));
        }

        // Filter files only
        if (this.state.onlyWithFiles) {
            results = results.filter(p => p.has_files || (p.model_papers && p.model_papers.length > 0));
        }

        // Filter Semester
        if (this.state.selectedSemester !== 'ALL') {
            results = results.filter(p => String(p.semester) === this.state.selectedSemester);
        }

        // Filter Course Type
        if (this.state.selectedCourseType !== 'ALL') {
            if (this.state.selectedCourseType === 'MIN') {
                results = results.filter(p => p.is_minor);
            } else {
                results = results.filter(p => p.course_type === this.state.selectedCourseType);
            }
        }

        // Filter Department (Major & Minor)
        if (this.state.selectedDept !== 'ALL') {
            results = results.filter(p => 
                p.parent_dept === this.state.selectedDept || 
                p.dept_code === this.state.selectedDept
            );
        }

        // High-Performance Multi-Term Fuzzy Search Query
        if (this.state.searchQuery) {
            const tokens = this.state.searchQuery.toLowerCase().split(/\s+/).filter(Boolean);
            results = results.filter(p => this.matchPaper(p, tokens, this.state.searchQuery));
        }

        this.filteredPapers = results;
        this.renderActiveFilterChips();
        this.renderPapers();
        this.renderPagination();
    },

    renderPapers() {
        const container = document.getElementById('papersGrid');
        const countEl = document.getElementById('resultsCount');
        if (!container) return;

        // Group filtered papers by course, enriching from catalog so every course card consolidates
        // ALL of its examination question papers and ALL of its model question papers
        const groupedCourses = this.groupPapersByCourse(this.filteredPapers, true);
        this.groupedCourses = groupedCourses;

        const totalCourses = groupedCourses.length;
        const totalPapers = this.filteredPapers.length;

        if (countEl) {
            if (totalCourses === 0) {
                countEl.textContent = 'No matching question papers';
            } else {
                countEl.textContent = `Showing ${totalCourses.toLocaleString()} ${totalCourses === 1 ? 'Course' : 'Courses'} (${totalPapers.toLocaleString()} question papers & model schemes)`;
            }
        }

        const pillCountEl = document.getElementById('filterActiveCount');
        if (pillCountEl) {
            pillCountEl.textContent = `${totalCourses.toLocaleString()} Courses`;
        }

        if (totalCourses === 0) {
            container.innerHTML = `
                <div class="col-span-full py-16 text-center bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-8 shadow-xs">
                    <div class="w-16 h-16 rounded-full bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 mx-auto flex items-center justify-center text-2xl mb-4">
                        <i class="bi bi-search"></i>
                    </div>
                    <h3 class="text-lg font-bold text-slate-800 dark:text-slate-100">
                        ${this.state.activeTab === 'bookmarks' ? 'No saved question papers yet' : 'No courses match your filters'}
                    </h3>
                    <p class="text-sm text-slate-500 dark:text-slate-400 mt-1 max-w-md mx-auto">
                        ${this.state.activeTab === 'bookmarks' ? 'Click "Save" on any question paper or course card to keep it here for quick revision.' : 'Try searching by course code (e.g. <code class="text-blue-600 font-mono font-bold">MG3DSEMAT202</code>), course name (e.g. <code class="text-blue-600 font-bold">Calculus</code>), or reset all filters.'}
                    </p>
                    ${this.state.activeTab === 'bookmarks' ? `
                        <button onclick="App.selectTab('departments')" class="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-semibold transition">
                            Browse Departments
                        </button>
                    ` : `
                        <button onclick="App.resetFilters()" class="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-semibold transition">
                            Reset All Filters
                        </button>
                    `}
                </div>
            `;
            return;
        }

        // Paginate grouped courses
        const start = (this.state.currentPage - 1) * this.state.pageSize;
        const pageItems = groupedCourses.slice(start, start + this.state.pageSize);

        if (this.state.viewMode === 'grid') {
            container.className = 'grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5';
            container.innerHTML = pageItems.map(course => this.renderGroupedCourseCard(course)).join('');
        } else {
            container.className = 'col-span-full';
            container.innerHTML = this.renderGroupedCourseTable(pageItems);
        }
    },

    extractMonthYear(name) {
        if (!name) return 'Exam Session';
        const monthMap = {
            'jan': 'January', 'feb': 'February', 'mar': 'March', 'apr': 'April',
            'may': 'May', 'jun': 'June', 'jul': 'July', 'aug': 'August',
            'sep': 'September', 'oct': 'October', 'nov': 'November', 'dec': 'December'
        };
        const setSuffix = name.includes('(Set A)') ? ' (Set A)' : (name.includes('(Set B)') ? ' (Set B)' : '');
        const m = name.match(/(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*[,\s\-]+(20\d\d)/i);
        if (m) {
            const rawM = m[1].toLowerCase().slice(0, 3);
            const fullM = monthMap[rawM] || m[1];
            return `${fullM} ${m[2]}${setSuffix}`;
        }
        const y = name.match(/20\d\d/);
        return y ? `${y[0]}${setSuffix}` : name;
    },

    groupPapersByCourse(paperList, enrichFromCatalog = false) {
        const groups = new Map();
        paperList.forEach(p => {
            const codeKey = (p.course_code || '').trim().toUpperCase();
            const titleKey = (p.title || '').trim().toUpperCase();
            const key = codeKey || titleKey || 'UNKNOWN';

            if (!groups.has(key)) {
                groups.set(key, {
                    course_code: p.course_code,
                    title: p.title,
                    course_type: p.course_type,
                    semester: p.semester,
                    parent_dept_name: p.parent_dept_name,
                    dept_name: p.dept_name,
                    dept_code: p.dept_code,
                    parent_dept: p.parent_dept,
                    is_minor: p.is_minor,
                    minor_name: p.minor_name,
                    model_papers: [],
                    papers: []
                });
            }

            const course = groups.get(key);

            // Merge metadata if missing
            if (!course.course_code && p.course_code) course.course_code = p.course_code;
            if (!course.title && p.title) course.title = p.title;
            if (!course.parent_dept_name && p.parent_dept_name) course.parent_dept_name = p.parent_dept_name;

            // Merge model papers
            if (p.model_papers && Array.isArray(p.model_papers)) {
                p.model_papers.forEach(m => {
                    const mKey = m.id || m.url || m.title;
                    if (!course.model_papers.some(em => (em.id || em.url || em.title) === mKey)) {
                        course.model_papers.push(m);
                    }
                });
            }

            // Merge papers
            const pKey = p.id || `${p.exam_id}_${p.exam_name}_${p.course_code}`;
            if (!course.papers.some(ep => (ep.id || `${ep.exam_id}_${ep.exam_name}_${ep.course_code}`) === pKey)) {
                course.papers.push(p);
            }
        });

        // If enrichFromCatalog is true, pull in all question papers and model papers for these courses from this.papers
        if (enrichFromCatalog && this.papers && this.papers.length > 0) {
            if (!this._courseCatalogMap) {
                this.buildCourseCatalogIndex();
            }

            groups.forEach(course => {
                const codeKey = (course.course_code || '').trim().toUpperCase();
                const titleKey = (course.title || '').trim().toUpperCase();

                const matchingCatalog = [];
                if (codeKey && this._courseCatalogMap.byCode.has(codeKey)) {
                    matchingCatalog.push(...this._courseCatalogMap.byCode.get(codeKey));
                } else if (titleKey && this._courseCatalogMap.byTitle.has(titleKey)) {
                    matchingCatalog.push(...this._courseCatalogMap.byTitle.get(titleKey));
                }

                const seenCatIds = new Set();
                matchingCatalog.forEach(cp => {
                    if (seenCatIds.has(cp.id)) return;
                    seenCatIds.add(cp.id);

                    // Merge model papers
                    if (cp.model_papers && Array.isArray(cp.model_papers)) {
                        cp.model_papers.forEach(m => {
                            const mKey = m.id || m.url || m.title;
                            if (!course.model_papers.some(em => (em.id || em.url || em.title) === mKey)) {
                                course.model_papers.push(m);
                            }
                        });
                    }

                    // Merge papers
                    const pKey = cp.id || `${cp.exam_id}_${cp.exam_name}_${cp.course_code}`;
                    if (!course.papers.some(ep => (ep.id || `${ep.exam_id}_${ep.exam_name}_${ep.course_code}`) === pKey)) {
                        course.papers.push(cp);
                    }
                });
            });
        }

        // Clean up course papers:
        // If course has real exam papers (has_qp || has_scheme), remove any placeholder records
        groups.forEach(course => {
            const realExamPapers = course.papers.filter(p => p.has_qp || p.has_scheme);
            if (realExamPapers.length > 0) {
                course.papers = realExamPapers;
            }
            // Sort chronologically by exam session
            course.papers.sort((a, b) => (b.exam_name || '').localeCompare(a.exam_name || ''));
        });

        const courseList = Array.from(groups.values());
        // Sort courses: Keep signature courses (college-specific syllabus) at the bottom
        courseList.sort((a, b) => {
            const aSig = this.isSignatureCourse(a);
            const bSig = this.isSignatureCourse(b);
            if (aSig !== bSig) return aSig ? 1 : -1;
            return (a.course_code || '').localeCompare(b.course_code || '');
        });

        return courseList;
    },

        getDeptSyllabus(deptCode, deptName) {
        if (!deptCode && !deptName) return null;
        const code = (deptCode || '').toUpperCase().trim();
        const name = (deptName || '').toLowerCase().trim();
        const list = this.syllabi || [];

        const EXACT_MAP = {
            'AGD': 'BA (Hons) Animation and Graphic Design',
            'AQC': 'BSc (Hons) Aquaculture',
            'ARB': 'BA (Hons) Arabic',
            'ADS': 'BSc (Hons) Artificial Intelligence and Data Science',
            'BCH': 'BSc (Hons) Biochemistry',
            'BIF': 'BSc (Hons) Bioinformatics',
            'BTS': 'BSc (Hons) Biological Techniques and Specimen Preparation',
            'BTG': 'BSc (Hons) Biotechnology',
            'BOT': 'BSc (Hons) Botany',
            'BBT': 'BSc (Hons) Botany and Biotechnology(Double Major Programme)',
            'BBA': 'Bachelor in Business Administration (Honours)',
            'CHE': 'BSc (Hons) Chemistry',
            'CHM': 'BSc (Hons) Chemistry',
            'CND': 'BSc (Hons) Clinical Nutrition and Dietetics',
            'COM': 'BCom (Hons)',
            'COA': 'BCom (Hons)',
            'COF': 'BCom (Hons)',
            'BCA': 'Bachelor in Computer Applications (Honours)',
            'CSA': 'Bachelor in Computer Applications (Honours)',
            'CSC': 'BSc (Hons) Computer Science',
            'CFS': 'BSc (Hons) Cyber Forensics',
            'CYB': 'BSc (Hons) Cyber Forensics',
            'ECO': 'BA (Hons) Economics',
            'ECT': 'BSc (Hons) Electronics with Computer Technology',
            'ELT': 'BSc (Hons) Electronics with Computer Technology',
            'ECC': 'BSc (Hons) Electronics with Computer Technology and Computer Science(Double Major Programme)',
            'ENG': 'BA (Hons) English',
            'FDG': 'BSc (Hons) Fashion Designing',
            'AAS': 'BFA (Hons) Applied Arts',
            'BFA': 'BFA (Hons) Applied Arts',
            'FSQ': 'BSc (Hons) Food Science and Quality Control',
            'FTQ': 'BSc (Hons) Food Technology and Quality Assurance',
            'FSC': 'BSc (Hons) Forensic Science',
            'FOR': 'BSc (Hons) Forensic Science',
            'FRH': 'French Minor and Other Courses',
            'GEO': 'BSc (Hons) Geology',
            'GER': 'German Minor and Other Courses',
            'HIN': 'BA (Hons) Hindi',
            'HIS': 'BA (Hons) History',
            'HSC': 'BSc (Hons) Home Science',
            'HMS': 'BSc (Hons) Home Science',
            'HMC': 'BSc (Hons) Hotel Management and Culinary Arts',
            'ISH': 'BA (Hons) Islamic History',
            'JMC': 'BA (Hons) Journalism and Mass Communication',
            'LIS': 'Library and Information Science Courses',
            'MAL': 'BA (Hons) Malayalam',
            'MAT': 'BSc (Hons) Mathematics',
            'MBG': 'BSc (Hons) Microbiology',
            'MCB': 'BSc (Hons) Microbiology',
            'MLM': 'BA (Hons) Multimedia',
            'MMD': 'BA (Hons) Multimedia',
            'MUS': 'BA (Hons) Music - Mridangam',
            'PFA': 'BA (Hons) Bharathanatyam',
            'DAN': 'BA (Hons) Bharathanatyam',
            'BHN': 'BA (Hons) Bharathanatyam',
            'MOH': 'BA (Hons) Mohiniyattam',
            'KAT': 'BA (Hons) Kathakali Vesham',
            'PHL': 'BA (Hons) Philosophy',
            'PES': 'BPES (Hons)',
            'PHY': 'BSc (Hons) Physics',
            'POL': 'BA (Hons) Political Science',
            'PJM': 'BA (Hons) Political Science with Journalism and Mass Communication(Double Major Programme)',
            'PSY': 'BSc (Hons) Psychology',
            'SAN': 'BA (Hons) Sanskrit (Special) Sahithya',
            'SSP': 'BA (Hons) Sanskrit (Special) Sahithya',
            'SWK': 'BSW (Hons)',
            'BSW': 'BSW (Hons)',
            'SOC': 'BA (Hons) Sociology',
            'SMG': 'BSM (Hons)',
            'STA': 'BSc (Hons) Statistics',
            'SYR': 'Syriac Minor and Other Courses',
            'TAM': 'BA (Hons) Tamil',
            'TTM': 'BTTM (Hons)',
            'BTT': 'BTTM (Hons)',
            'ZGY': 'BSc (Hons) Zoology',
            'ZOO': 'BSc (Hons) Zoology',
            'ZIM': 'BSc (Hons) Zoology and Industrial Microbiology (Double Major Programme)'
        };

        const target = EXACT_MAP[code];
        if (target) {
            const found = list.find(p => p.program && p.program.toLowerCase().includes(target.toLowerCase()));
            if (found) return found;
        }

        if (name) {
            const found = list.find(p => {
                const pn = (p.program || '').toLowerCase();
                const regex = new RegExp('\\b' + name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '\\b', 'i');
                return regex.test(pn);
            });
            if (found) return found;
        }

        return {
            program: deptName ? `MGU FYUGP - ${deptName}` : 'Mahatma Gandhi University FYUGP',
            main_syllabus: 'https://cap.mgu.ac.in/mguugp/syllabus.jsp',
            links: [
                { title: 'Official MGU FYUGP Syllabus Portal', url: 'https://cap.mgu.ac.in/mguugp/syllabus.jsp' },
                { title: 'MGU-UGP Regulations & Amendments', url: 'https://cap.mgu.ac.in/mguugpdocs/1317-ACA_16-2025-MGU.pdf' }
            ]
        };
    },

    getCourseSyllabus(course) {
        if (!course) return null;
        const deptCode = (course.dept_code || course.parent_dept || '').toUpperCase();
        const deptName = (course.dept_name || course.parent_dept_name || '').toLowerCase();
        const title = (course.title || '').toLowerCase();

        const DEPT_MAP = {
            'STA': 'Statistics', 'MAT': 'Mathematics', 'PHY': 'Physics', 'CHE': 'Chemistry',
            'CSC': 'Computer Science', 'CSA': 'Computer Applications', 'BCA': 'Computer Applications',
            'BBA': 'Business Administration', 'BST': 'Business Administration', 'COM': 'BCom',
            'COA': 'BCom', 'COF': 'BCom', 'ECO': 'Economics', 'ENG': 'English', 'MAL': 'Malayalam',
            'HIN': 'Hindi', 'ARB': 'Arabic', 'SAN': 'Sanskrit', 'HIS': 'History', 'POL': 'Political Science',
            'SOC': 'Sociology', 'BOT': 'Botany', 'ZOO': 'Zoology', 'PSY': 'Psychology',
            'BCH': 'Biochemistry', 'BIF': 'Bioinformatics', 'BTG': 'Biotechnology',
            'BTS': 'Biological Techniques', 'AGD': 'Animation and Graphic Design',
            'AVE': 'Animation and Visual Effects', 'MMD': 'Multimedia', 'AQC': 'Aquaculture',
            'CYB': 'Cyber Forensics', 'ELT': 'Electronics', 'ECT': 'Electronics',
            'FTQ': 'Food Technology', 'FSQ': 'Food Science', 'FOR': 'Forensic Science',
            'GEO': 'Geology', 'HMS': 'Home Science', 'HMC': 'Hotel Management',
            'MCB': 'Microbiology', 'BSW': 'BSW', 'BTT': 'BTTM', 'BFA': 'Applied Arts',
            'MUM': 'Music', 'DAN': 'Bharathanatyam', 'BHN': 'Bharathanatyam',
            'MOH': 'Mohiniyattam', 'KAT': 'Kathakali', 'PHL': 'Philosophy', 'JMC': 'Journalism'
        };

        const target = DEPT_MAP[deptCode];
        const list = this.syllabi || [];

        if (target) {
            const found = list.find(p => p.program && p.program.toLowerCase().includes(target.toLowerCase()));
            if (found) return found;
        }
        if (deptName) {
            const found = list.find(p => p.program && (p.program.toLowerCase().includes(deptName) || deptName.includes(p.program.toLowerCase())));
            if (found) return found;
        }
        const words = title.split(/\s+/).filter(w => w.length > 4);
        for (const w of words) {
            const found = list.find(p => p.program && p.program.toLowerCase().includes(w));
            if (found) return found;
        }

        return {
            program: course.dept_name ? `MGU FYUGP - ${course.dept_name}` : 'MGU FYUGP Syllabus',
            main_syllabus: 'https://cap.mgu.ac.in/mguugp/syllabus.jsp',
            links: [{ title: 'Official MGU Syllabus', url: 'https://cap.mgu.ac.in/mguugp/syllabus.jsp' }]
        };
    },

    renderGroupedCourseCard(course) {
        const isAdmin = sessionStorage.getItem('mgu_admin_auth') === 'true';
        const ctypeClass = `badge-${(course.course_type || 'dsc').toLowerCase()}`;
        const firstPaper = (course.papers && course.papers[0]) || { id: course.course_code || 'paper' };
        const isBookmarked = (course.papers || []).some(p => this.bookmarks.has(p.id));
        const examPapers = (course.papers || []).filter(p => p.has_qp || p.has_scheme);

        return `
            <div class="paper-card bg-white dark:bg-slate-800 rounded-2xl p-5 flex flex-col justify-between shadow-xs border border-slate-200/80 dark:border-slate-700 hover:border-blue-400 dark:hover:border-blue-600 transition">
                <div>
                    <!-- Top Badge Bar -->
                    <div class="flex items-start justify-between gap-2 mb-3">
                        <div class="flex flex-wrap items-center gap-1.5">
                            <span class="text-xs font-bold px-2.5 py-0.5 rounded-md bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200">
                                Sem ${course.semester}
                            </span>
                            <span class="text-xs font-semibold px-2 py-0.5 rounded-md ${ctypeClass}">
                                ${course.course_type}
                            </span>
                            ${course.is_minor ? `
                                <span class="text-xs font-semibold px-2 py-0.5 rounded-md badge-minor">
                                    ${course.minor_name || course.dept_code} (Minor)
                                </span>
                            ` : ''}
                            ${this.isSignatureCourse(course) ? `
                                <span class="text-xs font-semibold px-2 py-0.5 rounded-md bg-amber-100 dark:bg-amber-950/70 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-700 flex items-center gap-1" title="Signature Course (College specific syllabus)">
                                    <i class="bi bi-pen-fill text-[10px]"></i> Signature
                                </span>
                            ` : ''}
                        </div>

                        <!-- Action Buttons: AI Notes + Bookmark -->
                        <div class="flex items-center gap-1.5 shrink-0">
                            <button 
                                onclick="App.openAiNotesForCourse('${course.course_code || ''}', '${course.title ? course.title.replace(/'/g, "\\'") : ''}')" 
                                title="Generate AI Study Notes & Exam Blueprint" 
                                class="px-2.5 py-1 text-xs font-semibold rounded-lg flex items-center gap-1.5 transition bg-indigo-50 hover:bg-indigo-100 dark:bg-indigo-950/60 dark:hover:bg-indigo-900/60 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800 shadow-2xs"
                            >
                                <i class="bi bi-stars text-indigo-500"></i>
                                <span class="hidden sm:inline">AI Notes</span>
                            </button>
                            <button 
                                data-bm-id="${firstPaper.id}"
                                onclick="App.toggleBookmark('${firstPaper.id}')" 
                                title="Save for revision" 
                            class="px-2.5 py-1 text-xs font-semibold rounded-lg flex items-center gap-1.5 transition ${
                                isBookmarked 
                                    ? 'bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-700' 
                                    : 'bg-slate-100 dark:bg-slate-700 hover:bg-amber-50 dark:hover:bg-amber-950/40 text-slate-600 dark:text-slate-300 hover:text-amber-700 border border-slate-200 dark:border-slate-600'
                            }"
                        >
                            <i class="bi ${isBookmarked ? 'bi-star-fill text-amber-500' : 'bi-star'}"></i>
                            <span>${isBookmarked ? 'Saved' : 'Save'}</span>
                            </button>
                        </div>
                    </div>

                    <!-- Course Code -->
                    <div class="flex items-center gap-2 mb-1.5">
                        <span class="font-mono font-bold text-sm text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/40 px-2 py-0.5 rounded border border-blue-100 dark:border-blue-900/40">
                            ${course.course_code || 'CODE N/A'}
                        </span>
                        <span class="text-[11px] font-semibold text-slate-400">
                            ${examPapers.length > 0 ? `${examPapers.length} ${examPapers.length === 1 ? 'Exam Paper' : 'Exam Papers'}` : 'Exam Paper Awaited'}
                            ${course.model_papers && course.model_papers.length > 0 ? ` · ${course.model_papers.length} Model` : ''}
                        </span>
                    </div>

                    <!-- Course Title -->
                    <h3 class="font-bold text-slate-900 dark:text-slate-100 text-base leading-snug line-clamp-2 mb-2" title="${course.title}">
                        ${course.title}
                    </h3>

                    <!-- Department info -->
                    ${course.parent_dept_name || course.dept_name ? `
                        <div class="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-1.5 truncate mb-3">
                            <i class="bi bi-mortarboard text-slate-400"></i>
                            <span class="truncate font-medium text-slate-600 dark:text-slate-300">
                                ${course.parent_dept_name || course.dept_name} ${course.is_minor ? `(${course.minor_name || course.dept_code})` : ''}
                            </span>
                        </div>
                    ` : ''}
                </div>

                <!-- Grouped Question Papers for this course -->
                <div class="pt-3 border-t border-slate-100 dark:border-slate-700/60 space-y-2">
                    ${examPapers.length > 0 ? `
                        <div class="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1">
                            Question Papers:
                        </div>
                        ${examPapers.map(p => {
                            const monthYear = this.extractMonthYear(p.exam_name);
                            return `
                                <div class="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-700/40 border border-slate-200/70 dark:border-slate-600/50 flex flex-wrap sm:flex-nowrap items-center justify-between gap-2">
                                    <div class="flex items-center gap-1.5 min-w-0">
                                        <i class="bi bi-calendar-event text-blue-600 dark:text-blue-400 text-xs"></i>
                                        <span class="text-xs font-semibold text-slate-800 dark:text-slate-200 truncate">
                                            ${monthYear}
                                        </span>
                                    </div>

                                    <div class="flex items-center gap-1.5 shrink-0">
                                        ${p.has_qp ? `
                                            <button onclick="App.previewPaper(this, ${JSON.stringify(p).replace(/"/g, '&quot;')}, 'QP')" class="px-2.5 py-1 text-xs font-semibold rounded-lg bg-blue-600 hover:bg-blue-500 text-white shadow-xs flex items-center gap-1 transition" title="Preview Question Paper">
                                                <i class="bi bi-eye"></i> QP
                                            </button>
                                            <button onclick="App.downloadPaper(this, ${JSON.stringify(p).replace(/"/g, '&quot;')}, 'QP')" class="p-1 text-xs rounded-lg bg-slate-200/80 dark:bg-slate-600 hover:bg-slate-300 dark:hover:bg-slate-500 text-slate-700 dark:text-slate-200 transition" title="Download Question Paper">
                                                <i class="bi bi-download"></i>
                                            </button>
                                        ` : ''}

                                        ${p.has_scheme ? `
                                            <button onclick="App.previewPaper(this, ${JSON.stringify(p).replace(/"/g, '&quot;')}, 'SCHEME')" class="px-2 py-1 text-xs font-semibold rounded-lg bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 hover:bg-emerald-100 flex items-center gap-1 transition" title="Preview Scheme">
                                                <i class="bi bi-journal-check"></i> Scheme
                                            </button>
                                            <button onclick="App.downloadPaper(this, ${JSON.stringify(p).replace(/"/g, '&quot;')}, 'SCHEME')" class="p-1 text-xs rounded-lg bg-slate-200/80 dark:bg-slate-600 hover:bg-slate-300 dark:hover:bg-slate-500 text-slate-700 dark:text-slate-200 transition" title="Download Evaluation Scheme">
                                                <i class="bi bi-download"></i>
                                            </button>
                                        ` : ''}

                                        ${isAdmin ? `
                                            <button onclick="App.handleDeletePaper('${p.id}', this)" title="Delete Paper (Admin)" class="p-1 text-xs rounded-lg bg-rose-50 hover:bg-rose-100 dark:bg-rose-950/60 text-rose-600 dark:text-rose-300 border border-rose-200 dark:border-rose-800 transition">
                                                <i class="bi bi-trash3 text-rose-500"></i>
                                            </button>
                                        ` : ''}
                                    </div>
                                </div>
                            `;
                        }).join('')}
                    ` : `
                        <div class="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-700/30 border border-dashed border-slate-200 dark:border-slate-700 text-xs text-slate-500 dark:text-slate-400 flex items-center gap-2">
                            <i class="bi bi-clock-history text-slate-400"></i>
                            <span>University exam papers not conducted/released yet</span>
                        </div>
                    `}

                    ${course.model_papers && course.model_papers.length > 0 ? `
                        <!-- SEPARATE MODEL QUESTION PAPERS SECTION (BELOW ACTUAL PAPERS) -->
                        <div class="mt-3 pt-3 border-t border-slate-100 dark:border-slate-700/60 space-y-1.5">
                            <div class="text-[11px] font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-400 mb-1">
                                Model Question Papers:
                            </div>
                            ${course.model_papers.map(m => `
                                <div class="p-2.5 rounded-xl bg-indigo-50/70 dark:bg-indigo-950/30 border border-indigo-100 dark:border-indigo-900/40 flex flex-wrap sm:flex-nowrap items-center justify-between gap-2">
                                    <div class="flex items-center gap-1.5 min-w-0">
                                        <i class="${m.paper_type === 'PRACTICAL' ? 'bi bi-flask' : 'bi bi-file-earmark-text'} text-indigo-600 dark:text-indigo-400 text-xs"></i>
                                        <span class="text-[11px] sm:text-xs font-bold uppercase tracking-wider text-indigo-700 dark:text-indigo-300 truncate">
                                            ${m.paper_type === 'PRACTICAL' ? '🔬 Practical Model Paper:' : '📑 Model Question Paper:'}
                                        </span>
                                    </div>
                                    <div class="flex items-center gap-1.5 shrink-0">
                                        <button onclick="App.previewDirect(this, '${m.cdn_url || m.url}', '${m.title.replace(/'/g, "\\'")}', '${course.course_code || ''}')" class="px-2.5 py-1 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white shadow-xs flex items-center gap-1 transition" title="Preview Model Question Paper">
                                            <i class="bi bi-eye"></i> View
                                        </button>
                                        <button onclick="App.downloadDirect(this, '${m.cdn_url || m.url}', '${m.title ? m.title.replace(/'/g, "\\'") : 'Model_Paper'}', '${course.course_code || ''}')" class="p-1 text-xs rounded-lg bg-slate-200/80 dark:bg-slate-600 hover:bg-slate-300 dark:hover:bg-slate-500 text-slate-700 dark:text-slate-200 transition" title="Download Model Question Paper">
                                            <i class="bi bi-download"></i>
                                        </button>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    ` : ''}

                    <!-- Clean Inline Syllabus Action -->
                    <div class="mt-2 pt-2 border-t border-slate-100 dark:border-slate-700/50 flex items-center justify-between text-[11px]">
                        <span class="text-slate-400 font-medium">${course.dept_name || 'Department'}</span>
                        ${(() => {
                            const syl = this.getCourseSyllabus(course);
                            if (!syl || !syl.main_syllabus) return '';
                            return `
                                <button onclick="App.previewDirect(this, '${syl.main_syllabus}', 'Syllabus - ${syl.program}', '${course.course_code}')" class="text-emerald-600 dark:text-emerald-400 hover:underline font-semibold flex items-center gap-1 cursor-pointer" title="View Full Discipline Syllabus (from cap.mgu.ac.in)">
                                    <i class="bi bi-book-half"></i> Programme Syllabus
                                </button>
                            `;
                        })()}
                    </div>
                </div>
            </div>
        `;
    },

    renderPaperCard(p) {
        const isBookmarked = this.bookmarks.has(p.id);
        const isAdmin = sessionStorage.getItem('mgu_admin_auth') === 'true';
        const ctypeClass = `badge-${(p.course_type || 'dsc').toLowerCase()}`;
        const monthYear = this.extractMonthYear(p.exam_name);

        return `
            <div class="paper-card bg-white dark:bg-slate-800 rounded-2xl p-5 flex flex-col justify-between shadow-xs border border-slate-200/80 dark:border-slate-700 hover:border-blue-400 dark:hover:border-blue-600 transition">
                <div>
                    <!-- Top Badge Bar -->
                    <div class="flex items-start justify-between gap-2 mb-3">
                        <div class="flex flex-wrap items-center gap-1.5">
                            ${isAdmin ? `
                                <span class="text-xs font-bold px-2.5 py-0.5 rounded-md bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200">
                                    Sem ${p.semester}
                                </span>
                            ` : ''}
                            <span class="text-xs font-semibold px-2 py-0.5 rounded-md ${ctypeClass}">
                                ${p.course_type}
                            </span>
                            ${p.is_minor ? `
                                <span class="text-xs font-semibold px-2 py-0.5 rounded-md badge-minor">
                                    ${p.minor_name || p.dept_code} (Minor)
                                </span>
                            ` : ''}
                        </div>

                        <!-- Right Actions: AI Notes + Admin Delete + Save -->
                        <div class="flex items-center gap-1.5">
                            <button 
                                onclick="App.openAiNotesForCourse('${p.course_code || ''}', '${p.title ? p.title.replace(/'/g, "\\'") : ''}')" 
                                title="Generate AI Study Notes & Exam Blueprint" 
                                class="px-2.5 py-1 text-xs font-semibold rounded-lg flex items-center gap-1.5 transition bg-indigo-50 hover:bg-indigo-100 dark:bg-indigo-950/60 dark:hover:bg-indigo-900/60 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800 shadow-2xs"
                            >
                                <i class="bi bi-stars text-indigo-500"></i>
                                <span class="hidden sm:inline">AI Notes</span>
                            </button>
                            ${isAdmin ? `
                                <button 
                                    onclick="App.handleDeletePaper('${p.id}', this)" 
                                    title="Delete paper permanently (Admin)" 
                                    class="p-1.5 text-xs font-semibold rounded-lg bg-rose-50 hover:bg-rose-100 dark:bg-rose-950/60 dark:hover:bg-rose-900 text-rose-600 dark:text-rose-300 border border-rose-200 dark:border-rose-800 transition"
                                >
                                    <i class="bi bi-trash3 text-rose-500"></i>
                                </button>
                            ` : ''}
                            <button 
                                id="bm-btn-${p.id}" 
                                data-bm-id="${p.id}"
                                onclick="App.toggleBookmark('${p.id}')" 
                                title="Save for revision" 
                                class="px-2.5 py-1 text-xs font-semibold rounded-lg flex items-center gap-1.5 transition ${
                                    isBookmarked 
                                        ? 'bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-700' 
                                        : 'bg-slate-100 dark:bg-slate-700 hover:bg-amber-50 dark:hover:bg-amber-950/40 text-slate-600 dark:text-slate-300 hover:text-amber-700 border border-slate-200 dark:border-slate-600'
                                }"
                            >
                                <i class="bi ${isBookmarked ? 'bi-star-fill text-amber-500' : 'bi-star'}"></i>
                                <span>${isBookmarked ? 'Saved' : 'Save'}</span>
                            </button>
                        </div>
                    </div>

                    <!-- Course Code (NO QP Code) -->
                    <div class="flex items-center gap-2 mb-1.5">
                        <span class="font-mono font-bold text-sm text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/40 px-2 py-0.5 rounded border border-blue-100 dark:border-blue-900/40">
                            ${p.course_code || 'CODE N/A'}
                        </span>
                    </div>

                    <!-- Course Title -->
                    <h3 class="font-bold text-slate-900 dark:text-slate-100 text-base leading-snug line-clamp-2 mb-2" title="${p.title}">
                        ${p.title}
                    </h3>

                    <!-- Department & Exam Month Year -->
                    <div class="text-xs text-slate-500 dark:text-slate-400 space-y-1 mb-4">
                        <div class="flex items-center gap-1.5 truncate">
                            <i class="bi bi-mortarboard text-slate-400"></i>
                            <span class="truncate font-medium text-slate-700 dark:text-slate-300">
                                ${p.parent_dept_name} ${p.is_minor ? `(${p.minor_name || p.dept_name})` : ''}
                            </span>
                        </div>
                        <div class="flex items-center gap-1.5 truncate text-[11px] text-slate-500 font-medium">
                            <i class="bi bi-calendar-event text-blue-500"></i>
                            <span>Exam: <strong class="text-slate-700 dark:text-slate-200">${monthYear}</strong></span>
                        </div>
                    </div>
                </div>

                <!-- Action Buttons: Preview & Download -->
                <div class="pt-3 border-t border-slate-100 dark:border-slate-700/60 flex flex-wrap sm:flex-nowrap items-center justify-between gap-2">
                    <div class="flex items-center gap-1.5">
                        ${p.has_qp ? `
                            <button onclick="App.previewPaper(this, ${JSON.stringify(p).replace(/"/g, '&quot;')}, 'QP')" class="px-3 py-1.5 text-xs font-semibold rounded-lg bg-blue-600 hover:bg-blue-500 text-white shadow-xs flex items-center gap-1 transition">
                                <i class="bi bi-eye"></i> Preview QP
                            </button>
                            <a href="${p.qp_url}" target="_blank" download class="p-1.5 text-xs rounded-lg bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 transition" title="Download Question Paper">
                                <i class="bi bi-download"></i>
                            </a>
                        ` : '<span class="text-xs text-slate-400 italic">No QP</span>'}
                    </div>

                    <div class="flex items-center gap-1.5">
                        ${p.has_scheme ? `
                            <button onclick="App.previewPaper(this, ${JSON.stringify(p).replace(/"/g, '&quot;')}, 'SCHEME')" class="px-2.5 py-1.5 text-xs font-semibold rounded-lg bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 hover:bg-emerald-100 flex items-center gap-1 transition">
                                <i class="bi bi-journal-check"></i> Scheme
                            </button>
                            <a href="${p.scheme_url}" target="_blank" download class="p-1.5 text-xs rounded-lg bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 transition" title="Download Evaluation Scheme">
                                <i class="bi bi-download"></i>
                            </a>
                        ` : ''}
                    </div>
                </div>

                ${p.model_papers && p.model_papers.length > 0 ? `
                    <div class="mt-2.5 pt-2.5 border-t border-slate-100 dark:border-slate-700/60 space-y-1.5">
                        ${p.model_papers.map(m => `
                            <div class="p-2 rounded-xl bg-indigo-50/70 dark:bg-indigo-950/30 border border-indigo-100 dark:border-indigo-900/40 flex flex-wrap sm:flex-nowrap items-center justify-between gap-2">
                                <div class="flex items-center gap-1.5 min-w-0">
                                    <i class="${m.paper_type === 'PRACTICAL' ? 'bi bi-flask' : 'bi bi-file-earmark-text'} text-indigo-600 dark:text-indigo-400 text-xs"></i>
                                    <span class="text-[11px] font-bold uppercase tracking-wider text-indigo-700 dark:text-indigo-300 truncate">
                                        ${m.paper_type === 'PRACTICAL' ? '🔬 Practical Model Paper:' : '📑 Model Question Paper:'}
                                    </span>
                                </div>
                                <div class="flex items-center gap-1 shrink-0">
                                    <button onclick="App.previewDirect(this, '${m.cdn_url || m.url}', '${m.title.replace(/'/g, "\\'")}', '${p.course_code || ''}')" class="px-2 py-1 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white shadow-xs flex items-center gap-1 transition" title="Preview Model QP">
                                        <i class="bi bi-eye"></i> View
                                    </button>
                                    <button onclick="App.downloadDirect(this, '${m.cdn_url || m.url}', '${m.title ? m.title.replace(/'/g, "\\'") : 'Model_Paper'}', '${course.course_code || ''}')" class="p-1 text-xs rounded-lg bg-slate-200/80 dark:bg-slate-600 hover:bg-slate-300 dark:hover:bg-slate-500 text-slate-700 dark:text-slate-200 transition" title="Download Model QP">
                                        <i class="bi bi-download"></i>
                                    </button>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                ` : ''}

                <!-- OFFICIAL SYLLABUS SECTION (AFTER MODEL QUESTION PAPER) -->
                ${(() => {
                    const syl = this.getCourseSyllabus(p);
                    if (!syl || !syl.main_syllabus) return '';
                    const sylUrl = syl.main_syllabus;
                    const sylTitle = `Syllabus - ${syl.program || p.title}`;
                    return `
                        <div class="mt-2.5 pt-2.5 border-t border-slate-100 dark:border-slate-700/60 flex items-center justify-between gap-2 text-xs">
                            <div class="flex items-center gap-1.5 min-w-0">
                                <i class="bi bi-book-half text-emerald-600 dark:text-emerald-400 text-xs"></i>
                                <span class="text-[11px] font-bold text-emerald-800 dark:text-emerald-300 truncate" title="${syl.program}">
                                    📖 Syllabus: ${syl.program}
                                </span>
                            </div>
                            <div class="flex items-center gap-1 shrink-0">
                                <button onclick="App.previewDirect(this, '${sylUrl}', '${sylTitle.replace(/'/g, "\\'")}', '${p.course_code || ''}')" class="px-2 py-0.5 text-xs font-semibold rounded bg-emerald-600 hover:bg-emerald-500 text-white shadow-2xs flex items-center gap-1 transition" title="Preview Official Syllabus">
                                    <i class="bi bi-eye"></i> View
                                </button>
                                <a href="${sylUrl}" target="_blank" rel="noopener" class="p-0.5 text-xs text-slate-500 hover:text-emerald-600 transition" title="Open Syllabus Link">
                                    <i class="bi bi-box-arrow-up-right"></i>
                                </a>
                            </div>
                        </div>
                    `;
                })()}
            </div>
        `;
    },

    renderGroupedCourseTable(courses) {
        const isAdmin = sessionStorage.getItem('mgu_admin_auth') === 'true';

        return `
            <div class="space-y-2">
                <!-- Mobile Horizontal Scroll Guidance -->
                <div class="sm:hidden flex items-center gap-1.5 px-3 py-2 text-[11px] font-semibold text-slate-500 dark:text-slate-400 bg-slate-100 dark:bg-slate-800 rounded-xl border border-slate-200/70 dark:border-slate-700/60 shadow-xs">
                    <i class="bi bi-arrow-left-right text-blue-500"></i>
                    <span>Swipe horizontally to view full table details</span>
                </div>
                <div class="bg-white dark:bg-slate-800 rounded-2xl shadow-xs border border-slate-200 dark:border-slate-700 overflow-x-auto touch-scroll-x">
                    <table class="w-full text-left border-collapse text-xs sm:text-sm min-w-[760px]">
                        <thead>
                            <tr class="bg-slate-50 dark:bg-slate-700/50 border-b border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400 font-semibold">
                                <th class="py-3 px-4">Sem</th>
                                <th class="py-3 px-4">Course Code</th>
                                <th class="py-3 px-4">Course Title</th>
                                <th class="py-3 px-4">Department</th>
                                <th class="py-3 px-4">Type</th>
                                <th class="py-3 px-4">Question Papers & Schemes</th>
                                <th class="py-3 px-4 text-right">Save</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-100 dark:divide-slate-700/60">
                            ${courses.map(course => {
                                const examPapers = (course.papers || []).filter(p => p.has_qp || p.has_scheme);
                                const firstPaper = (course.papers && course.papers[0]) || { id: course.course_code || 'paper' };
                                const isBookmarked = (course.papers || []).some(p => this.bookmarks.has(p.id));
                                const ctypeClass = `badge-${(course.course_type || 'dsc').toLowerCase()}`;

                                return `
                                    <tr class="hover:bg-slate-50 dark:hover:bg-slate-700/30 transition">
                                        <td class="py-3 px-4 font-bold text-slate-700 dark:text-slate-300">Sem ${course.semester}</td>
                                        <td class="py-3 px-4 font-mono font-bold text-blue-600 dark:text-blue-400 whitespace-nowrap">
                                            <div class="flex items-center gap-1.5 flex-wrap">
                                                <span>${course.course_code || 'N/A'}</span>
                                                ${this.isSignatureCourse(course) ? `
                                                    <span class="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 dark:bg-amber-950/70 dark:text-amber-300 border border-amber-300 dark:border-amber-700" title="Signature Course (College specific syllabus)">
                                                        Signature
                                                    </span>
                                                ` : ''}
                                            </div>
                                        </td>
                                        <td class="py-3 px-4 font-medium text-slate-900 dark:text-slate-100 max-w-xs truncate" title="${course.title}">${course.title}</td>
                                        <td class="py-3 px-4 text-slate-600 dark:text-slate-300">
                                            ${course.parent_dept_name || course.dept_name || ''} ${course.is_minor ? `<span class="text-[10px] bg-pink-100 text-pink-700 px-1.5 py-0.5 rounded font-semibold ml-1">${course.minor_name || course.dept_code}</span>` : ''}
                                        </td>
                                        <td class="py-3 px-4">
                                            <span class="text-[11px] font-semibold px-2 py-0.5 rounded ${ctypeClass}">${course.course_type}</span>
                                        </td>
                                        <td class="py-3 px-4">
                                            <div class="space-y-1.5">
                                                ${examPapers.length > 0 ? examPapers.map(p => {
                                                    const monthYear = this.extractMonthYear(p.exam_name);
                                                    return `
                                                        <div class="flex items-center gap-1.5 flex-wrap">
                                                            <span class="text-[11px] font-semibold text-slate-600 dark:text-slate-300 whitespace-nowrap">${monthYear}:</span>
                                                            ${p.has_qp ? `
                                                                <button onclick="App.previewPaper(this, ${JSON.stringify(p).replace(/"/g, '&quot;')}, 'QP')" class="px-2 py-0.5 text-xs font-semibold rounded bg-blue-600 text-white hover:bg-blue-500 shadow-2xs transition" title="Preview QP">
                                                                    QP
                                                                </button>
                                                                <a href="${p.qp_url}" target="_blank" download class="p-0.5 text-xs text-slate-500 hover:text-blue-600" title="Download QP">
                                                                    <i class="bi bi-download"></i>
                                                                </a>
                                                            ` : ''}
                                                            ${p.has_scheme ? `
                                                                <button onclick="App.previewPaper(this, ${JSON.stringify(p).replace(/"/g, '&quot;')}, 'SCHEME')" class="px-2 py-0.5 text-xs font-semibold rounded bg-emerald-600 text-white hover:bg-emerald-500 shadow-2xs transition" title="Preview Scheme">
                                                                    Scheme
                                                                </button>
                                                                <a href="${p.scheme_url}" target="_blank" download class="p-0.5 text-xs text-slate-500 hover:text-emerald-600" title="Download Scheme">
                                                                    <i class="bi bi-download"></i>
                                                                </a>
                                                            ` : ''}
                                                            ${isAdmin ? `
                                                                <button onclick="App.handleDeletePaper('${p.id}', this)" title="Delete Paper (Admin)" class="p-0.5 text-xs text-rose-500 hover:text-rose-700">
                                                                    <i class="bi bi-trash3"></i>
                                                                </button>
                                                            ` : ''}
                                                        </div>
                                                    `;
                                                }).join('') : '<span class="text-xs text-slate-400 italic">Exam papers awaited</span>'}

                                                ${course.model_papers && course.model_papers.length > 0 ? `
                                                    <div class="flex items-center gap-1.5 flex-wrap pt-1 border-t border-slate-100 dark:border-slate-700/50">
                                                        ${course.model_papers.map(m => `
                                                            <button onclick="App.previewDirect(this, '${m.cdn_url || m.url}', '${m.title.replace(/'/g, "\\'")}', '${course.course_code || ''}')" class="px-2 py-0.5 text-xs font-semibold rounded ${m.paper_type === 'PRACTICAL' ? 'bg-purple-600 hover:bg-purple-500' : 'bg-indigo-600 hover:bg-indigo-500'} text-white shadow-2xs flex items-center gap-1 transition" title="${m.title}">
                                                                <i class="bi ${m.paper_type === 'PRACTICAL' ? 'bi-flask' : 'bi-file-earmark-text'}"></i> ${m.paper_type === 'PRACTICAL' ? 'Model Prac' : 'Model QP'}
                                                            </button>
                                                            <a href="${m.cdn_url || m.url}" target="_blank" download class="p-0.5 text-xs text-slate-500 hover:text-indigo-600" title="Download Model QP">
                                                                <i class="bi bi-download"></i>
                                                            </a>
                                                        `).join('')}
                                                    </div>
                                                ` : ''}

                                                <!-- OFFICIAL SYLLABUS IN TABLE (AFTER MODEL QUESTION PAPER) -->
                                                ${(() => {
                                                    const syl = this.getCourseSyllabus(course);
                                                    if (!syl || !syl.main_syllabus) return '';
                                                    const sylUrl = syl.main_syllabus;
                                                    const sylTitle = `Syllabus - ${syl.program || course.title}`;
                                                    return `
                                                        <div class="pt-1 border-t border-slate-100 dark:border-slate-700/50">
                                                            <button onclick="App.previewDirect(this, '${sylUrl}', '${sylTitle.replace(/'/g, "\\'")}', '${course.course_code || ''}')" class="px-2 py-0.5 text-xs font-semibold rounded bg-emerald-600 hover:bg-emerald-500 text-white shadow-2xs flex items-center gap-1 transition" title="Preview Official Syllabus: ${syl.program}">
                                                                <i class="bi bi-book-half"></i> Syllabus
                                                            </button>
                                                        </div>
                                                    `;
                                                })()}
                                            </div>
                                        </td>
                                        <td class="py-3 px-4 text-right">
                                            <button 
                                                data-bm-id="${firstPaper.id}"
                                                onclick="App.toggleBookmark('${firstPaper.id}')" 
                                                class="px-2.5 py-1 text-xs font-semibold rounded flex items-center gap-1 transition ${
                                                    isBookmarked 
                                                        ? 'bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300' 
                                                        : 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300'
                                                }"
                                            >
                                                <i class="bi ${isBookmarked ? 'bi-star-fill text-amber-500' : 'bi-star'}"></i>
                                                <span>${isBookmarked ? 'Saved' : 'Save'}</span>
                                            </button>
                                        </td>
                                    </tr>
                                `;
                            }).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    },

    renderPaperTable(items) {
        return this.renderGroupedCourseTable(items);
    },

    renderPagination() {
        const container = document.getElementById('paginationControls');
        if (!container) return;

        const totalItems = this.groupedCourses ? this.groupedCourses.length : (this.filteredPapers ? this.filteredPapers.length : 0);
        const totalPages = Math.ceil(totalItems / this.state.pageSize);
        if (totalPages <= 1) {
            container.innerHTML = '';
            return;
        }

        const cur = this.state.currentPage;

        // Mobile compact pagination (< Prev | Page X of Y | Next >)
        let mobileHtml = `
            <div class="flex items-center justify-between sm:hidden w-full px-1 gap-2">
                <button onclick="App.goToPage(${cur - 1})" ${cur === 1 ? 'disabled' : ''} class="flex-1 py-2 text-xs font-semibold rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-50 transition flex items-center justify-center gap-1 shadow-xs min-h-[38px]">
                    <i class="bi bi-chevron-left"></i> Prev
                </button>
                <div class="px-3 py-2 text-xs font-bold text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shrink-0 shadow-xs min-h-[38px] flex items-center justify-center">
                    Page ${cur} of ${totalPages}
                </div>
                <button onclick="App.goToPage(${cur + 1})" ${cur === totalPages ? 'disabled' : ''} class="flex-1 py-2 text-xs font-semibold rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-50 transition flex items-center justify-center gap-1 shadow-xs min-h-[38px]">
                    Next <i class="bi bi-chevron-right"></i>
                </button>
            </div>
        `;

        // Desktop full pagination
        let desktopHtml = `
            <div class="hidden sm:flex items-center justify-center gap-1 sm:gap-2">
                <button onclick="App.goToPage(${cur - 1})" ${cur === 1 ? 'disabled' : ''} class="px-3 py-1.5 text-xs font-medium rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-50 transition min-h-[38px] flex items-center gap-1">
                    <i class="bi bi-chevron-left"></i> Prev
                </button>
        `;

        const maxButtons = 5;
        let startPage = Math.max(1, cur - 2);
        let endPage = Math.min(totalPages, startPage + maxButtons - 1);
        if (endPage - startPage < maxButtons - 1) {
            startPage = Math.max(1, endPage - maxButtons + 1);
        }

        if (startPage > 1) {
            desktopHtml += `<button onclick="App.goToPage(1)" class="w-8 h-8 text-xs font-medium rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 min-h-[38px]">1</button>`;
            if (startPage > 2) desktopHtml += `<span class="px-1 text-slate-400">...</span>`;
        }

        for (let p = startPage; p <= endPage; p++) {
            const isActive = p === cur;
            desktopHtml += `
                <button onclick="App.goToPage(${p})" class="w-8 h-8 text-xs font-semibold rounded-lg ${isActive ? 'bg-blue-600 text-white shadow-xs' : 'bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50'} transition min-h-[38px]">
                    ${p}
                </button>
            `;
        }

        if (endPage < totalPages) {
            if (endPage < totalPages - 1) desktopHtml += `<span class="px-1 text-slate-400">...</span>`;
            desktopHtml += `<button onclick="App.goToPage(${totalPages})" class="w-8 h-8 text-xs font-medium rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 min-h-[38px]">${totalPages}</button>`;
        }

        desktopHtml += `
                <button onclick="App.goToPage(${cur + 1})" ${cur === totalPages ? 'disabled' : ''} class="px-3 py-1.5 text-xs font-medium rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-50 transition min-h-[38px] flex items-center gap-1">
                    Next <i class="bi bi-chevron-right"></i>
                </button>
            </div>
        `;

        container.innerHTML = mobileHtml + desktopHtml;
    },

    goToPage(page) {
        const totalItems = this.groupedCourses ? this.groupedCourses.length : (this.filteredPapers ? this.filteredPapers.length : 0);
        const totalPages = Math.ceil(totalItems / this.state.pageSize);
        if (page < 1 || page > totalPages) return;
        this.state.currentPage = page;
        this.renderPapers();
        this.renderPagination();
        const grid = document.getElementById('papersGrid');
        if (grid) {
            window.scrollTo({ top: grid.offsetTop - 120, behavior: 'smooth' });
        }
    },

    resetFilters() {
        this.setButtonLoading('resetFiltersBtn', true, 'Resetting...');
        setTimeout(() => this.setButtonLoading('resetFiltersBtn', false), 350);

        this.state.searchQuery = '';
        this.state.selectedDept = 'ALL';
        this.state.selectedSemester = 'ALL';
        this.state.selectedCourseType = 'ALL';
        this.state.currentPage = 1;

        const searchInput = document.getElementById('searchInput');
        if (searchInput) searchInput.value = '';
        const clearBtn = document.getElementById('clearSearchBtn');
        if (clearBtn) clearBtn.classList.add('hidden');

        this.setSemester('ALL');
        this.setCourseType('ALL');
        this.setDepartment('ALL');
    },

    // -------------------------------------------------------------
    // DEPARTMENT HIERARCHY & DETAIL VIEW (Sem 1-8 -> Year-Wise)
    // -------------------------------------------------------------

    renderDepartmentsList() {
        const container = document.getElementById('deptCardsGrid');
        const deptSelect = document.getElementById('deptSelect');
        if (!container) return;

        // Ensure strictly alphabetical order (A–Z)
        this.departments.sort((a, b) => a.name.localeCompare(b.name));

        // Filter out departments with zero papers available
        const activeDepts = this.getActiveDepartments();

        // Populate filter dropdown in All Question Papers tab with only departments that have papers
        if (deptSelect) {
            deptSelect.innerHTML = `<option value="ALL">All Departments (${activeDepts.length} Available)</option>` +
                activeDepts.map(d => `<option value="${d.code}">${d.name} (${d.code})</option>`).join('');
        }

        // Apply quick department search query if entered
        let deptsToRender = activeDepts;
        if (this.deptState.deptSearchQuery) {
            const dq = this.deptState.deptSearchQuery.toLowerCase();
            const tokens = dq.split(/\s+/).filter(Boolean);
            deptsToRender = activeDepts.filter(d => {
                if (d.name.toLowerCase().includes(dq) || 
                    d.code.toLowerCase().includes(dq) || 
                    (d.description && d.description.toLowerCase().includes(dq)) ||
                    (d.category && d.category.toLowerCase().includes(dq)) ||
                    (d.minors && d.minors.some(m => m.name.toLowerCase().includes(dq) || m.code.toLowerCase().includes(dq)))) {
                    return true;
                }
                const deptCodes = new Set([d.code, ...(d.majors || []).map(m => m.code), ...(d.minors || []).map(m => m.code)]);
                return this.papers.some(p => 
                    (deptCodes.has(p.parent_dept) || deptCodes.has(p.dept_code)) &&
                    this.matchPaper(p, tokens, dq)
                );
            });
        }

        if (deptsToRender.length === 0) {
            container.innerHTML = `
                <div class="col-span-full py-12 text-center bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-8 shadow-xs">
                    <div class="w-12 h-12 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-400 mx-auto flex items-center justify-center text-lg mb-3">
                        <i class="bi bi-search"></i>
                    </div>
                    <p class="text-base font-semibold text-slate-800 dark:text-slate-100">No departments match "${this.deptState.deptSearchQuery}"</p>
                    <p class="text-xs text-slate-500 mt-1">Try searching by code like MAT, ENG, COM, or department name.</p>
                    <button onclick="App.clearDeptSearch()" class="mt-4 px-3.5 py-1.5 text-xs font-semibold bg-blue-600 text-white rounded-lg shadow-xs transition">
                        Show All Departments
                    </button>
                </div>
            `;
            return;
        }

        const isAdmin = sessionStorage.getItem('mgu_admin_auth') === 'true';

        // Render Cards
        container.innerHTML = deptsToRender.map(d => {
            const deptCodes = new Set([d.code, ...(d.majors || []).map(m => m.code), ...(d.minors || []).map(m => m.code)]);
            const deptPapers = this.papers.filter(p => (deptCodes.has(p.parent_dept) || deptCodes.has(p.dept_code)) && (p.has_files || (p.model_papers && p.model_papers.length > 0)));
            const majors = d.majors || [];
            const minors = d.minors || [];

            // Detect active semesters for this department
            const semCounts = {};
            deptPapers.forEach(p => {
                if (p.semester) semCounts[p.semester] = (semCounts[p.semester] || 0) + 1;
            });
            const activeSems = Object.keys(semCounts).sort((a,b) => a - b);

            const hasMultipleMajors = majors.length > 1;
            const hasMinors = minors.length > 0;
            const hasCollapsible = hasMultipleMajors || hasMinors;

            let collapsibleLabel = '';
            let collapsibleIcon = 'bi-layers';
            let collapsibleBadgeColor = 'text-blue-600 dark:text-blue-400';

            if (hasMultipleMajors && hasMinors) {
                collapsibleLabel = `${majors.length} Majors & ${minors.length} Minors`;
                collapsibleIcon = 'bi-collection';
            } else if (hasMultipleMajors) {
                collapsibleLabel = `${majors.length} Major Disciplines`;
                collapsibleIcon = 'bi-layers';
            } else if (hasMinors) {
                collapsibleLabel = `${minors.length} ${minors.length === 1 ? 'Minor' : 'Minors'}`;
                collapsibleIcon = 'bi-diagram-2';
                collapsibleBadgeColor = 'text-pink-600 dark:text-pink-400';
            }

            return `
                <div onclick="App.openDepartmentView('${d.code}')" data-code="${d.code}" class="dept-card bg-white dark:bg-slate-800 p-5 rounded-2xl border border-slate-200 dark:border-slate-700 hover:border-blue-400 dark:hover:border-blue-600 shadow-xs cursor-pointer transition flex flex-col justify-between group">
                    <div>
                        <div class="flex items-center justify-between gap-2 mb-3">
                            <div class="w-10 h-10 rounded-xl bg-blue-50 dark:bg-blue-900/40 text-blue-600 dark:text-blue-300 flex items-center justify-center text-lg group-hover:scale-105 transition-transform">
                                <i class="bi ${d.icon || 'bi-mortarboard'}"></i>
                            </div>
                            <span class="text-xs font-bold px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 font-mono">
                                ${d.code}
                            </span>
                        </div>
                        <h4 class="font-bold text-slate-900 dark:text-slate-100 text-base mb-1 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                            ${d.name}
                        </h4>
                    </div>

                    <div>
                        <!-- Semesters Badges (Visible for Admin Only) -->
                        ${isAdmin && activeSems.length > 0 ? `
                            <div class="mb-3 pt-2 border-t border-slate-100 dark:border-slate-700/60 flex flex-wrap items-center gap-1">
                                <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400 mr-1">Semesters:</span>
                                ${activeSems.map(s => `
                                    <span class="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300 border border-blue-100 dark:border-blue-900/40">
                                        Sem ${s}
                                    </span>
                                `).join('')}
                            </div>
                        ` : ''}

                        <!-- Collapsible Majors & Minors (Hidden by default, shown on click) -->
                        ${hasCollapsible ? `
                            <details class="group/dept-details my-2.5 border-t border-slate-100 dark:border-slate-700/60 pt-2 [&::-webkit-details-marker]:hidden" onclick="event.stopPropagation();">
                                <summary class="flex items-center justify-between text-xs font-semibold text-slate-500 dark:text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 cursor-pointer list-none select-none py-1 px-1.5 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700/50 transition">
                                    <span class="flex items-center gap-1.5 ${collapsibleBadgeColor}">
                                        <i class="bi ${collapsibleIcon}"></i>
                                        <span>${collapsibleLabel}</span>
                                    </span>
                                    <i class="bi bi-chevron-down text-[10px] text-slate-400 transition-transform duration-200 group-open/dept-details:rotate-180"></i>
                                </summary>

                                <div class="space-y-2.5 pt-2 pb-1 px-1">
                                    ${hasMultipleMajors ? `
                                        <div>
                                            <div class="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">${majors.length} Major Disciplines:</div>
                                            <div class="flex flex-wrap gap-1.5">
                                                ${majors.map(m => `
                                                    <span class="text-xs font-semibold px-2 py-0.5 rounded-lg bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300 border border-blue-100 dark:border-blue-900/40 shadow-2xs" title="${m.name} (${m.code})">
                                                        ${m.name} (${m.code})
                                                    </span>
                                                `).join('')}
                                            </div>
                                        </div>
                                    ` : ''}

                                    ${hasMinors ? `
                                        <div>
                                            <div class="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">${minors.length} ${minors.length === 1 ? 'Minor' : 'Minors'}:</div>
                                            <div class="flex flex-wrap gap-1.5">
                                                ${minors.map(m => `
                                                    <span class="text-xs font-semibold px-2.5 py-1 rounded-lg bg-pink-50 text-pink-700 dark:bg-pink-950/40 dark:text-pink-300 border border-pink-100 dark:border-pink-900/40 shadow-2xs" title="${m.name} (${m.code})">
                                                        ${m.name} (${m.code})
                                                    </span>
                                                `).join('')}
                                            </div>
                                        </div>
                                    ` : ''}
                                </div>
                            </details>
                        ` : ''}

                        <div class="flex items-center justify-between text-xs font-semibold text-blue-600 dark:text-blue-400 pt-2.5 border-t border-slate-100 dark:border-slate-700/60">
                            <span>${deptPapers.length} Question Papers</span>
                            <span class="flex items-center gap-1 group-hover:translate-x-1 transition-transform">
                                Explore <i class="bi bi-arrow-right"></i>
                            </span>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    },

    openDepartmentView(deptCode, targetSem = null, updateHash = true) {
        const dept = this.departments.find(d => d.code.toUpperCase() === deptCode.toUpperCase());
        if (!dept) {
            this.showDepartmentsList(false);
            return;
        }

        // Save scroll position of the departments list before opening
        const deptList = document.getElementById('deptListContainer');
        if (deptList && !deptList.classList.contains('hidden')) {
            this.lastDeptListScrollY = window.scrollY;
        }

        const normalizedSem = targetSem !== null && targetSem !== undefined 
            ? (String(targetSem).toUpperCase() === 'ALL' ? 'ALL' : parseInt(targetSem, 10)) 
            : null;

        this.deptState.activeDept = dept;
        this.deptState.selectedSemester = normalizedSem;
        this.deptState.searchQuery = '';
        this.deptState.signatureExpanded = false;

        const targetHash = normalizedSem !== null ? `#/department/${dept.code}/${normalizedSem}` : `#/department/${dept.code}`;
        if (updateHash && window.location.hash !== targetHash) {
            this.currentRoute = targetHash;
            if (window.location.hash.startsWith(`#/department/${dept.code}`)) {
                history.replaceState(null, '', targetHash);
            } else {
                window.location.hash = targetHash;
            }
        } else {
            this.currentRoute = targetHash;
        }

        // Switch to detail view and hide hero & homepage tabs so it acts as a dedicated page
        document.getElementById('heroSection')?.classList.add('hidden');
        document.getElementById('mainNavTabsContainer')?.classList.add('hidden');
        document.getElementById('deptListContainer')?.classList.add('hidden');
        document.getElementById('papersSection')?.classList.add('hidden');
        document.getElementById('filterControlsSection')?.classList.add('hidden');
        document.getElementById('adminPageSection')?.classList.add('hidden');

        document.getElementById('departmentsSection')?.classList.remove('hidden');
        const detailContainer = document.getElementById('deptDetailContainer');
        if (detailContainer) detailContainer.classList.remove('hidden');

        const majors = dept.majors || [];
        const minors = dept.minors || [];
        const deptCodes = new Set([dept.code, ...majors.map(m => m.code), ...minors.map(m => m.code)]);
        const allDeptPapers = this.papers.filter(p => (deptCodes.has(p.parent_dept) || deptCodes.has(p.dept_code)) && (p.has_files || (p.model_papers && p.model_papers.length > 0)));

        // Header Banner (Without curriculum description tags)
        const headerEl = document.getElementById('deptDetailHeader');
        if (headerEl) {
            headerEl.innerHTML = `
                <div class="flex flex-wrap items-center justify-between gap-4">
                    <div class="flex items-start gap-4">
                        <div class="w-12 h-12 rounded-2xl bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300 flex items-center justify-center text-2xl shrink-0">
                            <i class="bi ${dept.icon || 'bi-mortarboard'}"></i>
                        </div>
                        <div>
                            <div class="flex items-center gap-2">
                                <h3 class="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white">
                                    ${dept.name}
                                </h3>
                                <span class="font-mono text-xs font-bold px-2 py-0.5 rounded bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-900/40">
                                    ${dept.code}
                                </span>
                            </div>
                            ${majors.length > 1 ? `
                                <div class="flex flex-wrap items-center gap-1.5 mt-2">
                                    <span class="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Major Disciplines:</span>
                                    ${majors.map(m => `
                                        <span class="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-900/40">
                                            ${m.name} (${m.code})
                                        </span>
                                    `).join('')}
                                </div>
                            ` : ''}
                            ${minors.length > 0 ? `
                                <div class="flex flex-wrap items-center gap-1.5 mt-2">
                                    <span class="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Minor Programmes:</span>
                                    ${minors.map(m => `
                                        <span class="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-pink-50 dark:bg-pink-950/40 text-pink-700 dark:text-pink-300 border border-pink-200 dark:border-pink-900/40">
                                            ${m.name} (${m.code})
                                        </span>
                                    `).join('')}
                                </div>
                            ` : ''}
                        </div>
                    </div>
                    <div class="flex items-center gap-3">
                        <div class="text-right">
                            <div class="text-2xl font-bold font-mono text-blue-600 dark:text-blue-400">${allDeptPapers.length}</div>
                            <div class="text-[11px] text-slate-500 uppercase tracking-wider">Available FYUGP Papers</div>
                        </div>
                    </div>
                </div>

                <!-- OFFICIAL DEPARTMENT & MAJOR PROGRAMME SYLLABUS BANNER -->
                ${(() => {
                    const deptSyllabus = this.getDeptSyllabus(dept.code, dept.name);
                    if (!deptSyllabus || !deptSyllabus.main_syllabus) return '';
                    return `
                        <div class="mt-4 p-3.5 sm:p-4 rounded-2xl bg-gradient-to-r from-emerald-50 via-teal-50/70 to-emerald-50/40 dark:from-emerald-950/40 dark:via-teal-950/30 dark:to-emerald-950/20 border border-emerald-200 dark:border-emerald-800/60 shadow-xs flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                            <div class="flex items-center gap-3 min-w-0">
                                <div class="w-10 h-10 rounded-xl bg-emerald-600 text-white flex items-center justify-center text-xl shrink-0 shadow-xs">
                                    <i class="bi bi-book-half"></i>
                                </div>
                                <div class="min-w-0">
                                    <div class="flex items-center gap-2 flex-wrap">
                                        <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-600 text-white uppercase tracking-wider">
                                            Official MGU FYUGP Syllabus
                                        </span>
                                        <span class="text-xs font-bold text-emerald-900 dark:text-emerald-200 truncate">
                                            ${deptSyllabus.program}
                                        </span>
                                    </div>
                                    <div class="text-[11px] text-slate-600 dark:text-slate-300 mt-0.5">
                                        Complete Department Programme Syllabus & Regulations from cap.mgu.ac.in
                                    </div>
                                </div>
                            </div>

                            <div class="flex flex-wrap items-center gap-2 shrink-0">
                                <button onclick="App.previewDirect(this, '${deptSyllabus.main_syllabus}', 'Official Syllabus - ${deptSyllabus.program}', '${dept.code}')" class="px-3.5 py-1.5 rounded-xl text-xs font-bold bg-emerald-600 hover:bg-emerald-500 text-white shadow-xs hover:shadow-md transition flex items-center gap-1.5 cursor-pointer" title="Preview Official MGU Programme Syllabus PDF">
                                    <i class="bi bi-eye"></i> View Complete Syllabus
                                </button>
                                <a href="${deptSyllabus.main_syllabus}" target="_blank" rel="noopener" class="p-1.5 rounded-xl bg-white dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700 shadow-2xs transition flex items-center gap-1" title="Open Syllabus on MGU Portal">
                                    <i class="bi bi-box-arrow-up-right text-xs"></i>
                                </a>
                            </div>
                        </div>
                    `;
                })()}
            `;
        }

        const breadcrumbsEl = document.getElementById('deptBreadcrumbs');
        const backBtnText = document.getElementById('deptBackBtnText');
        const selectorView = document.getElementById('deptSemestersSelectorView');
        const papersView = document.getElementById('deptSemesterPapersView');

        if (normalizedSem === null) {
            // Mode 1: Landing on Department -> Ask which semester to proceed
            document.title = `${dept.name} (${dept.code}) - Select Semester | MGU FYUGP`;

            if (selectorView) selectorView.classList.remove('hidden');
            if (papersView) papersView.classList.add('hidden');
            if (backBtnText) backBtnText.textContent = 'Back to Departments';

            if (breadcrumbsEl) {
                breadcrumbsEl.innerHTML = `
                    <a href="#/departments" onclick="App.showDepartmentsList(true); return false;" class="text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1 font-medium">
                        <i class="bi bi-grid text-xs"></i>
                        <span>Departments</span>
                    </a>
                    <i class="bi bi-chevron-right text-[10px] text-slate-400"></i>
                    <span class="text-slate-900 dark:text-white font-bold truncate max-w-[160px] sm:max-w-none">${dept.name}</span>
                    <span class="font-mono text-[11px] font-bold px-1.5 py-0.2 rounded bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">${dept.code}</span>
                `;
            }

            this.renderDeptSemestersSelector();
        } else {
            // Mode 2: Dedicated Semester Page
            const semDisplay = normalizedSem === 'ALL' ? 'All Semesters' : `Semester ${normalizedSem}`;
            document.title = `${dept.name} - ${semDisplay} Papers | MGU FYUGP`;

            if (selectorView) selectorView.classList.add('hidden');
            if (papersView) papersView.classList.remove('hidden');
            if (backBtnText) backBtnText.textContent = 'Back to Departments';

            if (breadcrumbsEl) {
                breadcrumbsEl.innerHTML = `
                    <a href="#/departments" onclick="App.showDepartmentsList(true); return false;" class="text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1 font-medium">
                        <i class="bi bi-grid text-xs"></i>
                        <span>Departments</span>
                    </a>
                    <i class="bi bi-chevron-right text-[10px] text-slate-400"></i>
                    <a href="#/department/${dept.code}" onclick="App.openDepartmentView('${dept.code}', null, true); return false;" class="text-blue-600 dark:text-blue-400 hover:underline font-medium">
                        ${dept.name} (${dept.code})
                    </a>
                    <i class="bi bi-chevron-right text-[10px] text-slate-400"></i>
                    <span class="text-slate-900 dark:text-white font-bold">${semDisplay}</span>
                `;
            }

            // Reset in-department paper search input
            const deptPaperSearch = document.getElementById('deptPaperSearchInput');
            if (deptPaperSearch) deptPaperSearch.value = '';

            this.renderDeptSemesterTabs();
            this.renderDeptSemesterPapers();
        }

        window.scrollTo({ top: 0, behavior: 'instant' });
    },

    renderDeptSemesterTabs() {
        const tabsContainer = document.getElementById('deptSemesterTabs');
        if (!tabsContainer || !this.deptState.activeDept) return;

        const dept = this.deptState.activeDept;
        const deptCodes = new Set([dept.code, ...(dept.majors || []).map(m => m.code), ...(dept.minors || []).map(m => m.code)]);
        const allDeptPapers = this.papers.filter(p => (deptCodes.has(p.parent_dept) || deptCodes.has(p.dept_code)) && (p.has_files || (p.model_papers && p.model_papers.length > 0)));

        let html = '';

        // 1. "All Semesters" Tab Button
        const isAllSelected = this.deptState.selectedSemester === 'ALL';
        html += `
            <button 
                onclick="App.selectDeptSemester('ALL')" 
                class="px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 transition shrink-0 ${
                    isAllSelected 
                        ? 'bg-blue-600 text-white shadow-sm' 
                        : 'bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-600'
                }"
            >
                <span>All Semesters</span>
                <span class="text-[10px] px-1.5 py-0.2 rounded-full ${isAllSelected ? 'bg-white/20 text-white' : 'bg-slate-200 dark:bg-slate-600 text-slate-600 dark:text-slate-300'} font-bold">
                    ${allDeptPapers.length}
                </span>
            </button>
        `;

        // 2. Semester 1 to 8 Buttons
        for (let s = 1; s <= 8; s++) {
            const count = allDeptPapers.filter(p => p.semester === s).length;
            const isSelected = this.deptState.selectedSemester === s;
            html += `
                <button 
                    onclick="App.selectDeptSemester(${s})" 
                    class="px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 transition shrink-0 ${
                        isSelected 
                            ? 'bg-blue-600 text-white shadow-sm' 
                            : 'bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-600'
                    }"
                >
                    <span>Sem ${s}</span>
                    <span class="text-[10px] px-1.5 py-0.2 rounded-full ${isSelected ? 'bg-white/20 text-white' : 'bg-slate-200 dark:bg-slate-600 text-slate-600 dark:text-slate-300'} font-bold">
                        ${count}
                    </span>
                </button>
            `;
        }

        tabsContainer.innerHTML = html;
    },

    selectDeptSemester(sem) {
        if (!this.deptState.activeDept) return;
        this.openDepartmentView(this.deptState.activeDept.code, sem, true);
    },

    renderDeptSemesterPapers() {
        const container = document.getElementById('deptYearWisePapersContainer');
        const countBadge = document.getElementById('deptPaperCountBadge');
        if (!container || !this.deptState.activeDept) return;

        const dept = this.deptState.activeDept;
        const sem = this.deptState.selectedSemester;
        const deptCodes = new Set([dept.code, ...(dept.majors || []).map(m => m.code), ...(dept.minors || []).map(m => m.code)]);
        const isAdmin = sessionStorage.getItem('mgu_admin_auth') === 'true';

        // Filter papers for this department
        let semesterPapers = this.papers.filter(p => 
            (deptCodes.has(p.parent_dept) || deptCodes.has(p.dept_code)) && 
            (p.has_files || (p.model_papers && p.model_papers.length > 0))
        );

        // Filter specific semester if not 'ALL'
        if (sem !== 'ALL') {
            semesterPapers = semesterPapers.filter(p => p.semester === sem);
        }

        // Apply in-department search query if active
        if (this.deptState.searchQuery) {
            const tokens = this.deptState.searchQuery.toLowerCase().split(/\s+/).filter(Boolean);
            semesterPapers = semesterPapers.filter(p => this.matchPaper(p, tokens, this.deptState.searchQuery));
        }

        // Separate signature courses from standard (core/major/minor) papers
        const signaturePapers = semesterPapers.filter(p => this.isSignatureCourse(p));
        const standardPapers = semesterPapers.filter(p => !this.isSignatureCourse(p));

        if (countBadge) {
            if (signaturePapers.length > 0) {
                countBadge.textContent = `Showing ${standardPapers.length} core/minor papers + ${signaturePapers.length} signature`;
            } else {
                countBadge.textContent = `Showing ${semesterPapers.length} question papers`;
            }
        }

        if (semesterPapers.length === 0) {
            container.innerHTML = `
                <div class="py-16 text-center bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-8 shadow-xs">
                    <div class="w-14 h-14 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-400 mx-auto flex items-center justify-center text-xl mb-3">
                        <i class="bi bi-folder2-open"></i>
                    </div>
                    <h4 class="text-base font-bold text-slate-800 dark:text-slate-100">
                        ${sem === 'ALL' ? 'No Question Papers Match Query' : `No Question Papers Found for Semester ${sem}`}
                    </h4>
                    <p class="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-sm mx-auto">
                        ${this.deptState.searchQuery 
                            ? `Try clearing your search query "${this.deptState.searchQuery}".` 
                            : `Mahatma Gandhi University has not released examination schemes for Semester ${sem} in ${dept.name} yet.`}
                    </p>
                    <div class="mt-4 flex flex-wrap items-center justify-center gap-2">
                        ${this.deptState.searchQuery ? `
                            <button onclick="App.clearDeptPaperSearch()" class="px-3.5 py-1.5 bg-slate-600 hover:bg-slate-500 text-white rounded-lg text-xs font-semibold shadow-xs">Clear Search</button>
                        ` : ''}
                        <button onclick="App.openFeedbackModal('report', '${dept.code}', '${sem === 'ALL' ? '1' : sem}')" class="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold shadow-xs flex items-center gap-1.5">
                            <i class="bi bi-flag-fill"></i> Report Missing Paper for ${dept.code}
                        </button>
                    </div>
                </div>
            `;
            return;
        }

        // Partition standard papers into Major/Core Papers vs Minor Papers
        // Note: Signature courses are strictly excluded from major and minor sections!
        const majorPapers = standardPapers.filter(p => !p.is_minor);
        const minorPapers = standardPapers.filter(p => p.is_minor);

        let sectionsHtml = '';

        // 1. Major & Core Programmes Section (Grouped by course and partitioned by dept_code if multi-major)
        if (majorPapers.length > 0) {
            // Build map of major code -> major name from dept.majors
            const majorInfoMap = new Map();
            (dept.majors || []).forEach(m => {
                majorInfoMap.set(m.code, m.name);
            });

            // Group major papers by dept_code (fallback to dept.code)
            const papersByMajorCode = new Map();
            majorPapers.forEach(p => {
                const mCode = p.dept_code || dept.code;
                if (!papersByMajorCode.has(mCode)) {
                    papersByMajorCode.set(mCode, []);
                }
                papersByMajorCode.get(mCode).push(p);
            });

            const distinctMajorCodes = Array.from(papersByMajorCode.keys());
            const isMultiMajor = (dept.majors && dept.majors.length > 1) || distinctMajorCodes.length > 1;

            if (isMultiMajor && distinctMajorCodes.length > 1) {
                // Multi-Major Department (e.g. Performing Arts, Music, Sanskrit (Special)): separate each dept code with dividers
                sectionsHtml += `
                    <div class="space-y-8">
                        <div class="flex items-center justify-between border-b border-slate-200 dark:border-slate-700 pb-2">
                            <div class="flex items-center gap-2">
                                <span class="w-2.5 h-2.5 rounded-full bg-blue-600"></span>
                                <h4 class="text-base sm:text-lg font-bold text-slate-900 dark:text-white">
                                    Major Programmes (${distinctMajorCodes.length} Disciplines)
                                </h4>
                                <span class="text-xs font-semibold px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/50 text-blue-800 dark:text-blue-300">
                                    ${majorPapers.length} Papers
                                </span>
                            </div>
                            <span class="text-xs text-slate-400 font-medium">
                                ${isAdmin ? (sem === 'ALL' ? 'All Semesters' : `Semester ${sem}`) : ''}
                            </span>
                        </div>
                `;

                // Order major codes by order in dept.majors, then alphabetically
                const definedCodes = (dept.majors || []).map(m => m.code);
                distinctMajorCodes.sort((a, b) => {
                    const idxA = definedCodes.indexOf(a);
                    const idxB = definedCodes.indexOf(b);
                    if (idxA !== -1 && idxB !== -1) return idxA - idxB;
                    if (idxA !== -1) return -1;
                    if (idxB !== -1) return 1;
                    return a.localeCompare(b);
                }).forEach((mCode, index) => {
                    const pList = papersByMajorCode.get(mCode);
                    const grouped = this.groupPapersByCourse(pList);
                    const mName = majorInfoMap.get(mCode) || (pList[0] && pList[0].dept_name) || mCode;

                    sectionsHtml += `
                        <div class="major-code-block space-y-4 ${index > 0 ? 'pt-6 border-t-2 border-slate-200 dark:border-slate-700' : ''}">
                            <div class="flex flex-wrap items-center justify-between gap-3 bg-slate-50 dark:bg-slate-700/40 p-3.5 rounded-2xl border border-slate-200/80 dark:border-slate-600/60 shadow-2xs">
                                <div class="flex items-center gap-2.5">
                                    <div class="w-8 h-8 rounded-lg bg-blue-600 text-white flex items-center justify-center text-xs font-bold font-mono shadow-xs">
                                        ${mCode}
                                    </div>
                                    <div>
                                        <div class="flex items-center gap-2">
                                            <h5 class="text-sm sm:text-base font-bold text-slate-900 dark:text-white">
                                                ${mName}
                                            </h5>
                                            <span class="font-mono text-xs font-bold px-2 py-0.5 rounded bg-blue-100 dark:bg-blue-950/60 text-blue-800 dark:text-blue-300 border border-blue-200 dark:border-blue-900/40">
                                                ${mCode}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                                <div class="flex items-center gap-2">
                                    ${(() => {
                                        const mSyllabus = this.getDeptSyllabus(mCode, mName);
                                        if (!mSyllabus || !mSyllabus.main_syllabus) return '';
                                        return `
                                            <button onclick="App.previewDirect(this, '${mSyllabus.main_syllabus}', 'Official Syllabus - ${mSyllabus.program}', '${mCode}')" class="px-2.5 py-1 text-xs font-semibold rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white shadow-2xs flex items-center gap-1 transition" title="View ${mName} Discipline Syllabus">
                                                <i class="bi bi-book-half"></i> Discipline Syllabus
                                            </button>
                                        `;
                                    })()}
                                    <span class="text-xs font-semibold px-2.5 py-1 rounded-full bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700 shadow-2xs">
                                        ${grouped.length} ${grouped.length === 1 ? 'Course' : 'Courses'} (${pList.length} ${pList.length === 1 ? 'Paper' : 'Papers'})
                                    </span>
                                </div>
                            </div>

                            <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
                                ${grouped.map(course => this.renderGroupedCourseCard(course)).join('')}
                            </div>
                        </div>
                    `;
                });

                sectionsHtml += `</div>`;
            } else {
                // Single Major Department
                const groupedMajor = this.groupPapersByCourse(majorPapers);
                sectionsHtml += `
                    <div class="space-y-4">
                        <div class="flex flex-wrap items-center justify-between border-b border-slate-200 dark:border-slate-700 pb-2 gap-2">
                            <div class="flex items-center gap-2">
                                <span class="w-2.5 h-2.5 rounded-full bg-blue-600"></span>
                                <h4 class="text-base sm:text-lg font-bold text-slate-900 dark:text-white">
                                    Major & Core Programmes
                                </h4>
                                <span class="text-xs font-semibold px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/50 text-blue-800 dark:text-blue-300">
                                    ${groupedMajor.length} Courses (${majorPapers.length} Papers)
                                </span>
                            </div>
                            <div class="flex items-center gap-2">
                                ${(() => {
                                    const deptSyllabus = this.getDeptSyllabus(dept.code, dept.name);
                                    if (!deptSyllabus || !deptSyllabus.main_syllabus) return '';
                                    return `
                                        <button onclick="App.previewDirect(this, '${deptSyllabus.main_syllabus}', 'Official Syllabus - ${deptSyllabus.program}', '${dept.code}')" class="px-2.5 py-1 text-xs font-semibold rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white shadow-2xs flex items-center gap-1 transition" title="View Major Discipline Syllabus">
                                            <i class="bi bi-book-half"></i> Major Syllabus
                                        </button>
                                    `;
                                })()}
                                <span class="text-xs text-slate-400 font-medium">
                                    ${isAdmin ? (sem === 'ALL' ? 'All Semesters' : `Semester ${sem}`) : ''}
                                </span>
                            </div>
                        </div>

                        <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
                            ${groupedMajor.map(course => this.renderGroupedCourseCard(course)).join('')}
                        </div>
                    </div>
                `;
            }
        }

        // 2. Minor Headings and Minor Papers Section (Grouped by course)
        const deptMinors = dept.minors || [];
        const seenMinors = new Set();
        const minorsList = [];

        deptMinors.forEach(m => {
            seenMinors.add(m.code);
            minorsList.push({ code: m.code, name: m.name });
        });

        // Also detect minor programs from minor papers belonging to this department
        minorPapers.forEach(p => {
            const mCode = p.dept_code;
            if (mCode && !seenMinors.has(mCode)) {
                seenMinors.add(mCode);
                minorsList.push({ code: mCode, name: p.minor_name || p.dept_name || mCode });
            }
        });

        if (minorsList.length > 0) {
            const minorSectionsHtml = minorsList.map(minor => {
                const pForMinor = minorPapers.filter(p => 
                    p.dept_code === minor.code || 
                    (p.course_code && p.course_code.includes(minor.code))
                );

                if (pForMinor.length === 0) {
                    return '';
                }

                const groupedMinor = this.groupPapersByCourse(pForMinor);

                return `
                    <div class="minor-section bg-gradient-to-br from-pink-50/70 via-white to-purple-50/40 dark:from-pink-950/20 dark:via-slate-800 dark:to-purple-950/20 p-5 sm:p-6 rounded-2xl border border-pink-200/80 dark:border-pink-900/40 shadow-xs space-y-4">
                        <div class="flex flex-wrap items-center justify-between gap-3 border-b border-pink-200/60 dark:border-pink-900/40 pb-3">
                            <div class="flex items-center gap-3">
                                <div class="w-10 h-10 rounded-xl bg-pink-100 dark:bg-pink-900/60 text-pink-700 dark:text-pink-300 flex items-center justify-center text-lg font-bold shadow-2xs">
                                    <i class="bi bi-bookmark-star-fill"></i>
                                </div>
                                <div>
                                    <div class="flex items-center gap-2">
                                        <h4 class="text-base sm:text-lg font-bold text-slate-900 dark:text-white">
                                            Minor: ${minor.name}
                                        </h4>
                                        <span class="font-mono text-xs font-bold px-2 py-0.5 rounded-full bg-pink-100 dark:bg-pink-900/70 text-pink-800 dark:text-pink-200 border border-pink-200 dark:border-pink-800">
                                            ${minor.code}
                                        </span>
                                    </div>
                                </div>
                            </div>
                            <span class="text-xs font-semibold px-2.5 py-1 rounded-full bg-white dark:bg-slate-800 text-pink-700 dark:text-pink-300 border border-pink-200 dark:border-pink-800 shadow-2xs">
                                ${groupedMinor.length} Courses (${pForMinor.length} Papers)
                            </span>
                        </div>

                        <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
                            ${groupedMinor.map(course => this.renderGroupedCourseCard(course)).join('')}
                        </div>
                    </div>
                `;
            }).filter(Boolean).join('');

            if (minorSectionsHtml) {
                sectionsHtml += `
                    <div class="pt-2 space-y-5">
                        <div class="flex items-center gap-2 border-b border-pink-200 dark:border-pink-900/50 pb-2">
                            <i class="bi bi-stars text-pink-600 dark:text-pink-400"></i>
                            <h4 class="text-base font-bold text-slate-900 dark:text-white uppercase tracking-wider text-xs">
                                Minors
                            </h4>
                        </div>
                        ${minorSectionsHtml}
                    </div>
                `;
            }
        }

        // 3. Signature Courses Section (College-specific autonomous signature courses ending in A01, A02, A03, etc.)
        if (signaturePapers.length > 0) {
            const groupedSignature = this.groupPapersByCourse(signaturePapers);
            const isExpanded = Boolean(this.deptState.signatureExpanded);

            if (!sectionsHtml) {
                sectionsHtml = `
                    <div class="p-4 sm:p-5 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 text-center mb-6">
                        <p class="text-xs text-slate-500 dark:text-slate-400">
                            No common university core/major examination papers released for ${sem === 'ALL' ? 'this department' : `Semester ${sem}`} yet. College signature courses are available below.
                        </p>
                    </div>
                `;
            }

            sectionsHtml += `
                <div class="signature-courses-section mt-8 pt-6 border-t-2 border-dashed border-amber-300/80 dark:border-amber-900/60">
                    <div class="bg-gradient-to-r from-amber-50/80 via-white to-amber-50/40 dark:from-amber-950/20 dark:via-slate-800 dark:to-amber-950/10 rounded-2xl border border-amber-200/90 dark:border-amber-900/50 p-4 sm:p-5 shadow-xs transition">
                        <button type="button" 
                                onclick="App.toggleDeptSignatureDropdown()" 
                                id="signatureDropdownBtn"
                                class="w-full flex items-center justify-between gap-3 text-left focus:outline-hidden group cursor-pointer"
                                aria-expanded="${isExpanded ? 'true' : 'false'}">
                            <div class="flex items-center gap-3 min-w-0">
                                <div class="w-10 h-10 rounded-xl bg-amber-100 dark:bg-amber-900/60 text-amber-700 dark:text-amber-300 flex items-center justify-center text-lg shrink-0 shadow-2xs group-hover:scale-105 transition-transform">
                                    <i class="bi bi-pen-fill"></i>
                                </div>
                                <div>
                                    <div class="flex items-center gap-2 flex-wrap">
                                        <h4 class="text-base font-bold text-slate-900 dark:text-white group-hover:text-amber-600 dark:group-hover:text-amber-400 transition-colors">
                                            Show Signature Courses
                                        </h4>
                                        <span class="text-xs font-bold px-2.5 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900/70 text-amber-800 dark:text-amber-200 border border-amber-200 dark:border-amber-800 font-mono">
                                            ${groupedSignature.length} ${groupedSignature.length === 1 ? 'Course' : 'Courses'} (${signaturePapers.length} ${signaturePapers.length === 1 ? 'Paper' : 'Papers'})
                                        </span>
                                    </div>
                                    <p class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                                        College Specific Signature Courses
                                    </p>
                                </div>
                            </div>
                            <div class="flex items-center gap-2 shrink-0">
                                <span id="signatureDropdownLabel" class="text-xs font-semibold text-amber-700 dark:text-amber-400 hidden sm:inline">
                                    ${isExpanded ? 'Click to hide' : 'Click to show'}
                                </span>
                                <div id="signatureDropdownChevron" class="w-8 h-8 rounded-lg bg-amber-100/90 dark:bg-amber-900/50 text-amber-700 dark:text-amber-300 flex items-center justify-center text-sm transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}">
                                    <i class="bi bi-chevron-down"></i>
                                </div>
                            </div>
                        </button>

                        <div id="signatureDropdownContent" class="${isExpanded ? '' : 'hidden'} mt-5 pt-5 border-t border-amber-200/70 dark:border-amber-900/40 space-y-4">
                            <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
                                ${groupedSignature.map(course => this.renderGroupedCourseCard(course)).join('')}
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }

        const reportPromptBanner = `
            <div class="mt-8 p-4 rounded-2xl bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-slate-800 dark:to-slate-800/80 border border-blue-200/80 dark:border-slate-700 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs">
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-xl bg-blue-100 dark:bg-blue-900/50 text-blue-600 dark:text-blue-300 flex items-center justify-center text-lg shrink-0">
                        <i class="bi bi-flag-fill"></i>
                    </div>
                    <div>
                        <div class="font-bold text-slate-900 dark:text-white">Exam already conducted but paper or scheme missing?</div>
                        <div class="text-slate-500 dark:text-slate-400">Report missing papers or schemes for ${dept.name} and the admin will source and upload them.</div>
                    </div>
                </div>
                <button onclick="App.openFeedbackModal('report', '${dept.code}', '${sem === 'ALL' ? '' : sem}')" class="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl font-semibold shadow-xs shrink-0 flex items-center gap-1.5 transition">
                    <i class="bi bi-send-plus"></i> Report Missing Paper
                </button>
            </div>
        `;

        container.innerHTML = (sectionsHtml ? sectionsHtml + reportPromptBanner : '') || `
            <div class="py-12 text-center text-slate-400 text-xs">
                No papers found matching the current criteria.
            </div>
        `;
    },

    toggleDeptSignatureDropdown() {
        const content = document.getElementById('signatureDropdownContent');
        const chevron = document.getElementById('signatureDropdownChevron');
        const label = document.getElementById('signatureDropdownLabel');
        const btn = document.getElementById('signatureDropdownBtn');
        if (!content) return;

        const isHidden = content.classList.contains('hidden');
        if (isHidden) {
            content.classList.remove('hidden');
            if (chevron) chevron.classList.add('rotate-180');
            if (label) label.textContent = 'Click to hide';
            if (btn) btn.setAttribute('aria-expanded', 'true');
            this.deptState.signatureExpanded = true;
        } else {
            content.classList.add('hidden');
            if (chevron) chevron.classList.remove('rotate-180');
            if (label) label.textContent = 'Click to show';
            if (btn) btn.setAttribute('aria-expanded', 'false');
            this.deptState.signatureExpanded = false;
        }
    },

    handleDeptBackClick() {
        this.showDepartmentsList(true);
    },

    backToDepartmentSemesters() {
        if (this.deptState.activeDept) {
            this.openDepartmentView(this.deptState.activeDept.code, null, true);
        } else {
            this.showDepartmentsList(true);
        }
    },

    backToDepartmentsList() {
        this.showDepartmentsList(true);
    },

    renderDeptSemestersSelector() {
        const grid = document.getElementById('deptSemestersGrid');
        if (!grid || !this.deptState.activeDept) return;

        const dept = this.deptState.activeDept;
        const deptCodes = new Set([dept.code, ...(dept.majors || []).map(m => m.code), ...(dept.minors || []).map(m => m.code)]);
        const allDeptPapers = this.papers.filter(p => (deptCodes.has(p.parent_dept) || deptCodes.has(p.dept_code)) && (p.has_files || (p.model_papers && p.model_papers.length > 0)));

        let html = '';

        for (let s = 1; s <= 8; s++) {
            const semPapers = allDeptPapers.filter(p => p.semester === s);
            const semCourses = this.groupPapersByCourse(semPapers);

            html += `
                <div onclick="App.openDepartmentView('${dept.code}', ${s}, true)" class="bg-white dark:bg-slate-800 rounded-2xl p-5 border border-slate-200 dark:border-slate-700 hover:border-blue-500 dark:hover:border-blue-400 shadow-xs hover:shadow-md cursor-pointer transition flex flex-col justify-between group">
                    <div>
                        <div class="flex items-center justify-between gap-2 mb-3">
                            <div class="w-11 h-11 rounded-xl bg-blue-50 dark:bg-blue-900/40 text-blue-600 dark:text-blue-300 flex items-center justify-center font-extrabold text-base font-mono group-hover:scale-105 transition-transform">
                                S${s}
                            </div>
                            ${semPapers.length > 0 ? `
                                <span class="px-2.5 py-1 text-xs font-bold rounded-full bg-blue-50 dark:bg-blue-950/50 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-900/40 font-mono">
                                    ${semPapers.length} Papers
                                </span>
                            ` : `
                                <span class="px-2 py-0.5 text-[10px] font-medium rounded-full bg-slate-100 dark:bg-slate-700 text-slate-400">
                                    No Papers
                                </span>
                            `}
                        </div>
                        <h4 class="text-base font-bold text-slate-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                            Semester ${s}
                        </h4>
                        ${semCourses.length > 0 ? `
                            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1 font-medium">
                                ${semCourses.length} ${semCourses.length === 1 ? 'course' : 'courses'} available
                            </p>
                        ` : `
                            <p class="text-xs text-slate-400 dark:text-slate-500 mt-1">
                                No courses available
                            </p>
                        `}
                    </div>

                    <div class="mt-5 pt-3 border-t border-slate-100 dark:border-slate-700/60 flex items-center justify-between text-xs font-semibold ${semPapers.length > 0 ? 'text-blue-600 dark:text-blue-400' : 'text-slate-400'}">
                        <span>${semPapers.length > 0 ? 'Proceed to Papers' : 'Explore Semester'}</span>
                        <i class="bi bi-arrow-right transition-transform group-hover:translate-x-1"></i>
                    </div>
                </div>
            `;
        }

        // 9th Card: All Semesters (1–8)
        html += `
            <div onclick="App.openDepartmentView('${dept.code}', 'ALL', true)" class="bg-slate-50/70 dark:bg-slate-800/80 rounded-2xl p-5 border border-slate-200 dark:border-slate-700 hover:border-blue-500 dark:hover:border-blue-400 shadow-xs hover:shadow-md cursor-pointer transition flex flex-col justify-between group">
                <div>
                    <div class="flex items-center justify-between gap-2 mb-3">
                        <div class="w-11 h-11 rounded-xl bg-blue-600 text-white flex items-center justify-center font-extrabold text-base shadow-xs group-hover:scale-105 transition-transform">
                            <i class="bi bi-collection-fill"></i>
                        </div>
                        <span class="px-2.5 py-1 text-xs font-bold rounded-full bg-blue-50 dark:bg-blue-950/50 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-900/40 font-mono">
                            ${allDeptPapers.length} Papers
                        </span>
                    </div>
                    <h4 class="text-base font-bold text-slate-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                        All Semesters (1–8)
                    </h4>
                    <p class="text-xs text-slate-500 dark:text-slate-400 mt-1 font-medium">
                        All question papers & schemes
                    </p>
                </div>

                <div class="mt-5 pt-3 border-t border-slate-100 dark:border-slate-700/60 flex items-center justify-between text-xs font-semibold text-blue-600 dark:text-blue-400">
                    <span>Proceed to All Papers</span>
                    <i class="bi bi-arrow-right transition-transform group-hover:translate-x-1"></i>
                </div>
            </div>
        `;

        grid.innerHTML = html;
    },

    // -------------------------------------------------------------
    // ADMIN AUTH & CONTROL PAGE (#/admin)
    // -------------------------------------------------------------

    openAdminPage(updateHash = true) {
        if (updateHash && window.location.hash !== '#/admin' && window.location.hash !== '#admin') {
            this.currentRoute = '#/admin';
            window.location.hash = '#/admin';
        } else {
            this.currentRoute = '#/admin';
        }

        document.title = 'Admin Control Center - MGU FYUGP';

        // Hide homepage & department sections so Admin is a dedicated full page
        document.getElementById('heroSection')?.classList.add('hidden');
        document.getElementById('mainNavTabsContainer')?.classList.add('hidden');
        document.getElementById('deptListContainer')?.classList.add('hidden');
        document.getElementById('deptDetailContainer')?.classList.add('hidden');
        document.getElementById('departmentsSection')?.classList.add('hidden');
        document.getElementById('papersSection')?.classList.add('hidden');
        document.getElementById('filterControlsSection')?.classList.add('hidden');

        // Show dedicated admin page section
        const adminSection = document.getElementById('adminPageSection');
        if (adminSection) adminSection.classList.remove('hidden');

        const isAuth = sessionStorage.getItem('mgu_admin_auth') === 'true';
        document.getElementById('adminLoginView')?.classList.toggle('hidden', isAuth);
        document.getElementById('adminControlsView')?.classList.toggle('hidden', !isAuth);

        if (isAuth) {
            const userDisplay = document.getElementById('adminUserDisplayName');
            if (userDisplay) {
                userDisplay.textContent = sessionStorage.getItem('mgu_admin_user') || 'sinan_cc';
            }
            this.populateAdminDeptDropdown();
            this.switchAdminTab('upload');
            this.fetchVisitorStats();
            this.fetchPendingCount();
            document.getElementById('adminNavBtn')?.classList.remove('hidden');
            document.getElementById('adminActiveBadge')?.classList.remove('hidden');
        } else {
            setTimeout(() => {
                document.getElementById('adminUsernameInput')?.focus();
            }, 100);
        }

        window.scrollTo({ top: 0, behavior: 'smooth' });
    },

    backFromAdmin() {
        if (window.history.length > 1) {
            window.history.back();
        } else {
            this.showDepartmentsList(true);
        }
    },

    // Backward-compatibility aliases
    openAdminModal() {
        this.openAdminPage(true);
    },

    closeAdminModal() {
        this.backFromAdmin();
    },

    handleAdminLogin(e) {
        if (e) e.preventDefault();
        const userInput = document.getElementById('adminUsernameInput');
        const passInput = document.getElementById('adminPasswordInput');
        const err = document.getElementById('adminLoginError');

        this.setButtonLoading('adminLoginSubmitBtn', true, 'Logging in...');

        const username = userInput ? userInput.value.trim() : '';
        const password = passInput ? passInput.value : '';

        if ((username === 'sinan_cc' || username === 'sinan-maths') && password === 'Sinan@2001') {
            sessionStorage.setItem('mgu_admin_auth', 'true');
            sessionStorage.setItem('mgu_admin_user', username);
            if (err) err.classList.add('hidden');
            
            document.getElementById('adminLoginView')?.classList.add('hidden');
            document.getElementById('adminControlsView')?.classList.remove('hidden');
            
            // Reveal Admin Nav button when authenticated
            document.getElementById('adminNavBtn')?.classList.remove('hidden');
            document.getElementById('adminActiveBadge')?.classList.remove('hidden');
            
            const userDisplay = document.getElementById('adminUserDisplayName');
            if (userDisplay) {
                userDisplay.textContent = username;
            }

            this.populateAdminDeptDropdown();
            this.switchAdminTab('upload');
            this.fetchVisitorStats();
            this.renderPapers();
            if (this.deptState.activeDept) {
                this.renderDeptSemesterPapers();
            }
            this.setButtonLoading('adminLoginSubmitBtn', false);
        } else {
            this.setButtonLoading('adminLoginSubmitBtn', false);
            if (err) err.classList.remove('hidden');
            if (passInput) passInput.value = '';
        }
    },

    adminLogout() {
        sessionStorage.removeItem('mgu_admin_auth');
        sessionStorage.removeItem('mgu_admin_user');
        
        document.getElementById('adminLoginView')?.classList.remove('hidden');
        document.getElementById('adminControlsView')?.classList.add('hidden');
        
        // Hide Admin Nav button when logged out
        document.getElementById('adminNavBtn')?.classList.add('hidden');
        document.getElementById('adminActiveBadge')?.classList.add('hidden');
        
        const userInput = document.getElementById('adminUsernameInput');
        const passInput = document.getElementById('adminPasswordInput');
        if (userInput) userInput.value = '';
        if (passInput) passInput.value = '';
        
        this.renderPapers();
        if (this.deptState.activeDept) {
            this.renderDeptSemesterPapers();
        }
        this.backFromAdmin();
    },

    // -------------------------------------------------------------
    // VISITOR ANALYTICS & LIVE TRACKING (ADMIN ONLY)
    // -------------------------------------------------------------

    trackPortalVisit(pageName = '') {
        try {
            const page = pageName || window.location.hash || '#/departments';
            const isMobile = /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent) || window.innerWidth < 768;
            const deviceType = isMobile ? 'Mobile' : 'Desktop';
            const todayStr = new Date().toISOString().slice(0, 10).replace(/-/g, ''); // e.g. "20261019"

            // 1. Format clean page label
            let cleanPage = page.replace('#/', '').replace('#', '').trim();
            if (!cleanPage || cleanPage === 'departments') cleanPage = 'Academic Departments';
            else if (cleanPage === 'papers') cleanPage = 'All Question Papers';
            else if (cleanPage === 'bookmarks') cleanPage = 'Saved Question Papers';
            else if (cleanPage.startsWith('dept/')) cleanPage = 'Dept: ' + cleanPage.replace('dept/', '');
            else if (cleanPage === 'admin') cleanPage = 'Admin Control Center';

            // 2. Log visit locally in localStorage so recent access log is ALWAYS populated on all devices
            const now = new Date();
            const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + ', ' + now.toLocaleDateString([], { month: 'short', day: 'numeric' });
            let localLogs = [];
            try {
                const raw = localStorage.getItem('mgu_visit_logs');
                if (raw) localLogs = JSON.parse(raw);
            } catch (e) {}
            if (!Array.isArray(localLogs)) localLogs = [];

            localLogs.unshift({
                time: timeStr,
                device: deviceType,
                page: cleanPage
            });
            if (localLogs.length > 30) localLogs = localLogs.slice(0, 30);
            try {
                localStorage.setItem('mgu_visit_logs', JSON.stringify(localLogs));
            } catch (e) {}

            // 3. Determine Unique Visitor & Daily Visitor status
            const hasRegisteredUnique = localStorage.getItem('mgu_v4_registered') === 'true';
            const lastTrackedDay = localStorage.getItem('mgu_v4_day');
            const isNewDay = lastTrackedDay !== todayStr;

            // 4. Increment Cloud Counters (Public CORS-enabled CountAPI for static GitHub Pages)
            const countApiBase = 'https://countapi.mileshilliard.com/api/v1';

            // Always increment pageviews
            fetch(`${countApiBase}/hit/mgu_archive_v4_views`).catch(() => {});

            // Increment unique visitor once per device
            if (!hasRegisteredUnique) {
                localStorage.setItem('mgu_v4_registered', 'true');
                fetch(`${countApiBase}/hit/mgu_archive_v4_unique`).catch(() => {});
                if (isMobile) {
                    fetch(`${countApiBase}/hit/mgu_archive_v4_mobile`).catch(() => {});
                } else {
                    fetch(`${countApiBase}/hit/mgu_archive_v4_desktop`).catch(() => {});
                }
            }

            // Increment today visitor once per day per device
            if (isNewDay) {
                localStorage.setItem('mgu_v4_day', todayStr);
                fetch(`${countApiBase}/hit/mgu_archive_v4_today_${todayStr}`).catch(() => {});
            }

            // 5. Also notify local Python backend if available (localhost/server.py)
            const isLocalBackend = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') && window.location.port !== '';
            if (isLocalBackend) {
                let vid = localStorage.getItem('mgu_vid');
                if (!vid) {
                    vid = 'vid_' + Date.now().toString(36) + '_' + Math.random().toString(36).slice(2, 8);
                    localStorage.setItem('mgu_vid', vid);
                }
                fetch('/api/visit', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        visitor_id: vid,
                        device: isMobile ? 'mobile' : 'desktop',
                        page: cleanPage
                    })
                }).catch(() => {});
            }
        } catch (e) {
            console.warn('Visitor tracking error:', e);
        }
    },

    async fetchVisitorStats(btn = null) {
        if (btn) this.setButtonLoading(btn, true, 'Updating...');
        try {
            const countApiBase = 'https://countapi.mileshilliard.com/api/v1';
            const todayStr = new Date().toISOString().slice(0, 10).replace(/-/g, '');

            let totalUnique = 0;
            let todayUnique = 0;
            let totalViews = 0;
            let mobileCount = 0;
            let desktopCount = 0;
            let recentVisits = [];

            // A. Check local backend first if running locally on localhost
            const isLocalBackend = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') && window.location.port !== '';
            if (isLocalBackend) {
                try {
                    const res = await fetch('/api/visitors');
                    if (res.ok) {
                        const localData = await res.json();
                        totalUnique = localData.total_unique_visitors || 0;
                        todayUnique = localData.today_unique_visitors || 0;
                        totalViews = localData.total_pageviews || 0;
                        mobileCount = localData.device_breakdown?.mobile || 0;
                        desktopCount = localData.device_breakdown?.desktop || 0;
                        recentVisits = localData.recent_visits || [];
                    }
                } catch (e) {}
            }

            // B. Fetch live cloud counters (Works everywhere including GitHub Pages & mobile!)
            try {
                const [viewsRes, uniqueRes, todayRes, mobileRes, desktopRes] = await Promise.allSettled([
                    fetch(`${countApiBase}/get/mgu_archive_v4_views`).then(r => r.ok ? r.json() : null),
                    fetch(`${countApiBase}/get/mgu_archive_v4_unique`).then(r => r.ok ? r.json() : null),
                    fetch(`${countApiBase}/get/mgu_archive_v4_today_${todayStr}`).then(r => r.ok ? r.json() : null),
                    fetch(`${countApiBase}/get/mgu_archive_v4_mobile`).then(r => r.ok ? r.json() : null),
                    fetch(`${countApiBase}/get/mgu_archive_v4_desktop`).then(r => r.ok ? r.json() : null),
                ]);

                const cloudViews = viewsRes.status === 'fulfilled' && viewsRes.value ? viewsRes.value.value : 0;
                const cloudUnique = uniqueRes.status === 'fulfilled' && uniqueRes.value ? uniqueRes.value.value : 0;
                const cloudToday = todayRes.status === 'fulfilled' && todayRes.value ? todayRes.value.value : 0;
                const cloudMobile = mobileRes.status === 'fulfilled' && mobileRes.value ? mobileRes.value.value : 0;
                const cloudDesktop = desktopRes.status === 'fulfilled' && desktopRes.value ? desktopRes.value.value : 0;

                if (cloudViews > totalViews) totalViews = cloudViews;
                if (cloudUnique > totalUnique) totalUnique = cloudUnique;
                if (cloudToday > todayUnique) todayUnique = cloudToday;
                if (cloudMobile > mobileCount) mobileCount = cloudMobile;
                if (cloudDesktop > desktopCount) desktopCount = cloudDesktop;
            } catch (e) {
                console.warn('Cloud visitor stats lookup warning:', e);
            }

            // Ensure baseline of at least 1 when admin is viewing
            if (totalUnique < 1) totalUnique = 1;
            if (todayUnique < 1) todayUnique = 1;
            if (totalViews < totalUnique) totalViews = totalUnique;
            if (mobileCount === 0 && desktopCount === 0) {
                const isMobile = /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent) || window.innerWidth < 768;
                if (isMobile) mobileCount = 1; else desktopCount = 1;
            }

            // C. Recent Access Logs: Merge local storage logs with any server logs
            try {
                const localLogsRaw = localStorage.getItem('mgu_visit_logs');
                if (localLogsRaw) {
                    const parsed = JSON.parse(localLogsRaw);
                    if (Array.isArray(parsed) && parsed.length > 0) {
                        const merged = [...parsed, ...(recentVisits || [])];
                        // Deduplicate by time+page and keep top 25
                        const seen = new Set();
                        recentVisits = [];
                        for (const item of merged) {
                            const key = `${item.time}_${item.page}`;
                            if (!seen.has(key)) {
                                seen.add(key);
                                recentVisits.push(item);
                            }
                            if (recentVisits.length >= 25) break;
                        }
                    }
                }
            } catch (e) {}

            // D. Update DOM elements
            const totalVisitorsEl = document.getElementById('adminStatTotalVisitors');
            const todayVisitorsEl = document.getElementById('adminStatTodayVisitors');
            const totalViewsEl = document.getElementById('adminStatTotalPageviews');
            const mobileRatioEl = document.getElementById('adminStatMobileRatio');
            const desktopRatioEl = document.getElementById('adminStatDesktopRatio');
            const deviceBarEl = document.getElementById('adminStatDeviceBar');
            const lastUpdatedEl = document.getElementById('visitorLastUpdated');
            const recentVisitsList = document.getElementById('adminRecentVisitsList');

            if (totalVisitorsEl) totalVisitorsEl.textContent = totalUnique.toLocaleString();
            if (todayVisitorsEl) todayVisitorsEl.textContent = todayUnique.toLocaleString();
            if (totalViewsEl) totalViewsEl.textContent = totalViews.toLocaleString();

            const totalDev = mobileCount + desktopCount;
            const mPct = totalDev > 0 ? Math.round((mobileCount / totalDev) * 100) : 60;
            const dPct = 100 - mPct;

            if (mobileRatioEl) mobileRatioEl.innerHTML = `<i class="bi bi-phone"></i> ${mPct}% Mobile`;
            if (desktopRatioEl) desktopRatioEl.innerHTML = `<i class="bi bi-laptop"></i> ${dPct}% PC`;
            if (deviceBarEl) deviceBarEl.style.width = `${mPct}%`;

            if (lastUpdatedEl) {
                const now = new Date();
                lastUpdatedEl.textContent = `Updated ${now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}`;
            }

            if (recentVisitsList) {
                if (recentVisits.length === 0) {
                    const now = new Date();
                    const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + ', ' + now.toLocaleDateString([], { month: 'short', day: 'numeric' });
                    recentVisits = [
                        { time: timeStr, device: /Mobile/i.test(navigator.userAgent) ? 'Mobile' : 'Desktop', page: 'Academic Departments' }
                    ];
                }

                recentVisitsList.innerHTML = recentVisits.map(v => `
                    <div class="py-1.5 flex items-center justify-between gap-2">
                        <div class="flex items-center gap-2 min-w-0">
                            <span class="p-1 rounded bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300">
                                <i class="bi ${v.device === 'Mobile' ? 'bi-phone' : 'bi-laptop'} text-xs"></i>
                            </span>
                            <span class="truncate font-medium text-slate-800 dark:text-slate-200">${v.page || 'Academic Departments'}</span>
                        </div>
                        <span class="text-[11px] text-slate-400 shrink-0 font-mono">${v.time || 'Recently'}</span>
                    </div>
                `).join('');
            }
        } finally {
            if (btn) {
                setTimeout(() => this.setButtonLoading(btn, false), 350);
            }
        }
    },

    refreshVisitorStats(btn) {
        this.fetchVisitorStats(btn);
    },

    toggleVisitorActivityDrawer() {
        const drawer = document.getElementById('visitorActivityDrawer');
        const icon = document.getElementById('visitorDrawerIcon');
        if (!drawer) return;
        const isHidden = drawer.classList.contains('hidden');
        drawer.classList.toggle('hidden', !isHidden);
        if (icon) {
            icon.className = isHidden ? 'bi bi-chevron-up' : 'bi bi-chevron-down';
        }
    },

    switchAdminTab(tab) {
        const uploadView = document.getElementById('adminTabUploadView');
        const deleteView = document.getElementById('adminTabDeleteView');
        const syncView = document.getElementById('adminTabSyncView');
        const inboxView = document.getElementById('adminTabInboxView');
        const modelQpView = document.getElementById('adminTabModelQpView');
        const pendingView = document.getElementById('adminTabPendingView');
        const btnUpload = document.getElementById('adminTabBtnUpload');
        const btnDelete = document.getElementById('adminTabBtnDelete');
        const btnSync = document.getElementById('adminTabBtnSync');
        const btnInbox = document.getElementById('adminTabBtnInbox');
        const btnModelQp = document.getElementById('adminTabBtnModelQp');
        const btnPending = document.getElementById('adminTabBtnPending');

        const activeClass = 'px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-blue-600 text-white shadow-xs flex items-center gap-1.5 transition shrink-0';
        const inactiveClass = 'px-3.5 py-1.5 text-xs font-medium rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 flex items-center gap-1.5 transition shrink-0';

        if (uploadView) uploadView.classList.toggle('hidden', tab !== 'upload');
        if (deleteView) deleteView.classList.toggle('hidden', tab !== 'delete');
        if (syncView) syncView.classList.toggle('hidden', tab !== 'sync');
        if (inboxView) inboxView.classList.toggle('hidden', tab !== 'inbox');
        if (modelQpView) modelQpView.classList.toggle('hidden', tab !== 'modelQp');
        if (pendingView) pendingView.classList.toggle('hidden', tab !== 'pending');

        if (btnUpload) btnUpload.className = tab === 'upload' ? activeClass : inactiveClass;
        if (btnDelete) btnDelete.className = tab === 'delete' ? activeClass : inactiveClass;
        if (btnSync) btnSync.className = tab === 'sync' ? activeClass : inactiveClass;
        if (btnInbox) btnInbox.className = tab === 'inbox' ? activeClass : inactiveClass;
        if (btnModelQp) btnModelQp.className = tab === 'modelQp' ? activeClass : inactiveClass;
        if (btnPending) btnPending.className = tab === 'pending' ? activeClass : inactiveClass;

        if (tab === 'delete') {
            this.renderAdminDeleteList();
        } else if (tab === 'inbox') {
            this.renderAdminInbox();
        } else if (tab === 'modelQp') {
            this.renderAdminModelQp();
        } else if (tab === 'pending') {
            this.loadPendingPapers();
        }
    },

    async loadUntaggedModelPapers() {
        if (this.untaggedModels && this.untaggedModels.length > 0) return this.untaggedModels;
        try {
            const resp = await fetch('data/untagged_model_papers.json');
            if (resp.ok) {
                this.untaggedModels = await resp.json();
            } else {
                this.untaggedModels = [];
            }
        } catch (e) {
            console.error('Failed to load untagged model papers:', e);
            this.untaggedModels = [];
        }
        return this.untaggedModels;
    },

    populateCourseCodeDatalist() {
        const datalist = document.getElementById('courseCodeDatalist');
        if (!datalist || datalist.children.length > 0) return;
        const seen = new Set();
        const options = [];
        for (const p of this.papers) {
            const cc = (p.course_code || '').trim().toUpperCase();
            if (cc && !seen.has(cc)) {
                seen.add(cc);
                options.push(`<option value="${cc}">${p.title} (${p.dept_name || p.dept_code})</option>`);
            }
        }
        datalist.innerHTML = options.join('');
    },

    switchModelSubTab(subTab) {
        const viewUntagged = document.getElementById('adminModelSubViewUntagged');
        const viewAll = document.getElementById('adminModelSubViewAll');
        const viewUpload = document.getElementById('adminModelSubViewUpload');
        const btnUntagged = document.getElementById('adminModelSubBtnUntagged');
        const btnAll = document.getElementById('adminModelSubBtnAll');
        const btnUpload = document.getElementById('adminModelSubBtnUpload');

        const activeSubClass = 'px-3 py-1.5 rounded-lg font-bold bg-indigo-600 text-white shadow-xs flex items-center gap-1.5 transition';
        const inactiveSubClass = 'px-3 py-1.5 rounded-lg font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 flex items-center gap-1.5 transition';

        if (viewUntagged) viewUntagged.classList.toggle('hidden', subTab !== 'untagged');
        if (viewAll) viewAll.classList.toggle('hidden', subTab !== 'all');
        if (viewUpload) viewUpload.classList.toggle('hidden', subTab !== 'upload');

        if (btnUntagged) btnUntagged.className = subTab === 'untagged' ? 'px-3 py-1.5 rounded-lg font-bold bg-amber-500 text-white shadow-xs flex items-center gap-1.5 transition' : inactiveSubClass;
        if (btnAll) btnAll.className = subTab === 'all' ? activeSubClass : inactiveSubClass;
        if (btnUpload) btnUpload.className = subTab === 'upload' ? activeSubClass : inactiveSubClass;

        if (subTab === 'all') {
            this.renderAdminAllModelList();
        } else if (subTab === 'untagged') {
            this.renderAdminUntaggedModelList();
        }
    },

    async renderAdminModelQp() {
        this.populateCourseCodeDatalist();
        await this.loadUntaggedModelPapers();
        
        const badge = document.getElementById('adminUntaggedCountBadge');
        const countSpan = document.getElementById('adminModelUntaggedCount');
        const totalSpan = document.getElementById('adminModelTotalCount');
        const assignedSpan = document.getElementById('adminModelAssignedCount');

        const untaggedCount = this.untaggedModels ? this.untaggedModels.length : 0;
        if (badge) {
            badge.textContent = untaggedCount;
            badge.classList.toggle('hidden', untaggedCount === 0);
        }
        if (countSpan) countSpan.textContent = untaggedCount;
        if (totalSpan) totalSpan.textContent = 1151;
        if (assignedSpan) assignedSpan.textContent = Math.max(0, 1151 - untaggedCount);

        this.renderAdminUntaggedModelList();
    },

    renderAdminUntaggedModelList() {
        const container = document.getElementById('adminUntaggedListContainer');
        if (!container) return;

        if (!this.untaggedModels || this.untaggedModels.length === 0) {
            container.innerHTML = `
                <div class="text-center py-8 text-slate-500 dark:text-slate-400">
                    <i class="bi bi-check-circle-fill text-emerald-500 text-2xl block mb-2"></i>
                    <p class="font-bold">All model question papers are tagged!</p>
                    <p class="text-xs">No pending untagged papers require course codes.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = this.untaggedModels.map(item => `
            <div class="p-3.5 rounded-xl border border-amber-200 dark:border-amber-900/60 bg-amber-50/40 dark:bg-amber-950/20 flex flex-col gap-2.5 transition hover:shadow-xs">
                <div class="flex items-center justify-between gap-2 flex-wrap">
                    <div class="flex items-center gap-2 min-w-0">
                        <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-200 dark:bg-amber-900 text-amber-900 dark:text-amber-200 shrink-0">
                            NEEDS COURSE CODE
                        </span>
                        <span class="text-xs font-mono font-bold text-slate-800 dark:text-slate-200 truncate" title="${item.filename}">
                            ${item.filename}
                        </span>
                    </div>
                    <div class="flex items-center gap-2 shrink-0">
                        <span class="text-[11px] font-semibold text-slate-500 dark:text-slate-400">
                            <i class="bi bi-file-earmark"></i> ${item.pages} ${item.pages === 1 ? 'page' : 'pages'} (QP Length: 1–7 pgs)
                        </span>
                        <button onclick="App.previewDirect(this, '${item.url}', '${item.filename}', 'UNTAGGED')" class="px-2.5 py-1 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white shadow-xs flex items-center gap-1 transition">
                            <i class="bi bi-eye"></i> Preview PDF
                        </button>
                    </div>
                </div>

                <div class="text-[11px] font-mono text-slate-600 dark:text-slate-400 bg-white/80 dark:bg-slate-800/80 p-2 rounded-lg border border-slate-200 dark:border-slate-700 line-clamp-2">
                    ${item.snippet || 'No text extracted. Click Preview PDF to inspect paper.'}
                </div>

                <!-- Form to tag course code -->
                <div class="grid grid-cols-1 sm:grid-cols-12 gap-2 items-center pt-1">
                    <div class="sm:col-span-5">
                        <input 
                            type="text" 
                            id="tagCode_${item.model_id}" 
                            value="${item.suggested_code || ''}" 
                            placeholder="Course Code (e.g. MG1DSCCHE100)" 
                            list="courseCodeDatalist"
                            class="w-full px-2.5 py-1.5 text-xs font-mono font-bold uppercase rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-indigo-500"
                        >
                    </div>
                    <div class="sm:col-span-4">
                        <select id="tagType_${item.model_id}" class="w-full px-2 py-1.5 text-xs rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100">
                            <option value="THEORY" ${!item.is_practical ? 'selected' : ''}>Theory Model QP</option>
                            <option value="PRACTICAL" ${item.is_practical ? 'selected' : ''}>Practical Model QP</option>
                        </select>
                    </div>
                    <div class="sm:col-span-3">
                        <button onclick="App.handleTagModelPaper('${item.model_id}', this)" class="w-full px-3 py-1.5 text-xs font-bold rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white shadow-xs flex items-center justify-center gap-1 transition min-h-[34px]">
                            <i class="bi bi-check2-circle"></i> Save & Tag
                        </button>
                    </div>
                </div>
            </div>
        `).join('');
    },

    handleTagModelPaper(modelId, btn = null) {
        const item = this.untaggedModels.find(u => u.model_id === modelId);
        if (!item) return;

        const codeInput = document.getElementById(`tagCode_${modelId}`);
        const typeSelect = document.getElementById(`tagType_${modelId}`);

        let courseCode = codeInput ? codeInput.value.trim().toUpperCase() : '';
        const paperType = typeSelect ? typeSelect.value : 'THEORY';

        if (!courseCode) {
            alert('Please enter or select a Course Code for this question paper.');
            codeInput?.focus();
            return;
        }

        if (btn) this.setButtonLoading(btn, true, 'Tagging...');

        courseCode = courseCode.replace(/\s+/g, '');

        const newModelObj = {
            id: modelId,
            title: paperType === 'PRACTICAL' ? 'Official Practical Model Paper' : 'Official Theory Model Paper',
            paper_type: paperType,
            pages: item.pages,
            url: item.url,
            raw_url: item.url,
            filename: item.filename
        };

        let attachedCount = 0;
        for (const p of this.papers) {
            if ((p.course_code || '').trim().toUpperCase() === courseCode) {
                if (!p.model_papers) p.model_papers = [];
                const ptype = (newModelObj.paper_type || 'THEORY').toUpperCase();
                p.model_papers = p.model_papers.filter(m => m.id !== modelId && (m.paper_type || 'THEORY').toUpperCase() !== ptype);
                p.model_papers.push(newModelObj);
                p.has_files = true;
                attachedCount++;
            }
        }

        if (attachedCount === 0) {
            const newCourse = {
                id: `model_only_${courseCode}`,
                qp_code: 'AWAITED',
                course_code: courseCode,
                title: `${courseCode} Course`,
                raw_header: `${courseCode}`,
                semester: item.semester || 1,
                semester_label: `Semester ${item.semester || 1}`,
                course_type: 'DSC',
                course_type_name: 'Discipline Specific Core',
                dept_code: 'GEN',
                dept_name: 'General',
                parent_dept: 'GEN',
                parent_dept_name: 'General',
                is_minor: false,
                exam_id: 'model_catalog',
                exam_name: 'FYUGP 2024 (Exam Question Paper Awaited)',
                batch: '2024 Admission',
                is_fyugp: true,
                has_qp: false,
                qp_url: '',
                has_scheme: false,
                scheme_url: '',
                files: [],
                has_files: true,
                minor_name: '',
                model_papers: [newModelObj]
            };
            this.papers.push(newCourse);
        }

        this.untaggedModels = this.untaggedModels.filter(u => u.model_id !== modelId);
        this.renderAdminModelQp();
        this.applyFilters();

        try {
            localStorage.setItem('mgu_untagged_models', JSON.stringify(this.untaggedModels));
        } catch (e) {}

        if (btn) this.setButtonLoading(btn, false);
        alert(`Model Question Paper successfully tagged to ${courseCode}!`);
    },

    renderAdminAllModelList() {
        const container = document.getElementById('adminAllModelListContainer');
        if (!container) return;

        const coursesWithModels = [];
        const seen = new Set();
        for (const p of this.papers) {
            if (p.model_papers && p.model_papers.length > 0) {
                const cc = p.course_code;
                if (!seen.has(cc)) {
                    seen.add(cc);
                    coursesWithModels.push({
                        code: cc,
                        title: p.title,
                        dept: p.dept_name || p.dept_code,
                        sem: p.semester,
                        models: p.model_papers
                    });
                }
            }
        }

        const q = (document.getElementById('adminModelSearchInput')?.value || '').toLowerCase().trim();
        const filtered = q 
            ? coursesWithModels.filter(c => c.code.toLowerCase().includes(q) || c.title.toLowerCase().includes(q) || c.dept.toLowerCase().includes(q))
            : coursesWithModels;

        if (filtered.length === 0) {
            container.innerHTML = '<div class="text-center py-6 text-slate-400">No matching model question papers found.</div>';
            return;
        }

        container.innerHTML = filtered.slice(0, 50).map(c => `
            <div class="p-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 flex items-center justify-between gap-3 text-xs">
                <div>
                    <div class="flex items-center gap-2 mb-1">
                        <span class="font-mono font-bold text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-950/40 px-2 py-0.5 rounded">
                            ${c.code}
                        </span>
                        <span class="text-slate-400">Sem ${c.sem} • ${c.dept}</span>
                    </div>
                    <div class="font-semibold text-slate-800 dark:text-slate-200 truncate max-w-md">
                        ${c.title}
                    </div>
                </div>
                <div class="flex items-center gap-2 shrink-0">
                    <span class="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-700 font-semibold text-slate-600 dark:text-slate-300">
                        ${c.models.length} ${c.models.length === 1 ? 'Model QP' : 'Model QPs'}
                    </span>
                    <button onclick="App.previewDirect(this, '${c.models[0].url}', '${(c.models[0].title || 'Model QP').replace(/'/g, "\\'")}', '${c.code}')" class="px-2.5 py-1 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white shadow-xs flex items-center gap-1 transition">
                        <i class="bi bi-eye"></i> View
                    </button>
                </div>
            </div>
        `).join('');
    },

    filterAdminModelList() {
        this.renderAdminAllModelList();
    },

    handleAdminModelUploadSubmit(e) {
        if (e) e.preventDefault();
        const codeInput = document.getElementById('adminModelUpCourseCode');
        const typeSelect = document.getElementById('adminModelUpType');
        const fileInput = document.getElementById('adminModelUpFile');

        const courseCode = codeInput ? codeInput.value.trim().toUpperCase() : '';
        const paperType = typeSelect ? typeSelect.value : 'THEORY';
        const file = fileInput?.files?.[0];

        if (!courseCode || !file) {
            alert('Please select a PDF file and specify the Course Code.');
            return;
        }

        this.setButtonLoading('adminModelUploadSubmitBtn', true, 'Uploading Model QP...');

        try {
            const objectUrl = URL.createObjectURL(file);
            const newModelObj = {
                id: `model_custom_${Date.now()}`,
                title: paperType === 'PRACTICAL' ? 'Official Practical Model Paper' : 'Official Theory Model Paper',
                paper_type: paperType,
                pages: 2,
                url: objectUrl,
                raw_url: objectUrl,
                filename: file.name
            };

            let attached = false;
            for (const p of this.papers) {
                if ((p.course_code || '').trim().toUpperCase() === courseCode) {
                    if (!p.model_papers) p.model_papers = [];
                    const ptype = (newModelObj.paper_type || 'THEORY').toUpperCase();
                    p.model_papers = p.model_papers.filter(m => (m.paper_type || 'THEORY').toUpperCase() !== ptype);
                    p.model_papers.push(newModelObj);
                    p.has_files = true;
                    attached = true;
                }
            }

            if (!attached) {
                this.papers.push({
                    id: `model_only_${courseCode}`,
                    qp_code: 'AWAITED',
                    course_code: courseCode,
                    title: `${courseCode} Course`,
                    raw_header: courseCode,
                    semester: 1,
                    semester_label: 'Semester 1',
                    course_type: 'DSC',
                    course_type_name: 'Discipline Specific Core',
                    dept_code: 'GEN',
                    dept_name: 'General',
                    parent_dept: 'GEN',
                    parent_dept_name: 'General',
                    is_minor: false,
                    exam_id: 'model_catalog',
                    exam_name: 'FYUGP 2024 (Exam Question Paper Awaited)',
                    batch: '2024 Admission',
                    is_fyugp: true,
                    has_qp: false,
                    qp_url: '',
                    has_scheme: false,
                    scheme_url: '',
                    files: [],
                    has_files: true,
                    minor_name: '',
                    model_papers: [newModelObj]
                });
            }

            this.applyFilters();
            alert(`Model Question Paper for ${courseCode} uploaded and linked successfully!`);
            codeInput.value = '';
            fileInput.value = '';
            this.switchModelSubTab('all');
        } finally {
            this.setButtonLoading('adminModelUploadSubmitBtn', false);
        }
    },

    toggleAdminMinorFields() {
        const isMinor = document.getElementById('adminUploadIsMinor')?.checked;
        const container = document.getElementById('adminMinorFieldsContainer');
        if (container) {
            container.classList.toggle('hidden', !isMinor);
        }
    },

    populateAdminDeptDropdown() {
        const select = document.getElementById('adminUploadDept');
        if (!select) return;
        select.innerHTML = '<option value="">-- Select Department --</option>' +
            this.departments.map(d => `<option value="${d.code}">${d.name} (${d.code})</option>`).join('');
    },

    bindDropzoneEvents() {
        const dropzone = document.getElementById('adminPdfDropzone');
        if (!dropzone) return;

        ['dragenter', 'dragover'].forEach(eventName => {
            dropzone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropzone.classList.add('border-blue-500', 'bg-blue-50/50', 'dark:bg-blue-950/40');
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropzone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropzone.classList.remove('border-blue-500', 'bg-blue-50/50', 'dark:bg-blue-950/40');
            }, false);
        });

        dropzone.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            const files = dt?.files;
            if (files && files.length > 0) {
                const file = files[0];
                if (file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')) {
                    this.processSmartPdfFile(file);
                } else {
                    alert('Please drop a valid PDF document.');
                }
            }
        }, false);
    },

    handlePaperCategoryChange(category) {
        this.currentPaperCategory = category;
        const catLabelQP = document.getElementById('catLabelQP');
        const catLabelModel = document.getElementById('catLabelModel');
        const examDetails = document.getElementById('adminExamDetailsSection');
        const schemeSection = document.getElementById('adminSchemeSection');

        if (category === 'MODEL') {
            if (catLabelModel) {
                catLabelModel.className = 'flex items-start gap-3 p-3.5 rounded-xl border-2 border-indigo-600 bg-indigo-50/40 dark:bg-indigo-950/30 cursor-pointer transition';
            }
            if (catLabelQP) {
                catLabelQP.className = 'flex items-start gap-3 p-3.5 rounded-xl border border-slate-200 dark:border-slate-700 hover:border-blue-400 bg-white dark:bg-slate-800 cursor-pointer transition';
            }
            if (examDetails) examDetails.classList.add('hidden');
            if (schemeSection) schemeSection.classList.add('hidden');
        } else {
            if (catLabelQP) {
                catLabelQP.className = 'flex items-start gap-3 p-3.5 rounded-xl border-2 border-blue-600 bg-blue-50/40 dark:bg-blue-950/30 cursor-pointer transition';
            }
            if (catLabelModel) {
                catLabelModel.className = 'flex items-start gap-3 p-3.5 rounded-xl border border-slate-200 dark:border-slate-700 hover:border-indigo-400 bg-white dark:bg-slate-800 cursor-pointer transition';
            }
            if (examDetails) examDetails.classList.remove('hidden');
            if (schemeSection) schemeSection.classList.remove('hidden');
        }

        this.handleCourseCodeManualChange();
    },

    async extractPdfText(file) {
        if (typeof pdfjsLib === 'undefined') {
            console.warn('PDF.js library is not loaded');
            return '';
        }
        try {
            pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
            const arrayBuffer = await file.arrayBuffer();
            const loadingTask = pdfjsLib.getDocument({ data: arrayBuffer });
            const pdf = await loadingTask.promise;
            let fullText = '';
            const pagesToScan = Math.min(pdf.numPages, 3);
            for (let i = 1; i <= pagesToScan; i++) {
                const page = await pdf.getPage(i);
                const tokenized = await page.getTextContent();
                const pageText = tokenized.items.map(item => item.str).join(' ');
                fullText += ' ' + pageText;
            }
            return fullText;
        } catch (err) {
            console.error('Failed to extract text from PDF via PDF.js:', err);
            return '';
        }
    },

    normalizeCourseCode(rawStr, defaultSem = 1) {
        if (!rawStr) return '';
        let c = String(rawStr).trim().toUpperCase().replace(/[^A-Z0-9]/g, '');
        if (c.startsWith('24MG')) {
            c = c.slice(2);
        }
        if (/^MGU[1-8]/.test(c)) {
            c = 'MG' + c.slice(3);
        } else if (c.startsWith('MGU') && c.length >= 4) {
            c = 'MG' + c.slice(3);
        }
        if (/^MG[IL]/i.test(c)) {
            c = 'MG1' + c.slice(3);
        }
        if (/^[1-8][A-Z]{2,}/.test(c)) {
            c = 'MG' + c;
        }

        // Rule: "Names of Course code will always have number at end."
        // Strip trailing letters attached after the 3-digit level (e.g. MG4DSEMAT201TRANS -> MG4DSEMAT201)
        const trailingJunkMatch = c.match(/^(MG[1-8](?:DSC|DSE|SEC|MDC|VAC|CCR|AEC|MDE|SDC|MPC|HON|MIN|MDE)[A-Z]{2,5}[1-4][0-9]{2})[A-Z]+$/);
        if (trailingJunkMatch) {
            c = trailingJunkMatch[1];
        }

        return c;
    },

    isDepartmentNameOrCode(str) {
        if (!str) return false;
        const clean = String(str).trim().toLowerCase();
        if (clean.length <= 2) return true;
        for (const d of (this.departments || [])) {
            if (d.name && d.name.trim().toLowerCase() === clean) return true;
            if (d.code && d.code.trim().toLowerCase() === clean) return true;
            if (d.majors && Array.isArray(d.majors)) {
                for (const m of d.majors) {
                    if (m.name && m.name.trim().toLowerCase() === clean) return true;
                    if (m.code && m.code.trim().toLowerCase() === clean) return true;
                }
            }
        }
        return false;
    },

    parseCourseCode(rawStr) {
        if (!rawStr) return null;
        let clean = String(rawStr).trim().toUpperCase().replace(/[^A-Z0-9]/g, '');
        clean = clean.replace('MGS5', 'MG5').replace('DEC', 'DSE');
        // Format: MG + [1-8] + [Type: DSC,DSE,SEC,MDC,VAC,CCR,AEC,MDE,SDC,MPC,HON,MIN,DEC] + [Dept] + [optional A + 2 digits for signature | 3-digit level 100-599]
        // Examples: MG4DSEMAT201 (regular), MG3DSEBOTA03 (signature code), MG5DSECHEA01
        const m = clean.match(/^MG([1-8])(DSC|DSE|SEC|MDC|VAC|CCR|AEC|MDE|SDC|MPC|HON|MIN|MDE|DEC)([A-Z]{2,5})(A\d{2}|[1-5][0-9]{2})$/);
        if (!m) return null;

        const semester = parseInt(m[1], 10);
        const courseType = m[2] === 'DEC' ? 'DSE' : m[2];
        const deptCode = m[3];
        const isSignature = m[4].startsWith('A');
        const courseLevel = isSignature ? parseInt(m[4].slice(1), 10) : parseInt(m[4], 10);

        const expectedYear = Math.ceil(semester / 2);
        const actualYear = isSignature ? expectedYear : Math.floor(courseLevel / 100);
        const yearMatches = (expectedYear === actualYear);

        return {
            isValid: true,
            fullCode: clean,
            semester: semester,
            courseType: courseType,
            deptCode: deptCode,
            isSignature: isSignature,
            courseLevel: courseLevel,
            yearMatches: yearMatches
        };
    },

    isSignatureCourse(rawCode) {
        if (!rawCode) return false;
        let code = '';
        if (typeof rawCode === 'object') {
            code = rawCode.course_code || rawCode.code || '';
        } else {
            code = String(rawCode);
        }
        const clean = code.trim().toUpperCase();
        if (!clean) return false;

        // In 12-character MGU FYUGP course codes (e.g. MG1DSCSTA100 vs MG3DSEBOTA03),
        // the last 3 values strictly determine whether it is a signature course:
        // - Signature courses end in A followed by 2 digits: A00, A01, A02, A03, etc.
        // - Standard courses end in 3 digits: 100, 101, 200, 201, 300, etc.
        // Department codes ending in 'A' (e.g. STA, BBA, BCA, CMA, GRA, IAA, FTA) are regular courses.
        const last3 = clean.slice(-3);
        return /^A\d{2}$/.test(last3);
    },

    extractPageHeaderCourseInfo(pageText, defaultSem = 1) {
        if (!pageText) {
            return {
                isStart: false,
                courseCode: '',
                allCodes: [],
                title: '',
                deptCode: 'MAT',
                semester: defaultSem || 1,
                paperType: 'THEORY',
                isSignature: false,
                confidence: 'low',
                matchedPaper: null
            };
        }

        // Take top 2200 characters of the page for header inspection
        const headerSlice = pageText.slice(0, 2200);
        const cleanHeader = headerSlice.replace(/\s+/g, ' ');
        const collapsedHeader = cleanHeader.replace(/(?<=\b[A-Za-z0-9])\s+(?=[A-Za-z0-9]\b)/g, '');
        const upperHeader = cleanHeader.toUpperCase();
        const collapsedUpper = collapsedHeader.toUpperCase();
        const fullUpper = pageText.toUpperCase();

        // 1. Paper Type Detection (Theory vs Practical)
        const isPractical = /(?:PRACTICAL\s*(?:EXAMINATION|MODEL|QP|EXAM)|EXPERIMENT\s*NO|CONDUCT\s*ONE\s*EXPERIMENT|LAB\s*EXAMINATION)/i.test(fullUpper);
        const paperType = isPractical ? 'PRACTICAL' : 'THEORY';

        // 2. Known Catalog Map from portal papers
        const knownCoursesMap = new Map();
        (this.papers || []).forEach(p => {
            const cc = (p.course_code || '').trim().toUpperCase();
            if (cc && !knownCoursesMap.has(cc)) {
                knownCoursesMap.set(cc, p);
            }
            const norm = this.normalizeCourseCode(cc);
            if (norm && !knownCoursesMap.has(norm)) {
                knownCoursesMap.set(norm, p);
            }
        });

        // 3. Extract Candidate Course Codes from this page's header adhering to FYUGP structure:
        // MG + [1-8] + [Type] + [Dept] + optional [A] + [Level 100-599]
        // Rule: "Names of Course code will always have number at end."
        const rawCodeMatches = [];

        for (const txt of [cleanHeader, collapsedHeader]) {
            // Pattern A: Explicit "COURSE CODE: [code]" - split comma/slash separated codes
            const explicitMatches = txt.matchAll(/(?:COURSE\s*(?:CODE|NO\.?)|PAPER\s*CODE)\s*[:\-–\s]+\s*([A-Z0-9_\-\s,]{6,60})/gi);
            for (const m of explicitMatches) {
                if (m && m[1]) {
                    m[1].split(/[,;\/]+/).forEach(p => {
                        const trimmed = p.trim();
                        if (trimmed) rawCodeMatches.push(trimmed);
                    });
                }
            }

            // Pattern B: FYUGP MGU Code pattern matching MG[1-8](Type)(Dept)A?(Level)
            const mgMatches = txt.matchAll(/(?:24)?\s*(?:MG|MGU)\s*[1-8Il]?\s*(?:DSC|DSE|SEC|MDC|VAC|CCR|AEC|MDE|SDC|MPC|HON|MIN|MDE|DEC)\s*[A-Z]{2,5}\s*(?:A\d{2}|[1-5][0-9]{2})(?![0-9A-Z])/gi);
            for (const m of mgMatches) {
                if (m && m[0]) rawCodeMatches.push(m[0]);
            }

            // Pattern C: Standard boundary code - strictly ending in digits
            const standardMatches = txt.matchAll(/\b(MG[1-8][A-Z]{2,8}(?:A\d{2}|[1-5][0-9]{2}))\b/gi);
            for (const m of standardMatches) {
                if (m && m[1]) rawCodeMatches.push(m[1]);
            }
        }

        // Normalize all extracted code candidates
        const normalizedCandidates = [];
        for (const raw of rawCodeMatches) {
            let norm = this.normalizeCourseCode(raw, defaultSem);
            if (!norm) continue;
            norm = norm.replace('MGS5', 'MG5').replace('DEC', 'DSE');
            if (norm.startsWith('MGDSE') || norm.startsWith('MGDSC') || norm.startsWith('MGSEC')) {
                norm = 'MG5' + norm.slice(2);
            }
            if (/^MG[1-46-8]/.test(norm) && (upperHeader.includes('FIFTH') || defaultSem === 5)) {
                norm = 'MG5' + norm.slice(3);
            }
            // Strip trailing letters e.g. TRANS
            const mStrip = norm.match(/^(MG[1-8](?:DSC|DSE|SEC|MDC|VAC|CCR|AEC|MDE|SDC|MPC|HON|MIN|MDE)[A-Z]{2,5}(?:A\d{2}|[1-5][0-9]{2}))[A-Z]+$/);
            if (mStrip) norm = mStrip[1];

            if (norm.length >= 8 && norm.startsWith('MG') && /\d$/.test(norm)) {
                if (!normalizedCandidates.includes(norm)) {
                    normalizedCandidates.push(norm);
                }
            }
        }

        // 4. Start Header Detection (University header + Exam Title + Marks/Time/Sem)
        // Rule: A continuation page with questions (Part B/C and marks) is NEVER an exam start!
        const hasUniv = /(?:MAHATMA\s*GANDHI\s*UNIVERSITY|MGU|M\.?\s*G\.?\s*UNIVERSITY|MODEL\s*QUESTION\s*PAPER|MGU-UGP|MGU\s*UGP)/i.test(upperHeader) ||
                        /(?:MAHATMA\s*GANDHI\s*UNIVERSITY|MGU|M\.?\s*G\.?\s*UNIVERSITY|MODEL\s*QUESTION\s*PAPER|MGU-UGP|MGU\s*UGP)/i.test(collapsedUpper);
        const hasExamTitle = /(?:EXAMINATION|EXAM\b|MODEL\s*QUESTION\s*PAPER|MODEL\s*EXAM|MODEL\s*QP)/i.test(upperHeader) ||
                             /(?:EXAMINATION|EXAM\b|MODEL\s*QUESTION\s*PAPER|MODEL\s*EXAM|MODEL\s*QP)/i.test(collapsedUpper);
        const hasMarks = /(?:MAX(?:IMUM)?\.?\s*MARKS|TOTAL\s*MARKS|MARKS\s*[:\-–]|\bMARKS\b)/i.test(upperHeader);
        const hasTime = /(?:TIME\s*[:\-–]|DURATION\s*[:\-–]|\b\d+\s*HOURS\b|\b\d+\s*HRS\b)/i.test(upperHeader);
        const hasSemWord = /(?:FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH|SEVENTH|EIGHTH|[1-8](?:ST|ND|RD|TH)?)\s*SEMESTER/i.test(upperHeader) ||
                           /(?:FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH|SEVENTH|EIGHTH|[1-8](?:ST|ND|RD|TH)?)\s*SEMESTER/i.test(collapsedUpper);

        const isStart = (hasUniv && hasExamTitle && (hasMarks || hasTime || hasSemWord)) ||
                        (normalizedCandidates.length > 0 && hasExamTitle && (hasMarks || hasTime)) ||
                        (hasUniv && /MODEL\s*(?:QUESTION|QP)/i.test(upperHeader));

        // Validate candidates with parseCourseCode and catalog
        const parsedCandidates = normalizedCandidates.map(cand => ({
            code: cand,
            parsed: this.parseCourseCode(cand),
            inCatalog: knownCoursesMap.has(cand)
        }));

        let matchedCatalogPaper = null;
        let bestCourseCode = '';
        let parsedInfo = null;

        // Preference 1: Valid parsed code that is also in catalog
        const catParsed = parsedCandidates.find(c => c.parsed && c.parsed.isValid && c.inCatalog);
        if (catParsed) {
            matchedCatalogPaper = knownCoursesMap.get(catParsed.code);
            bestCourseCode = catParsed.code;
            parsedInfo = catParsed.parsed;
        }

        // Preference 2: Any candidate in catalog
        if (!bestCourseCode) {
            const catAny = parsedCandidates.find(c => c.inCatalog);
            if (catAny) {
                matchedCatalogPaper = knownCoursesMap.get(catAny.code);
                bestCourseCode = catAny.code;
                parsedInfo = catAny.parsed || this.parseCourseCode(catAny.code);
            }
        }

        // Preference 3: Valid parsed code according to FYUGP QP pattern
        if (!bestCourseCode) {
            const validPattern = parsedCandidates.find(c => c.parsed && c.parsed.isValid);
            if (validPattern) {
                bestCourseCode = validPattern.code;
                parsedInfo = validPattern.parsed;
            }
        }

        // Preference 4: First normalized candidate ending with a number
        if (!bestCourseCode && normalizedCandidates.length > 0) {
            const numEndCand = normalizedCandidates.find(c => /\d$/.test(c));
            if (numEndCand) {
                bestCourseCode = numEndCand;
                parsedInfo = this.parseCourseCode(bestCourseCode);
            }
        }

        // If still no code, check if any catalog course code is contained inside this header
        if (!bestCourseCode) {
            const sortedKnown = Array.from(knownCoursesMap.keys()).sort((a, b) => b.length - a.length);
            for (const knownCode of sortedKnown) {
                if (knownCode.length >= 8 && /\d$/.test(knownCode) && (upperHeader.includes(knownCode) || collapsedUpper.includes(knownCode))) {
                    matchedCatalogPaper = knownCoursesMap.get(knownCode);
                    bestCourseCode = knownCode;
                    parsedInfo = this.parseCourseCode(knownCode);
                    break;
                }
            }
        }

        // 5. Semester Detection
        let detectedSem = null;
        if (parsedInfo && parsedInfo.semester) {
            detectedSem = parsedInfo.semester;
        } else if (matchedCatalogPaper && matchedCatalogPaper.semester) {
            detectedSem = matchedCatalogPaper.semester;
        } else if (bestCourseCode) {
            const semMatch = bestCourseCode.match(/^MG([1-8])/);
            if (semMatch) detectedSem = parseInt(semMatch[1], 10);
        }
        if (!detectedSem) {
            const semWords = {
                'FIRST': 1, 'SECOND': 2, 'THIRD': 3, 'FOURTH': 4,
                'FIFTH': 5, 'SIXTH': 6, 'SEVENTH': 7, 'EIGHTH': 8,
                'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7, 'VIII': 8
            };
            const sm = upperHeader.match(/(?:SEMESTER|SEM\.?)\s*[:\-–]?\s*([1-8]|FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH|SEVENTH|EIGHTH|I{1,3}|IV|VI{0,3}|VIII)\b/i);
            if (sm && sm[1]) {
                const val = sm[1].toUpperCase();
                detectedSem = /^[1-8]$/.test(val) ? parseInt(val, 10) : (semWords[val] || defaultSem);
            }
        }
        if (!detectedSem) detectedSem = defaultSem || 1;

        // 6. Title Detection: Look for course name after course code
        // Rule: "name of paper will never be same as department name"
        let detectedTitle = '';

        // Priority 1: Explicit COURSE TITLE: ...
        for (const txt of [cleanHeader, collapsedHeader]) {
            const explicitTitleMatch = txt.match(/(?:COURSE\s*TITLE|TITLE\s*OF\s*(?:THE\s*)?COURSE|PAPER\s*NAME)\s*[:\-–—\s]+([A-Za-z0-9\s,&'\/-]{3,90})/i);
            if (explicitTitleMatch && explicitTitleMatch[1]) {
                let cand = explicitTitleMatch[1].trim();
                cand = cand.replace(/\s*(?:Time|Duration|Max|Part|Section|Marks|MGU|Admission).*$/i, '').trim();
                if (cand && !this.isDepartmentNameOrCode(cand)) {
                    detectedTitle = cand;
                    break;
                }
            }
        }

        // Priority 2: Catalog Paper Match
        if (!detectedTitle && matchedCatalogPaper && matchedCatalogPaper.title && !this.isDepartmentNameOrCode(matchedCatalogPaper.title)) {
            detectedTitle = matchedCatalogPaper.title;
        }

        // Priority 3: Title after code (hyphen or space)
        if (!detectedTitle && bestCourseCode) {
            const escapedCode = bestCourseCode.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
            for (const txt of [cleanHeader, collapsedHeader]) {
                const hyphenMatch = txt.match(new RegExp(escapedCode + '\\s*[:\\-–—\\u2013\\u2014\\ufb01]+\\s*(?!(?:Part|Section|Answer|Max|Duration|Total|Skill|Time|Marks|Hours|Reg|Roll|No|Semester)\\b)([A-Za-z0-9][A-Za-z0-9\\s,\\/&\':\\-–]{2,90}?)(?=\\s*(?:\\n|\\r|\\(|\\bDuration\\b|\\bTime\\b|\\bMax(?:imum)?\\b|\\bTotal\\b|\\bPart\\b|\\bSection\\b|\\bAnswer\\b|\\d+\\s*hrs|\\d+\\s*hours|\\bMarks\\b|\\d{4}\\s*Admi|\\bAdmission\\b|$))', 'i'));
                if (hyphenMatch && hyphenMatch[1]) {
                    const cand = hyphenMatch[1].trim();
                    if (!this.isDepartmentNameOrCode(cand)) {
                        detectedTitle = cand;
                        break;
                    }
                }
                const spaceMatch = txt.match(new RegExp(escapedCode + '\\s+(?!(?:Part|Section|Answer|Max|Duration|Total|Skill|Time|Marks|Hours|Reg|Roll|No|Semester)\\b)([A-Za-z0-9][A-Za-z0-9\\s,\\/&\'-]{3,90}?)(?=\\s*(?:\\n|\\r|\\(|\\bDuration\\b|\\bTime\\b|\\bMax(?:imum)?\\b|\\bTotal\\b|\\bPart\\b|\\bSection\\b|\\bAnswer\\b|\\d+\\s*hrs|\\d+\\s*hours|\\bMarks\\b|\\d{4}\\s*Admi|\\bAdmission\\b|$))', 'i'));
                if (spaceMatch && spaceMatch[1]) {
                    const cand = spaceMatch[1].trim();
                    if (!this.isDepartmentNameOrCode(cand)) {
                        detectedTitle = cand;
                        break;
                    }
                }
            }
        }

        // Priority 4: Title before code
        if (!detectedTitle && bestCourseCode) {
            const escapedCode = bestCourseCode.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
            for (const txt of [cleanHeader, collapsedHeader]) {
                const beforeMatch = txt.match(new RegExp('(?:EXAMINATION|ONWARDS|DEGREE|HONOURS|\\)|PAPER)\\s*[:\\-–—\\u2013\\u2014\\ufb01\\s]*([A-Za-z][A-Za-z0-9\\s,\\/&\'-]{2,90}?)\\s*[:\\-–—\\u2013\\u2014\\ufb01\\s(]+' + escapedCode, 'i'));
                if (beforeMatch && beforeMatch[1]) {
                    const cand = beforeMatch[1].trim();
                    if (!this.isDepartmentNameOrCode(cand)) {
                        detectedTitle = cand;
                        break;
                    }
                }
            }
        }

        // Clean extracted title
        if (detectedTitle) {
            detectedTitle = detectedTitle
                .replace(/\s*MODEL\s*QUESTION\s*PAPER.*$/i, '')
                .replace(/\s*(?:TIME|DURATION|MAXIMUM\s*MARKS|TOTAL\s*MARKS).*$/i, '')
                .replace(/[:\-–—\s]+$/, '')
                .trim();
        }

        // Rule: "name of paper will never be same as department name"
        if (this.isDepartmentNameOrCode(detectedTitle)) {
            detectedTitle = '';
        }

        // Fallback title: Never allow title to be department name
        if (!detectedTitle || this.isDepartmentNameOrCode(detectedTitle)) {
            if (matchedCatalogPaper && matchedCatalogPaper.title && !this.isDepartmentNameOrCode(matchedCatalogPaper.title)) {
                detectedTitle = matchedCatalogPaper.title;
            } else if (bestCourseCode) {
                detectedTitle = `Course ${bestCourseCode}`;
            }
        }

        // 7. Department Detection
        let detectedDeptCode = (parsedInfo && parsedInfo.deptCode) || (matchedCatalogPaper ? (matchedCatalogPaper.parent_dept || matchedCatalogPaper.dept_code) : '');
        if (!detectedDeptCode && bestCourseCode) {
            const deptInCodeMatch = bestCourseCode.match(/(?:MG[1-8][A-Z]{3}|[A-Z]{3,4}[1-8])([A-Z]{3})/);
            if (deptInCodeMatch && deptInCodeMatch[1]) {
                const candDept = (this.departments || []).find(d => d.code === deptInCodeMatch[1]);
                if (candDept) detectedDeptCode = candDept.code;
            }
        }
        if (!detectedDeptCode && bestCourseCode) {
            for (const dept of (this.departments || [])) {
                if (bestCourseCode.includes(dept.code)) {
                    detectedDeptCode = dept.code;
                    break;
                }
            }
        }

        const isSignature = Boolean(parsedInfo && parsedInfo.isSignature || this.isSignatureCourse(bestCourseCode));

        return {
            isStart: isStart,
            courseCode: bestCourseCode,
            allCodes: normalizedCandidates,
            title: detectedTitle,
            deptCode: detectedDeptCode || 'MAT',
            semester: detectedSem,
            paperType: paperType,
            isSignature: isSignature,
            confidence: matchedCatalogPaper ? 'high' : (bestCourseCode ? 'medium' : 'low'),
            matchedPaper: matchedCatalogPaper
        };
    },

    detectCourseInfo(rawText, filename = '', ignoreFilename = false) {
        const headerInfo = this.extractPageHeaderCourseInfo(rawText);
        const combined = `${ignoreFilename ? '' : filename} ${rawText}`.toUpperCase();

        // 1. Detect if it's a Model Question Paper
        const isModelPaper = /MODEL\s*QUESTION|MODEL\s*QP|SAMPLE\s*QUESTION|MODEL\s*EXAMINATION/i.test(combined) ||
                             (!ignoreFilename && /model/i.test(filename));

        // 2. Build list of all known course codes from portal catalog
        const knownCoursesMap = new Map();
        (this.papers || []).forEach(p => {
            const cc = (p.course_code || '').trim().toUpperCase();
            if (cc && !knownCoursesMap.has(cc)) {
                knownCoursesMap.set(cc, p);
            }
            const norm = this.normalizeCourseCode(cc);
            if (norm && !knownCoursesMap.has(norm)) {
                knownCoursesMap.set(norm, p);
            }
        });

        const sortedKnownCodes = Array.from(knownCoursesMap.keys()).sort((a, b) => b.length - a.length);
        let matchedPaper = headerInfo.matchedPaper || null;
        let matchedCourseCode = headerInfo.courseCode || '';

        // Check filename only if NOT ignored (e.g. single upload)
        if (!ignoreFilename && !matchedCourseCode && filename) {
            const cleanFilename = filename.toUpperCase().replace(/\.PDF$/i, '');
            for (const code of sortedKnownCodes) {
                if (cleanFilename.includes(code)) {
                    matchedPaper = knownCoursesMap.get(code);
                    matchedCourseCode = code;
                    break;
                }
            }
        }

        // Check extracted PDF text if header check did not find known code
        if (!matchedCourseCode && rawText) {
            for (const code of sortedKnownCodes) {
                const escaped = code.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
                const regex = new RegExp(`(?:^|[^A-Z0-9])${escaped}(?:[^A-Z0-9]|$)`, 'i');
                if (regex.test(rawText)) {
                    matchedPaper = knownCoursesMap.get(code);
                    matchedCourseCode = code;
                    break;
                }
            }
        }

        // Heuristic pattern extraction if exact code not matched
        if (!matchedCourseCode) {
            const patterns = [
                /(?:COURSE\s*(?:CODE|NO\.?)|PAPER\s*CODE)\s*[:\-–]?\s*([A-Z0-9_\-]{5,18})/i,
                /\b(MG[1-8][A-Z]{2,8}[0-9]{1,4})\b/i,
                /\b([A-Z]{2,6}[1-8][A-Z]{2,8}[0-9]{1,4})\b/i
            ];

            for (const pat of patterns) {
                const m = rawText.match(pat) || (!ignoreFilename && filename ? filename.match(pat) : null);
                if (m && m[1]) {
                    const cand = this.normalizeCourseCode(m[1].trim().toUpperCase());
                    if (!cand.startsWith('SEMESTER') && cand.length >= 6) {
                        matchedCourseCode = cand;
                        break;
                    }
                }
            }
        }

        // Semester detection
        let detectedSem = headerInfo.semester || (matchedPaper ? matchedPaper.semester : null);
        if (!detectedSem) {
            const semInCodeMatch = matchedCourseCode.match(/(?:MG|([A-Z]{2,4}))([1-8])/i);
            if (semInCodeMatch && semInCodeMatch[2]) {
                detectedSem = parseInt(semInCodeMatch[2], 10);
            }
        }
        if (!detectedSem) detectedSem = 1;

        // QP Code detection
        let detectedQpCode = '';
        const qpMatch = rawText.match(/(?:QP\s*CODE|Q\.P\.\s*CODE)\s*[:\-–]?\s*([0-9]{6,10})/i) ||
                        rawText.match(/\b(24[0-9]{6})\b/) ||
                        (!ignoreFilename && filename ? filename.match(/\b(24[0-9]{6})\b/) : null);
        if (qpMatch && qpMatch[1]) {
            detectedQpCode = qpMatch[1].trim();
        } else if (matchedPaper && matchedPaper.qp_code) {
            detectedQpCode = matchedPaper.qp_code;
        }

        // Course Type detection
        let detectedCourseType = 'DSC';
        if (matchedPaper && matchedPaper.course_type) {
            detectedCourseType = matchedPaper.course_type;
        } else {
            const types = ['DSC', 'DSE', 'SEC', 'VAC', 'MDC', 'AEC', 'CCR', 'MDE', 'MIN'];
            for (const t of types) {
                if (matchedCourseCode.includes(t) || new RegExp(`\\b${t}\\b`, 'i').test(rawText)) {
                    detectedCourseType = t;
                    break;
                }
            }
        }

        // Department & Title detection
        // Rule: "name of paper will never be same as department name"
        let detectedTitle = (headerInfo.title && !this.isDepartmentNameOrCode(headerInfo.title))
            ? headerInfo.title
            : ((matchedPaper && matchedPaper.title && !this.isDepartmentNameOrCode(matchedPaper.title)) ? matchedPaper.title : '');
        let detectedDeptCode = headerInfo.deptCode || (matchedPaper ? (matchedPaper.parent_dept || matchedPaper.dept_code) : '');
        let isMinor = matchedPaper ? Boolean(matchedPaper.is_minor) : false;
        let minorName = matchedPaper ? (matchedPaper.minor_name || '') : '';
        let minorCode = matchedPaper ? (matchedPaper.dept_code || '') : '';

        // Extract Title from text if not yet identified: Look for course name after course code
        // Most probably separated by a hyphen '-' followed by course name (usually 5 to 15 words)
        if (!detectedTitle && matchedCourseCode && rawText) {
            const cleanText = rawText.replace(/\s+/g, ' ');
            const escapedCode = matchedCourseCode.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');

            // Pattern 1: [Code] [-–—:] [Course Name] (up to 140 chars / 5-15 words)
            const p1 = cleanText.match(new RegExp(escapedCode + '\\s*[:\\-–—\\u2013\\u2014\\ufb01]+\\s*(?!(?:Part|Section|Answer|Max|Duration|Total|Skill|Time|Marks|Hours|Reg|Roll|No|Semester)\\b)([A-Za-z0-9][A-Za-z0-9\\s,\\/&\':\\-–]{2,140}?)(?=\\s*(?:\\n|\\r|\\(|\\bDuration\\b|\\bTime\\b|\\bMax(?:imum)?\\b|\\bTotal\\b|\\bPart\\b|\\bSection\\b|\\bAnswer\\b|\\d+\\s*hrs|\\d+\\s*hours|\\bMarks\\b|\\d{4}\\s*Admi|\\bAdmission\\b|$))', 'i'));
            if (p1 && p1[1]) {
                const cand = p1[1].trim();
                if (!this.isDepartmentNameOrCode(cand)) {
                    detectedTitle = cand;
                }
            }
            if (!detectedTitle) {
                // Pattern 2: [Code] [Course Name] with whitespace
                const p2 = cleanText.match(new RegExp(escapedCode + '\\s+(?!(?:Part|Section|Answer|Max|Duration|Total|Skill|Time|Marks|Hours|Reg|Roll|No|Semester)\\b)([A-Za-z0-9][A-Za-z0-9\\s,\\/&\'-]{3,140}?)(?=\\s*(?:\\n|\\r|\\(|\\bDuration\\b|\\bTime\\b|\\bMax(?:imum)?\\b|\\bTotal\\b|\\bPart\\b|\\bSection\\b|\\bAnswer\\b|\\d+\\s*hrs|\\d+\\s*hours|\\bMarks\\b|\\d{4}\\s*Admi|\\bAdmission\\b|$))', 'i'));
                if (p2 && p2[1]) {
                    const cand = p2[1].trim();
                    if (!this.isDepartmentNameOrCode(cand)) {
                        detectedTitle = cand;
                    }
                } else {
                    const p3 = cleanText.match(new RegExp('(?:ONWARDS|EXAMINATION|\\))\\s*[:\\-–—\\u2013\\u2014\\ufb01\\s]*([A-Za-z][A-Za-z0-9\\s,\\/&\'-]{2,140}?)\\s*[:\\-–—\\u2013\\u2014\\ufb01\\s]+' + escapedCode, 'i'));
                    if (p3 && p3[1]) {
                        const cand = p3[1].trim();
                        if (!this.isDepartmentNameOrCode(cand)) {
                            detectedTitle = cand;
                        }
                    }
                }
            }
            if (detectedTitle) {
                detectedTitle = detectedTitle
                    .replace(/\s*MODEL\s*QUESTION\s*PAPER.*$/i, '')
                    .replace(/\s*(?:TIME|DURATION|MAXIMUM\s*MARKS|TOTAL\s*MARKS).*$/i, '')
                    .replace(/[:\-–—\s]+$/, '')
                    .trim();
            }
        }

        // Rule: "name of paper will never be same as department name"
        if (this.isDepartmentNameOrCode(detectedTitle)) {
            detectedTitle = '';
        }
        if (!detectedTitle) {
            if (matchedPaper && matchedPaper.title && !this.isDepartmentNameOrCode(matchedPaper.title)) {
                detectedTitle = matchedPaper.title;
            } else if (matchedCourseCode) {
                detectedTitle = `Course ${matchedCourseCode}`;
            }
        }

        // Rule: "Names of Course code will always have number at end."
        if (matchedCourseCode && !/\d$/.test(matchedCourseCode)) {
            matchedCourseCode = '';
        }

        if (!detectedDeptCode && matchedCourseCode) {
            for (const dept of (this.departments || [])) {
                if (matchedCourseCode.includes(dept.code)) {
                    detectedDeptCode = dept.code;
                    break;
                }
            }
        }
        if (!detectedDeptCode && matchedCourseCode) {
            const m = matchedCourseCode.match(/(?:MG[1-8][A-Z]{3}|[A-Z]{3,4}[1-8])([A-Z]{3})/);
            if (m && m[1]) {
                const candDept = (this.departments || []).find(d => d.code === m[1]);
                if (candDept) detectedDeptCode = candDept.code;
            }
        }

        // Exam Session Name
        let examName = 'MGU-UGP (Honours) 2024 Admission Regular Examination';
        if (rawText.includes('SUPPLEMENTARY')) {
            examName = 'MGU-UGP (Honours) 2024 Admission Supplementary Examination';
        }

        const isSignature = Boolean(headerInfo.isSignature || this.isSignatureCourse(matchedCourseCode));

        return {
            courseCode: matchedCourseCode,
            title: detectedTitle,
            deptCode: detectedDeptCode || 'MAT',
            semester: detectedSem,
            courseType: detectedCourseType,
            paperType: headerInfo.paperType || 'THEORY',
            isMinor: isMinor,
            minorName: minorName,
            minorCode: minorCode,
            qpCode: detectedQpCode,
            examName: examName,
            isModelPaper: isModelPaper,
            isSignature: isSignature,
            confidence: matchedPaper ? 'high' : (matchedCourseCode ? 'medium' : 'low'),
            matchedPaper: matchedPaper
        };
    },

    checkPaperDuplicate(courseCode, qpCode, isModelPaper, paperType = 'THEORY') {
        if (!courseCode || !courseCode.trim()) {
            return { isDuplicate: false, message: 'Please enter or scan a valid course code.' };
        }

        const cc = courseCode.trim().toUpperCase();
        const existing = (this.papers || []).find(p => (p.course_code || '').trim().toUpperCase() === cc);

        if (isModelPaper) {
            if (existing && existing.model_papers && existing.model_papers.length > 0) {
                const pt = (paperType || 'THEORY').toUpperCase();
                const hasSameType = existing.model_papers.some(m => (m.paper_type || 'THEORY').toUpperCase() === pt);
                if (hasSameType) {
                    return {
                        isDuplicate: true,
                        type: 'model_exists',
                        paper: existing,
                        message: `A ${pt.toLowerCase()} model question paper already exists for course ${cc} ("${existing.title}"). Adding this will replace it.`
                    };
                }
            }
            return { isDuplicate: false, paper: existing, message: 'No existing model paper found for this course code.' };
        }

        // For regular University Exam QP:
        // Check 1: QP Code duplicate across ANY paper
        if (qpCode && qpCode.trim()) {
            const qpClean = qpCode.trim();
            const qpDuplicate = (this.papers || []).find(p => p.qp_code === qpClean && (p.course_code || '').trim().toUpperCase() !== cc);
            if (qpDuplicate) {
                return {
                    isDuplicate: true,
                    type: 'qp_conflict',
                    paper: qpDuplicate,
                    message: `QP Code "${qpClean}" is already registered to course ${qpDuplicate.course_code} ("${qpDuplicate.title}").`
                };
            }
        }

        // Check 2: Does this course code already have an active question paper?
        if (existing && existing.has_qp) {
            return {
                isDuplicate: true,
                type: 'qp_exists',
                paper: existing,
                message: `Question Paper for course ${cc} ("${existing.title}") already exists in website (QP Code: ${existing.qp_code || 'N/A'}).`
            };
        }

        return {
            isDuplicate: false,
            paper: existing,
            message: 'No duplicate found. Course code is clear for new ingestion.'
        };
    },

    previewMasterPdf(e) {
        if (e) {
            e.preventDefault();
            e.stopPropagation();
        }
        if (this.masterPdfUrl) {
            PDFViewer.openDirect(this.masterPdfUrl, this.selectedSmartPdfFile?.name || 'Master Upload', 'MASTER');
        }
    },

    previewSplitPdf(idx) {
        const item = this.adminSplitPapers[idx];
        if (!item || !item.blobUrl) return;
        PDFViewer.openDirect(item.blobUrl, `${item.courseCode || 'SPLIT'} - ${item.title || 'Model QP'} (Pages ${item.startPage}–${item.endPage})`, item.courseCode || 'MODEL');
    },

    async slicePdfPages(srcDoc, startPage, endPage) {
        if (!srcDoc || typeof PDFLib === 'undefined') {
            return null;
        }
        try {
            const subDoc = await PDFLib.PDFDocument.create();
            const indices = [];
            for (let p = startPage - 1; p <= endPage - 1; p++) {
                indices.push(p);
            }
            const copied = await subDoc.copyPages(srcDoc, indices);
            copied.forEach(p => subDoc.addPage(p));
            const subBytes = await subDoc.save();
            const blob = new Blob([subBytes], { type: 'application/pdf' });
            const blobUrl = URL.createObjectURL(blob);

            const base64 = await new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = () => resolve(reader.result);
                reader.onerror = reject;
                reader.readAsDataURL(blob);
            });

            return { blob, blobUrl, base64, bytes: subBytes };
        } catch (err) {
            console.error('Error slicing PDF pages with pdf-lib:', err);
            return null;
        }
    },

    detectPaperBoundaries(pagesText, numPages) {
        if (numPages <= 1) {
            return [{ startPage: 1, endPage: 1, pageCount: 1, detectedCode: '', detectedTitle: '' }];
        }

        // Step 1: Analyze header of EVERY single page individually
        const pageData = [];
        for (let i = 0; i < numPages; i++) {
            const raw = pagesText[i] || '';
            const info = this.extractPageHeaderCourseInfo(raw);
            pageData.push({
                idx: i,
                pageNumber: i + 1,
                info: info
            });
        }

        // Step 2: Track boundaries. Page 0 (Page 1) always starts the first paper.
        const segments = [];
        let currentStart = 0;
        let currentCode = pageData[0].info.courseCode || '';

        for (let i = 1; i < numPages; i++) {
            const pd = pageData[i];
            const candCode = pd.info.courseCode || '';
            const isStart = pd.info.isStart;
            const pagesElapsed = i - currentStart;

            let isNewPaper = false;

            // Trigger 1: Page has a new course code different from the current paper's code
            if (candCode && currentCode && (candCode !== currentCode) && pagesElapsed >= 1) {
                isNewPaper = true;
            }
            // Trigger 2: Explicit exam start header encountered after at least 1 page
            else if (isStart && pagesElapsed >= 1) {
                isNewPaper = true;
            }
            // Trigger 3: Course code found on page where previously no code was known, plus start header
            else if (candCode && !currentCode && isStart && pagesElapsed >= 1) {
                isNewPaper = true;
            }
            // Trigger 4: Safety maximum cap for extraordinarily long compilation chunks
            else if (pagesElapsed >= 25) {
                isNewPaper = true;
            }

            if (isNewPaper) {
                segments.push({
                    startPage: currentStart + 1,
                    endPage: i,
                    pageCount: pagesElapsed,
                    detectedCode: currentCode,
                    startInfo: pageData[currentStart].info
                });
                currentStart = i;
                currentCode = candCode;
            } else {
                if (!currentCode && candCode) {
                    currentCode = candCode;
                }
            }
        }

        // Push the final segment to the end of the document
        segments.push({
            startPage: currentStart + 1,
            endPage: numPages,
            pageCount: numPages - currentStart,
            detectedCode: currentCode,
            startInfo: pageData[currentStart].info
        });

        return segments;
    },

    async buildSplitPapersFromSegments(segments) {
        if (!this.adminPdfSourceDoc || !segments || segments.length === 0) return;

        const spinner = document.getElementById('adminScanSpinner');
        const spinnerText = document.getElementById('adminScanSpinnerText');
        if (spinner) spinner.classList.remove('hidden');

        this.adminSplitPapers = [];

        for (let s = 0; s < segments.length; s++) {
            const seg = segments[s];
            if (spinnerText) spinnerText.textContent = `Splitting paper ${s + 1} of ${segments.length} (Pages ${seg.startPage}–${seg.endPage})...`;

            // Slice pages into independent PDF
            const sliced = await this.slicePdfPages(this.adminPdfSourceDoc, seg.startPage, seg.endPage);

            // Combine text of this segment's pages
            const segPages = (this.adminPagesText || []).slice(seg.startPage - 1, seg.endPage);
            const firstPageText = segPages[0] || '';
            const segText = segPages.join(' ');

            // Header info from first page of this paper (where course code & title reside!)
            const headerInfo = this.extractPageHeaderCourseInfo(firstPageText);

            // Detect course info from full segment text, strictly ignoring outer filename!
            const detected = this.detectCourseInfo(segText, '', true);

            // Merge detected info
            const finalCode = headerInfo.courseCode || detected.courseCode || seg.detectedCode || '';
            const finalPaperType = headerInfo.paperType || 'THEORY';
            const finalSem = headerInfo.semester || detected.semester || 1;
            const confidence = headerInfo.confidence || detected.confidence || (finalCode ? 'medium' : 'low');

            // Support multiple codes per segment (e.g. Botany P.1-2 for both BOT and BBT)
            const codesToProcess = (headerInfo.allCodes && headerInfo.allCodes.length > 0)
                ? headerInfo.allCodes
                : [finalCode];

            for (const cCode of codesToProcess) {
                if (!cCode) continue;
                const dupResult = this.checkPaperDuplicate(cCode, detected.qpCode, true, finalPaperType);
                const isSignature = Boolean(this.isSignatureCourse(cCode));
                let cTitle = headerInfo.title || detected.title;
                if (this.isDepartmentNameOrCode(cTitle)) cTitle = '';
                const catCourse = (this.papers || []).find(p => (p.course_code || '').trim().toUpperCase() === cCode);
                if (catCourse && catCourse.title && !this.isDepartmentNameOrCode(catCourse.title)) {
                    cTitle = catCourse.title;
                }
                if (!cTitle) {
                    cTitle = cCode ? `Model QP - ${cCode}` : '';
                }
                const cDept = (catCourse && (catCourse.parent_dept || catCourse.dept_code)) || headerInfo.deptCode || detected.deptCode || 'MAT';

                this.adminSplitPapers.push({
                    idx: this.adminSplitPapers.length,
                    startPage: seg.startPage,
                    endPage: seg.endPage,
                    pageCount: seg.pageCount,
                    courseCode: cCode,
                    title: cTitle,
                    deptCode: cDept,
                    semester: (catCourse && catCourse.semester) || finalSem,
                    paperType: finalPaperType,
                    isSignature: isSignature,
                    courseType: (catCourse && catCourse.course_type) || detected.courseType || 'DSC',
                    isMinor: detected.isMinor,
                    minorName: detected.minorName,
                    minorCode: detected.minorCode,
                    qpCode: detected.qpCode,
                    examName: detected.examName,
                    confidence: confidence,
                    isDuplicate: dupResult.isDuplicate,
                    dupMessage: dupResult.message,
                    existingPaper: dupResult.paper,
                    blob: sliced ? sliced.blob : null,
                    blobUrl: sliced ? sliced.blobUrl : this.masterPdfUrl,
                    base64: sliced ? sliced.base64 : '',
                    published: false
                });
            }
        }

        if (spinner) spinner.classList.add('hidden');

        // Hide single form, show multi split view
        document.getElementById('adminUploadForm')?.classList.add('hidden');
        document.getElementById('adminScanResultContainer')?.classList.add('hidden');
        document.getElementById('adminMultiSplitContainer')?.classList.remove('hidden');

        this.renderSplitCardsUI();
    },

    parseCustomPageRanges(rangeStr, maxPages) {
        if (!rangeStr || !rangeStr.trim()) return null;
        const parts = rangeStr.split(/[,;\n]+/).map(s => s.trim()).filter(Boolean);
        if (parts.length === 0) return null;

        const segments = [];
        for (const part of parts) {
            if (part.includes('-')) {
                const [sStr, eStr] = part.split('-');
                const start = parseInt(sStr.trim(), 10);
                const end = parseInt(eStr.trim(), 10);
                if (!isNaN(start) && !isNaN(end) && start >= 1 && end >= start && start <= maxPages) {
                    const boundedEnd = Math.min(end, maxPages);
                    segments.push({
                        startPage: start,
                        endPage: boundedEnd,
                        pageCount: boundedEnd - start + 1
                    });
                }
            } else {
                const page = parseInt(part.trim(), 10);
                if (!isNaN(page) && page >= 1 && page <= maxPages) {
                    segments.push({
                        startPage: page,
                        endPage: page,
                        pageCount: 1
                    });
                }
            }
        }
        return segments.length > 0 ? segments : null;
    },

    applySplitPreset(pageSize) {
        if (!this.adminNumPages || !this.adminPdfSourceDoc) {
            alert('Please upload a PDF document first.');
            return;
        }
        const maxPages = this.adminNumPages;
        const segments = [];
        for (let p = 1; p <= maxPages; p += pageSize) {
            const end = Math.min(p + pageSize - 1, maxPages);
            segments.push({
                startPage: p,
                endPage: end,
                pageCount: end - p + 1
            });
        }
        const rangeInput = document.getElementById('adminCustomSplitInput');
        if (rangeInput) {
            rangeInput.value = segments.map(s => s.startPage === s.endPage ? `${s.startPage}` : `${s.startPage}-${s.endPage}`).join(', ');
        }
        this.buildSplitPapersFromSegments(segments);
    },

    applyCustomSplitInput() {
        if (!this.adminNumPages || !this.adminPdfSourceDoc) {
            alert('Please upload a PDF document first.');
            return;
        }
        const input = document.getElementById('adminCustomSplitInput');
        const val = input ? input.value.trim() : '';
        if (!val) {
            alert('Please enter page ranges, e.g. 1-2, 3-4, 5-7 or 1, 2-3, 4-5');
            return;
        }
        const segments = this.parseCustomPageRanges(val, this.adminNumPages);
        if (!segments) {
            alert(`Invalid page ranges. Please enter valid pages between 1 and ${this.adminNumPages} (e.g. 1-2, 3-4)`);
            return;
        }
        this.buildSplitPapersFromSegments(segments);
    },

    reRunAutoBoundaryDetection() {
        if (!this.adminNumPages || !this.adminPdfSourceDoc || !this.adminPagesText) {
            alert('Please upload a PDF document first.');
            return;
        }
        const segments = this.detectPaperBoundaries(this.adminPagesText, this.adminNumPages);
        const rangeInput = document.getElementById('adminCustomSplitInput');
        if (rangeInput) {
            rangeInput.value = segments.map(s => s.startPage === s.endPage ? `${s.startPage}` : `${s.startPage}-${s.endPage}`).join(', ');
        }
        this.buildSplitPapersFromSegments(segments);
    },

    async handleSmartPdfFileSelected(e) {
        const files = e.target.files;
        if (!files || files.length === 0) return;
        if (files.length === 1) {
            this.processSmartPdfFile(files[0]);
        } else {
            await this.processMultipleSmartPdfFiles(Array.from(files));
        }
    },

    async processMultipleSmartPdfFiles(files) {
        const spinner = document.getElementById('adminScanSpinner');
        const spinnerText = document.getElementById('adminScanSpinnerText');
        if (spinner) spinner.classList.remove('hidden');

        this.adminSplitPapers = [];
        let totalDocsPages = 0;

        for (let fIdx = 0; fIdx < files.length; fIdx++) {
            const file = files[fIdx];
            if (spinnerText) spinnerText.textContent = `Processing PDF ${fIdx + 1} of ${files.length}: ${file.name}...`;

            try {
                const arrayBuffer = await file.arrayBuffer();
                pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
                const loadingTask = pdfjsLib.getDocument({ data: arrayBuffer });
                const pdf = await loadingTask.promise;
                const numPages = pdf.numPages;
                totalDocsPages += numPages;

                let srcDoc = null;
                if (typeof PDFLib !== 'undefined') {
                    try {
                        srcDoc = await PDFLib.PDFDocument.load(arrayBuffer);
                    } catch (err) {
                        console.warn('PDFLib error:', err);
                    }
                }

                const pagesText = [];
                for (let i = 1; i <= numPages; i++) {
                    const page = await pdf.getPage(i);
                    const tokenized = await page.getTextContent();
                    pagesText.push(tokenized.items.map(it => it.str).join(' '));
                }

                const segments = this.detectPaperBoundaries(pagesText, numPages);

                for (let s = 0; s < segments.length; s++) {
                    const seg = segments[s];
                    const sliced = srcDoc ? await this.slicePdfPages(srcDoc, seg.startPage, seg.endPage) : null;
                    const segPages = pagesText.slice(seg.startPage - 1, seg.endPage);
                    const firstPageText = segPages[0] || '';
                    const segText = segPages.join(' ');
                    const headerInfo = this.extractPageHeaderCourseInfo(firstPageText);
                    const detected = this.detectCourseInfo(segText, '', true);

                    const finalCode = headerInfo.courseCode || detected.courseCode || seg.detectedCode || '';
                    const finalPaperType = headerInfo.paperType || 'THEORY';
                    const codesToProcess = (headerInfo.allCodes && headerInfo.allCodes.length > 0)
                        ? headerInfo.allCodes
                        : [finalCode];

                    for (const cCode of codesToProcess) {
                        if (!cCode) continue;
                        const dupResult = this.checkPaperDuplicate(cCode, detected.qpCode, true, finalPaperType);
                        const isSignature = Boolean(this.isSignatureCourse(cCode));
                        let cTitle = headerInfo.title || detected.title;
                        if (this.isDepartmentNameOrCode(cTitle)) cTitle = '';
                        const catCourse = (this.papers || []).find(p => (p.course_code || '').trim().toUpperCase() === cCode);
                        if (catCourse && catCourse.title && !this.isDepartmentNameOrCode(catCourse.title)) {
                            cTitle = catCourse.title;
                        }
                        if (!cTitle) {
                            cTitle = cCode ? `Model QP - ${cCode}` : '';
                        }
                        const cDept = (catCourse && (catCourse.parent_dept || catCourse.dept_code)) || headerInfo.deptCode || detected.deptCode || 'MAT';

                        this.adminSplitPapers.push({
                            idx: this.adminSplitPapers.length,
                            startPage: seg.startPage,
                            endPage: seg.endPage,
                            pageCount: seg.pageCount,
                            courseCode: cCode,
                            title: cTitle,
                            deptCode: cDept,
                            semester: (catCourse && catCourse.semester) || headerInfo.semester || 1,
                            paperType: finalPaperType,
                            isSignature: isSignature,
                            courseType: (catCourse && catCourse.course_type) || detected.courseType || 'DSC',
                            isMinor: detected.isMinor,
                            minorName: detected.minorName,
                            minorCode: detected.minorCode,
                            qpCode: detected.qpCode,
                            examName: detected.examName,
                            confidence: headerInfo.confidence || 'medium',
                            isDuplicate: dupResult.isDuplicate,
                            dupMessage: dupResult.message,
                            existingPaper: dupResult.paper,
                            blob: sliced ? sliced.blob : null,
                            blobUrl: sliced ? sliced.blobUrl : '',
                            base64: sliced ? sliced.base64 : '',
                            published: false
                        });
                    }
                }
            } catch (fileErr) {
                console.error(`Error processing ${file.name}:`, fileErr);
            }
        }

        if (spinner) spinner.classList.add('hidden');

        const badge = document.getElementById('adminSelectedFileNameBadge');
        const nameEl = document.getElementById('adminSelectedFileName');
        const sizeEl = document.getElementById('adminSelectedFileSize');
        if (nameEl) nameEl.textContent = `${files.length} Compilation PDFs`;
        if (sizeEl) sizeEl.textContent = `(${this.adminSplitPapers.length} Papers Detected)`;
        if (badge) badge.classList.remove('hidden');

        const totalPagesBadge = document.getElementById('adminTotalPagesCountBadge');
        if (totalPagesBadge) totalPagesBadge.textContent = `${totalDocsPages} pages total`;

        document.getElementById('adminUploadForm')?.classList.add('hidden');
        document.getElementById('adminScanResultContainer')?.classList.add('hidden');
        document.getElementById('adminMultiSplitContainer')?.classList.remove('hidden');

        this.renderSplitCardsUI();
    },

    async processSmartPdfFile(file) {
        this.selectedSmartPdfFile = file;
        this.masterPdfUrl = URL.createObjectURL(file);

        // Display selected file badge
        const badge = document.getElementById('adminSelectedFileNameBadge');
        const nameEl = document.getElementById('adminSelectedFileName');
        const sizeEl = document.getElementById('adminSelectedFileSize');
        if (nameEl) nameEl.textContent = file.name;
        if (sizeEl) sizeEl.textContent = `(${(file.size / (1024 * 1024)).toFixed(2)} MB)`;
        if (badge) badge.classList.remove('hidden');

        // Show scanner spinner
        const spinner = document.getElementById('adminScanSpinner');
        const spinnerText = document.getElementById('adminScanSpinnerText');
        if (spinner) spinner.classList.remove('hidden');
        if (spinnerText) spinnerText.textContent = 'Parsing PDF document...';

        try {
            const arrayBuffer = await file.arrayBuffer();

            // Load via PDF.js for text extraction
            pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
            const loadingTask = pdfjsLib.getDocument({ data: arrayBuffer });
            const pdf = await loadingTask.promise;
            const numPages = pdf.numPages;

            // Load via PDFLib for page slicing
            let srcDoc = null;
            if (typeof PDFLib !== 'undefined') {
                try {
                    srcDoc = await PDFLib.PDFDocument.load(arrayBuffer);
                } catch (err) {
                    console.warn('PDFLib failed to load document:', err);
                }
            }

            // Extract all pages text
            const pagesText = [];
            for (let i = 1; i <= numPages; i++) {
                if (spinnerText) spinnerText.textContent = `Reading PDF page ${i} of ${numPages}...`;
                const page = await pdf.getPage(i);
                const tokenized = await page.getTextContent();
                const pageText = tokenized.items.map(it => it.str).join(' ');
                pagesText.push(pageText);
            }

            // Store references on instance for instantaneous re-splitting / custom presets
            this.adminPdfSourceDoc = srcDoc;
            this.adminPagesText = pagesText;
            this.adminNumPages = numPages;

            // Detect boundaries
            if (spinnerText) spinnerText.textContent = 'Analyzing course boundaries and checking catalog...';
            const segments = this.detectPaperBoundaries(pagesText, numPages);

            // Populate total pages badge
            const totalPagesBadge = document.getElementById('adminTotalPagesCountBadge');
            if (totalPagesBadge) totalPagesBadge.textContent = `${numPages} pages`;

            // Pre-fill custom split input with detected ranges
            const customSplitInput = document.getElementById('adminCustomSplitInput');
            if (customSplitInput) {
                customSplitInput.value = segments.map(s => s.startPage === s.endPage ? `${s.startPage}` : `${s.startPage}-${s.endPage}`).join(', ');
            }

            // Check if overall document is Model Paper
            const combinedAllText = pagesText.join(' ');
            const isDocModel = /MODEL\s*QUESTION|MODEL\s*QP|SAMPLE\s*QUESTION/i.test(combinedAllText) || /model/i.test(file.name);
            if (isDocModel && this.currentPaperCategory !== 'MODEL') {
                this.handlePaperCategoryChange('MODEL');
                const radioModel = document.querySelector('input[name="adminPaperCategory"][value="MODEL"]');
                if (radioModel) radioModel.checked = true;
            }

            if (numPages > 1 && srcDoc) {
                // MULTI-PAGE DOCUMENT: Always use multi-split mode so admin sees all individual papers,
                // previews each split PDF, and can adjust split boundaries with 1 click
                await this.buildSplitPapersFromSegments(segments);
            } else {
                // SINGLE PAPER MODE (numPages === 1)
                this.adminSplitPapers = [];
                document.getElementById('adminMultiSplitContainer')?.classList.add('hidden');
                document.getElementById('adminUploadForm')?.classList.remove('hidden');

                const detected = this.detectCourseInfo(combinedAllText, file.name);

                if (detected.isModelPaper && this.currentPaperCategory !== 'MODEL') {
                    this.handlePaperCategoryChange('MODEL');
                    const radioModel = document.querySelector('input[name="adminPaperCategory"][value="MODEL"]');
                    if (radioModel) radioModel.checked = true;
                }

                // Fill form fields
                const codeInput = document.getElementById('adminUploadCourseCode');
                const titleInput = document.getElementById('adminUploadTitle');
                const deptSelect = document.getElementById('adminUploadDept');
                const semSelect = document.getElementById('adminUploadSemester');
                const ctypeSelect = document.getElementById('adminUploadCourseType');
                const isMinorCheck = document.getElementById('adminUploadIsMinor');
                const minorNameInput = document.getElementById('adminUploadMinorName');
                const minorCodeInput = document.getElementById('adminUploadMinorCode');
                const qpCodeInput = document.getElementById('adminUploadQpCode');
                const examNameInput = document.getElementById('adminUploadExamName');

                if (codeInput && detected.courseCode) codeInput.value = detected.courseCode;
                if (titleInput && detected.title) titleInput.value = detected.title;
                if (deptSelect && detected.deptCode) deptSelect.value = detected.deptCode;
                if (semSelect && detected.semester) semSelect.value = String(detected.semester);
                if (ctypeSelect && detected.courseType) ctypeSelect.value = detected.courseType;
                if (qpCodeInput && detected.qpCode) qpCodeInput.value = detected.qpCode;
                if (examNameInput && detected.examName) examNameInput.value = detected.examName;

                if (isMinorCheck) {
                    isMinorCheck.checked = Boolean(detected.isMinor);
                    this.toggleAdminMinorFields();
                    if (minorNameInput && detected.minorName) minorNameInput.value = detected.minorName;
                    if (minorCodeInput && detected.minorCode) minorCodeInput.value = detected.minorCode;
                }

                const isModel = this.currentPaperCategory === 'MODEL';
                const dupResult = this.checkPaperDuplicate(detected.courseCode, detected.qpCode, isModel);

                this.renderScanResultUI(detected, dupResult);
            }
        } catch (err) {
            console.error('Error processing PDF:', err);
            alert(`Failed to process PDF: ${err.message}`);
        } finally {
            if (spinner) spinner.classList.add('hidden');
        }
    },

    setSplitCardsFilter(filter) {
        this.splitCardsFilter = filter;
        ['ALL', 'THEORY', 'PRACTICAL', 'READY', 'DUP'].forEach(f => {
            const btn = document.getElementById(`splitFilter_${f}`);
            if (btn) {
                if (f === filter) {
                    btn.className = 'px-2.5 py-1 rounded-lg text-xs font-bold bg-indigo-600 text-white shadow-2xs transition';
                } else {
                    btn.className = 'px-2.5 py-1 rounded-lg text-xs font-semibold bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 text-slate-700 dark:text-slate-200 transition';
                }
            }
        });
        this.renderSplitCardsUI();
    },

    handleSplitCardsSearch(q) {
        this.splitCardsSearchQuery = (q || '').trim().toLowerCase();
        this.renderSplitCardsUI();
    },

    handleSplitPaperTypeChange(idx, val) {
        const item = this.adminSplitPapers[idx];
        if (item) {
            item.paperType = val;
        }
    },

    renderSplitCardsUI() {
        const container = document.getElementById('adminSplitCardsContainer');
        const totalBadge = document.getElementById('adminSplitTotalBadge');
        if (!container) return;

        const totalPapers = this.adminSplitPapers.length;
        const totalPages = this.adminSplitPapers.reduce((sum, p) => sum + p.pageCount, 0);
        const dupCount = this.adminSplitPapers.filter(p => p.isDuplicate).length;
        const verifiedCount = totalPapers - dupCount;
        const theoryCount = this.adminSplitPapers.filter(p => (p.paperType || 'THEORY') === 'THEORY').length;
        const practicalCount = this.adminSplitPapers.filter(p => (p.paperType || 'THEORY') === 'PRACTICAL').length;

        if (totalBadge) {
            totalBadge.textContent = `${totalPapers} Papers (${theoryCount} Theory, ${practicalCount} Practical) • ${totalPages} Pages Total (${verifiedCount} Ready, ${dupCount} Existing)`;
        }

        // Update pill counts if badges exist
        const allBtn = document.getElementById('splitFilter_ALL');
        const theoryBtn = document.getElementById('splitFilter_THEORY');
        const practicalBtn = document.getElementById('splitFilter_PRACTICAL');
        const readyBtn = document.getElementById('splitFilter_READY');
        const dupBtn = document.getElementById('splitFilter_DUP');
        if (allBtn) allBtn.textContent = `All (${totalPapers})`;
        if (theoryBtn) theoryBtn.textContent = `Theory (${theoryCount})`;
        if (practicalBtn) practicalBtn.textContent = `Practical (${practicalCount})`;
        if (readyBtn) readyBtn.textContent = `Ready (${verifiedCount})`;
        if (dupBtn) dupBtn.textContent = `In Catalog (${dupCount})`;

        const deptOptionsHtml = (selectedCode) => {
            return '<option value="">-- Select Department --</option>' +
                this.departments.map(d => `<option value="${d.code}" ${d.code === selectedCode ? 'selected' : ''}>${d.name} (${d.code})</option>`).join('');
        };

        const semOptionsHtml = (selectedSem) => {
            let html = '';
            for (let s = 1; s <= 8; s++) {
                html += `<option value="${s}" ${s === Number(selectedSem) ? 'selected' : ''}>Semester ${s}</option>`;
            }
            return html;
        };

        // Filter items according to current filter & search query
        let filteredItems = this.adminSplitPapers.slice();

        if (this.splitCardsFilter === 'THEORY') {
            filteredItems = filteredItems.filter(p => (p.paperType || 'THEORY') === 'THEORY');
        } else if (this.splitCardsFilter === 'PRACTICAL') {
            filteredItems = filteredItems.filter(p => (p.paperType || 'THEORY') === 'PRACTICAL');
        } else if (this.splitCardsFilter === 'READY') {
            filteredItems = filteredItems.filter(p => !p.isDuplicate);
        } else if (this.splitCardsFilter === 'DUP') {
            filteredItems = filteredItems.filter(p => p.isDuplicate);
        }

        if (this.splitCardsSearchQuery) {
            const q = this.splitCardsSearchQuery;
            filteredItems = filteredItems.filter(p => {
                return (p.courseCode && p.courseCode.toLowerCase().includes(q)) ||
                       (p.title && p.title.toLowerCase().includes(q)) ||
                       (p.deptCode && p.deptCode.toLowerCase().includes(q)) ||
                       String(p.startPage).includes(q) ||
                       String(p.endPage).includes(q);
            });
        }

        // Sort split cards: keep signature courses (college-specific syllabus) at the bottom
        filteredItems.sort((a, b) => {
            const aSig = Boolean(a.isSignature || this.isSignatureCourse(a.courseCode));
            const bSig = Boolean(b.isSignature || this.isSignatureCourse(b.courseCode));
            if (aSig !== bSig) return aSig ? 1 : -1;
            return a.idx - b.idx;
        });

        if (filteredItems.length === 0) {
            container.innerHTML = `
                <div class="p-8 text-center bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-xs space-y-2">
                    <i class="bi bi-funnel text-2xl text-slate-400"></i>
                    <p class="text-xs font-semibold text-slate-600 dark:text-slate-300">No split papers match the current filter or search query.</p>
                    <button type="button" onclick="App.setSplitCardsFilter('ALL'); document.getElementById('adminSplitSearchInput').value='';" class="px-3 py-1.5 rounded-lg text-xs font-bold bg-indigo-50 text-indigo-600 dark:bg-indigo-950/40 dark:text-indigo-300">
                        Reset Filters
                    </button>
                </div>
            `;
            return;
        }

        container.innerHTML = filteredItems.map(item => {
            const idx = item.idx;
            const isDup = item.isDuplicate;
            const isPublished = item.published;
            const isSig = Boolean(item.isSignature || this.isSignatureCourse(item.courseCode));

            const confidenceBadge = item.confidence === 'high'
                ? '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-300 flex items-center gap-1"><i class="bi bi-check-circle-fill"></i> Catalog Match</span>'
                : '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800 dark:bg-blue-900/60 dark:text-blue-300 flex items-center gap-1"><i class="bi bi-magic"></i> Auto-Detected</span>';

            const dupBadge = isDup
                ? '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-900 dark:bg-amber-900/60 dark:text-amber-200 flex items-center gap-1"><i class="bi bi-exclamation-triangle-fill text-amber-600"></i> In Catalog</span>'
                : '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-200 flex items-center gap-1"><i class="bi bi-check2-circle text-emerald-600"></i> Ready</span>';

            const typeBadge = item.paperType === 'PRACTICAL'
                ? '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-100 text-purple-800 dark:bg-purple-900/60 dark:text-purple-300 flex items-center gap-1"><i class="bi bi-gear-fill"></i> Practical</span>'
                : '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-sky-100 text-sky-800 dark:bg-sky-900/60 dark:text-sky-300 flex items-center gap-1"><i class="bi bi-book-fill"></i> Theory</span>';

            const sigBadge = isSig
                ? '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800 dark:bg-amber-950/70 dark:text-amber-300 border border-amber-300 dark:border-amber-700 flex items-center gap-1" title="Signature Course (College specific syllabus)"><i class="bi bi-pen-fill text-[9px]"></i> Signature</span>'
                : '';

            const dupAlert = isDup ? `
                <div class="p-3 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-900/40 text-xs text-amber-900 dark:text-amber-200 flex items-center justify-between gap-2 flex-wrap">
                    <div class="flex items-center gap-1.5 font-medium">
                        <i class="bi bi-exclamation-triangle-fill text-amber-600 shrink-0"></i>
                        <span>${item.dupMessage}</span>
                    </div>
                    ${item.existingPaper ? `
                    <button type="button" onclick="App.previewPaper(this, App.findPaperById('${item.existingPaper.id}'), 'QP')" class="px-2.5 py-1 rounded-lg text-xs font-semibold bg-amber-200 hover:bg-amber-300 dark:bg-amber-800 dark:hover:bg-amber-700 text-amber-950 dark:text-amber-100 flex items-center gap-1 transition shrink-0">
                        <i class="bi bi-eye"></i> View Existing
                    </button>` : ''}
                </div>
            ` : '';

            return `
                <div class="p-5 rounded-2xl bg-white dark:bg-slate-800 border ${isPublished ? 'border-emerald-500 dark:border-emerald-500/80 bg-emerald-50/10' : (isDup ? 'border-amber-300 dark:border-amber-700/80' : 'border-slate-200 dark:border-slate-700')} shadow-xs space-y-4 transition" id="splitCard_${idx}">
                    <!-- Card Top Header -->
                    <div class="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-100 dark:border-slate-700/80">
                        <div class="flex items-center gap-2 flex-wrap">
                            <span class="px-2.5 py-1 rounded-lg text-xs font-mono font-bold bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-2xs">
                                PAPER #${idx + 1}
                            </span>
                            <span class="px-2.5 py-1 rounded-lg text-xs font-mono font-bold bg-blue-50 dark:bg-blue-950/50 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-900/50 flex items-center gap-1">
                                <i class="bi bi-file-earmark-break"></i> Pages ${item.startPage} – ${item.endPage} (${item.pageCount} ${item.pageCount === 1 ? 'page' : 'pages'})
                            </span>
                            ${typeBadge}
                            ${sigBadge}
                            ${confidenceBadge}
                            ${dupBadge}
                        </div>

                        <div class="flex items-center gap-2">
                            <!-- PREVIEW BUTTON: Opens this exact split 1-4 page PDF -->
                            <button type="button" onclick="App.previewSplitPdf(${idx})" class="px-3.5 py-1.5 rounded-xl text-xs font-bold bg-indigo-600 hover:bg-indigo-500 text-white shadow-xs flex items-center gap-1.5 transition">
                                <i class="bi bi-eye-fill"></i>
                                <span>Preview Split PDF</span>
                            </button>
                        </div>
                    </div>

                    ${dupAlert}

                    <!-- Editable Fields for This Split Paper -->
                    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 text-xs">
                        <div>
                            <label class="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                                Course Code <span class="text-rose-500">*</span>
                            </label>
                            <input 
                                type="text" 
                                id="splitCourseCode_${idx}" 
                                value="${item.courseCode || ''}" 
                                oninput="App.handleSplitCourseCodeChange(${idx})" 
                                placeholder="e.g. MG1DSCMAT100" 
                                class="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-700/60 font-mono font-bold uppercase text-xs"
                                ${isPublished ? 'disabled' : ''}
                            >
                        </div>
                        <div class="lg:col-span-2">
                            <label class="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                                Course Title <span class="text-rose-500">*</span>
                            </label>
                            <input 
                                type="text" 
                                id="splitTitle_${idx}" 
                                value="${item.title || ''}" 
                                placeholder="Course Title" 
                                class="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-700/60 text-xs"
                                ${isPublished ? 'disabled' : ''}
                            >
                        </div>
                        <div>
                            <label class="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                                Department <span class="text-rose-500">*</span>
                            </label>
                            <select 
                                id="splitDept_${idx}" 
                                class="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-700/60 text-xs"
                                ${isPublished ? 'disabled' : ''}
                            >
                                ${deptOptionsHtml(item.deptCode)}
                            </select>
                        </div>
                        <div>
                            <label class="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                                Semester & Type <span class="text-rose-500">*</span>
                            </label>
                            <div class="grid grid-cols-2 gap-1.5">
                                <select 
                                    id="splitSem_${idx}" 
                                    class="w-full px-2 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-700/60 text-xs font-semibold"
                                    ${isPublished ? 'disabled' : ''}
                                >
                                    ${semOptionsHtml(item.semester)}
                                </select>
                                <select 
                                    id="splitPaperType_${idx}" 
                                    onchange="App.handleSplitPaperTypeChange(${idx}, this.value)"
                                    class="w-full px-2 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-700/60 text-xs font-semibold"
                                    ${isPublished ? 'disabled' : ''}
                                >
                                    <option value="THEORY" ${item.paperType !== 'PRACTICAL' ? 'selected' : ''}>Theory</option>
                                    <option value="PRACTICAL" ${item.paperType === 'PRACTICAL' ? 'selected' : ''}>Practical</option>
                                </select>
                            </div>
                        </div>
                    </div>

                    <!-- Bottom Actions for this card -->
                    <div class="flex items-center justify-between pt-2 border-t border-slate-100 dark:border-slate-700/80">
                        <div id="splitStatus_${idx}" class="text-xs font-semibold">
                            ${isPublished ? '<span class="text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5"><i class="bi bi-check-circle-fill"></i> Successfully Added into Website</span>' : ''}
                        </div>

                        ${!isPublished ? `
                        <button type="button" id="splitPublishBtn_${idx}" onclick="App.publishSingleSplitPaper(${idx})" class="px-4 py-2 rounded-xl text-xs font-bold ${isDup ? 'bg-amber-600 hover:bg-amber-500' : 'bg-blue-600 hover:bg-blue-500'} text-white shadow-xs flex items-center gap-1.5 transition ml-auto">
                            <i class="bi ${isDup ? 'bi-arrow-repeat' : 'bi-plus-circle-fill'}"></i>
                            <span>${isDup ? 'Update / Overwrite in Website' : 'Add into Website'}</span>
                        </button>` : ''}
                    </div>
                </div>
            `;
        }).join('');
    },

    handleSplitCourseCodeChange(idx) {
        const item = this.adminSplitPapers[idx];
        if (!item) return;

        const codeInput = document.getElementById(`splitCourseCode_${idx}`);
        const titleInput = document.getElementById(`splitTitle_${idx}`);
        const deptSelect = document.getElementById(`splitDept_${idx}`);
        const semSelect = document.getElementById(`splitSem_${idx}`);

        const rawCode = codeInput ? codeInput.value : '';
        const newCode = this.normalizeCourseCode(rawCode);
        if (codeInput && newCode && newCode !== rawCode) {
            codeInput.value = newCode;
        }
        item.courseCode = newCode;

        if (newCode) {
            const match = (this.papers || []).find(p => (p.course_code || '').trim().toUpperCase() === newCode);
            if (match) {
                if (titleInput && (!titleInput.value || titleInput.value === item.title)) {
                    titleInput.value = match.title;
                    item.title = match.title;
                }
                if (deptSelect && (!deptSelect.value || deptSelect.value === item.deptCode)) {
                    deptSelect.value = match.parent_dept || match.dept_code;
                    item.deptCode = deptSelect.value;
                }
                if (semSelect && match.semester) {
                    semSelect.value = String(match.semester);
                    item.semester = match.semester;
                }
                item.confidence = 'high';
            }
        }

        const isModel = true;
        const dupResult = this.checkPaperDuplicate(newCode, item.qpCode, isModel);
        item.isDuplicate = dupResult.isDuplicate;
        item.dupMessage = dupResult.message;
        item.existingPaper = dupResult.paper;

        this.renderSplitCardsUI();
    },

    async publishSingleSplitPaper(idx) {
        const item = this.adminSplitPapers[idx];
        if (!item || item.published) return;

        const btn = document.getElementById(`splitPublishBtn_${idx}`);
        const courseCode = document.getElementById(`splitCourseCode_${idx}`)?.value.trim().toUpperCase() || item.courseCode;
        const title = document.getElementById(`splitTitle_${idx}`)?.value.trim() || item.title;
        const deptCode = document.getElementById(`splitDept_${idx}`)?.value.trim().toUpperCase() || item.deptCode;
        const semester = parseInt(document.getElementById(`splitSem_${idx}`)?.value || item.semester, 10);
        const paperType = document.getElementById(`splitPaperType_${idx}`)?.value || item.paperType || 'THEORY';

        if (!courseCode) {
            alert('Please specify a Course Code for this paper.');
            return;
        }

        if (btn) this.setButtonLoading(btn, true, 'Publishing...');

        try {
            const isModel = true;
            const deptObj = this.departments.find(d => d.code === deptCode);
            const deptName = deptObj ? deptObj.name : deptCode;
            const isSignature = Boolean(item.isSignature || this.isSignatureCourse(courseCode));

            const payload = {
                is_model_paper: isModel,
                paper_type: paperType,
                course_code: courseCode,
                is_signature: isSignature,
                title: title || `Model QP - ${courseCode} (${paperType})`,
                dept_code: deptCode,
                dept_name: deptName,
                parent_dept: deptCode,
                parent_dept_name: deptName,
                semester: semester,
                course_type: item.courseType || 'DSC',
                is_minor: Boolean(item.isMinor),
                minor_name: item.minorName || '',
                qp_code: item.qpCode || '',
                exam_name: `Model Question Paper - FYUGP 2024 (${paperType})`,
                qp_file_b64: item.base64,
                scheme_file_b64: '',
                scheme_url: ''
            };

            const isLocalBackend = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') && window.location.port !== '';

            let data;
            if (isLocalBackend) {
                const res = await fetch('/api/admin/upload-paper', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                data = await res.json();
            } else {
                const ts = Date.now();
                const modelObj = {
                    id: `model_${courseCode}_${paperType.toLowerCase()}_${ts}`,
                    url: item.blobUrl || "#",
                    filename: `Model_${courseCode}_${paperType}_Pages_${item.startPage}-${item.endPage}.pdf`,
                    title: title || `Model QP - ${courseCode} (${paperType})`,
                    paper_type: paperType,
                    pages: item.pageCount,
                    source: "Admin Ingestion"
                };
                let existing = this.papers.find(p => (p.course_code || '').toUpperCase() === courseCode);
                if (existing) {
                    if (!existing.model_papers) existing.model_papers = [];
                    const ptype = (modelObj.paper_type || 'THEORY').toUpperCase();
                    existing.model_papers = existing.model_papers.filter(m => (m.paper_type || 'THEORY').toUpperCase() !== ptype);
                    existing.model_papers.push(modelObj);
                    existing.has_files = true;
                    if (isSignature) {
                        existing.is_signature = true;
                    }
                } else {
                    existing = {
                        id: `custom_split_${courseCode}_${ts}`,
                        course_code: courseCode,
                        is_signature: isSignature,
                        title: title || `Model QP - ${courseCode}`,
                        raw_header: `${courseCode} ${title}`,
                        semester: semester,
                        semester_label: `Semester ${semester}`,
                        course_type: item.courseType || 'DSC',
                        dept_code: deptCode,
                        dept_name: deptName,
                        parent_dept: deptCode,
                        parent_dept_name: deptName,
                        batch: "2024 Admission",
                        is_fyugp: true,
                        has_qp: false,
                        has_scheme: false,
                        files: [],
                        has_files: true,
                        model_papers: [modelObj]
                    };
                    this.papers.unshift(existing);
                }
                data = { success: true, paper: existing };
            }

            if (data.success) {
                if (data.paper) {
                    const existingIdx = this.papers.findIndex(p => p.id === data.paper.id || (p.course_code && p.course_code.toUpperCase() === data.paper.course_code.toUpperCase()));
                    if (existingIdx !== -1) {
                        this.papers[existingIdx] = data.paper;
                    } else {
                        this.papers.unshift(data.paper);
                    }
                }

                item.published = true;
                this.applyFilters();
                this.renderDepartmentsList();
                if (this.deptState.activeDept) {
                    this.renderDeptSemesterTabs();
                    this.renderDeptSemesterPapers();
                }
                this.updateStatsUI();

                this.renderSplitCardsUI();
            } else {
                throw new Error(data.error || 'Server rejected paper upload');
            }
        } catch (err) {
            alert(`Error publishing paper: ${err.message}`);
        } finally {
            if (btn) this.setButtonLoading(btn, false);
        }
    },

    async publishAllSplitPapers() {
        const pending = this.adminSplitPapers.filter(p => !p.published);
        if (pending.length === 0) {
            alert('All split papers have already been published!');
            return;
        }

        const btn = document.getElementById('adminPublishAllBtn');
        const origText = document.getElementById('adminPublishAllBtnText');

        if (btn) this.setButtonLoading(btn, true, `Publishing (0/${pending.length})...`);

        let count = 0;
        for (let i = 0; i < this.adminSplitPapers.length; i++) {
            const paper = this.adminSplitPapers[i];
            if (!paper.published) {
                count++;
                if (origText) origText.textContent = `Publishing (${count}/${pending.length})...`;
                await this.publishSingleSplitPaper(i);
            }
        }

        if (btn) this.setButtonLoading(btn, false);
        alert(`Successfully published all ${count} split model question papers into the website!`);
    },

    renderScanResultUI(info, dupResult) {
        const container = document.getElementById('adminScanResultContainer');
        if (!container) return;

        container.classList.remove('hidden');

        const isDup = dupResult && dupResult.isDuplicate;
        const confidenceBadge = info.confidence === 'high'
            ? '<span class="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-300 flex items-center gap-1"><i class="bi bi-check-circle-fill"></i> Matched with Portal Catalog</span>'
            : (info.confidence === 'medium'
                ? '<span class="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-blue-100 text-blue-800 dark:bg-blue-900/60 dark:text-blue-300 flex items-center gap-1"><i class="bi bi-magic"></i> Pattern Detected</span>'
                : '<span class="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800 dark:bg-amber-900/60 dark:text-amber-300 flex items-center gap-1"><i class="bi bi-pencil"></i> Manual Review Needed</span>');

        const categoryBadge = this.currentPaperCategory === 'MODEL'
            ? '<span class="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-indigo-100 text-indigo-800 dark:bg-indigo-900/60 dark:text-indigo-300">Model Question Paper</span>'
            : '<span class="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-blue-100 text-blue-800 dark:bg-blue-900/60 dark:text-blue-300">University Exam QP</span>';

        container.innerHTML = `
            <div class="p-4 rounded-2xl border ${isDup ? 'border-amber-300 dark:border-amber-700/80 bg-amber-50/60 dark:bg-amber-950/30' : 'border-emerald-300 dark:border-emerald-700/80 bg-emerald-50/60 dark:bg-emerald-950/30'} space-y-3">
                <div class="flex items-center justify-between gap-2 flex-wrap">
                    <div class="flex items-center gap-2">
                        ${confidenceBadge}
                        ${categoryBadge}
                    </div>
                    <div class="text-[11px] font-mono text-slate-600 dark:text-slate-300">
                        Course Code: <strong class="text-slate-900 dark:text-white font-bold">${info.courseCode || 'None detected'}</strong>
                    </div>
                </div>

                <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2 border-t ${isDup ? 'border-amber-200 dark:border-amber-800/60' : 'border-emerald-200 dark:border-emerald-800/60'}">
                    <div>
                        <div class="text-xs font-bold ${isDup ? 'text-amber-950 dark:text-amber-200' : 'text-emerald-950 dark:text-emerald-200'} flex items-center gap-1.5">
                            <i class="bi ${isDup ? 'bi-exclamation-triangle-fill text-amber-600' : 'bi-check-circle-fill text-emerald-600'}"></i>
                            <span>${isDup ? 'Duplicate Alert' : 'No Duplicate Detected — Ready to Ingest'}</span>
                        </div>
                        <p class="text-[11px] ${isDup ? 'text-amber-800 dark:text-amber-300' : 'text-emerald-800 dark:text-emerald-300'} mt-0.5 font-medium">
                            ${dupResult ? dupResult.message : ''}
                        </p>
                    </div>

                    ${isDup && dupResult.paper ? `
                    <div class="shrink-0 flex items-center gap-2">
                        <button type="button" onclick="App.previewPaper(this, App.findPaperById('${dupResult.paper.id}'), 'QP')" class="px-3 py-1.5 rounded-xl bg-amber-200 hover:bg-amber-300 dark:bg-amber-800 dark:hover:bg-amber-700 text-amber-950 dark:text-amber-100 font-semibold text-xs transition flex items-center gap-1 shadow-2xs">
                            <i class="bi bi-eye"></i> View Existing Paper
                        </button>
                    </div>` : ''}
                </div>
            </div>
        `;

        const btnText = document.getElementById('adminUploadSubmitBtnText');
        const warnHint = document.getElementById('adminDuplicateWarningHint');
        const submitBtn = document.getElementById('adminUploadSubmitBtn');

        if (warnHint) warnHint.classList.toggle('hidden', !isDup);

        if (isDup) {
            if (btnText) btnText.textContent = 'Update / Overwrite in Website';
            if (submitBtn) {
                submitBtn.className = 'px-6 py-2.5 bg-amber-600 hover:bg-amber-500 text-white rounded-xl font-bold shadow-xs flex items-center gap-1.5 text-xs transition';
            }
        } else {
            if (btnText) btnText.textContent = 'Add into Website';
            if (submitBtn) {
                submitBtn.className = 'px-6 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl font-bold shadow-xs flex items-center gap-1.5 text-xs transition';
            }
        }
    },

    handleCourseCodeManualChange() {
        const codeInput = document.getElementById('adminUploadCourseCode');
        const qpCodeInput = document.getElementById('adminUploadQpCode');
        const courseCode = codeInput ? codeInput.value.trim().toUpperCase() : '';
        const qpCode = qpCodeInput ? qpCodeInput.value.trim() : '';

        if (courseCode) {
            const match = (this.papers || []).find(p => (p.course_code || '').trim().toUpperCase() === courseCode);
            if (match) {
                const titleInput = document.getElementById('adminUploadTitle');
                const deptSelect = document.getElementById('adminUploadDept');
                const semSelect = document.getElementById('adminUploadSemester');
                const ctypeSelect = document.getElementById('adminUploadCourseType');
                if (titleInput && !titleInput.value) titleInput.value = match.title;
                if (deptSelect && (!deptSelect.value || deptSelect.value === '')) deptSelect.value = match.parent_dept || match.dept_code;
                if (semSelect && match.semester) semSelect.value = String(match.semester);
                if (ctypeSelect && match.course_type) ctypeSelect.value = match.course_type;
            }
        }

        const isModel = this.currentPaperCategory === 'MODEL';
        const dupResult = this.checkPaperDuplicate(courseCode, qpCode, isModel);

        const info = {
            courseCode: courseCode,
            confidence: (this.papers || []).some(p => (p.course_code || '').trim().toUpperCase() === courseCode) ? 'high' : 'medium',
            semester: document.getElementById('adminUploadSemester')?.value || 1
        };

        this.renderScanResultUI(info, dupResult);
    },

    findPaperById(id) {
        return (this.papers || []).find(p => p.id === id) || null;
    },

    async handleAdminSmartUploadSubmit(e) {
        if (e) e.preventDefault();

        const statusEl = document.getElementById('adminUploadStatus');
        if (statusEl) {
            statusEl.className = 'p-3 rounded-xl text-xs bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-900 flex items-center gap-2';
            statusEl.innerHTML = '<div class="animate-spin rounded-full h-3.5 w-3.5 border-2 border-blue-600 border-t-transparent"></div> Publishing paper into website...';
            statusEl.classList.remove('hidden');
        }
        this.setButtonLoading('adminUploadSubmitBtn', true, 'Publishing to Website...');

        try {
            const isModel = this.currentPaperCategory === 'MODEL';
            const courseCode = document.getElementById('adminUploadCourseCode').value.trim().toUpperCase();
            const title = document.getElementById('adminUploadTitle').value.trim();
            const deptCode = document.getElementById('adminUploadDept').value.trim().toUpperCase();
            const semester = parseInt(document.getElementById('adminUploadSemester').value, 10);
            const courseType = document.getElementById('adminUploadCourseType').value.trim().toUpperCase();
            const isMinor = document.getElementById('adminUploadIsMinor').checked;
            const minorName = document.getElementById('adminUploadMinorName')?.value.trim() || '';
            const minorCode = document.getElementById('adminUploadMinorCode')?.value.trim().toUpperCase() || '';
            const qpCode = document.getElementById('adminUploadQpCode')?.value.trim() || '';
            const examName = document.getElementById('adminUploadExamName')?.value.trim() || 'MGU-UGP (Honours) 2024 Admission Regular Examination';
            
            const pdfFile = this.selectedSmartPdfFile || document.getElementById('adminSmartPdfFile')?.files[0];
            const schemeFile = document.getElementById('adminUploadSchemeFile')?.files[0];
            const schemeUrl = document.getElementById('adminUploadSchemeUrl')?.value.trim() || '';

            if (!pdfFile && !isModel) {
                throw new Error('Please select or drop a Question Paper PDF before publishing.');
            }

            const deptObj = this.departments.find(d => d.code === deptCode);
            const deptName = deptObj ? deptObj.name : deptCode;

            const toB64 = (file) => new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = () => resolve(reader.result);
                reader.onerror = reject;
                reader.readAsDataURL(file);
            });

            let qpFileB64 = '';
            if (pdfFile) qpFileB64 = await toB64(pdfFile);

            let schemeFileB64 = '';
            if (schemeFile) schemeFileB64 = await toB64(schemeFile);

            const isSignature = this.isSignatureCourse(courseCode);

            const payload = {
                is_model_paper: isModel,
                course_code: courseCode,
                is_signature: isSignature,
                title: title,
                dept_code: isMinor && minorCode ? minorCode : deptCode,
                dept_name: isMinor && minorName ? minorName : deptName,
                parent_dept: deptCode,
                parent_dept_name: deptName,
                semester: semester,
                course_type: courseType,
                is_minor: isMinor,
                minor_name: minorName,
                qp_code: qpCode,
                exam_name: examName,
                qp_file_b64: qpFileB64,
                scheme_file_b64: schemeFileB64,
                scheme_url: schemeUrl
            };

            const isLocalBackend = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') && window.location.port !== '';

            let data;
            if (isLocalBackend) {
                const res = await fetch('/api/admin/upload-paper', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                data = await res.json();
            } else {
                const ts = Date.now();
                if (isModel) {
                    const modelObj = {
                        url: qpFileB64 || "#",
                        filename: pdfFile ? pdfFile.name : `Model_${courseCode}.pdf`,
                        title: title || `Model QP - ${courseCode}`
                    };
                    let existing = this.papers.find(p => (p.course_code || '').toUpperCase() === courseCode);
                    if (existing) {
                        if (!existing.model_papers) existing.model_papers = [];
                        const ptype = (modelObj.paper_type || 'THEORY').toUpperCase();
                        existing.model_papers = existing.model_papers.filter(m => (m.paper_type || 'THEORY').toUpperCase() !== ptype);
                        existing.model_papers.push(modelObj);
                        if (isSignature) existing.is_signature = true;
                    } else {
                        existing = {
                            id: `custom_model_${courseCode}_${ts}`,
                            course_code: courseCode,
                            is_signature: isSignature,
                            title: title,
                            raw_header: `${courseCode} ${title}`,
                            semester: semester,
                            semester_label: `Semester ${semester}`,
                            course_type: courseType,
                            dept_code: isMinor && minorCode ? minorCode : deptCode,
                            dept_name: isMinor && minorName ? minorName : deptName,
                            parent_dept: deptCode,
                            parent_dept_name: deptName,
                            is_minor: isMinor,
                            minor_name: minorName,
                            batch: "2024 Admission",
                            is_fyugp: true,
                            has_qp: false,
                            has_scheme: false,
                            files: [],
                            has_files: false,
                            model_papers: [modelObj]
                        };
                        this.papers.unshift(existing);
                    }
                    data = { success: true, paper: existing };
                } else {
                    const files = [];
                    if (qpFileB64) files.push({ type: "QP", label: "QUESTION PAPER", url: qpFileB64 });
                    if (schemeFileB64 || schemeUrl) files.push({ type: "SCHEME", label: "SCHEME", url: schemeFileB64 || schemeUrl });

                    const customPaper = {
                        id: `custom_${courseCode}_${ts}`,
                        qp_code: qpCode,
                        course_code: courseCode,
                        title: title,
                        raw_header: `${qpCode} - ${courseCode} ${title}`.trim(),
                        semester: semester,
                        semester_label: `Semester ${semester}`,
                        course_type: courseType,
                        dept_code: isMinor && minorCode ? minorCode : deptCode,
                        dept_name: isMinor && minorName ? minorName : deptName,
                        parent_dept: deptCode,
                        parent_dept_name: deptName,
                        is_minor: isMinor,
                        minor_name: minorName,
                        exam_name: examName,
                        batch: "2024 Admission",
                        is_fyugp: true,
                        is_signature: isSignature,
                        has_qp: Boolean(qpFileB64),
                        qp_url: qpFileB64 || "#",
                        has_scheme: Boolean(schemeFileB64 || schemeUrl),
                        scheme_url: schemeFileB64 || schemeUrl || "#",
                        files: files,
                        has_files: files.length > 0
                    };
                    this.papers.unshift(customPaper);
                    data = { success: true, paper: customPaper };
                }
            }

            if (data.success) {
                if (data.paper) {
                    const idx = this.papers.findIndex(p => p.id === data.paper.id || (p.course_code && p.course_code.toUpperCase() === data.paper.course_code.toUpperCase()));
                    if (idx !== -1) {
                        this.papers[idx] = data.paper;
                    } else {
                        this.papers.unshift(data.paper);
                    }
                }

                this.applyFilters();
                this.renderDepartmentsList();
                if (this.deptState.activeDept) {
                    this.renderDeptSemesterTabs();
                    this.renderDeptSemesterPapers();
                }
                this.updateStatsUI();

                if (statusEl) {
                    statusEl.className = 'p-3 rounded-xl text-xs bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 flex items-center gap-2';
                    statusEl.innerHTML = `<i class="bi bi-check-circle-fill text-emerald-600"></i> Paper "${courseCode} - ${title}" added successfully into the website!`;
                }

                this.resetSmartUploadForm();
            } else {
                throw new Error(data.error || 'Server rejected paper upload');
            }
        } catch (err) {
            if (statusEl) {
                statusEl.className = 'p-3 rounded-xl text-xs bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800';
                statusEl.innerHTML = `<i class="bi bi-exclamation-triangle-fill text-rose-600"></i> Error: ${err.message}`;
            }
        } finally {
            this.setButtonLoading('adminUploadSubmitBtn', false);
        }
    },

    // Legacy alias
    handleAdminUploadSubmit(e) {
        return this.handleAdminSmartUploadSubmit(e);
    },

    resetSmartUploadForm() {
        this.selectedSmartPdfFile = null;
        this.adminSplitPapers = [];
        this.adminPdfSourceDoc = null;
        this.adminPagesText = null;
        this.adminNumPages = 0;
        if (this.masterPdfUrl) {
            URL.revokeObjectURL(this.masterPdfUrl);
            this.masterPdfUrl = null;
        }

        const fileInput = document.getElementById('adminSmartPdfFile');
        if (fileInput) fileInput.value = '';
        const badge = document.getElementById('adminSelectedFileNameBadge');
        if (badge) badge.classList.add('hidden');
        const scanRes = document.getElementById('adminScanResultContainer');
        if (scanRes) {
            scanRes.innerHTML = '';
            scanRes.classList.add('hidden');
        }

        // Multi split container reset
        const multiContainer = document.getElementById('adminMultiSplitContainer');
        if (multiContainer) multiContainer.classList.add('hidden');
        const splitCards = document.getElementById('adminSplitCardsContainer');
        if (splitCards) splitCards.innerHTML = '';
        const customSplitInput = document.getElementById('adminCustomSplitInput');
        if (customSplitInput) customSplitInput.value = '';
        const splitSearchInput = document.getElementById('adminSplitSearchInput');
        if (splitSearchInput) splitSearchInput.value = '';
        this.splitCardsFilter = 'ALL';
        this.splitCardsSearchQuery = '';
        const totalPagesBadge = document.getElementById('adminTotalPagesCountBadge');
        if (totalPagesBadge) totalPagesBadge.textContent = '--';

        // Form reset
        const uploadForm = document.getElementById('adminUploadForm');
        if (uploadForm) uploadForm.classList.remove('hidden');

        const warnHint = document.getElementById('adminDuplicateWarningHint');
        if (warnHint) warnHint.classList.add('hidden');
        const submitBtnText = document.getElementById('adminUploadSubmitBtnText');
        if (submitBtnText) submitBtnText.textContent = 'Add into Website';
        const submitBtn = document.getElementById('adminUploadSubmitBtn');
        if (submitBtn) {
            submitBtn.className = 'px-6 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl font-bold shadow-xs flex items-center gap-1.5 text-xs transition';
        }

        const codeInput = document.getElementById('adminUploadCourseCode');
        if (codeInput) codeInput.value = '';
        const titleInput = document.getElementById('adminUploadTitle');
        if (titleInput) titleInput.value = '';
        const qpCodeEl = document.getElementById('adminUploadQpCode');
        if (qpCodeEl) qpCodeEl.value = '';
        const schemeFileEl = document.getElementById('adminUploadSchemeFile');
        if (schemeFileEl) schemeFileEl.value = '';
        const schemeUrlEl = document.getElementById('adminUploadSchemeUrl');
        if (schemeUrlEl) schemeUrlEl.value = '';
    },

    renderAdminDeleteList() {
        const container = document.getElementById('adminDeleteListContainer');
        const badge = document.getElementById('adminDeleteCountBadge');
        const searchInput = document.getElementById('adminDeleteSearchInput');
        if (!container) return;

        const q = (searchInput ? searchInput.value : '').trim().toLowerCase();
        let list = this.papers;
        if (q) {
            list = list.filter(p => 
                (p.course_code && p.course_code.toLowerCase().includes(q)) ||
                (p.title && p.title.toLowerCase().includes(q)) ||
                (p.qp_code && p.qp_code.toLowerCase().includes(q)) ||
                (p.dept_name && p.dept_name.toLowerCase().includes(q)) ||
                (p.parent_dept_name && p.parent_dept_name.toLowerCase().includes(q)) ||
                (p.dept_code && p.dept_code.toLowerCase().includes(q)) ||
                (p.course_type && p.course_type.toLowerCase().includes(q))
            );
        }

        if (badge) {
            badge.textContent = `${list.length} papers`;
        }

        if (list.length === 0) {
            container.innerHTML = `
                <div class="py-8 text-center text-slate-400">
                    <p class="text-xs">No papers match your search.</p>
                </div>
            `;
            return;
        }

        const displayList = list.slice(0, 100);
        container.innerHTML = displayList.map(p => `
            <div class="p-3 hover:bg-slate-50 dark:hover:bg-slate-700/40 flex items-center justify-between gap-3 transition">
                <div class="min-w-0 flex-1">
                    <div class="flex items-center gap-1.5 flex-wrap">
                        <span class="font-mono font-bold text-xs text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/40 px-1.5 py-0.5 rounded">
                            ${p.course_code || 'CODE N/A'}
                        </span>
                        <span class="text-[10px] font-semibold px-1.5 py-0.2 rounded bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300">
                            Sem ${p.semester}
                        </span>
                        <span class="text-[10px] font-semibold px-1.5 py-0.2 rounded ${`badge-${(p.course_type || 'dsc').toLowerCase()}`}">
                            ${p.course_type}
                        </span>
                        ${p.is_minor ? `
                            <span class="text-[10px] font-semibold px-1.5 py-0.2 rounded badge-minor">
                                ${p.dept_code} (Minor)
                            </span>
                        ` : ''}
                        ${p.qp_code ? `
                            <span class="font-mono text-[10px] text-slate-400">QP: ${p.qp_code}</span>
                        ` : ''}
                    </div>
                    <div class="font-medium text-slate-900 dark:text-slate-100 truncate mt-0.5" title="${p.title}">
                        ${p.title}
                    </div>
                    <div class="text-[11px] text-slate-400 truncate">
                        ${p.parent_dept_name || p.dept_name}
                    </div>
                </div>
                <div class="shrink-0 flex items-center gap-1.5">
                    ${p.has_qp ? `
                        <button onclick="App.previewPaper(this, ${JSON.stringify(p).replace(/"/g, '&quot;')}, 'QP')" class="px-2 py-1 text-[11px] font-semibold rounded bg-slate-100 hover:bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-200 transition" title="Preview Paper">
                            <i class="bi bi-eye"></i>
                        </button>
                    ` : ''}
                    <button onclick="App.handleDeletePaper('${p.id}', this)" class="px-2.5 py-1 text-xs font-semibold rounded-lg bg-rose-50 hover:bg-rose-100 dark:bg-rose-950/50 text-rose-600 dark:text-rose-300 border border-rose-200 dark:border-rose-800 transition flex items-center gap-1" title="Delete Paper Permanently">
                        <i class="bi bi-trash3"></i> Delete
                    </button>
                </div>
            </div>
        `).join('');
    },

    async handleDeletePaper(paperId, btn = null) {
        const paper = this.papers.find(p => p.id === paperId);
        const title = paper ? `${paper.course_code} - ${paper.title}` : `Paper ID ${paperId}`;
        if (!confirm(`Are you sure you want to delete "${title}" permanently?`)) {
            return;
        }

        if (btn) this.setButtonLoading(btn, true, 'Deleting...');

        const isLocalBackend = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') && window.location.port !== '';

        try {
            if (isLocalBackend) {
                const res = await fetch('/api/admin/delete-paper', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id: paperId })
                });
                const data = await res.json();
                if (!data.success) {
                    if (btn) this.setButtonLoading(btn, false);
                    alert(`Failed to delete paper: ${data.error || 'Unknown error'}`);
                    return;
                }
            }

            this.papers = this.papers.filter(p => p.id !== paperId);
            this.applyFilters();
            this.renderDepartmentsList();
            if (this.deptState.activeDept) {
                this.renderDeptSemesterTabs();
                this.renderDeptSemesterPapers();
            }
            this.renderAdminDeleteList();
            this.updateStatsUI();
            if (btn) this.setButtonLoading(btn, false);
            alert(`Paper "${title}" successfully deleted!`);
        } catch (e) {
            this.papers = this.papers.filter(p => p.id !== paperId);
            this.applyFilters();
            this.renderDepartmentsList();
            if (this.deptState.activeDept) {
                this.renderDeptSemesterTabs();
                this.renderDeptSemesterPapers();
            }
            this.renderAdminDeleteList();
            if (btn) this.setButtonLoading(btn, false);
            alert(`Paper removed from session.`);
        }
    },


    async fetchPendingCount() {
        try {
            const res = await fetch('/api/admin/pending-papers');
            if (res.ok) {
                const data = await res.json();
                const count = data.total || 0;
                this.pendingPapers = data.papers || [];
                const badge = document.getElementById('adminPendingBadge');
                if (badge) {
                    badge.textContent = count;
                    badge.className = count > 0 
                        ? 'ml-1 px-1.5 py-0.2 bg-amber-500 text-white rounded-full text-[10px] font-bold animate-pulse'
                        : 'ml-1 px-1.5 py-0.2 bg-slate-400 text-white rounded-full text-[10px] font-bold';
                }
                const headerCount = document.getElementById('adminPendingCountHeader');
                if (headerCount) headerCount.textContent = count;
                return count;
            }
        } catch (e) {
            console.error('Failed to fetch pending papers count:', e);
        }
        return 0;
    },

    async loadPendingPapers(force = false) {
        const container = document.getElementById('adminPendingContainer');
        if (container) {
            container.innerHTML = `
                <div class="p-8 text-center text-xs text-slate-400 flex items-center justify-center gap-2">
                    <span class="inline-block w-4 h-4 border-2 border-amber-500 border-t-transparent rounded-full animate-spin"></span>
                    <span>Loading ambiguous papers review queue...</span>
                </div>
            `;
        }

        try {
            const res = await fetch('/api/admin/pending-papers');
            if (res.ok) {
                const data = await res.json();
                this.pendingPapers = data.papers || [];
                const count = data.total || 0;
                const badge = document.getElementById('adminPendingBadge');
                if (badge) {
                    badge.textContent = count;
                    badge.className = count > 0 
                        ? 'ml-1 px-1.5 py-0.2 bg-amber-500 text-white rounded-full text-[10px] font-bold animate-pulse'
                        : 'ml-1 px-1.5 py-0.2 bg-slate-400 text-white rounded-full text-[10px] font-bold';
                }
                const headerCount = document.getElementById('adminPendingCountHeader');
                if (headerCount) headerCount.textContent = count;
                this.renderPendingPapers();
            } else {
                if (container) container.innerHTML = '<div class="p-4 text-center text-xs text-rose-500">Failed to load review queue.</div>';
            }
        } catch (e) {
            console.error('Failed to load pending papers:', e);
            if (container) container.innerHTML = `<div class="p-4 text-center text-xs text-rose-500">Error loading review queue: ${e.message}</div>`;
        }
    },

    renderPendingPapers() {
        const container = document.getElementById('adminPendingContainer');
        if (!container) return;

        const papers = this.pendingPapers || [];
        if (papers.length === 0) {
            container.innerHTML = `
                <div class="p-8 text-center rounded-2xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 shadow-xs space-y-3">
                    <div class="w-12 h-12 mx-auto rounded-full bg-emerald-100 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 flex items-center justify-center text-2xl">
                        <i class="bi bi-check-circle-fill"></i>
                    </div>
                    <div class="font-bold text-sm text-slate-800 dark:text-slate-100">All Question Papers Verified!</div>
                    <div class="text-xs text-slate-500 max-w-md mx-auto">
                        There are currently no ambiguous question papers in the review queue. All uploaded and scraped papers have verified course codes, clean titles, and departments.
                    </div>
                </div>
            `;
            return;
        }

        container.innerHTML = papers.map((p, idx) => {
            const rawHeader = p.raw_header || p.title || 'Untitled University Paper';
            const examName = p.exam_name || `Exam Session ${p.exam_id || ''}`;
            const sem = p.semester || 1;
            const files = p.files || [];
            const qpFile = files.find(f => f.type === 'QP') || (p.qp_url ? { url: p.qp_url, label: 'Question Paper' } : null);
            const schFile = files.find(f => f.type === 'SCHEME') || (p.scheme_url ? { url: p.scheme_url, label: 'Valuation Scheme' } : null);

            return `
                <div class="p-4 bg-white dark:bg-slate-800 rounded-2xl border border-amber-200 dark:border-amber-900/60 shadow-xs space-y-4 text-xs transition">
                    <!-- Paper Info Header -->
                    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-100 dark:border-slate-700/60">
                        <div class="space-y-0.5">
                            <div class="flex items-center gap-2 flex-wrap">
                                <span class="px-2 py-0.5 rounded-md font-bold text-[10px] bg-amber-100 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300">
                                    <i class="bi bi-clock-history"></i> Needs Admin Verification
                                </span>
                                <span class="px-2 py-0.5 rounded-md font-semibold text-[10px] bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">
                                    Semester ${sem}
                                </span>
                                ${p.qp_code ? `<span class="px-2 py-0.5 rounded-md font-mono font-semibold text-[10px] bg-blue-50 dark:bg-blue-950/50 text-blue-700 dark:text-blue-300">QP: ${p.qp_code}</span>` : ''}
                                <span class="text-[11px] text-slate-400 font-mono">ID: ${p.id}</span>
                            </div>
                            <div class="font-bold text-xs text-slate-900 dark:text-slate-100 mt-1">
                                ${this.escapeHtml(rawHeader)}
                            </div>
                            <div class="text-[11px] text-slate-500 dark:text-slate-400">
                                Exam Session: <span class="font-medium text-slate-700 dark:text-slate-300">${this.escapeHtml(examName)}</span>
                            </div>
                        </div>

                        <!-- Direct PDF Preview Buttons -->
                        <div class="flex items-center gap-1.5 shrink-0">
                            ${qpFile ? `
                                <button type="button" onclick="App.openPdfPreview('${qpFile.url}', 'QP - ${this.escapeHtml(rawHeader)}')" class="px-2.5 py-1.5 bg-blue-50 hover:bg-blue-100 dark:bg-blue-950/40 dark:hover:bg-blue-900/40 text-blue-700 dark:text-blue-300 rounded-lg font-semibold flex items-center gap-1 text-[11px] border border-blue-200 dark:border-blue-800 transition">
                                    <i class="bi bi-file-earmark-pdf-fill text-blue-600"></i> Read QP PDF
                                </button>
                            ` : ''}
                            ${schFile ? `
                                <button type="button" onclick="App.openPdfPreview('${schFile.url}', 'Scheme - ${this.escapeHtml(rawHeader)}')" class="px-2.5 py-1.5 bg-emerald-50 hover:bg-emerald-100 dark:bg-emerald-950/40 dark:hover:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300 rounded-lg font-semibold flex items-center gap-1 text-[11px] border border-emerald-200 dark:border-emerald-800 transition">
                                    <i class="bi bi-file-earmark-check-fill text-emerald-600"></i> Read Scheme PDF
                                </button>
                            ` : ''}
                        </div>
                    </div>

                    <!-- Editable Verification Form -->
                    <div class="grid grid-cols-1 sm:grid-cols-4 gap-3 bg-slate-50 dark:bg-slate-900/40 p-3 rounded-xl border border-slate-200/80 dark:border-slate-700/60">
                        <!-- Course Code -->
                        <div class="sm:col-span-1">
                            <label class="block text-[11px] font-bold text-slate-700 dark:text-slate-300 mb-1">
                                Correct Course Code <span class="text-rose-500">*</span>
                            </label>
                            <input 
                                type="text" 
                                id="pending_code_${p.id}" 
                                value="${p.course_code && p.course_code !== 'GEN' ? p.course_code : ''}" 
                                placeholder="e.g. MG3DSCCOM200" 
                                oninput="App.handlePendingCodeInput('${p.id}', this.value)"
                                class="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-white font-mono uppercase font-bold focus:ring-2 focus:ring-blue-500 text-xs"
                                list="courseCodeDatalist"
                            >
                            <span class="text-[10px] text-slate-400 mt-0.5 block">MG + Sem + Type + Dept + Num</span>
                        </div>

                        <!-- Course Title -->
                        <div class="sm:col-span-2">
                            <label class="block text-[11px] font-bold text-slate-700 dark:text-slate-300 mb-1">
                                Course Title <span class="text-rose-500">*</span>
                            </label>
                            <input 
                                type="text" 
                                id="pending_title_${p.id}" 
                                value="${p.title && !p.title.startsWith('Course ') && p.title !== rawHeader ? p.title : ''}" 
                                placeholder="e.g. Financial Accounting" 
                                class="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-white font-medium focus:ring-2 focus:ring-blue-500 text-xs"
                            >
                            <span class="text-[10px] text-slate-400 mt-0.5 block">Official subject name from PDF header</span>
                        </div>

                        <!-- Semester -->
                        <div class="sm:col-span-1">
                            <label class="block text-[11px] font-bold text-slate-700 dark:text-slate-300 mb-1">
                                Semester <span class="text-rose-500">*</span>
                            </label>
                            <select id="pending_sem_${p.id}" class="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-xs">
                                <option value="1" ${sem == 1 ? 'selected' : ''}>Semester 1</option>
                                <option value="2" ${sem == 2 ? 'selected' : ''}>Semester 2</option>
                                <option value="3" ${sem == 3 ? 'selected' : ''}>Semester 3</option>
                                <option value="4" ${sem == 4 ? 'selected' : ''}>Semester 4</option>
                                <option value="5" ${sem == 5 ? 'selected' : ''}>Semester 5</option>
                                <option value="6" ${sem == 6 ? 'selected' : ''}>Semester 6</option>
                                <option value="7" ${sem == 7 ? 'selected' : ''}>Semester 7</option>
                                <option value="8" ${sem == 8 ? 'selected' : ''}>Semester 8</option>
                            </select>
                        </div>
                    </div>

                    <!-- Action Buttons -->
                    <div class="flex items-center justify-between pt-1">
                        <div id="pending_status_${p.id}" class="text-xs font-semibold text-slate-500">
                            <!-- Live status message -->
                        </div>
                        <div class="flex items-center gap-2">
                            <button 
                                type="button" 
                                onclick="App.discardPendingPaper('${p.id}')" 
                                class="px-3 py-1.5 text-xs font-semibold rounded-lg text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/40 border border-rose-200 dark:border-rose-900/50 transition flex items-center gap-1"
                            >
                                <i class="bi bi-trash3"></i> Discard
                            </button>
                            <button 
                                type="button" 
                                id="btn_resolve_${p.id}"
                                onclick="App.resolvePendingPaper('${p.id}')" 
                                class="px-4 py-1.5 text-xs font-bold rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white shadow-xs transition flex items-center gap-1.5"
                            >
                                <i class="bi bi-check2-circle"></i> Verify, Deduplicate & Publish
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    },

    handlePendingCodeInput(paperId, val) {
        if (!val) return;
        const clean = val.trim().toUpperCase();
        const codeInput = document.getElementById(`pending_code_${paperId}`);
        if (codeInput && codeInput.value !== clean) {
            codeInput.value = clean;
        }

        const semSelect = document.getElementById(`pending_sem_${paperId}`);
        if (semSelect && clean.length >= 3 && clean.startsWith('MG')) {
            const semChar = clean.charAt(2);
            if (['1','2','3','4','5','6','7','8'].includes(semChar)) {
                semSelect.value = semChar;
            }
        }

        const titleInput = document.getElementById(`pending_title_${paperId}`);
        if (titleInput && (!titleInput.value || titleInput.value.startsWith('Course '))) {
            const existing = (this.papers || []).find(p => p.course_code === clean);
            if (existing && existing.title && !existing.title.startsWith('Course ')) {
                titleInput.value = existing.title;
            }
        }
    },

    async resolvePendingPaper(paperId) {
        const codeInput = document.getElementById(`pending_code_${paperId}`);
        const titleInput = document.getElementById(`pending_title_${paperId}`);
        const semSelect = document.getElementById(`pending_sem_${paperId}`);
        const statusEl = document.getElementById(`pending_status_${paperId}`);
        const btn = document.getElementById(`btn_resolve_${paperId}`);

        const courseCode = codeInput ? codeInput.value.trim().toUpperCase() : '';
        const title = titleInput ? titleInput.value.trim() : '';
        const semester = semSelect ? parseInt(semSelect.value, 10) : 1;

        if (!courseCode) {
            alert('Please enter a valid course code (e.g. MG3DSCCOM200).');
            if (codeInput) codeInput.focus();
            return;
        }

        if (!courseCode.endsWith('0') && !courseCode.endsWith('1') && !courseCode.endsWith('2') && !courseCode.endsWith('3') && !courseCode.endsWith('4') && !courseCode.endsWith('5') && !courseCode.endsWith('6') && !courseCode.endsWith('7') && !courseCode.endsWith('8') && !courseCode.endsWith('9')) {
            alert(`Invalid course code '${courseCode}': Course codes must end with a number.`);
            return;
        }

        if (btn) this.setButtonLoading(btn, true, 'Verifying...');
        if (statusEl) statusEl.innerHTML = '<span class="text-blue-500">Processing verification & deduplication...</span>';

        try {
            const resp = await fetch('/api/admin/resolve-paper', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    paper_id: paperId,
                    course_code: courseCode,
                    course_title: title,
                    semester: semester
                })
            });

            const data = await resp.json();
            if (resp.ok && data.success) {
                if (data.action === 'merged') {
                    alert(`✅ Duplicate Found & Merged!\n\n${data.message}`);
                } else {
                    alert(`✅ Paper Published Successfully!\n\n${data.message}`);
                }

                this.pendingPapers = (this.pendingPapers || []).filter(p => p.id !== paperId);
                const badge = document.getElementById('adminPendingBadge');
                if (badge) badge.textContent = this.pendingPapers.length;
                const headerCount = document.getElementById('adminPendingCountHeader');
                if (headerCount) headerCount.textContent = this.pendingPapers.length;

                this.renderPendingPapers();
                await this.refreshPortalData();
            } else {
                alert(`❌ Verification failed: ${data.error || 'Unknown error'}`);
                if (btn) this.setButtonLoading(btn, false);
                if (statusEl) statusEl.innerHTML = `<span class="text-rose-500">${data.error || 'Error'}</span>`;
            }
        } catch (e) {
            alert(`Error: ${e.message}`);
            if (btn) this.setButtonLoading(btn, false);
            if (statusEl) statusEl.innerHTML = `<span class="text-rose-500">${e.message}</span>`;
        }
    },

    async discardPendingPaper(paperId) {
        if (!confirm('Are you sure you want to permanently discard this ambiguous paper? It will be removed from data.')) {
            return;
        }

        try {
            const resp = await fetch('/api/admin/discard-pending-paper', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ paper_id: paperId })
            });

            const data = await resp.json();
            if (resp.ok && data.success) {
                this.pendingPapers = (this.pendingPapers || []).filter(p => p.id !== paperId);
                const badge = document.getElementById('adminPendingBadge');
                if (badge) badge.textContent = this.pendingPapers.length;
                const headerCount = document.getElementById('adminPendingCountHeader');
                if (headerCount) headerCount.textContent = this.pendingPapers.length;
                this.renderPendingPapers();
                alert('Paper discarded and removed.');
            } else {
                alert(`Failed to discard: ${data.error || 'Unknown error'}`);
            }
        } catch (e) {
            alert(`Error: ${e.message}`);
        }
    },

    async refreshPortalData() {
        try {
            const resp = await fetch('data/papers.json?t=' + Date.now());
            if (resp.ok) {
                const rawPapers = await resp.json();
                this.papers = rawPapers.filter(p => 
                    p.batch !== 'CBCS' && 
                    p.course_type !== 'CBCS' &&
                    !p.needs_review &&
                    p.status !== 'pending_review' &&
                    p.dept_code !== 'GEN' &&
                    p.course_code &&
                    p.course_code !== 'GEN'
                );
                this.buildCourseCatalogIndex();
                this.applyFilters();
                this.renderDepartmentsList();
                if (this.deptState.activeDept) {
                    this.renderDeptSemesterTabs();
                    this.renderDeptSemesterPapers();
                }
                this.updateStatsUI();
            }
        } catch (e) {
            console.error('Error refreshing portal data:', e);
        }
    },

    async triggerSync() {
        const syncStatusEl = document.getElementById('syncStatusNotice');
        if (syncStatusEl) {
            syncStatusEl.className = 'mt-4 p-4 rounded-xl bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-900 text-blue-800 dark:text-blue-200 text-sm flex items-center gap-3';
            syncStatusEl.innerHTML = `<div class="animate-spin rounded-full h-4 w-4 border-2 border-blue-600 border-t-transparent"></div> Syncing FYUGP question papers with https://assist.mgu.ac.in/schema/...`;
            syncStatusEl.classList.remove('hidden');
        }

        this.setButtonLoading('triggerSyncBtn', true, 'Syncing...');

        try {
            const res = await fetch('/api/sync', { method: 'POST' });
            const data = await res.json();
            if (syncStatusEl) {
                syncStatusEl.className = 'mt-4 p-4 rounded-xl bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-900 text-blue-800 dark:text-blue-200 text-sm flex items-center gap-3';
                syncStatusEl.innerHTML = `<div class="animate-spin rounded-full h-4 w-4 border-2 border-blue-600 border-t-transparent"></div> Crawl initiated in background. Polling for results...`;
            }

            // Poll for sync completion and update history
            let attempts = 0;
            const pollInterval = setInterval(async () => {
                attempts++;
                try {
                    await this.loadCrawlHistory(true);
                    if (this.crawlHistoryCache && this.crawlHistoryCache.length > 0) {
                        const latest = this.crawlHistoryCache[0];
                        const diffSeconds = (Date.now() - new Date(latest.timestamp).getTime()) / 1000;
                        if (diffSeconds < 60 || attempts >= 10) {
                            clearInterval(pollInterval);
                            this.setButtonLoading('triggerSyncBtn', false);
                            if (syncStatusEl) {
                                syncStatusEl.className = 'mt-4 p-4 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-900 text-emerald-800 dark:text-emerald-200 text-sm flex items-center gap-3';
                                syncStatusEl.innerHTML = `<i class="bi bi-check-circle-fill text-emerald-600"></i> Crawl Complete: ${latest.summary || 'Ingested latest files!'}`;
                            }
                            this.init(); // Refresh catalog in memory
                        }
                    }
                } catch (pollErr) {
                    if (attempts >= 10) {
                        clearInterval(pollInterval);
                        this.setButtonLoading('triggerSyncBtn', false);
                    }
                }
            }, 2500);

            return;
        } catch (e) {
            if (syncStatusEl) {
                syncStatusEl.className = 'mt-4 p-4 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-900 text-amber-800 dark:text-amber-200 text-sm flex items-center gap-3';
                syncStatusEl.innerHTML = `<i class="bi bi-info-circle-fill text-amber-600"></i> Manual sync triggers background scraper. Scheduled sync runs daily automatically via GitHub Actions.`;
            }
        } finally {
            this.setButtonLoading('triggerSyncBtn', false);
        }
    },

    async triggerModelSync() {
        const syncStatusEl = document.getElementById('modelSyncStatusNotice');
        if (syncStatusEl) {
            syncStatusEl.className = 'mt-3 p-3.5 rounded-xl bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-900 text-indigo-800 dark:text-indigo-200 text-xs flex items-center gap-2.5';
            syncStatusEl.innerHTML = `<div class="animate-spin rounded-full h-4 w-4 border-2 border-indigo-600 border-t-transparent"></div> Crawling https://www.mgu.ac.in/examinations/model-question-papers-fyugp-2024/, splitting papers and assigning to courses...`;
            syncStatusEl.classList.remove('hidden');
        }

        this.setButtonLoading('triggerModelSyncBtn', true, 'Running...');

        try {
            const res = await fetch('/api/sync-model', { method: 'POST' });
            const data = await res.json();
            if (syncStatusEl) {
                syncStatusEl.className = 'mt-3 p-3.5 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-900 text-emerald-800 dark:text-emerald-200 text-xs flex items-center gap-2.5';
                syncStatusEl.innerHTML = `<i class="bi bi-check-circle-fill text-emerald-600"></i> ${data.message || 'MGU Model Question Papers crawler initiated successfully!'}`;
            }
            setTimeout(async () => {
                await this.loadAllData();
                this.updateStatsUI();
                this.applyFilters();
            }, 5000);
        } catch (e) {
            if (syncStatusEl) {
                syncStatusEl.className = 'mt-3 p-3.5 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-900 text-amber-800 dark:text-amber-200 text-xs flex items-center gap-2.5';
                syncStatusEl.innerHTML = `<i class="bi bi-info-circle-fill text-amber-600"></i> Model question papers crawler runs daily via GitHub Actions. Triggered in background.`;
            }
        } finally {
            this.setButtonLoading('triggerModelSyncBtn', false);
        }
    },

    // -------------------------------------------------------------
    // STUDENT REPORTS & FEEDBACK CONTROLLERS
    // -------------------------------------------------------------

    populateFeedbackDeptDropdown(selectedDept = '') {
        const select = document.getElementById('reportDeptSelect');
        if (!select) return;
        select.innerHTML = '<option value="">Select Department...</option>' +
            this.departments.map(d => `<option value="${d.code}">${d.name} (${d.code})</option>`).join('');
        if (selectedDept) {
            select.value = selectedDept;
        }
    },

    openFeedbackModal(initialTab = 'general', deptCode = '', sem = '', courseCode = '', courseTitle = '') {
        const modal = document.getElementById('feedbackModal');
        if (!modal) return;
        modal.classList.remove('hidden');

        this.populateFeedbackDeptDropdown(deptCode);
        if (deptCode) {
            const dSelect = document.getElementById('reportDeptSelect');
            if (dSelect) dSelect.value = deptCode;
        }
        if (sem) {
            const sSelect = document.getElementById('reportSemesterSelect');
            if (sSelect) sSelect.value = sem;
        }
        if (courseCode) {
            const cInput = document.getElementById('reportCourseCode');
            if (cInput) cInput.value = courseCode;
        }
        if (courseTitle) {
            const tInput = document.getElementById('reportCourseTitle');
            if (tInput) tInput.value = courseTitle;
        }

        document.getElementById('reportSuccessAlert')?.classList.add('hidden');
        document.getElementById('feedbackSuccessAlert')?.classList.add('hidden');

        this.switchFeedbackTab(initialTab);
    },

    closeFeedbackModal() {
        document.getElementById('feedbackModal')?.classList.add('hidden');
    },

    switchFeedbackTab(tab) {
        const reportForm = document.getElementById('missingPaperForm');
        const generalForm = document.getElementById('generalFeedbackForm');
        const btnReport = document.getElementById('feedbackTabBtnReport');
        const btnGeneral = document.getElementById('feedbackTabBtnGeneral');

        const activeClass = 'pb-2.5 text-xs font-semibold border-b-2 border-blue-600 text-blue-600 dark:text-blue-400 flex items-center gap-1.5 transition';
        const inactiveClass = 'pb-2.5 text-xs font-medium border-b-2 border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 flex items-center gap-1.5 transition';

        if (reportForm) reportForm.classList.toggle('hidden', tab !== 'report');
        if (generalForm) generalForm.classList.toggle('hidden', tab !== 'general');

        if (btnReport) btnReport.className = tab === 'report' ? activeClass : inactiveClass;
        if (btnGeneral) btnGeneral.className = tab === 'general' ? activeClass : inactiveClass;
    },

    async loadFeedbackReports() {
        try {
            let serverReports = [];
            try {
                const res = await fetch('/api/feedback');
                if (res.ok) {
                    serverReports = await res.json();
                } else {
                    const staticRes = await fetch('data/reports.json');
                    if (staticRes.ok) serverReports = await staticRes.json();
                }
            } catch (e) {
                try {
                    const staticRes = await fetch('data/reports.json');
                    if (staticRes.ok) serverReports = await staticRes.json();
                } catch (err) {}
            }

            let localReports = [];
            try {
                const localStr = localStorage.getItem('mgu_feedback_reports');
                if (localStr) localReports = JSON.parse(localStr);
            } catch (e) {}

            const map = new Map();
            (Array.isArray(serverReports) ? serverReports : []).forEach(r => { if (r && r.id) map.set(r.id, r); });
            (Array.isArray(localReports) ? localReports : []).forEach(r => { if (r && r.id) map.set(r.id, r); });

            this.feedbackReports = Array.from(map.values()).sort((a, b) => new Date(b.createdAt || 0) - new Date(a.createdAt || 0));
        } catch (e) {
            this.feedbackReports = [];
        }
        this.updateAdminInboxBadge();
    },

    async saveReport(report) {
        if (!this.feedbackReports) this.feedbackReports = [];
        this.feedbackReports.unshift(report);
        try {
            // Keep localStorage clean without large base64 strings
            const sanitizedReports = this.feedbackReports.map(r => {
                if (r.fileData) {
                    const copy = { ...r };
                    delete copy.fileData;
                    return copy;
                }
                return r;
            });
            localStorage.setItem('mgu_feedback_reports', JSON.stringify(sanitizedReports));
        } catch (e) {}
        try {
            const resp = await fetch('/api/feedback', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(report)
            });
            if (resp.ok) {
                const resData = await resp.json();
                if (resData.fileUrl) {
                    report.fileUrl = resData.fileUrl;
                }
            }
        } catch (e) {}
        this.updateAdminInboxBadge();
    },

    async handleMissingPaperSubmit(e) {
        e.preventDefault();
        const dept = document.getElementById('reportDeptSelect')?.value;
        const semester = document.getElementById('reportSemesterSelect')?.value;
        const courseCode = (document.getElementById('reportCourseCode')?.value || '').trim().toUpperCase();
        const title = (document.getElementById('reportCourseTitle')?.value || '').trim();
        const examDate = (document.getElementById('reportExamDate')?.value || '').trim();
        const missingType = document.getElementById('reportMissingType')?.value || 'Both QP & Scheme';
        const driveLink = (document.getElementById('reportDriveLink')?.value || '').trim();
        const contact = (document.getElementById('reportContact')?.value || '').trim();

        if (!dept || !semester || !title || !examDate) {
            alert('Please fill in all required fields (Department, Semester, Course Title, Exam Month & Year).');
            return;
        }

        this.setButtonLoading('reportSubmitBtn', true, 'Submitting Report...');

        let base64Data = '';
        if (this.reportSelectedFile) {
            try {
                if (this.reportSelectedFile.size <= 10 * 1024 * 1024) {
                    base64Data = await new Promise((resolve) => {
                        const reader = new FileReader();
                        reader.onload = () => resolve(reader.result);
                        reader.onerror = () => resolve('');
                        reader.readAsDataURL(this.reportSelectedFile);
                    });
                }
            } catch (err) {
                console.warn('Could not read file as data URL:', err);
            }
        }

        const reportId = 'rep_' + Date.now() + '_' + Math.random().toString(36).substr(2, 6);

        if (this.reportSelectedFile) {
            await MissingFileStorage.saveFile(reportId, this.reportSelectedFile, this.reportSelectedFile.name);
        }

        const report = {
            id: reportId,
            type: 'missing_paper',
            status: 'pending',
            createdAt: new Date().toISOString(),
            dept,
            semester,
            courseCode,
            title,
            examDate,
            missingType,
            driveLink,
            contact,
            fileName: this.reportSelectedFile ? this.reportSelectedFile.name : '',
            fileSize: this.reportSelectedFile ? this.reportSelectedFile.size : 0,
            fileData: base64Data
        };

        await this.saveReport(report);

        const successAlert = document.getElementById('reportSuccessAlert');
        if (successAlert) successAlert.classList.remove('hidden');

        const codeEl = document.getElementById('reportCourseCode');
        const titleEl = document.getElementById('reportCourseTitle');
        const dateEl = document.getElementById('reportExamDate');
        const linkEl = document.getElementById('reportDriveLink');
        const contEl = document.getElementById('reportContact');
        if (codeEl) codeEl.value = '';
        if (titleEl) titleEl.value = '';
        if (dateEl) dateEl.value = '';
        if (linkEl) linkEl.value = '';
        if (contEl) contEl.value = '';
        this.clearReportFile();

        this.setButtonLoading('reportSubmitBtn', false);

        setTimeout(() => {
            this.closeFeedbackModal();
        }, 1800);
    },

    async handleGeneralFeedbackSubmit(e) {
        e.preventDefault();
        const category = document.getElementById('feedbackCategory')?.value || 'Suggestion';
        const message = (document.getElementById('feedbackMessage')?.value || '').trim();
        const contact = (document.getElementById('feedbackContact')?.value || '').trim();

        if (!message) {
            alert('Please enter your feedback message.');
            return;
        }

        this.setButtonLoading('feedbackSubmitBtn', true, 'Sending Feedback...');

        const feedback = {
            id: 'fb_' + Date.now() + '_' + Math.random().toString(36).substr(2, 6),
            type: 'general_feedback',
            status: 'pending',
            createdAt: new Date().toISOString(),
            category,
            message,
            contact
        };

        await this.saveReport(feedback);

        const successAlert = document.getElementById('feedbackSuccessAlert');
        if (successAlert) successAlert.classList.remove('hidden');

        const msgEl = document.getElementById('feedbackMessage');
        const contEl = document.getElementById('feedbackContact');
        if (msgEl) msgEl.value = '';
        if (contEl) contEl.value = '';

        this.setButtonLoading('feedbackSubmitBtn', false);

        setTimeout(() => {
            this.closeFeedbackModal();
        }, 1800);
    },

    updateAdminInboxBadge() {
        const badge = document.getElementById('adminInboxBadge');
        const countAll = document.getElementById('inboxCountAll');
        const countPending = document.getElementById('inboxCountPending');

        const total = (this.feedbackReports || []).length;
        const pending = (this.feedbackReports || []).filter(r => r.status === 'pending').length;

        if (badge) {
            badge.textContent = pending;
            badge.classList.toggle('hidden', pending === 0);
        }
        if (countAll) countAll.textContent = total;
        if (countPending) countPending.textContent = pending;
    },

    filterAdminInbox(filter) {
        this.inboxFilter = filter;
        const btnAll = document.getElementById('inboxFilterAll');
        const btnPending = document.getElementById('inboxFilterPending');
        const btnMissing = document.getElementById('inboxFilterMissing');
        const btnFeedback = document.getElementById('inboxFilterFeedback');

        const activeClass = 'px-2.5 py-1 rounded-md font-semibold bg-blue-600 text-white shadow-xs';
        const inactiveClass = 'px-2.5 py-1 rounded-md font-medium text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-700 hover:bg-slate-200';

        if (btnAll) btnAll.className = filter === 'all' ? activeClass : inactiveClass;
        if (btnPending) btnPending.className = filter === 'pending' ? activeClass : inactiveClass;
        if (btnMissing) btnMissing.className = filter === 'missing' ? activeClass : inactiveClass;
        if (btnFeedback) btnFeedback.className = filter === 'feedback' ? activeClass : inactiveClass;

        this.renderAdminInbox();
    },

    renderAdminInbox() {
        const container = document.getElementById('adminInboxListContainer');
        if (!container) return;

        this.updateAdminInboxBadge();

        let list = this.feedbackReports || [];
        if (this.inboxFilter === 'pending') {
            list = list.filter(r => r.status === 'pending');
        } else if (this.inboxFilter === 'missing') {
            list = list.filter(r => r.type === 'missing_paper');
        } else if (this.inboxFilter === 'feedback') {
            list = list.filter(r => r.type === 'general_feedback');
        }

        if (list.length === 0) {
            container.innerHTML = `
                <div class="py-12 text-center text-slate-400">
                    <div class="w-10 h-10 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center mx-auto text-lg mb-2 text-slate-400">
                        <i class="bi bi-inbox"></i>
                    </div>
                    <div class="font-bold text-slate-700 dark:text-slate-300">No reports found</div>
                    <div class="text-[11px] text-slate-400 mt-0.5">There are no reports matching the "${this.inboxFilter}" filter.</div>
                </div>
            `;
            return;
        }

        const escapeHtml = (str) => {
            if (!str) return '';
            return String(str).replace(/[&<>"']/g, m => ({
                '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;'
            }[m]));
        };

        container.innerHTML = list.map(r => {
            const isMissing = r.type === 'missing_paper';
            const isPending = r.status === 'pending';
            const dateStr = r.createdAt ? new Date(r.createdAt).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : 'Recently';

            return `
                <div class="p-3 bg-white dark:bg-slate-800/80 rounded-xl border border-slate-200 dark:border-slate-700/70 hover:border-slate-300 dark:hover:border-slate-600 transition space-y-2.5">
                    <div class="flex flex-wrap items-center justify-between gap-2">
                        <div class="flex items-center gap-2">
                            ${isMissing ? `
                                <span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-800 flex items-center gap-1">
                                    <i class="bi bi-flag-fill"></i> Missing Paper
                                </span>
                            ` : `
                                <span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-indigo-100 dark:bg-indigo-950/60 text-indigo-800 dark:text-indigo-300 border border-indigo-300 dark:border-indigo-800 flex items-center gap-1">
                                    <i class="bi bi-chat-left-text-fill"></i> ${escapeHtml(r.category || 'Feedback')}
                                </span>
                            `}

                            <span class="px-2 py-0.5 rounded-full text-[10px] font-bold ${isPending ? 'bg-rose-100 dark:bg-rose-950/60 text-rose-800 dark:text-rose-300 border border-rose-300 dark:border-rose-800 animate-pulse' : 'bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800'} flex items-center gap-1">
                                <i class="bi ${isPending ? 'bi-clock-history' : 'bi-check-lg'}"></i> ${isPending ? 'Pending' : 'Resolved'}
                            </span>
                        </div>
                        <span class="text-[11px] text-slate-400 font-mono">${dateStr}</span>
                    </div>

                    ${isMissing ? `
                        <div>
                            <div class="font-bold text-slate-900 dark:text-white text-xs sm:text-sm">
                                ${escapeHtml(r.title)}
                                ${r.courseCode ? `<span class="font-mono text-blue-600 dark:text-blue-400 font-semibold ml-1">(${escapeHtml(r.courseCode)})</span>` : ''}
                            </div>
                            <div class="text-[11px] text-slate-600 dark:text-slate-300 mt-1 flex flex-wrap items-center gap-x-2 gap-y-1">
                                <span><strong class="text-slate-800 dark:text-slate-200">Dept:</strong> ${escapeHtml(r.dept)}</span>
                                <span>•</span>
                                <span><strong class="text-slate-800 dark:text-slate-200">Semester:</strong> ${escapeHtml(r.semester)}</span>
                                <span>•</span>
                                <span><strong class="text-slate-800 dark:text-slate-200">Exam:</strong> ${escapeHtml(r.examDate || 'N/A')}</span>
                                <span>•</span>
                                <span><strong class="text-slate-800 dark:text-slate-200">Missing:</strong> ${escapeHtml(r.missingType || 'Both')}</span>
                            </div>
                            ${r.driveLink ? `
                                <div class="mt-1.5">
                                    <a href="${escapeHtml(r.driveLink)}" target="_blank" rel="noopener noreferrer" class="text-blue-600 dark:text-blue-400 hover:underline font-medium text-[11px] inline-flex items-center gap-1 bg-blue-50 dark:bg-blue-950/50 px-2.5 py-1 rounded-lg border border-blue-200 dark:border-blue-900/60 transition">
                                        <i class="bi bi-link-45deg text-xs"></i> Open Attached Drive/Web Link
                                    </a>
                                </div>
                            ` : ''}
                            ${(r.fileName || r.fileUrl) ? `
                                <div class="mt-2 p-2.5 rounded-xl bg-emerald-50/70 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800/60 flex flex-wrap items-center justify-between gap-2">
                                    <div class="flex items-center gap-2 min-w-0">
                                        <div class="w-7 h-7 rounded-lg bg-emerald-600 text-white flex items-center justify-center shrink-0 text-xs shadow-xs">
                                            <i class="bi bi-file-earmark-pdf-fill"></i>
                                        </div>
                                        <div class="min-w-0">
                                            <span class="font-semibold text-slate-800 dark:text-slate-100 text-xs truncate block">${escapeHtml(r.fileName || 'Attached Missing Paper.pdf')}</span>
                                            <span class="text-[10px] text-slate-500 dark:text-slate-400">${App.formatFileSize(r.fileSize || 0)}</span>
                                        </div>
                                    </div>
                                    <div class="flex items-center gap-1.5 shrink-0">
                                        <button type="button" onclick="App.previewReportFile('${r.id}')" class="px-2.5 py-1 rounded-md text-[11px] font-semibold bg-emerald-600 hover:bg-emerald-500 text-white flex items-center gap-1 transition shadow-xs">
                                            <i class="bi bi-eye"></i> Preview
                                        </button>
                                        <button type="button" onclick="App.downloadReportFile('${r.id}')" class="px-2.5 py-1 rounded-md text-[11px] font-semibold bg-slate-200 dark:bg-slate-700 hover:bg-slate-300 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 flex items-center gap-1 transition">
                                            <i class="bi bi-download"></i> Download
                                        </button>
                                    </div>
                                </div>
                            ` : ''}
                            ${r.contact ? `
                                <div class="text-slate-400 text-[10px] mt-1">
                                    <i class="bi bi-person"></i> Student contact: ${escapeHtml(r.contact)}
                                </div>
                            ` : ''}
                        </div>
                    ` : `
                        <div>
                            <div class="text-slate-800 dark:text-slate-200 text-xs whitespace-pre-wrap leading-relaxed">
                                ${escapeHtml(r.message)}
                            </div>
                            ${r.contact ? `
                                <div class="text-slate-400 text-[10px] mt-1.5">
                                    <i class="bi bi-person"></i> Contact: ${escapeHtml(r.contact)}
                                </div>
                            ` : ''}
                        </div>
                    `}

                    <div class="flex items-center justify-end gap-2 pt-1 border-t border-slate-100 dark:border-slate-700/50">
                        ${isMissing ? `
                            <button onclick="App.prefillUploadFromReport('${r.id}')" class="px-2.5 py-1 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300 hover:bg-blue-100 font-semibold text-[11px] transition flex items-center gap-1 border border-blue-200 dark:border-blue-800">
                                <i class="bi bi-pencil-square"></i> Upload Paper
                            </button>
                        ` : ''}
                        <button onclick="App.toggleReportStatus('${r.id}')" class="px-2.5 py-1 rounded-lg ${isPending ? 'bg-emerald-600 hover:bg-emerald-500 text-white font-semibold' : 'bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-200'} text-[11px] transition flex items-center gap-1">
                            <i class="bi ${isPending ? 'bi-check2' : 'bi-arrow-counterclockwise'}"></i> ${isPending ? 'Mark Resolved' : 'Re-open'}
                        </button>
                        <button onclick="App.deleteReport('${r.id}')" class="p-1 text-slate-400 hover:text-rose-600 dark:hover:text-rose-400 transition" title="Delete Report">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </div>
            `;
        }).join('');
    },

    async toggleReportStatus(id) {
        const rep = (this.feedbackReports || []).find(r => r.id === id);
        if (!rep) return;
        rep.status = rep.status === 'resolved' ? 'pending' : 'resolved';
        try {
            localStorage.setItem('mgu_feedback_reports', JSON.stringify(this.feedbackReports));
            await fetch('/api/feedback', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'update_status', id, status: rep.status })
            });
        } catch (e) {}
        this.updateAdminInboxBadge();
        this.renderAdminInbox();
    },

    async deleteReport(id) {
        if (!confirm('Are you sure you want to delete this report?')) return;
        this.feedbackReports = (this.feedbackReports || []).filter(r => r.id !== id);
        try {
            localStorage.setItem('mgu_feedback_reports', JSON.stringify(this.feedbackReports));
            await fetch('/api/feedback', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'delete', id })
            });
        } catch (e) {}
        this.updateAdminInboxBadge();
        this.renderAdminInbox();
    },

    async clearResolvedReports() {
        const resolvedCount = (this.feedbackReports || []).filter(r => r.status === 'resolved').length;
        if (resolvedCount === 0) {
            alert('No resolved reports to clear.');
            return;
        }
        if (!confirm(`Are you sure you want to clear ${resolvedCount} resolved report(s)?`)) return;
        this.feedbackReports = (this.feedbackReports || []).filter(r => r.status !== 'resolved');
        try {
            localStorage.setItem('mgu_feedback_reports', JSON.stringify(this.feedbackReports));
            await fetch('/api/feedback', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'clear_resolved' })
            });
        } catch (e) {}
        this.updateAdminInboxBadge();
        this.renderAdminInbox();
    },

    exportReportsJson() {
        const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(this.feedbackReports || [], null, 2));
        const downloadAnchor = document.createElement('a');
        downloadAnchor.setAttribute('href', dataStr);
        downloadAnchor.setAttribute('download', `mgu_reports_feedback_${new Date().toISOString().slice(0, 10)}.json`);
        document.body.appendChild(downloadAnchor);
        downloadAnchor.click();
        downloadAnchor.remove();
    },

    prefillUploadFromReport(id) {
        const report = (this.feedbackReports || []).find(r => r.id === id);
        if (!report) return;

        this.switchAdminTab('upload');

        if (report.dept) {
            const deptSelect = document.getElementById('adminUploadDept');
            if (deptSelect) deptSelect.value = report.dept;
        }
        if (report.semester) {
            const semSelect = document.getElementById('adminUploadSemester');
            if (semSelect) semSelect.value = report.semester;
        }
        if (report.courseCode) {
            const codeInput = document.getElementById('adminUploadCourseCode');
            if (codeInput) codeInput.value = report.courseCode;
        }
        if (report.title) {
            const titleInput = document.getElementById('adminUploadTitle');
            if (titleInput) titleInput.value = report.title;
        }
        if (report.examDate) {
            const examInput = document.getElementById('adminUploadExamName');
            if (examInput) examInput.value = report.examDate;
        }
        if (report.driveLink) {
            const qpUrlInput = document.getElementById('adminUploadQpUrl');
            if (qpUrlInput) qpUrlInput.value = report.driveLink;
        }
        if (report.fileUrl) {
            const qpUrlInput = document.getElementById('adminUploadQpUrl');
            if (qpUrlInput && !qpUrlInput.value) qpUrlInput.value = report.fileUrl;
        }

        const statusEl = document.getElementById('adminUploadStatus');
        if (statusEl) {
            statusEl.className = 'p-3 rounded-lg text-xs bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800 flex items-center justify-between gap-2';
            statusEl.innerHTML = `
                <div class="flex items-center gap-1.5">
                    <i class="bi bi-info-circle-fill text-blue-600"></i>
                    <span>Pre-filled from student report for <strong>${report.courseCode || report.title}</strong></span>
                </div>
                <button type="button" onclick="App.toggleReportStatus('${report.id}')" class="underline font-semibold hover:text-blue-900 dark:hover:text-blue-100">
                    Mark Report Resolved
                </button>
            `;
            statusEl.classList.remove('hidden');
        }

        document.getElementById('adminUploadTitle')?.focus();
    },

    bindModelPapersEvents() {
        const sInput = document.getElementById('modelSearchInput');
        const clearBtn = document.getElementById('clearModelSearchBtn');
        if (sInput) {
            sInput.addEventListener('input', (e) => {
                this.modelState.searchQuery = e.target.value;
                this.modelState.currentPage = 1;
                if (clearBtn) clearBtn.classList.toggle('hidden', !e.target.value.trim());
                this.renderModelPapers();
            });
        }
        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                if (sInput) sInput.value = '';
                this.modelState.searchQuery = '';
                clearBtn.classList.add('hidden');
                this.modelState.currentPage = 1;
                this.renderModelPapers();
            });
        }
        const dSelect = document.getElementById('modelDeptSelect');
        if (dSelect) {
            dSelect.addEventListener('change', (e) => {
                this.modelState.selectedDept = e.target.value;
                this.modelState.currentPage = 1;
                this.renderModelPapers();
            });
        }
        const tSelect = document.getElementById('modelTypeSelect');
        if (tSelect) {
            tSelect.addEventListener('change', (e) => {
                this.modelState.selectedType = e.target.value;
                this.modelState.currentPage = 1;
                this.renderModelPapers();
            });
        }
        document.querySelectorAll('.model-sem-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.setModelSemester(btn.dataset.modelSem);
            });
        });
    },

    populateModelDepartments() {
        const select = document.getElementById('modelDeptSelect');
        if (!select || select.options.length > 1) return;
        (this.departments || []).forEach(d => {
            const opt = document.createElement('option');
            opt.value = d.code;
            opt.textContent = d.name;
            select.appendChild(opt);
        });
    },

    setModelSemester(sem) {
        this.modelState.selectedSemester = sem;
        this.modelState.currentPage = 1;
        document.querySelectorAll('.model-sem-btn').forEach(btn => {
            const isAct = btn.dataset.modelSem === String(sem);
            if (isAct) {
                btn.className = 'model-sem-btn px-3 py-1 text-xs font-semibold rounded-lg bg-indigo-600 text-white shadow-xs transition shrink-0';
            } else {
                btn.className = 'model-sem-btn px-2.5 py-1 text-xs font-medium rounded-lg text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition shrink-0';
            }
        });
        this.renderModelPapers();
    },

    resetModelFilters() {
        this.modelState.searchQuery = '';
        this.modelState.selectedSemester = 'all';
        this.modelState.selectedDept = '';
        this.modelState.selectedType = '';
        this.modelState.currentPage = 1;

        const sInput = document.getElementById('modelSearchInput');
        if (sInput) sInput.value = '';
        const dSelect = document.getElementById('modelDeptSelect');
        if (dSelect) dSelect.value = '';
        const tSelect = document.getElementById('modelTypeSelect');
        if (tSelect) tSelect.value = '';
        const clearBtn = document.getElementById('clearModelSearchBtn');
        if (clearBtn) clearBtn.classList.add('hidden');

        document.querySelectorAll('.model-sem-btn').forEach(btn => {
            const isAll = btn.dataset.modelSem === 'all';
            if (isAll) {
                btn.className = 'model-sem-btn px-3 py-1 text-xs font-semibold rounded-lg bg-indigo-600 text-white shadow-xs transition shrink-0';
            } else {
                btn.className = 'model-sem-btn px-2.5 py-1 text-xs font-medium rounded-lg text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition shrink-0';
            }
        });

        this.renderModelPapers();
    },

    renderModelPapers() {
        const grid = document.getElementById('modelPapersGrid');
        const countEl = document.getElementById('modelResultsCount');
        const paginationEl = document.getElementById('modelPapersPagination');
        if (!grid) return;

        // Ensure model catalog populated
        if (!this.modelCatalog || this.modelCatalog.length === 0) {
            this.modelCatalog = [];
            (this.papers || []).forEach(p => {
                if (p.model_papers && Array.isArray(p.model_papers)) {
                    p.model_papers.forEach(m => {
                        this.modelCatalog.push({
                            course_code: p.course_code,
                            course_title: p.title,
                            semester: p.semester,
                            dept_code: p.dept_code,
                            dept_name: p.dept_name,
                            course_type: p.course_type,
                            is_signature: this.isSignatureCourse(p.course_code),
                            model_id: m.id,
                            title: m.title,
                            paper_type: m.paper_type,
                            url: m.url,
                            cdn_url: m.cdn_url,
                            pages: m.pages
                        });
                    });
                }
            });
        }

        const query = (this.modelState.searchQuery || '').trim().toLowerCase();
        const sem = this.modelState.selectedSemester;
        const dept = (this.modelState.selectedDept || '').toUpperCase();
        const ptype = (this.modelState.selectedType || '').toUpperCase();

        let filtered = this.modelCatalog.filter(m => {
            if (sem !== 'all' && m.semester !== parseInt(sem, 10)) {
                return false;
            }
            if (dept && m.dept_code !== dept) {
                return false;
            }
            if (ptype && (m.paper_type || 'THEORY').toUpperCase() !== ptype) {
                return false;
            }
            if (query) {
                const matchCode = (m.course_code || '').toLowerCase().includes(query);
                const matchTitle = (m.title || m.course_title || '').toLowerCase().includes(query);
                const matchDept = (m.dept_name || '').toLowerCase().includes(query);
                if (!matchCode && !matchTitle && !matchDept) return false;
            }
            return true;
        });

        // Separate standard courses and college-specific signature courses (placed at the bottom)
        const regular = filtered.filter(m => !this.isSignatureCourse(m));
        const signature = filtered.filter(m => this.isSignatureCourse(m));
        const sortedResults = [...regular, ...signature];

        if (countEl) {
            countEl.textContent = `Showing ${sortedResults.length.toLocaleString()} Model Question Papers`;
        }

        if (sortedResults.length === 0) {
            grid.innerHTML = `
                <div class="col-span-full py-16 text-center">
                    <div class="w-16 h-16 rounded-2xl bg-indigo-50 dark:bg-indigo-950/40 text-indigo-500 mx-auto flex items-center justify-center text-3xl mb-3">
                        <i class="bi bi-file-earmark-x"></i>
                    </div>
                    <h3 class="text-base font-bold text-slate-800 dark:text-slate-200">No Model Question Papers Found</h3>
                    <p class="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-sm mx-auto">
                        Try adjusting your search query, semester filter, or department selection.
                    </p>
                    <button onclick="App.resetModelFilters()" class="mt-4 px-4 py-2 text-xs font-semibold rounded-xl bg-indigo-600 text-white hover:bg-indigo-500 transition shadow-xs">
                        Reset Filters
                    </button>
                </div>
            `;
            if (paginationEl) paginationEl.innerHTML = '';
            return;
        }

        const itemsPerPage = this.modelState.itemsPerPage || 24;
        const totalPages = Math.ceil(sortedResults.length / itemsPerPage);
        const page = Math.min(Math.max(1, this.modelState.currentPage || 1), totalPages);
        this.modelState.currentPage = page;

        const startIdx = (page - 1) * itemsPerPage;
        const pageItems = sortedResults.slice(startIdx, startIdx + itemsPerPage);

        grid.innerHTML = pageItems.map(m => this.renderModelPaperCard(m)).join('');

        this.renderModelPagination(totalPages, page, paginationEl);
    },

    renderModelPaperCard(m) {
        const isPrac = (m.paper_type || 'THEORY').toUpperCase() === 'PRACTICAL';
        const pdfUrl = m.cdn_url || m.url;
        const safeTitle = (m.title || m.course_title || `Course ${m.course_code}`).replace(/'/g, "\\'");
        const isSig = this.isSignatureCourse(m.course_code);

        return `
            <div class="bg-white dark:bg-slate-800 rounded-2xl p-4 sm:p-5 border ${isSig ? 'border-amber-200 dark:border-amber-900/60' : 'border-slate-200 dark:border-slate-700/80'} shadow-xs hover:shadow-md transition flex flex-col justify-between">
                <div>
                    <!-- Badges Row -->
                    <div class="flex items-center justify-between gap-2 mb-2.5">
                        <div class="flex items-center gap-1.5 flex-wrap">
                            <span class="px-2 py-0.5 rounded text-[11px] font-bold font-mono bg-blue-50 dark:bg-blue-950/50 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-900/40">
                                ${m.course_code}
                            </span>
                            <span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300">
                                Sem ${m.semester}
                            </span>
                            ${m.course_type ? `
                                <span class="px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-slate-100 dark:bg-slate-750 text-slate-500">
                                    ${m.course_type}
                                </span>
                            ` : ''}
                        </div>
                        ${isSig ? `
                            <span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800" title="College-Specific Signature Course">
                                <i class="bi bi-patch-check-fill text-amber-500"></i> Signature
                            </span>
                        ` : ''}
                    </div>

                    <!-- Course Title -->
                    <h3 class="font-bold text-slate-900 dark:text-slate-100 text-sm sm:text-base leading-snug line-clamp-2 mb-1.5" title="${m.title || m.course_title}">
                        ${m.title || m.course_title}
                    </h3>

                    <!-- Department -->
                    <div class="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-1.5 truncate mb-4">
                        <i class="bi bi-mortarboard text-slate-400"></i>
                        <span class="truncate font-medium text-slate-600 dark:text-slate-300">
                            ${m.dept_name || m.dept_code || 'MGU FYUGP'}
                        </span>
                    </div>
                </div>

                <!-- Footer with Model Paper Info & Actions -->
                <div class="pt-3 border-t border-slate-100 dark:border-slate-700/60 flex items-center justify-between gap-2">
                    <div class="flex items-center gap-1.5 min-w-0">
                        <i class="${isPrac ? 'bi bi-flask text-purple-600' : 'bi bi-file-earmark-text text-indigo-600'} text-sm"></i>
                        <span class="text-xs font-bold uppercase tracking-wider ${isPrac ? 'text-purple-700 dark:text-purple-300' : 'text-indigo-700 dark:text-indigo-300'} truncate">
                            ${isPrac ? 'Practical QP' : 'Theory QP'}
                        </span>
                        ${m.pages ? `<span class="text-[11px] text-slate-400">(${m.pages}p)</span>` : ''}
                    </div>

                    <div class="flex items-center gap-1.5 shrink-0">
                        <button onclick="App.previewDirect(this, '${pdfUrl}', '${safeTitle}', '${m.course_code}')" class="px-3 py-1.5 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white shadow-xs flex items-center gap-1 transition" title="Preview Model Question Paper">
                            <i class="bi bi-eye"></i> View
                        </button>
                        <a href="${pdfUrl}" target="_blank" download class="p-1.5 text-xs rounded-lg bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 transition" title="Download Model PDF">
                            <i class="bi bi-download"></i>
                        </a>
                    </div>
                </div>
            </div>
        `;
    },

    renderModelPagination(totalPages, cur, container) {
        if (!container || totalPages <= 1) {
            if (container) container.innerHTML = '';
            return;
        }

        let mobileHtml = `
            <div class="flex items-center justify-between sm:hidden w-full px-1 gap-2">
                <button onclick="App.goToModelPage(${cur - 1})" ${cur === 1 ? 'disabled' : ''} class="flex-1 py-2 text-xs font-semibold rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-50 transition flex items-center justify-center gap-1 shadow-xs min-h-[38px]">
                    <i class="bi bi-chevron-left"></i> Prev
                </button>
                <div class="px-3 py-2 text-xs font-bold text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shrink-0 shadow-xs min-h-[38px] flex items-center justify-center">
                    Page ${cur} of ${totalPages}
                </div>
                <button onclick="App.goToModelPage(${cur + 1})" ${cur === totalPages ? 'disabled' : ''} class="flex-1 py-2 text-xs font-semibold rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-50 transition flex items-center justify-center gap-1 shadow-xs min-h-[38px]">
                    Next <i class="bi bi-chevron-right"></i>
                </button>
            </div>
        `;

        let desktopHtml = `
            <div class="hidden sm:flex items-center justify-center gap-1 sm:gap-2">
                <button onclick="App.goToModelPage(${cur - 1})" ${cur === 1 ? 'disabled' : ''} class="px-3 py-1.5 text-xs font-medium rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-50 transition min-h-[38px] flex items-center gap-1">
                    <i class="bi bi-chevron-left"></i> Prev
                </button>
        `;

        const maxButtons = 5;
        let startPage = Math.max(1, cur - 2);
        let endPage = Math.min(totalPages, startPage + maxButtons - 1);
        if (endPage - startPage < maxButtons - 1) {
            startPage = Math.max(1, endPage - maxButtons + 1);
        }

        if (startPage > 1) {
            desktopHtml += `<button onclick="App.goToModelPage(1)" class="w-8 h-8 text-xs font-medium rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 min-h-[38px]">1</button>`;
            if (startPage > 2) desktopHtml += `<span class="px-1 text-slate-400">...</span>`;
        }

        for (let p = startPage; p <= endPage; p++) {
            const isActive = p === cur;
            desktopHtml += `
                <button onclick="App.goToModelPage(${p})" class="w-8 h-8 text-xs font-semibold rounded-lg ${isActive ? 'bg-indigo-600 text-white shadow-xs' : 'bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50'} transition min-h-[38px]">
                    ${p}
                </button>
            `;
        }

        if (endPage < totalPages) {
            if (endPage < totalPages - 1) desktopHtml += `<span class="px-1 text-slate-400">...</span>`;
            desktopHtml += `<button onclick="App.goToModelPage(${totalPages})" class="w-8 h-8 text-xs font-medium rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 min-h-[38px]">${totalPages}</button>`;
        }

        desktopHtml += `
                <button onclick="App.goToModelPage(${cur + 1})" ${cur === totalPages ? 'disabled' : ''} class="px-3 py-1.5 text-xs font-medium rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-50 transition min-h-[38px] flex items-center gap-1">
                    Next <i class="bi bi-chevron-right"></i>
                </button>
            </div>
        `;

        container.innerHTML = mobileHtml + desktopHtml;
    },

    goToModelPage(page) {
        this.modelState.currentPage = page;
        this.renderModelPapers();
        const grid = document.getElementById('modelPapersGrid');
        if (grid) {
            const offset = grid.getBoundingClientRect().top + window.scrollY - 100;
            window.scrollTo({ top: offset, behavior: 'smooth' });
        }
    },

};

window.App = App;

// Start on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    App.init();
});


// Global fetchResource helper fallback
window.fetchResource = async (apiUrl, staticUrl) => {
    if (window.App && typeof window.App.fetchResource === 'function') {
        return await window.App.fetchResource(apiUrl, staticUrl);
    }
    try {
        const res = await fetch(apiUrl);
        if (res.ok) return await res.json();
    } catch (e) {}
    try {
        const resStatic = await fetch(staticUrl);
        if (resStatic.ok) return await resStatic.json();
    } catch (e) {}
    return null;
};

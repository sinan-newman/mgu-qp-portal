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

const App = {
    // Data stores
    papers: [],
    departments: [],
    stats: {},
    bookmarks: new Set(),
    filteredPapers: [],

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
        'bsw': ['bsw', 'social work']
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
        deptSearchQuery: ''      // Department list quick filter
    },

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

        // Ensure By Department is default active view
        this.switchTab('departments');

        if (window.location.hash === '#admin') {
            this.openAdminModal();
        }
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

    initTheme() {
        const savedTheme = localStorage.getItem('mgu_theme');
        if (savedTheme === 'dark' || (!savedTheme && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
            this.setTheme(true);
        } else {
            this.setTheme(false);
        }
    },

    setTheme(isDark) {
        this.state.isDarkMode = isDark;
        if (isDark) {
            document.documentElement.classList.add('dark');
            localStorage.setItem('mgu_theme', 'dark');
            const icon = document.getElementById('themeIcon');
            if (icon) icon.className = 'bi bi-sun text-amber-400';
        } else {
            document.documentElement.classList.remove('dark');
            localStorage.setItem('mgu_theme', 'light');
            const icon = document.getElementById('themeIcon');
            if (icon) icon.className = 'bi bi-moon-stars text-slate-600';
        }
    },

    toggleTheme() {
        this.setTheme(!this.state.isDarkMode);
    },

    async loadAllData() {
        const isLocalBackend = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') && window.location.port !== '';

        const fetchResource = async (apiUrl, staticUrl) => {
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
        };

        const [papersData, deptsData, statsData] = await Promise.all([
            fetchResource('/api/papers?limit=10000&has_files=false', 'data/papers.json'),
            fetchResource('/api/departments', 'data/departments.json'),
            fetchResource('/api/stats', 'data/stats.json')
        ]);

        const rawPapers = (papersData && papersData.papers) ? papersData.papers : (Array.isArray(papersData) ? papersData : []);
        
        // Strict FYUGP restriction: filter out any CBCS records
        this.papers = rawPapers.filter(p => p.batch !== 'CBCS' && p.course_type !== 'CBCS');
        
        // Sort departments strictly alphabetically (A-Z)
        const rawDepts = deptsData || [];
        this.departments = rawDepts.sort((a, b) => a.name.localeCompare(b.name));
        this.stats = statsData || {};
    },

    updateStatsUI() {
        const totalPapersEl = document.getElementById('statTotalPapers');
        const totalSchemesEl = document.getElementById('statTotalSchemes');
        const totalDeptsEl = document.getElementById('statTotalDepartments');
        const lastSyncEl = document.getElementById('statLastSync');

        const totalQPs = this.papers.filter(p => p.has_qp).length;
        const totalSchemes = this.papers.filter(p => p.has_scheme).length;

        if (totalPapersEl) totalPapersEl.textContent = `${totalQPs.toLocaleString()}+`;
        if (totalSchemesEl) totalSchemesEl.textContent = `${totalSchemes.toLocaleString()}+`;
        if (totalDeptsEl) totalDeptsEl.textContent = `${this.departments.length}`;
        if (lastSyncEl) lastSyncEl.textContent = '2024 Admission';
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

        // 2. Department Cards Quick Search Input
        const deptSearchInput = document.getElementById('deptSearchInput');
        const clearDeptSearchBtn = document.getElementById('clearDeptSearchBtn');
        if (deptSearchInput) {
            deptSearchInput.addEventListener('input', (e) => {
                this.deptState.deptSearchQuery = e.target.value.trim().toLowerCase();
                if (clearDeptSearchBtn) {
                    clearDeptSearchBtn.classList.toggle('hidden', !this.deptState.deptSearchQuery);
                }
                this.renderDepartmentsList();
            });
        }

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
                this.switchTab(btn.dataset.tab);
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
                gridViewBtn.className = 'p-1.5 rounded bg-blue-100 text-blue-700 dark:bg-blue-900/60 dark:text-blue-300';
                tableViewBtn.className = 'p-1.5 rounded text-slate-500 hover:text-slate-800 dark:hover:text-slate-200';
                this.renderPapers();
            });
            tableViewBtn.addEventListener('click', () => {
                this.state.viewMode = 'table';
                tableViewBtn.className = 'p-1.5 rounded bg-blue-100 text-blue-700 dark:bg-blue-900/60 dark:text-blue-300';
                gridViewBtn.className = 'p-1.5 rounded text-slate-500 hover:text-slate-800 dark:hover:text-slate-200';
                this.renderPapers();
            });
        }

        // 10. Theme Toggle Button
        const themeBtn = document.getElementById('themeToggleBtn');
        if (themeBtn) {
            themeBtn.addEventListener('click', () => this.toggleTheme());
        }
    },

    clearDeptSearch() {
        const input = document.getElementById('deptSearchInput');
        const btn = document.getElementById('clearDeptSearchBtn');
        if (input) input.value = '';
        if (btn) btn.classList.add('hidden');
        this.deptState.deptSearchQuery = '';
        this.renderDepartmentsList();
    },

    clearDeptPaperSearch() {
        const input = document.getElementById('deptPaperSearchInput');
        if (input) input.value = '';
        this.deptState.searchQuery = '';
        this.renderDeptSemesterPapers();
    },

    switchTab(tab) {
        this.state.activeTab = tab;

        // Update nav button active classes
        document.querySelectorAll('.nav-tab-btn').forEach(btn => {
            const isActive = btn.dataset.tab === tab;
            if (isActive) {
                btn.className = 'nav-tab-btn px-4 py-2 font-semibold text-sm rounded-lg bg-blue-600 text-white shadow-sm flex items-center gap-2 transition shrink-0';
            } else {
                btn.className = 'nav-tab-btn px-4 py-2 font-medium text-sm rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center gap-2 transition shrink-0';
            }
        });

        // Hide/Show containers
        const papersSection = document.getElementById('papersSection');
        const departmentsSection = document.getElementById('departmentsSection');
        const filterControls = document.getElementById('filterControlsSection');

        if (tab === 'departments') {
            if (papersSection) papersSection.classList.add('hidden');
            if (departmentsSection) departmentsSection.classList.remove('hidden');
            if (filterControls) filterControls.classList.add('hidden');
        } else if (tab === 'papers' || tab === 'bookmarks') {
            if (papersSection) papersSection.classList.remove('hidden');
            if (departmentsSection) departmentsSection.classList.add('hidden');
            if (filterControls) filterControls.classList.remove('hidden');
            this.state.currentPage = 1;
            this.applyFilters();
        }
    },

    setSemester(sem) {
        this.state.selectedSemester = sem;
        this.state.currentPage = 1;

        document.querySelectorAll('.sem-filter-btn').forEach(btn => {
            const isActive = btn.dataset.sem === sem;
            if (isActive) {
                btn.className = 'sem-filter-btn px-3 py-1.5 text-xs font-semibold rounded-lg bg-blue-600 text-white shadow-xs transition';
            } else {
                btn.className = 'sem-filter-btn px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 transition';
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
                btn.className = 'ctype-filter-btn px-3 py-1 text-xs font-semibold rounded-full bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-xs transition';
            } else {
                btn.className = 'ctype-filter-btn px-3 py-1 text-xs font-medium rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 transition';
            }
        });

        this.applyFilters();
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
        let results = this.papers;

        // If on bookmarks tab, filter only bookmarks
        if (this.state.activeTab === 'bookmarks') {
            results = results.filter(p => this.bookmarks.has(p.id));
        }

        // Filter files only
        if (this.state.onlyWithFiles) {
            results = results.filter(p => p.has_files);
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
        this.renderPapers();
        this.renderPagination();
    },

    renderPapers() {
        const container = document.getElementById('papersGrid');
        const countEl = document.getElementById('resultsCount');
        if (!container) return;

        const total = this.filteredPapers.length;
        if (countEl) {
            countEl.textContent = `Showing ${total.toLocaleString()} FYUGP question papers & schemes`;
        }

        if (total === 0) {
            container.innerHTML = `
                <div class="col-span-full py-16 text-center bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-8 shadow-xs">
                    <div class="w-16 h-16 rounded-full bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 mx-auto flex items-center justify-center text-2xl mb-4">
                        <i class="bi bi-search"></i>
                    </div>
                    <h3 class="text-lg font-bold text-slate-800 dark:text-slate-100">No question papers match your filters</h3>
                    <p class="text-sm text-slate-500 dark:text-slate-400 mt-1 max-w-md mx-auto">
                        Try searching by course code (e.g. <code class="text-blue-600 font-mono font-bold">MG3DSEMAT202</code>), course name (e.g. <code class="text-blue-600 font-bold">Calculus</code>), or reset all filters.
                    </p>
                    <button onclick="App.resetFilters()" class="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-semibold transition">
                        Reset All Filters
                    </button>
                </div>
            `;
            return;
        }

        // Paginate
        const start = (this.state.currentPage - 1) * this.state.pageSize;
        const pageItems = this.filteredPapers.slice(start, start + this.state.pageSize);

        if (this.state.viewMode === 'grid') {
            container.className = 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5';
            container.innerHTML = pageItems.map(p => this.renderPaperCard(p)).join('');
        } else {
            container.className = 'col-span-full';
            container.innerHTML = this.renderPaperTable(pageItems);
        }
    },

    renderPaperCard(p) {
        const isBookmarked = this.bookmarks.has(p.id);
        const ctypeClass = `badge-${(p.course_type || 'dsc').toLowerCase()}`;

        return `
            <div class="paper-card bg-white dark:bg-slate-800 rounded-2xl p-5 flex flex-col justify-between shadow-xs border border-slate-200/80 dark:border-slate-700 hover:border-blue-400 dark:hover:border-blue-600 transition">
                <div>
                    <!-- Top Badge Bar -->
                    <div class="flex items-start justify-between gap-2 mb-3">
                        <div class="flex flex-wrap items-center gap-1.5">
                            <span class="text-xs font-bold px-2.5 py-0.5 rounded-md bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200">
                                Sem ${p.semester}
                            </span>
                            <span class="text-xs font-semibold px-2 py-0.5 rounded-md ${ctypeClass}">
                                ${p.course_type}
                            </span>
                            ${p.is_minor ? `
                                <span class="text-xs font-semibold px-2 py-0.5 rounded-md badge-minor">
                                    ${p.dept_code} (Minor)
                                </span>
                            ` : ''}
                        </div>

                        <!-- Save Button with Star Icon & Text -->
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

                    <!-- Course Code & QP Code -->
                    <div class="flex items-center gap-2 mb-1.5">
                        <span class="font-mono font-bold text-sm text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/40 px-2 py-0.5 rounded border border-blue-100 dark:border-blue-900/40">
                            ${p.course_code || 'CODE N/A'}
                        </span>
                        ${p.qp_code ? `
                            <span class="font-mono text-xs text-slate-500 dark:text-slate-400 bg-slate-100 dark:bg-slate-700/60 px-1.5 py-0.5 rounded">
                                QP: ${p.qp_code}
                            </span>
                        ` : ''}
                    </div>

                    <!-- Course Title -->
                    <h3 class="font-bold text-slate-900 dark:text-slate-100 text-base leading-snug line-clamp-2 mb-2" title="${p.title}">
                        ${p.title}
                    </h3>

                    <!-- Department & Exam -->
                    <div class="text-xs text-slate-500 dark:text-slate-400 space-y-1 mb-4">
                        <div class="flex items-center gap-1.5 truncate">
                            <i class="bi bi-mortarboard text-slate-400"></i>
                            <span class="truncate font-medium text-slate-700 dark:text-slate-300">
                                ${p.parent_dept_name} ${p.is_minor ? `(${p.dept_name})` : ''}
                            </span>
                        </div>
                        <div class="flex items-center gap-1.5 truncate text-[11px] text-slate-400 dark:text-slate-500">
                            <i class="bi bi-calendar3"></i>
                            <span class="truncate">${p.exam_name}</span>
                        </div>
                    </div>
                </div>

                <!-- Action Buttons: Preview & Download -->
                <div class="pt-3 border-t border-slate-100 dark:border-slate-700/60 flex items-center justify-between gap-2">
                    <div class="flex items-center gap-1.5">
                        ${p.has_qp ? `
                            <button onclick="PDFViewer.open(${JSON.stringify(p).replace(/"/g, '&quot;')}, 'QP')" class="px-3 py-1.5 text-xs font-semibold rounded-lg bg-blue-600 hover:bg-blue-500 text-white shadow-xs flex items-center gap-1 transition">
                                <i class="bi bi-eye"></i> Preview QP
                            </button>
                            <a href="${p.qp_url}" target="_blank" download class="p-1.5 text-xs rounded-lg bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 transition" title="Download Question Paper">
                                <i class="bi bi-download"></i>
                            </a>
                        ` : '<span class="text-xs text-slate-400 italic">No QP</span>'}
                    </div>

                    <div class="flex items-center gap-1.5">
                        ${p.has_scheme ? `
                            <button onclick="PDFViewer.open(${JSON.stringify(p).replace(/"/g, '&quot;')}, 'SCHEME')" class="px-2.5 py-1.5 text-xs font-semibold rounded-lg bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 hover:bg-emerald-100 flex items-center gap-1 transition">
                                <i class="bi bi-journal-check"></i> Scheme
                            </button>
                            <a href="${p.scheme_url}" target="_blank" download class="p-1.5 text-xs rounded-lg bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 transition" title="Download Evaluation Scheme">
                                <i class="bi bi-download"></i>
                            </a>
                        ` : ''}
                    </div>
                </div>
            </div>
        `;
    },

    renderPaperTable(items) {
        return `
            <div class="bg-white dark:bg-slate-800 rounded-2xl shadow-xs border border-slate-200 dark:border-slate-700 overflow-x-auto">
                <table class="w-full text-left border-collapse text-xs sm:text-sm">
                    <thead>
                        <tr class="bg-slate-50 dark:bg-slate-700/50 border-b border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400 font-semibold">
                            <th class="py-3 px-4">Sem</th>
                            <th class="py-3 px-4">Course Code</th>
                            <th class="py-3 px-4">QP Code</th>
                            <th class="py-3 px-4">Course Title</th>
                            <th class="py-3 px-4">Department</th>
                            <th class="py-3 px-4">Type</th>
                            <th class="py-3 px-4 text-right">Actions</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-100 dark:divide-slate-700/60">
                        ${items.map(p => {
                            const isBookmarked = this.bookmarks.has(p.id);
                            return `
                                <tr class="hover:bg-slate-50 dark:hover:bg-slate-700/30 transition">
                                    <td class="py-3 px-4 font-bold text-slate-700 dark:text-slate-300">Sem ${p.semester}</td>
                                    <td class="py-3 px-4 font-mono font-bold text-blue-600 dark:text-blue-400">${p.course_code}</td>
                                    <td class="py-3 px-4 font-mono text-slate-500">${p.qp_code || '-'}</td>
                                    <td class="py-3 px-4 font-medium text-slate-900 dark:text-slate-100 max-w-xs truncate">${p.title}</td>
                                    <td class="py-3 px-4 text-slate-600 dark:text-slate-300">
                                        ${p.parent_dept_name} ${p.is_minor ? `<span class="text-[10px] bg-pink-100 text-pink-700 px-1.5 py-0.5 rounded font-semibold ml-1">${p.dept_code}</span>` : ''}
                                    </td>
                                    <td class="py-3 px-4">
                                        <span class="text-[11px] font-semibold px-2 py-0.5 rounded ${`badge-${(p.course_type || 'dsc').toLowerCase()}`}">${p.course_type}</span>
                                    </td>
                                    <td class="py-3 px-4 text-right">
                                        <div class="flex items-center justify-end gap-2">
                                            ${p.has_qp ? `
                                                <button onclick="PDFViewer.open(${JSON.stringify(p).replace(/"/g, '&quot;')}, 'QP')" class="px-2 py-1 text-xs font-semibold rounded bg-blue-600 text-white hover:bg-blue-500">
                                                    QP
                                                </button>
                                            ` : ''}
                                            ${p.has_scheme ? `
                                                <button onclick="PDFViewer.open(${JSON.stringify(p).replace(/"/g, '&quot;')}, 'SCHEME')" class="px-2 py-1 text-xs font-semibold rounded bg-emerald-600 text-white hover:bg-emerald-500">
                                                    Scheme
                                                </button>
                                            ` : ''}
                                            <button 
                                                data-bm-id="${p.id}"
                                                onclick="App.toggleBookmark('${p.id}')" 
                                                class="px-2 py-1 text-xs font-semibold rounded flex items-center gap-1 transition ${
                                                    isBookmarked 
                                                        ? 'bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300' 
                                                        : 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300'
                                                }"
                                            >
                                                <i class="bi ${isBookmarked ? 'bi-star-fill text-amber-500' : 'bi-star'}"></i>
                                                <span>${isBookmarked ? 'Saved' : 'Save'}</span>
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            `;
                        }).join('')}
                    </tbody>
                </table>
            </div>
        `;
    },

    renderPagination() {
        const container = document.getElementById('paginationControls');
        if (!container) return;

        const totalPages = Math.ceil(this.filteredPapers.length / this.state.pageSize);
        if (totalPages <= 1) {
            container.innerHTML = '';
            return;
        }

        const cur = this.state.currentPage;
        let html = `
            <div class="flex items-center justify-center gap-1 sm:gap-2">
                <button onclick="App.goToPage(${cur - 1})" ${cur === 1 ? 'disabled' : ''} class="px-3 py-1.5 text-xs font-medium rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-50 transition">
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
            html += `<button onclick="App.goToPage(1)" class="w-8 h-8 text-xs font-medium rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200">1</button>`;
            if (startPage > 2) html += `<span class="px-1 text-slate-400">...</span>`;
        }

        for (let p = startPage; p <= endPage; p++) {
            const isActive = p === cur;
            html += `
                <button onclick="App.goToPage(${p})" class="w-8 h-8 text-xs font-semibold rounded-lg ${isActive ? 'bg-blue-600 text-white shadow-xs' : 'bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50'} transition">
                    ${p}
                </button>
            `;
        }

        if (endPage < totalPages) {
            if (endPage < totalPages - 1) html += `<span class="px-1 text-slate-400">...</span>`;
            html += `<button onclick="App.goToPage(${totalPages})" class="w-8 h-8 text-xs font-medium rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200">${totalPages}</button>`;
        }

        html += `
                <button onclick="App.goToPage(${cur + 1})" ${cur === totalPages ? 'disabled' : ''} class="px-3 py-1.5 text-xs font-medium rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-50 transition">
                    Next <i class="bi bi-chevron-right"></i>
                </button>
            </div>
        `;

        container.innerHTML = html;
    },

    goToPage(page) {
        const totalPages = Math.ceil(this.filteredPapers.length / this.state.pageSize);
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

        // Populate filter dropdown in All Question Papers tab
        if (deptSelect) {
            deptSelect.innerHTML = `<option value="ALL">All Departments (${this.departments.length} Available)</option>` +
                this.departments.map(d => `<option value="${d.code}">${d.name} (${d.code})</option>`).join('');
        }

        // Apply quick department search query if entered
        let deptsToRender = this.departments;
        if (this.deptState.deptSearchQuery) {
            const dq = this.deptState.deptSearchQuery.toLowerCase();
            deptsToRender = this.departments.filter(d => 
                d.name.toLowerCase().includes(dq) || 
                d.code.toLowerCase().includes(dq) || 
                (d.description && d.description.toLowerCase().includes(dq)) ||
                (d.category && d.category.toLowerCase().includes(dq)) ||
                (d.minors && d.minors.some(m => m.name.toLowerCase().includes(dq) || m.code.toLowerCase().includes(dq)))
            );
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

        // Render Cards
        container.innerHTML = deptsToRender.map(d => {
            const deptCodes = new Set([d.code, ...(d.minors || []).map(m => m.code)]);
            const deptPapers = this.papers.filter(p => (deptCodes.has(p.parent_dept) || deptCodes.has(p.dept_code)) && p.has_files);
            const minors = d.minors || [];

            // Detect active semesters for this department
            const semCounts = {};
            deptPapers.forEach(p => {
                if (p.semester) semCounts[p.semester] = (semCounts[p.semester] || 0) + 1;
            });
            const activeSems = Object.keys(semCounts).sort((a,b) => a - b);

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
                        <p class="text-xs text-slate-500 dark:text-slate-400 line-clamp-2 mb-3">
                            ${d.description}
                        </p>
                    </div>

                    <div>
                        <!-- Semesters Badges -->
                        <div class="mb-3 pt-2 border-t border-slate-100 dark:border-slate-700/60 flex flex-wrap items-center gap-1">
                            <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400 mr-1">Semesters:</span>
                            ${activeSems.length > 0 ? activeSems.map(s => `
                                <span class="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300 border border-blue-100 dark:border-blue-900/40">
                                    Sem ${s}
                                </span>
                            `).join('') : '<span class="text-[10px] text-slate-400 italic">Upcoming</span>'}
                        </div>

                        ${minors.length > 0 ? `
                            <div class="mb-3 pt-2 border-t border-slate-100 dark:border-slate-700/60">
                                <div class="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1">Includes Minors:</div>
                                <div class="flex flex-wrap gap-1">
                                    ${minors.map(m => `
                                        <span class="text-[11px] font-medium px-2 py-0.5 rounded-full bg-pink-50 text-pink-700 dark:bg-pink-950/40 dark:text-pink-300 border border-pink-100 dark:border-pink-900/40" title="${m.name}">
                                            ${m.code} · ${m.name.split(' ')[0]}
                                        </span>
                                    `).join('')}
                                </div>
                            </div>
                        ` : ''}

                        <div class="flex items-center justify-between text-xs font-semibold text-blue-600 dark:text-blue-400 pt-2 border-t border-slate-100 dark:border-slate-700/60">
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

    openDepartmentView(deptCode, targetSem = null) {
        const dept = this.departments.find(d => d.code === deptCode);
        if (!dept) return;

        this.deptState.activeDept = dept;
        this.deptState.searchQuery = '';

        // Switch to detail view
        document.getElementById('deptListContainer')?.classList.add('hidden');
        const detailContainer = document.getElementById('deptDetailContainer');
        if (detailContainer) detailContainer.classList.remove('hidden');

        // Breadcrumbs
        const breadcrumbsEl = document.getElementById('deptBreadcrumbs');
        if (breadcrumbsEl) {
            breadcrumbsEl.innerHTML = `Departments <i class="bi bi-chevron-right text-[10px] mx-1"></i> <span class="text-slate-800 dark:text-slate-100 font-bold">${dept.name} (${dept.code})</span>`;
        }

        const deptCodes = new Set([dept.code, ...(dept.minors || []).map(m => m.code)]);
        const allDeptPapers = this.papers.filter(p => (deptCodes.has(p.parent_dept) || deptCodes.has(p.dept_code)) && p.has_files);
        const minors = dept.minors || [];

        // Header Banner
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
                            <p class="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1">
                                ${dept.description}
                            </p>
                            ${minors.length > 0 ? `
                                <div class="flex flex-wrap items-center gap-1.5 mt-2">
                                    <span class="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Minor Departments:</span>
                                    ${minors.map(m => `
                                        <span class="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-pink-50 dark:bg-pink-950/40 text-pink-700 dark:text-pink-300 border border-pink-200 dark:border-pink-900/40">
                                            ${m.code} - ${m.name}
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
            `;
        }

        // Reset in-department paper search input
        const deptPaperSearch = document.getElementById('deptPaperSearchInput');
        if (deptPaperSearch) deptPaperSearch.value = '';

        // Pick initial semester: if targetSem given, use it; else pick first semester with papers, or ALL
        let initialSem = targetSem;
        if (!initialSem) {
            for (let s = 1; s <= 8; s++) {
                const count = allDeptPapers.filter(p => p.semester === s).length;
                if (count > 0) {
                    initialSem = s;
                    break;
                }
            }
        }
        this.deptState.selectedSemester = initialSem || 'ALL';

        // Render Semester Tabs and Year-Wise Papers
        this.renderDeptSemesterTabs();
        this.renderDeptSemesterPapers();

        window.scrollTo({ top: 0, behavior: 'smooth' });
    },

    renderDeptSemesterTabs() {
        const tabsContainer = document.getElementById('deptSemesterTabs');
        if (!tabsContainer || !this.deptState.activeDept) return;

        const dept = this.deptState.activeDept;
        const deptCodes = new Set([dept.code, ...(dept.minors || []).map(m => m.code)]);
        const allDeptPapers = this.papers.filter(p => (deptCodes.has(p.parent_dept) || deptCodes.has(p.dept_code)) && p.has_files);

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
        this.deptState.selectedSemester = sem;
        this.renderDeptSemesterTabs();
        this.renderDeptSemesterPapers();
    },

    renderDeptSemesterPapers() {
        const container = document.getElementById('deptYearWisePapersContainer');
        const countBadge = document.getElementById('deptPaperCountBadge');
        if (!container || !this.deptState.activeDept) return;

        const dept = this.deptState.activeDept;
        const sem = this.deptState.selectedSemester;
        const deptCodes = new Set([dept.code, ...(dept.minors || []).map(m => m.code)]);

        // Filter papers for this department
        let semesterPapers = this.papers.filter(p => 
            (deptCodes.has(p.parent_dept) || deptCodes.has(p.dept_code)) && 
            p.has_files
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

        if (countBadge) {
            countBadge.textContent = `Showing ${semesterPapers.length} question papers`;
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
                    ${this.deptState.searchQuery ? `
                        <button onclick="App.clearDeptPaperSearch()" class="mt-4 px-3.5 py-1.5 bg-blue-600 text-white rounded-lg text-xs font-semibold shadow-xs">Clear Search</button>
                    ` : ''}
                </div>
            `;
            return;
        }

        // Group Year-Wise
        const byYear = {};
        semesterPapers.forEach(p => {
            const yrMatch = p.exam_name.match(/202\d/);
            const yr = yrMatch ? yrMatch[0] : '2025';
            byYear[yr] = byYear[yr] || [];
            byYear[yr].push(p);
        });

        const sortedYears = Object.keys(byYear).sort((a, b) => b.localeCompare(a));

        container.innerHTML = sortedYears.map(yr => {
            const yearPapers = byYear[yr];
            return `
                <div class="space-y-4">
                    <div class="flex items-center justify-between border-b border-slate-200 dark:border-slate-700 pb-2">
                        <div class="flex items-center gap-2">
                            <span class="w-2.5 h-2.5 rounded-full bg-blue-600"></span>
                            <h4 class="text-base sm:text-lg font-bold text-slate-900 dark:text-white">
                                ${yr} Examination Sessions
                            </h4>
                            <span class="text-xs font-semibold px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/50 text-blue-800 dark:text-blue-300">
                                ${yearPapers.length} Papers
                            </span>
                        </div>
                        <span class="text-xs text-slate-400 font-medium">
                            ${sem === 'ALL' ? 'All Semesters' : `Semester ${sem}`}
                        </span>
                    </div>

                    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                        ${yearPapers.map(p => this.renderPaperCard(p)).join('')}
                    </div>
                </div>
            `;
        }).join('');
    },

    backToDepartmentsList() {
        document.getElementById('deptDetailContainer')?.classList.add('hidden');
        document.getElementById('deptListContainer')?.classList.remove('hidden');
        window.scrollTo({ top: 0, behavior: 'smooth' });
    },

    // -------------------------------------------------------------
    // ADMIN AUTH & CONTROL MODAL
    // -------------------------------------------------------------

    openAdminModal() {
        const modal = document.getElementById('adminModal');
        if (!modal) return;
        modal.classList.remove('hidden');

        const isAuth = sessionStorage.getItem('mgu_admin_auth') === 'true';
        document.getElementById('adminLoginView')?.classList.toggle('hidden', isAuth);
        document.getElementById('adminControlsView')?.classList.toggle('hidden', !isAuth);
    },

    closeAdminModal() {
        document.getElementById('adminModal')?.classList.add('hidden');
    },

    handleAdminLogin(e) {
        if (e) e.preventDefault();
        const input = document.getElementById('adminPasskeyInput');
        const err = document.getElementById('adminLoginError');
        const val = input ? input.value.trim() : '';
        if (val === 'admin123' || val === 'mguadmin' || val === 'admin') {
            sessionStorage.setItem('mgu_admin_auth', 'true');
            if (err) err.classList.add('hidden');
            document.getElementById('adminLoginView')?.classList.add('hidden');
            document.getElementById('adminControlsView')?.classList.remove('hidden');
        } else {
            if (err) err.classList.remove('hidden');
        }
    },

    adminLogout() {
        sessionStorage.removeItem('mgu_admin_auth');
        document.getElementById('adminLoginView')?.classList.remove('hidden');
        document.getElementById('adminControlsView')?.classList.add('hidden');
        const input = document.getElementById('adminPasskeyInput');
        if (input) input.value = '';
    },

    async triggerSync() {
        const syncStatusEl = document.getElementById('syncStatusNotice');
        if (syncStatusEl) {
            syncStatusEl.className = 'mt-4 p-4 rounded-xl bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-900 text-blue-800 dark:text-blue-200 text-sm flex items-center gap-3';
            syncStatusEl.innerHTML = `<div class="animate-spin rounded-full h-4 w-4 border-2 border-blue-600 border-t-transparent"></div> Syncing FYUGP question papers with https://assist.mgu.ac.in/schema/...`;
            syncStatusEl.classList.remove('hidden');
        }

        try {
            const res = await fetch('/api/sync', { method: 'POST' });
            const data = await res.json();
            if (syncStatusEl) {
                syncStatusEl.className = 'mt-4 p-4 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-900 text-emerald-800 dark:text-emerald-200 text-sm flex items-center gap-3';
                syncStatusEl.innerHTML = `<i class="bi bi-check-circle-fill text-emerald-600"></i> ${data.message || 'Sync initiated successfully!'}`;
            }
        } catch (e) {
            if (syncStatusEl) {
                syncStatusEl.className = 'mt-4 p-4 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-900 text-amber-800 dark:text-amber-200 text-sm flex items-center gap-3';
                syncStatusEl.innerHTML = `<i class="bi bi-info-circle-fill text-amber-600"></i> Manual sync triggers background scraper. Scheduled sync runs daily automatically via GitHub Actions.`;
            }
        }
    }
};

window.App = App;

// Start on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    App.init();
});

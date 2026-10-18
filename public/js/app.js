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
    feedbackReports: [],
    inboxFilter: 'all',

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

        // Load reports & feedback
        await this.loadFeedbackReports();

        const isAuth = sessionStorage.getItem('mgu_admin_auth') === 'true';
        if (isAuth) {
            document.getElementById('adminNavBtn')?.classList.remove('hidden');
            document.getElementById('adminActiveBadge')?.classList.remove('hidden');
            const userDisplay = document.getElementById('adminUserDisplayName');
            if (userDisplay) {
                userDisplay.textContent = sessionStorage.getItem('mgu_admin_user') || 'sinan_cc';
            }
            this.populateAdminDeptDropdown();
        } else {
            document.getElementById('adminNavBtn')?.classList.add('hidden');
        }

        // Close feedback modal on Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeFeedbackModal();
            }
        });

        // Secret Admin URL triggers: #admin or ?admin
        const checkAdminHash = () => {
            const hasAdminHash = window.location.hash.toLowerCase() === '#admin';
            const hasAdminParam = new URLSearchParams(window.location.search).has('admin');
            if (hasAdminHash || hasAdminParam) {
                this.openAdminModal();
            }
        };
        checkAdminHash();
        window.addEventListener('hashchange', checkAdminHash);

        // Secret Keyboard Shortcut: Ctrl + Shift + A or Alt + A
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey && e.shiftKey && (e.key === 'A' || e.key === 'a')) || (e.altKey && (e.key === 'a' || e.key === 'A'))) {
                e.preventDefault();
                this.openAdminModal();
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

    getActiveDepartments() {
        return this.departments.filter(d => {
            const deptCodes = new Set([d.code, ...(d.minors || []).map(m => m.code)]);
            return this.papers.some(p => (deptCodes.has(p.parent_dept) || deptCodes.has(p.dept_code)) && p.has_files);
        });
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

    handleLiveSearch(query) {
        const dropdown = document.getElementById('deptSearchDropdown');
        const clearBtn = document.getElementById('clearDeptSearchBtn');
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
                                <button onclick="PDFViewer.open(${JSON.stringify(p).replace(/"/g, '&quot;')}, 'QP'); App.closeSearchDropdown();" class="px-2.5 py-1 text-xs font-semibold rounded-lg bg-blue-600 hover:bg-blue-500 text-white shadow-xs flex items-center gap-1 transition" title="Preview Question Paper">
                                    <i class="bi bi-eye"></i> QP
                                </button>
                            ` : ''}
                            ${p.has_scheme ? `
                                <button onclick="PDFViewer.open(${JSON.stringify(p).replace(/"/g, '&quot;')}, 'Scheme'); App.closeSearchDropdown();" class="px-2.5 py-1 text-xs font-semibold rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white shadow-xs flex items-center gap-1 transition" title="Preview Evaluation Scheme">
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

    groupPapersByCourse(paperList) {
        const groups = new Map();
        paperList.forEach(p => {
            const key = (p.course_code || p.title || 'UNKNOWN').trim().toUpperCase();
            if (!groups.has(key)) {
                groups.set(key, {
                    course_code: p.course_code,
                    title: p.title,
                    course_type: p.course_type,
                    semester: p.semester,
                    parent_dept_name: p.parent_dept_name,
                    dept_name: p.dept_name,
                    dept_code: p.dept_code,
                    is_minor: p.is_minor,
                    minor_name: p.minor_name,
                    papers: []
                });
            }
            groups.get(key).papers.push(p);
        });
        return Array.from(groups.values());
    },

    renderGroupedCourseCard(course) {
        const isAdmin = sessionStorage.getItem('mgu_admin_auth') === 'true';
        const ctypeClass = `badge-${(course.course_type || 'dsc').toLowerCase()}`;
        const firstPaper = course.papers[0];
        const isBookmarked = course.papers.some(p => this.bookmarks.has(p.id));

        return `
            <div class="paper-card bg-white dark:bg-slate-800 rounded-2xl p-5 flex flex-col justify-between shadow-xs border border-slate-200/80 dark:border-slate-700 hover:border-blue-400 dark:hover:border-blue-600 transition">
                <div>
                    <!-- Top Badge Bar -->
                    <div class="flex items-start justify-between gap-2 mb-3">
                        <div class="flex flex-wrap items-center gap-1.5">
                            ${isAdmin ? `
                                <span class="text-xs font-bold px-2.5 py-0.5 rounded-md bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200">
                                    Sem ${course.semester}
                                </span>
                            ` : ''}
                            <span class="text-xs font-semibold px-2 py-0.5 rounded-md ${ctypeClass}">
                                ${course.course_type}
                            </span>
                            ${course.is_minor ? `
                                <span class="text-xs font-semibold px-2 py-0.5 rounded-md badge-minor">
                                    ${course.minor_name || course.dept_code} (Minor)
                                </span>
                            ` : ''}
                        </div>

                        <!-- Bookmark Button -->
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

                    <!-- Course Code (NO QP Code on card) -->
                    <div class="flex items-center gap-2 mb-1.5">
                        <span class="font-mono font-bold text-sm text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/40 px-2 py-0.5 rounded border border-blue-100 dark:border-blue-900/40">
                            ${course.course_code || 'CODE N/A'}
                        </span>
                        <span class="text-[11px] font-semibold text-slate-400">
                            ${course.papers.length} ${course.papers.length === 1 ? 'Exam Paper' : 'Exam Papers'}
                        </span>
                    </div>

                    <!-- Course Title -->
                    <h3 class="font-bold text-slate-900 dark:text-slate-100 text-base leading-snug line-clamp-2 mb-3" title="${course.title}">
                        ${course.title}
                    </h3>
                </div>

                <!-- Grouped Question Papers for this course -->
                <div class="pt-3 border-t border-slate-100 dark:border-slate-700/60 space-y-2">
                    <div class="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1">
                        Question Papers:
                    </div>
                    ${course.papers.map(p => {
                        const monthYear = this.extractMonthYear(p.exam_name);
                        return `
                            <div class="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-700/40 border border-slate-200/70 dark:border-slate-600/50 flex items-center justify-between gap-2">
                                <div class="flex items-center gap-1.5 min-w-0">
                                    <i class="bi bi-calendar-event text-blue-600 dark:text-blue-400 text-xs"></i>
                                    <span class="text-xs font-semibold text-slate-800 dark:text-slate-200 truncate">
                                        ${monthYear}
                                    </span>
                                </div>

                                <div class="flex items-center gap-1.5 shrink-0">
                                    ${p.has_qp ? `
                                        <button onclick="PDFViewer.open(${JSON.stringify(p).replace(/"/g, '&quot;')}, 'QP')" class="px-2.5 py-1 text-xs font-semibold rounded-lg bg-blue-600 hover:bg-blue-500 text-white shadow-xs flex items-center gap-1 transition" title="Preview Question Paper">
                                            <i class="bi bi-eye"></i> QP
                                        </button>
                                        <a href="${p.qp_url}" target="_blank" download class="p-1 text-xs rounded-lg bg-slate-200/80 dark:bg-slate-600 hover:bg-slate-300 dark:hover:bg-slate-500 text-slate-700 dark:text-slate-200 transition" title="Download Question Paper">
                                            <i class="bi bi-download"></i>
                                        </a>
                                    ` : ''}

                                    ${p.has_scheme ? `
                                        <button onclick="PDFViewer.open(${JSON.stringify(p).replace(/"/g, '&quot;')}, 'SCHEME')" class="px-2 py-1 text-xs font-semibold rounded-lg bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 hover:bg-emerald-100 flex items-center gap-1 transition" title="Preview Scheme">
                                            <i class="bi bi-journal-check"></i> Scheme
                                        </button>
                                        <a href="${p.scheme_url}" target="_blank" download class="p-1 text-xs rounded-lg bg-slate-200/80 dark:bg-slate-600 hover:bg-slate-300 dark:hover:bg-slate-500 text-slate-700 dark:text-slate-200 transition" title="Download Evaluation Scheme">
                                            <i class="bi bi-download"></i>
                                        </a>
                                    ` : ''}

                                    ${isAdmin ? `
                                        <button onclick="App.handleDeletePaper('${p.id}')" title="Delete Paper (Admin)" class="p-1 text-xs rounded-lg bg-rose-50 hover:bg-rose-100 dark:bg-rose-950/60 text-rose-600 dark:text-rose-300 border border-rose-200 dark:border-rose-800 transition">
                                            <i class="bi bi-trash3 text-rose-500"></i>
                                        </button>
                                    ` : ''}
                                </div>
                            </div>
                        `;
                    }).join('')}
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

                        <!-- Right Actions: Admin Delete + Save -->
                        <div class="flex items-center gap-1.5">
                            ${isAdmin ? `
                                <button 
                                    onclick="App.handleDeletePaper('${p.id}')" 
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
        const isAdmin = sessionStorage.getItem('mgu_admin_auth') === 'true';

        return `
            <div class="bg-white dark:bg-slate-800 rounded-2xl shadow-xs border border-slate-200 dark:border-slate-700 overflow-x-auto">
                <table class="w-full text-left border-collapse text-xs sm:text-sm">
                    <thead>
                        <tr class="bg-slate-50 dark:bg-slate-700/50 border-b border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400 font-semibold">
                            ${isAdmin ? '<th class="py-3 px-4">Sem</th>' : ''}
                            <th class="py-3 px-4">Course Code</th>
                            <th class="py-3 px-4">Exam Session</th>
                            <th class="py-3 px-4">Course Title</th>
                            <th class="py-3 px-4">Department</th>
                            <th class="py-3 px-4">Type</th>
                            <th class="py-3 px-4 text-right">Actions</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-100 dark:divide-slate-700/60">
                        ${items.map(p => {
                            const isBookmarked = this.bookmarks.has(p.id);
                            const monthYear = this.extractMonthYear(p.exam_name);
                            return `
                                <tr class="hover:bg-slate-50 dark:hover:bg-slate-700/30 transition">
                                    ${isAdmin ? `<td class="py-3 px-4 font-bold text-slate-700 dark:text-slate-300">Sem ${p.semester}</td>` : ''}
                                    <td class="py-3 px-4 font-mono font-bold text-blue-600 dark:text-blue-400">${p.course_code}</td>
                                    <td class="py-3 px-4 font-medium text-slate-600 dark:text-slate-300 whitespace-nowrap">${monthYear}</td>
                                    <td class="py-3 px-4 font-medium text-slate-900 dark:text-slate-100 max-w-xs truncate">${p.title}</td>
                                    <td class="py-3 px-4 text-slate-600 dark:text-slate-300">
                                        ${p.parent_dept_name} ${p.is_minor ? `<span class="text-[10px] bg-pink-100 text-pink-700 px-1.5 py-0.5 rounded font-semibold ml-1">${p.minor_name || p.dept_code}</span>` : ''}
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
                                            ${isAdmin ? `
                                                <button onclick="App.handleDeletePaper('${p.id}')" title="Delete Paper (Admin)" class="px-2 py-1 text-xs font-semibold rounded bg-rose-100 text-rose-700 hover:bg-rose-200 dark:bg-rose-950 dark:text-rose-300">
                                                    <i class="bi bi-trash3"></i>
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
                const deptCodes = new Set([d.code, ...(d.minors || []).map(m => m.code)]);
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

                        <!-- Minors (Full Names) -->
                        ${minors.length > 0 ? `
                            <div class="mb-3 pt-2 border-t border-slate-100 dark:border-slate-700/60">
                                <div class="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">Minors:</div>
                                <div class="flex flex-wrap gap-1.5">
                                    ${minors.map(m => `
                                        <span class="text-xs font-semibold px-2.5 py-1 rounded-lg bg-pink-50 text-pink-700 dark:bg-pink-950/40 dark:text-pink-300 border border-pink-100 dark:border-pink-900/40 shadow-2xs" title="${m.name} (${m.code})">
                                            ${m.name} (${m.code})
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
        const isAdmin = sessionStorage.getItem('mgu_admin_auth') === 'true';

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

        // Partition into Major/Core Papers vs Minor Papers
        const majorPapers = semesterPapers.filter(p => !p.is_minor);
        const minorPapers = semesterPapers.filter(p => p.is_minor);

        let sectionsHtml = '';

        // 1. Major & Core Programmes Section (Grouped by course)
        if (majorPapers.length > 0) {
            const groupedMajor = this.groupPapersByCourse(majorPapers);
            sectionsHtml += `
                <div class="space-y-4">
                    <div class="flex items-center justify-between border-b border-slate-200 dark:border-slate-700 pb-2">
                        <div class="flex items-center gap-2">
                            <span class="w-2.5 h-2.5 rounded-full bg-blue-600"></span>
                            <h4 class="text-base sm:text-lg font-bold text-slate-900 dark:text-white">
                                Major & Core Programmes
                            </h4>
                            <span class="text-xs font-semibold px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/50 text-blue-800 dark:text-blue-300">
                                ${groupedMajor.length} Courses (${majorPapers.length} Papers)
                            </span>
                        </div>
                        <span class="text-xs text-slate-400 font-medium">
                            ${isAdmin ? (sem === 'ALL' ? 'All Semesters' : `Semester ${sem}`) : ''}
                        </span>
                    </div>

                    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                        ${groupedMajor.map(course => this.renderGroupedCourseCard(course)).join('')}
                    </div>
                </div>
            `;
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

                        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
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

        if (isAuth) {
            const userDisplay = document.getElementById('adminUserDisplayName');
            if (userDisplay) {
                userDisplay.textContent = sessionStorage.getItem('mgu_admin_user') || 'sinan_cc';
            }
            this.populateAdminDeptDropdown();
            this.switchAdminTab('upload');
            document.getElementById('adminNavBtn')?.classList.remove('hidden');
            document.getElementById('adminActiveBadge')?.classList.remove('hidden');
        } else {
            setTimeout(() => {
                document.getElementById('adminUsernameInput')?.focus();
            }, 100);
        }
    },

    closeAdminModal() {
        document.getElementById('adminModal')?.classList.add('hidden');
        if (window.location.hash.toLowerCase() === '#admin') {
            history.replaceState(null, '', window.location.pathname + window.location.search);
        }
    },

    handleAdminLogin(e) {
        if (e) e.preventDefault();
        const userInput = document.getElementById('adminUsernameInput');
        const passInput = document.getElementById('adminPasswordInput');
        const err = document.getElementById('adminLoginError');

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
            this.renderPapers();
            if (this.deptState.activeDept) {
                this.renderDeptSemesterPapers();
            }
        } else {
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
        this.closeAdminModal();
    },

    switchAdminTab(tab) {
        const uploadView = document.getElementById('adminTabUploadView');
        const deleteView = document.getElementById('adminTabDeleteView');
        const syncView = document.getElementById('adminTabSyncView');
        const inboxView = document.getElementById('adminTabInboxView');
        const btnUpload = document.getElementById('adminTabBtnUpload');
        const btnDelete = document.getElementById('adminTabBtnDelete');
        const btnSync = document.getElementById('adminTabBtnSync');
        const btnInbox = document.getElementById('adminTabBtnInbox');

        const activeClass = 'px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-blue-600 text-white shadow-xs flex items-center gap-1.5 transition shrink-0';
        const inactiveClass = 'px-3.5 py-1.5 text-xs font-medium rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 flex items-center gap-1.5 transition shrink-0';

        if (uploadView) uploadView.classList.toggle('hidden', tab !== 'upload');
        if (deleteView) deleteView.classList.toggle('hidden', tab !== 'delete');
        if (syncView) syncView.classList.toggle('hidden', tab !== 'sync');
        if (inboxView) inboxView.classList.toggle('hidden', tab !== 'inbox');

        if (btnUpload) btnUpload.className = tab === 'upload' ? activeClass : inactiveClass;
        if (btnDelete) btnDelete.className = tab === 'delete' ? activeClass : inactiveClass;
        if (btnSync) btnSync.className = tab === 'sync' ? activeClass : inactiveClass;
        if (btnInbox) btnInbox.className = tab === 'inbox' ? activeClass : inactiveClass;

        if (tab === 'delete') {
            this.renderAdminDeleteList();
        } else if (tab === 'inbox') {
            this.renderAdminInbox();
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

    async handleAdminUploadSubmit(e) {
        if (e) e.preventDefault();

        const statusEl = document.getElementById('adminUploadStatus');
        const submitBtn = document.getElementById('adminUploadSubmitBtn');
        if (statusEl) {
            statusEl.className = 'p-3 rounded-lg text-xs bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-900 flex items-center gap-2';
            statusEl.innerHTML = '<div class="animate-spin rounded-full h-3.5 w-3.5 border-2 border-blue-600 border-t-transparent"></div> Processing and uploading question paper...';
            statusEl.classList.remove('hidden');
        }
        if (submitBtn) submitBtn.disabled = true;

        try {
            const courseCode = document.getElementById('adminUploadCourseCode').value.trim().toUpperCase();
            const title = document.getElementById('adminUploadTitle').value.trim();
            const deptCode = document.getElementById('adminUploadDept').value.trim().toUpperCase();
            const semester = parseInt(document.getElementById('adminUploadSemester').value, 10);
            const courseType = document.getElementById('adminUploadCourseType').value.trim().toUpperCase();
            const isMinor = document.getElementById('adminUploadIsMinor').checked;
            const minorName = document.getElementById('adminUploadMinorName')?.value.trim() || '';
            const minorCode = document.getElementById('adminUploadMinorCode')?.value.trim().toUpperCase() || '';
            const qpCode = document.getElementById('adminUploadQpCode').value.trim();
            const examName = document.getElementById('adminUploadExamName').value.trim();
            const qpFile = document.getElementById('adminUploadQpFile')?.files[0];
            const qpUrl = document.getElementById('adminUploadQpUrl')?.value.trim();
            const schemeFile = document.getElementById('adminUploadSchemeFile')?.files[0];
            const schemeUrl = document.getElementById('adminUploadSchemeUrl')?.value.trim();

            const deptObj = this.departments.find(d => d.code === deptCode);
            const deptName = deptObj ? deptObj.name : deptCode;

            const toB64 = (file) => new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = () => resolve(reader.result);
                reader.onerror = reject;
                reader.readAsDataURL(file);
            });

            let qpFileB64 = '';
            if (qpFile) qpFileB64 = await toB64(qpFile);

            let schemeFileB64 = '';
            if (schemeFile) schemeFileB64 = await toB64(schemeFile);

            const payload = {
                course_code: courseCode,
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
                qp_url: qpUrl,
                scheme_url: schemeUrl,
                qp_file_b64: qpFileB64,
                scheme_file_b64: schemeFileB64
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
                const files = [];
                if (qpUrl || qpFileB64) files.push({ type: "QP", label: "QUESTION PAPER", url: qpUrl || "#" });
                if (schemeUrl || schemeFileB64) files.push({ type: "SCHEME", label: "SCHEME", url: schemeUrl || "#" });

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
                    has_qp: Boolean(qpUrl || qpFileB64),
                    qp_url: qpUrl || "#",
                    has_scheme: Boolean(schemeUrl || schemeFileB64),
                    scheme_url: schemeUrl || "#",
                    files: files,
                    has_files: files.length > 0
                };
                data = { success: true, paper: customPaper };
            }

            if (data.success && data.paper) {
                this.papers.unshift(data.paper);
                this.applyFilters();
                this.renderDepartmentsList();
                if (this.deptState.activeDept) {
                    this.renderDeptSemesterTabs();
                    this.renderDeptSemesterPapers();
                }
                this.updateStatsUI();

                if (statusEl) {
                    statusEl.className = 'p-3 rounded-lg text-xs bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 flex items-center gap-2';
                    statusEl.innerHTML = `<i class="bi bi-check-circle-fill text-emerald-600"></i> Paper "${courseCode} - ${title}" published successfully!`;
                }

                document.getElementById('adminUploadCourseCode').value = '';
                document.getElementById('adminUploadTitle').value = '';
                document.getElementById('adminUploadQpCode').value = '';
                if (document.getElementById('adminUploadQpFile')) document.getElementById('adminUploadQpFile').value = '';
                if (document.getElementById('adminUploadQpUrl')) document.getElementById('adminUploadQpUrl').value = '';
                if (document.getElementById('adminUploadSchemeFile')) document.getElementById('adminUploadSchemeFile').value = '';
                if (document.getElementById('adminUploadSchemeUrl')) document.getElementById('adminUploadSchemeUrl').value = '';
            } else {
                throw new Error(data.error || 'Server rejected paper upload');
            }
        } catch (err) {
            if (statusEl) {
                statusEl.className = 'p-3 rounded-lg text-xs bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800';
                statusEl.innerHTML = `<i class="bi bi-exclamation-triangle-fill text-rose-600"></i> Error: ${err.message}`;
            }
        } finally {
            if (submitBtn) submitBtn.disabled = false;
        }
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
                        <button onclick="PDFViewer.open(${JSON.stringify(p).replace(/"/g, '&quot;')}, 'QP')" class="px-2 py-1 text-[11px] font-semibold rounded bg-slate-100 hover:bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-200" title="Preview Paper">
                            <i class="bi bi-eye"></i>
                        </button>
                    ` : ''}
                    <button onclick="App.handleDeletePaper('${p.id}')" class="px-2.5 py-1 text-xs font-semibold rounded-lg bg-rose-50 hover:bg-rose-100 dark:bg-rose-950/50 text-rose-600 dark:text-rose-300 border border-rose-200 dark:border-rose-800 transition flex items-center gap-1" title="Delete Paper Permanently">
                        <i class="bi bi-trash3"></i> Delete
                    </button>
                </div>
            </div>
        `).join('');
    },

    async handleDeletePaper(paperId) {
        const paper = this.papers.find(p => p.id === paperId);
        const title = paper ? `${paper.course_code} - ${paper.title}` : `Paper ID ${paperId}`;
        if (!confirm(`Are you sure you want to delete "${title}" permanently?`)) {
            return;
        }

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
            alert(`Paper removed from session.`);
        }
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

    openFeedbackModal(initialTab = 'report', deptCode = '', sem = '', courseCode = '', courseTitle = '') {
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
            localStorage.setItem('mgu_feedback_reports', JSON.stringify(this.feedbackReports));
        } catch (e) {}
        try {
            await fetch('/api/feedback', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(report)
            });
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

        const submitBtn = document.getElementById('reportSubmitBtn');
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = `<div class="animate-spin rounded-full h-3.5 w-3.5 border-2 border-white border-t-transparent"></div> Submitting...`;
        }

        const report = {
            id: 'rep_' + Date.now() + '_' + Math.random().toString(36).substr(2, 6),
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
            contact
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

        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = `<i class="bi bi-send-fill"></i> Submit Missing Paper Report`;
        }

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

        const submitBtn = document.getElementById('feedbackSubmitBtn');
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = `<div class="animate-spin rounded-full h-3.5 w-3.5 border-2 border-white border-t-transparent"></div> Sending...`;
        }

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

        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = `<i class="bi bi-send-fill"></i> Send Feedback`;
        }

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
                                    <a href="${escapeHtml(r.driveLink)}" target="_blank" rel="noopener noreferrer" class="text-blue-600 dark:text-blue-400 hover:underline font-medium text-[11px] inline-flex items-center gap-1 bg-blue-50 dark:bg-blue-950/50 px-2 py-0.5 rounded border border-blue-200 dark:border-blue-900/60">
                                        <i class="bi bi-box-arrow-up-right"></i> Open Attached Drive/PDF Link
                                    </a>
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
    }
};

window.App = App;

// Start on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    App.init();
});

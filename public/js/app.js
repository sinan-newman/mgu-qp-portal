/**
 * Main Application Logic for MGU Question Papers Portal
 */

const App = {
    // Data stores
    papers: [],
    departments: [],
    modelCourses: [],
    modelPapers: [],
    stats: {},
    bookmarks: new Set(),

    // State
    state: {
        activeTab: 'papers', // 'papers' | 'departments' | 'bookmarks'
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
        if (this.state.activeTab === 'bookmarks') {
            this.renderPapers();
        } else {
            // Update button UI on card
            const btn = document.getElementById(`bm-btn-${paperId}`);
            if (btn) {
                const isBookmarked = this.bookmarks.has(paperId);
                btn.innerHTML = `<i class="bi ${isBookmarked ? 'bi-star-fill text-amber-500' : 'bi-star text-slate-400'}"></i>`;
            }
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

        // Robust fetch: try API endpoint on local backend, direct static data/ file on static hosts (e.g. GitHub Pages)
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

        const [papersData, deptsData, coursesData, modelPapersData, statsData] = await Promise.all([
            fetchResource('/api/papers?limit=10000&has_files=false', 'data/papers.json'),
            fetchResource('/api/departments', 'data/departments.json'),
            fetchResource('/api/model-courses', 'data/model_courses.json'),
            fetchResource('/api/model-papers', 'data/model_papers.json'),
            fetchResource('/api/stats', 'data/stats.json')
        ]);

        this.papers = (papersData && papersData.papers) ? papersData.papers : (Array.isArray(papersData) ? papersData : []);
        this.departments = deptsData || [];
        this.modelCourses = coursesData || [];
        this.modelPapers = modelPapersData || [];
        this.stats = statsData || {};
    },

    updateStatsUI() {
        const totalPapersEl = document.getElementById('statTotalPapers');
        const totalSchemesEl = document.getElementById('statTotalSchemes');
        const totalDeptsEl = document.getElementById('statTotalDepartments');
        const lastSyncEl = document.getElementById('statLastSync');

        const totalQPs = this.papers.filter(p => p.has_qp).length;
        const totalSchemes = this.papers.filter(p => p.has_scheme).length;

        if (totalPapersEl) totalPapersEl.textContent = totalQPs.toLocaleString();
        if (totalSchemesEl) totalSchemesEl.textContent = totalSchemes.toLocaleString();
        if (totalDeptsEl) totalDeptsEl.textContent = `${this.departments.length || 23}+`;
        if (lastSyncEl) lastSyncEl.textContent = 'Auto-Sync Active';
    },

    bindEvents() {
        // Search Input
        const searchInput = document.getElementById('searchInput');
        const clearSearchBtn = document.getElementById('clearSearchBtn');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.state.searchQuery = e.target.value.trim().toLowerCase();
                this.state.currentPage = 1;
                clearSearchBtn.classList.toggle('hidden', !this.state.searchQuery);
                this.applyFilters();
            });

            // Focus on '/' key
            document.addEventListener('keydown', (e) => {
                if (e.key === '/' && document.activeElement !== searchInput) {
                    e.preventDefault();
                    searchInput.focus();
                }
            });
        }

        if (clearSearchBtn) {
            clearSearchBtn.addEventListener('click', () => {
                searchInput.value = '';
                this.state.searchQuery = '';
                clearSearchBtn.classList.add('hidden');
                this.state.currentPage = 1;
                this.applyFilters();
            });
        }

        // Semester Buttons
        document.querySelectorAll('.sem-filter-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const sem = btn.dataset.sem;
                this.setSemester(sem);
            });
        });

        // Course Type Buttons
        document.querySelectorAll('.ctype-filter-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const ctype = btn.dataset.ctype;
                this.setCourseType(ctype);
            });
        });

        // Department Select Dropdown
        const deptSelect = document.getElementById('deptSelect');
        if (deptSelect) {
            deptSelect.addEventListener('change', (e) => {
                this.setDepartment(e.target.value);
            });
        }

        // Navigation Tabs
        document.querySelectorAll('.nav-tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.switchTab(btn.dataset.tab);
            });
        });

        // Files only toggle
        const filesOnlyCheckbox = document.getElementById('filesOnlyCheckbox');
        if (filesOnlyCheckbox) {
            filesOnlyCheckbox.addEventListener('change', (e) => {
                this.state.onlyWithFiles = e.target.checked;
                this.state.currentPage = 1;
                this.applyFilters();
            });
        }

        // View Mode Toggles
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

        // Theme Toggle Button
        const themeBtn = document.getElementById('themeToggleBtn');
        if (themeBtn) {
            themeBtn.addEventListener('click', () => this.toggleTheme());
        }

        // Sync Portal Button
        const syncBtn = document.getElementById('triggerSyncBtn');
        if (syncBtn) {
            syncBtn.addEventListener('click', () => this.triggerSync());
        }
    },

    switchTab(tab) {
        this.state.activeTab = tab;

        // Update nav button active classes
        document.querySelectorAll('.nav-tab-btn').forEach(btn => {
            const isActive = btn.dataset.tab === tab;
            if (isActive) {
                btn.className = 'nav-tab-btn px-4 py-2 font-semibold text-sm rounded-lg bg-blue-600 text-white shadow-sm flex items-center gap-2 transition';
            } else {
                btn.className = 'nav-tab-btn px-4 py-2 font-medium text-sm rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center gap-2 transition';
            }
        });

        // Hide/Show containers
        const containers = {
            'papers': document.getElementById('papersSection'),
            'departments': document.getElementById('departmentsSection'),
            'bookmarks': document.getElementById('papersSection') // Bookmarks reuses papers section
        };

        Object.keys(containers).forEach(k => {
            if (containers[k]) {
                if (k === tab || (tab === 'bookmarks' && k === 'papers')) {
                    containers[k].classList.remove('hidden');
                } else {
                    containers[k].classList.add('hidden');
                }
            }
        });

        // Filter Controls visibility (only relevant on papers or bookmarks)
        const filterControls = document.getElementById('filterControlsSection');
        if (filterControls) {
            if (tab === 'papers' || tab === 'bookmarks') {
                filterControls.classList.remove('hidden');
            } else {
                filterControls.classList.add('hidden');
            }
        }

        if (tab === 'papers' || tab === 'bookmarks') {
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

        // Sync dropdown value
        const deptSelect = document.getElementById('deptSelect');
        if (deptSelect && deptSelect.value !== deptCode) {
            deptSelect.value = deptCode;
        }

        // Highlight active dept card in departments tab
        document.querySelectorAll('.dept-card').forEach(card => {
            card.classList.toggle('ring-2', card.dataset.code === deptCode);
            card.classList.toggle('ring-blue-600', card.dataset.code === deptCode);
        });

        this.applyFilters();
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

        // Search Query
        if (this.state.searchQuery) {
            const q = this.state.searchQuery;
            results = results.filter(p => {
                const text = `${p.course_code} ${p.qp_code} ${p.title} ${p.raw_header} ${p.dept_name} ${p.parent_dept_name} ${p.course_type_name}`.toLowerCase();
                return text.includes(q);
            });
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
            countEl.textContent = `Showing ${total.toLocaleString()} question papers & schemes`;
        }

        if (total === 0) {
            container.innerHTML = `
                <div class="col-span-full py-16 text-center bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-8">
                    <div class="w-16 h-16 rounded-full bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 mx-auto flex items-center justify-center text-2xl mb-4">
                        <i class="bi bi-search"></i>
                    </div>
                    <h3 class="text-lg font-bold text-slate-800 dark:text-slate-100">No question papers match your filters</h3>
                    <p class="text-sm text-slate-500 dark:text-slate-400 mt-1 max-w-md mx-auto">
                        Try searching by course code (e.g. <code class="text-blue-600 font-mono">MG3DSEMAT202</code>), QP code, or clear the department filter.
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
        const ctypeClass = `badge-${p.course_type.toLowerCase()}`;

        return `
            <div class="paper-card bg-white dark:bg-slate-800 rounded-2xl p-5 flex flex-col justify-between shadow-xs">
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

                        <!-- Bookmark Button -->
                        <button id="bm-btn-${p.id}" onclick="App.toggleBookmark('${p.id}')" title="Save / Bookmark" class="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-400 transition">
                            <i class="bi ${isBookmarked ? 'bi-star-fill text-amber-500' : 'bi-star'}"></i>
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

                <!-- Action Buttons -->
                <div class="pt-3 border-t border-slate-100 dark:border-slate-700/60 flex items-center justify-between gap-2">
                    <div class="flex items-center gap-1.5">
                        ${p.has_qp ? `
                            <button onclick="PDFViewer.open(${JSON.stringify(p).replace(/"/g, '&quot;')}, 'QP')" class="px-3 py-1.5 text-xs font-semibold rounded-lg bg-blue-600 hover:bg-blue-500 text-white shadow-xs flex items-center gap-1 transition">
                                <i class="bi bi-eye"></i> QP
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
                            <a href="${p.scheme_url}" target="_blank" download class="p-1.5 text-xs rounded-lg bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 transition" title="Download Scheme">
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
                        ${items.map(p => `
                            <tr class="hover:bg-slate-50 dark:hover:bg-slate-700/30 transition">
                                <td class="py-3 px-4 font-bold text-slate-700 dark:text-slate-300">Sem ${p.semester}</td>
                                <td class="py-3 px-4 font-mono font-bold text-blue-600 dark:text-blue-400">${p.course_code}</td>
                                <td class="py-3 px-4 font-mono text-slate-500">${p.qp_code || '-'}</td>
                                <td class="py-3 px-4 font-medium text-slate-900 dark:text-slate-100 max-w-xs truncate">${p.title}</td>
                                <td class="py-3 px-4 text-slate-600 dark:text-slate-300">
                                    ${p.parent_dept_name} ${p.is_minor ? `<span class="text-[10px] bg-pink-100 text-pink-700 px-1.5 py-0.5 rounded font-semibold ml-1">${p.dept_code}</span>` : ''}
                                </td>
                                <td class="py-3 px-4">
                                    <span class="text-[11px] font-semibold px-2 py-0.5 rounded ${`badge-${p.course_type.toLowerCase()}`}">${p.course_type}</span>
                                </td>
                                <td class="py-3 px-4 text-right">
                                    <div class="flex items-center justify-end gap-1.5">
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
                                        <button onclick="App.toggleBookmark('${p.id}')" class="p-1 text-slate-400 hover:text-amber-500">
                                            <i class="bi ${this.bookmarks.has(p.id) ? 'bi-star-fill text-amber-500' : 'bi-star'}"></i>
                                        </button>
                                    </div>
                                </td>
                            </tr>
                        `).join('')}
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

        // Page buttons window
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
        window.scrollTo({ top: document.getElementById('papersGrid').offsetTop - 120, behavior: 'smooth' });
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

    renderDepartmentsList() {
        const container = document.getElementById('deptCardsGrid');
        const deptSelect = document.getElementById('deptSelect');
        if (!container) return;

        // Populate dropdown
        if (deptSelect) {
            deptSelect.innerHTML = `<option value="ALL">All Departments (100% Archive)</option>` +
                this.departments.map(d => `<option value="${d.code}">${d.name} (${d.code})</option>`).join('');
        }

        // Populate visual cards
        container.innerHTML = this.departments.map(d => {
            const paperCount = this.papers.filter(p => p.parent_dept === d.code || p.dept_code === d.code).length;
            const minors = d.minors || [];

            return `
                <div onclick="App.selectDeptAndBrowse('${d.code}')" data-code="${d.code}" class="dept-card bg-white dark:bg-slate-800 p-5 rounded-2xl border border-slate-200 dark:border-slate-700 hover:border-blue-400 dark:hover:border-blue-600 shadow-xs cursor-pointer transition flex flex-col justify-between">
                    <div>
                        <div class="flex items-center justify-between gap-2 mb-3">
                            <div class="w-10 h-10 rounded-xl bg-blue-50 dark:bg-blue-900/40 text-blue-600 dark:text-blue-300 flex items-center justify-center text-lg">
                                <i class="bi ${d.icon || 'bi-mortarboard'}"></i>
                            </div>
                            <span class="text-xs font-bold px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 font-mono">
                                ${d.code}
                            </span>
                        </div>
                        <h4 class="font-bold text-slate-900 dark:text-slate-100 text-base mb-1">
                            ${d.name}
                        </h4>
                        <p class="text-xs text-slate-500 dark:text-slate-400 line-clamp-2 mb-3">
                            ${d.description}
                        </p>
                    </div>

                    <div>
                        ${minors.length > 0 ? `
                            <div class="mb-3 pt-2 border-t border-slate-100 dark:border-slate-700/60">
                                <div class="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1">Minor Departments:</div>
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
                            <span>${paperCount} Papers Available</span>
                            <i class="bi bi-arrow-right"></i>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    },

    selectDeptAndBrowse(deptCode) {
        this.setDepartment(deptCode);
        this.switchTab('papers');
    },

    renderModelCourses() {
        const container = document.getElementById('modelCoursesTableBody');
        const countEl = document.getElementById('modelCoursesCount');
        if (!container) return;

        if (countEl) countEl.textContent = `${this.modelCourses.length} Courses Uploaded`;

        container.innerHTML = this.modelCourses.map((c, idx) => `
            <tr class="hover:bg-slate-50 dark:hover:bg-slate-700/30 transition text-xs sm:text-sm">
                <td class="py-3 px-4 font-bold text-slate-500 font-mono">${idx + 1}</td>
                <td class="py-3 px-4 font-mono font-bold text-blue-600 dark:text-blue-400">
                    ${c.course_code}
                </td>
                <td class="py-3 px-4 font-semibold text-slate-900 dark:text-slate-100">
                    ${c.title}
                </td>
                <td class="py-3 px-4">
                    <span class="text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200">
                        Sem ${c.semester}
                    </span>
                </td>
                <td class="py-3 px-4">
                    <span class="text-xs font-semibold px-2 py-0.5 rounded ${`badge-${c.course_type.toLowerCase()}`}">
                        ${c.course_type}
                    </span>
                </td>
                <td class="py-3 px-4 text-slate-600 dark:text-slate-300">
                    ${c.parent_dept_name}
                    ${c.is_minor ? `<span class="ml-1 text-[10px] font-bold px-1.5 py-0.5 rounded bg-pink-100 text-pink-700 dark:bg-pink-900 dark:text-pink-200">${c.dept_code} Minor</span>` : ''}
                </td>
                <td class="py-3 px-4 text-right">
                    <button onclick="App.searchCourseInArchive('${c.course_code}')" class="px-2.5 py-1 text-xs font-semibold rounded-lg bg-blue-50 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 hover:bg-blue-100 transition flex items-center gap-1 ml-auto">
                        <i class="bi bi-search"></i> Find Papers
                    </button>
                </td>
            </tr>
        `).join('');
    },

    searchCourseInArchive(courseCode) {
        const searchInput = document.getElementById('searchInput');
        if (searchInput) searchInput.value = courseCode;
        this.state.searchQuery = courseCode.toLowerCase();
        this.state.selectedDept = 'ALL';
        this.state.selectedSemester = 'ALL';
        this.state.selectedCourseType = 'ALL';
        this.switchTab('papers');
        this.applyFilters();
    },

    async triggerSync() {
        const syncStatusEl = document.getElementById('syncStatusNotice');
        if (syncStatusEl) {
            syncStatusEl.className = 'mt-4 p-4 rounded-xl bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-900 text-blue-800 dark:text-blue-200 text-sm flex items-center gap-3';
            syncStatusEl.innerHTML = `<div class="animate-spin rounded-full h-4 w-4 border-2 border-blue-600 border-t-transparent"></div> Syncing with https://assist.mgu.ac.in/schema/...`;
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

    openAdminModal() {
        const modal = document.getElementById('adminModal');
        if (modal) modal.classList.remove('hidden');
        const isAuth = sessionStorage.getItem('mgu_admin_auth') === 'true';
        const loginView = document.getElementById('adminLoginView');
        const controlsView = document.getElementById('adminControlsView');
        if (loginView && controlsView) {
            loginView.classList.toggle('hidden', isAuth);
            controlsView.classList.toggle('hidden', !isAuth);
        }
        document.body.classList.add('overflow-hidden');
    },

    closeAdminModal() {
        const modal = document.getElementById('adminModal');
        if (modal) modal.classList.add('hidden');
        document.body.classList.remove('overflow-hidden');
        if (window.location.hash === '#admin') {
            history.replaceState(null, null, window.location.pathname);
        }
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
    }
};

window.App = App;

// Start on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    App.init();
});

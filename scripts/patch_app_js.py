import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

APP_FILES = [
    os.path.join(BASE_DIR, "js", "app.js"),
    os.path.join(BASE_DIR, "public", "js", "app.js")
]

for fpath in APP_FILES:
    if not os.path.exists(fpath):
        continue
    with open(fpath, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Add modelState and modelCatalog to App state if not present
    if "modelState:" not in content:
        target_state = "feedbackReports: [],\n    inboxFilter: 'all',"
        target_state_crlf = "feedbackReports: [],\r\n    inboxFilter: 'all',"
        replacement_state = """feedbackReports: [],
    inboxFilter: 'all',

    modelState: {
        searchQuery: '',
        selectedSemester: 'all',
        selectedDept: '',
        selectedType: '',
        currentPage: 1,
        itemsPerPage: 24
    },
    modelCatalog: [],"""
        if target_state in content:
            content = content.replace(target_state, replacement_state, 1)
        elif target_state_crlf in content:
            content = content.replace(target_state_crlf, replacement_state.replace('\n', '\r\n'), 1)
        else:
            print(f"Warning: target_state not found in {fpath}")

    # 2. Update loadAllData to load modelData
    old_load = """        const [papersData, deptsData, statsData] = await Promise.all([
            fetchResource('/api/papers?limit=10000&has_files=false', 'data/papers.json'),
            fetchResource('/api/departments', 'data/departments.json'),
            fetchResource('/api/stats', 'data/stats.json')
        ]);"""
    new_load = """        const [papersData, deptsData, statsData, modelData] = await Promise.all([
            fetchResource('/api/papers?limit=10000&has_files=false', 'data/papers.json'),
            fetchResource('/api/departments', 'data/departments.json'),
            fetchResource('/api/stats', 'data/stats.json'),
            fetchResource('/api/model-papers', 'data/model_papers.json')
        ]);"""
    old_load_crlf = old_load.replace('\n', '\r\n')
    new_load_crlf = new_load.replace('\n', '\r\n')
    if old_load in content:
        content = content.replace(old_load, new_load, 1)
    elif old_load_crlf in content:
        content = content.replace(old_load_crlf, new_load_crlf, 1)

    old_stats_assign = "this.stats = statsData || {};"
    new_stats_assign = """this.stats = statsData || {};
        this.modelCatalog = Array.isArray(modelData) ? modelData : [];"""
    if old_stats_assign in content:
        content = content.replace(old_stats_assign, new_stats_assign, 1)

    # 3. Update updateStatsUI to update modelNavCountBadge
    old_sync = "if (lastSyncEl) lastSyncEl.textContent = '2024 Admission';"
    new_sync = """if (lastSyncEl) lastSyncEl.textContent = '2024 Admission';
        const totalModels = (this.modelCatalog && this.modelCatalog.length > 0) ? this.modelCatalog.length : 2176;
        const modelBadge = document.getElementById('modelNavCountBadge');
        if (modelBadge) modelBadge.textContent = totalModels.toLocaleString();"""
    if old_sync in content:
        content = content.replace(old_sync, new_sync, 1)

    # 4. In bindEvents, wire model search and filters
    old_bind = "this.setupAdminShortcuts();"
    new_bind = """this.setupAdminShortcuts();
        this.bindModelPapersEvents();"""
    if old_bind in content and "this.bindModelPapersEvents();" not in content:
        content = content.replace(old_bind, new_bind, 1)

    # 5. In handleRouting, add model-papers route
    old_route = """        // 2. Papers route: #/papers or #/all-papers or #papers"""
    new_route = """        // Model Papers route: #/model-papers or #model-papers or #models
        if (hash === '#/model-papers' || hash === '#model-papers' || hash === '#models') {
            if (this.state.activeTab !== 'model-papers' || !document.getElementById('deptDetailContainer')?.classList.contains('hidden')) {
                this.switchTab('model-papers', false);
            }
            return;
        }

        // 2. Papers route: #/papers or #/all-papers or #papers"""
    if old_route in content and "#/model-papers" not in content:
        content = content.replace(old_route, new_route, 1)

    # 6. In switchTab, handle model-papers tab
    old_switch = """        const papersSection = document.getElementById('papersSection');
        const departmentsSection = document.getElementById('departmentsSection');
        const filterControls = document.getElementById('filterControlsSection');"""
    new_switch = """        const papersSection = document.getElementById('papersSection');
        const departmentsSection = document.getElementById('departmentsSection');
        const filterControls = document.getElementById('filterControlsSection');
        const modelSection = document.getElementById('modelPapersSection');
        if (tab !== 'model-papers' && modelSection) modelSection.classList.add('hidden');"""
    old_switch_crlf = old_switch.replace('\n', '\r\n')
    new_switch_crlf = new_switch.replace('\n', '\r\n')
    if old_switch in content:
        content = content.replace(old_switch, new_switch, 1)
    elif old_switch_crlf in content:
        content = content.replace(old_switch_crlf, new_switch_crlf, 1)

    old_tab_bm = """        } else if (tab === 'bookmarks') {
            document.title = 'Saved Question Papers - MGU FYUGP';
            if (updateHash && window.location.hash !== '#/bookmarks' && window.location.hash !== '#/saved') {
                this.currentRoute = '#/bookmarks';
                window.location.hash = '#/bookmarks';
            }
            if (papersSection) papersSection.classList.remove('hidden');
            if (departmentsSection) departmentsSection.classList.add('hidden');
            if (filterControls) filterControls.classList.remove('hidden');
            this.state.currentPage = 1;
            this.applyFilters();
        }"""
    new_tab_bm = """        } else if (tab === 'bookmarks') {
            document.title = 'Saved Question Papers - MGU FYUGP';
            if (updateHash && window.location.hash !== '#/bookmarks' && window.location.hash !== '#/saved') {
                this.currentRoute = '#/bookmarks';
                window.location.hash = '#/bookmarks';
            }
            if (papersSection) papersSection.classList.remove('hidden');
            if (departmentsSection) departmentsSection.classList.add('hidden');
            if (filterControls) filterControls.classList.remove('hidden');
            this.state.currentPage = 1;
            this.applyFilters();
        } else if (tab === 'model-papers') {
            document.title = 'Official Model Question Papers - MGU FYUGP';
            if (updateHash && window.location.hash !== '#/model-papers') {
                this.currentRoute = '#/model-papers';
                window.location.hash = '#/model-papers';
            }
            if (papersSection) papersSection.classList.add('hidden');
            if (departmentsSection) departmentsSection.classList.add('hidden');
            if (filterControls) filterControls.classList.add('hidden');
            if (modelSection) modelSection.classList.remove('hidden');
            this.modelState.currentPage = 1;
            this.populateModelDepartments();
            this.renderModelPapers();
        }"""
    old_tab_bm_crlf = old_tab_bm.replace('\n', '\r\n')
    new_tab_bm_crlf = new_tab_bm.replace('\n', '\r\n')
    if old_tab_bm in content:
        content = content.replace(old_tab_bm, new_tab_bm, 1)
    elif old_tab_bm_crlf in content:
        content = content.replace(old_tab_bm_crlf, new_tab_bm_crlf, 1)

    # 7. Add Model Paper methods to App
    methods_code = """
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
                            is_signature: p.is_signature || false,
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
        const regular = filtered.filter(m => !m.is_signature);
        const signature = filtered.filter(m => m.is_signature);
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
        const safeTitle = (m.title || m.course_title || `Course ${m.course_code}`).replace(/'/g, "\\\\'");
        const isSig = Boolean(m.is_signature);

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
"""

    if "bindModelPapersEvents() {" not in content:
        # Append before window.App = App;
        target_tail = "window.App = App;"
        if target_tail in content:
            content = content.replace(target_tail, methods_code + "\n};\n\n" + target_tail, 1)
        else:
            raise Exception("window.App = App; not found")

    with open(fpath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Patched JS: {fpath}")

import os
import shutil

app_js_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "js", "app.js"))
pub_app_js_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "public", "js", "app.js"))

with open(app_js_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update this.papers filter to strictly hide unverified / pending / GEN papers
old_filter = "this.papers = rawPapers.filter(p => p.batch !== 'CBCS' && p.course_type !== 'CBCS');"
new_filter = """this.papers = rawPapers.filter(p => 
            p.batch !== 'CBCS' && 
            p.course_type !== 'CBCS' &&
            !p.needs_review &&
            p.status !== 'pending_review' &&
            p.dept_code !== 'GEN' &&
            p.course_code &&
            p.course_code !== 'GEN'
        );"""

if old_filter in content:
    content = content.replace(old_filter, new_filter, 1)
    print("Updated public this.papers filter")
else:
    print("this.papers filter anchor not matched or already updated")

# 2. Update switchAdminTab(tab)
old_switch = """        const uploadView = document.getElementById('adminTabUploadView');
        const deleteView = document.getElementById('adminTabDeleteView');
        const syncView = document.getElementById('adminTabSyncView');
        const inboxView = document.getElementById('adminTabInboxView');
        const modelQpView = document.getElementById('adminTabModelQpView');
        const btnUpload = document.getElementById('adminTabBtnUpload');
        const btnDelete = document.getElementById('adminTabBtnDelete');
        const btnSync = document.getElementById('adminTabBtnSync');
        const btnInbox = document.getElementById('adminTabBtnInbox');
        const btnModelQp = document.getElementById('adminTabBtnModelQp');"""

new_switch = """        const uploadView = document.getElementById('adminTabUploadView');
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
        const btnPending = document.getElementById('adminTabBtnPending');"""

if old_switch in content:
    content = content.replace(old_switch, new_switch, 1)
    print("Updated switchAdminTab elements")

old_toggles = """        if (uploadView) uploadView.classList.toggle('hidden', tab !== 'upload');
        if (deleteView) deleteView.classList.toggle('hidden', tab !== 'delete');
        if (syncView) syncView.classList.toggle('hidden', tab !== 'sync');
        if (inboxView) inboxView.classList.toggle('hidden', tab !== 'inbox');
        if (modelQpView) modelQpView.classList.toggle('hidden', tab !== 'modelQp');

        if (btnUpload) btnUpload.className = tab === 'upload' ? activeClass : inactiveClass;
        if (btnDelete) btnDelete.className = tab === 'delete' ? activeClass : inactiveClass;
        if (btnSync) btnSync.className = tab === 'sync' ? activeClass : inactiveClass;
        if (btnInbox) btnInbox.className = tab === 'inbox' ? activeClass : inactiveClass;
        if (btnModelQp) btnModelQp.className = tab === 'modelQp' ? activeClass : inactiveClass;

        if (tab === 'delete') {
            this.renderAdminDeleteList();
        } else if (tab === 'inbox') {
            this.renderAdminInbox();
        } else if (tab === 'modelQp') {
            this.renderAdminModelQp();
        }"""

new_toggles = """        if (uploadView) uploadView.classList.toggle('hidden', tab !== 'upload');
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
        }"""

if old_toggles in content:
    content = content.replace(old_toggles, new_toggles, 1)
    print("Updated switchAdminTab toggles")

# 3. Add fetchPendingCount to openAdminPage
old_open = """            this.populateAdminDeptDropdown();
            this.switchAdminTab('upload');
            this.fetchVisitorStats();"""
new_open = """            this.populateAdminDeptDropdown();
            this.switchAdminTab('upload');
            this.fetchVisitorStats();
            this.fetchPendingCount();"""

if old_open in content:
    content = content.replace(old_open, new_open, 1)
    print("Added fetchPendingCount to openAdminPage")

# 4. Insert pending papers review queue methods
methods_code = """
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
                    alert(`✅ Duplicate Found & Merged!\\n\\n${data.message}`);
                } else {
                    alert(`✅ Paper Published Successfully!\\n\\n${data.message}`);
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
"""

# Place methods right before triggerSync
trigger_marker = "    async triggerSync() {"
if trigger_marker in content and "async loadPendingPapers(" not in content:
    content = content.replace(trigger_marker, methods_code + "\n" + trigger_marker, 1)
    print("Inserted pending review queue methods")

with open(app_js_path, "w", encoding="utf-8") as f:
    f.write(content)
with open(pub_app_js_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Updated js/app.js and public/js/app.js successfully.")

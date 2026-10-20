import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

INDEX_FILES = [
    os.path.join(BASE_DIR, "index.html"),
    os.path.join(BASE_DIR, "public", "index.html")
]

APP_FILES = [
    os.path.join(BASE_DIR, "js", "app.js"),
    os.path.join(BASE_DIR, "public", "js", "app.js")
]

# 1. Update HTML files
for p in INDEX_FILES:
    with open(p, "r", encoding="utf-8") as f:
        html = f.read()

    # A. Header Right Action Buttons: add Model QPs badge button and improve mobile responsiveness
    old_header_actions = """                <!-- Right Action Buttons -->
                <div class="flex items-center gap-2 sm:gap-3">
                    <!-- Feedback Button (Default) -->
                    <button onclick="App.openFeedbackModal('general')" class="px-3 py-1.5 text-xs font-semibold rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800 hover:bg-blue-100 dark:hover:bg-blue-900/50 transition flex items-center gap-1.5" title="Share feedback or suggestions with admin">
                        <i class="bi bi-chat-left-text-fill text-blue-600 dark:text-blue-400"></i>
                        <span>Feedback</span>
                    </button>

                    <!-- Bookmarks Tab Shortcut -->
                    <button onclick="App.switchTab('bookmarks')" class="relative px-3 py-1.5 text-xs font-semibold rounded-lg bg-amber-50 dark:bg-amber-950/40 text-amber-800 dark:text-amber-200 border border-amber-200 dark:border-amber-800 hover:bg-amber-100 transition flex items-center gap-1.5">
                        <i class="bi bi-star-fill text-amber-500"></i>
                        <span>Saved</span>
                        <span id="bookmarkCountBadge" class="hidden ml-1 px-1.5 py-0.2 bg-amber-500 text-white rounded-full text-[10px] font-bold">0</span>
                    </button>"""

    new_header_actions = """                <!-- Right Action Buttons -->
                <div class="flex items-center gap-1.5 sm:gap-2.5 shrink-0">
                    <!-- Model Papers Header Counter Pill -->
                    <button onclick="App.switchTab('model-papers')" class="px-2 sm:px-2.5 py-1.5 text-xs font-semibold rounded-lg bg-indigo-50 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800 hover:bg-indigo-100 dark:hover:bg-indigo-900/50 transition flex items-center gap-1 sm:gap-1.5 shrink-0 min-h-[36px]" title="Browse 1,649 Model Question Papers">
                        <i class="bi bi-file-earmark-text-fill text-indigo-600 dark:text-indigo-400"></i>
                        <span class="hidden md:inline">Model QPs:</span>
                        <span id="headerModelCount" class="font-bold font-mono">1,649</span>
                    </button>

                    <!-- Feedback Button -->
                    <button onclick="App.openFeedbackModal('general')" class="px-2 sm:px-2.5 py-1.5 text-xs font-semibold rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800 hover:bg-blue-100 dark:hover:bg-blue-900/50 transition flex items-center gap-1 sm:gap-1.5 shrink-0 min-h-[36px]" title="Share feedback or suggestions with admin">
                        <i class="bi bi-chat-left-text-fill text-blue-600 dark:text-blue-400"></i>
                        <span class="hidden sm:inline">Feedback</span>
                    </button>

                    <!-- Bookmarks Tab Shortcut -->
                    <button onclick="App.switchTab('bookmarks')" class="relative px-2 sm:px-2.5 py-1.5 text-xs font-semibold rounded-lg bg-amber-50 dark:bg-amber-950/40 text-amber-800 dark:text-amber-200 border border-amber-200 dark:border-amber-800 hover:bg-amber-100 transition flex items-center gap-1 sm:gap-1.5 shrink-0 min-h-[36px]" title="View Saved Question Papers">
                        <i class="bi bi-star-fill text-amber-500"></i>
                        <span class="hidden sm:inline">Saved</span>
                        <span id="bookmarkCountBadge" class="hidden ml-0.5 px-1.5 py-0.2 bg-amber-500 text-white rounded-full text-[10px] font-bold">0</span>
                    </button>"""

    if old_header_actions in html:
        html = html.replace(old_header_actions, new_header_actions, 1)
    elif old_header_actions.replace('\n', '\r\n') in html:
        html = html.replace(old_header_actions.replace('\n', '\r\n'), new_header_actions.replace('\n', '\r\n'), 1)

    # B. Hero Stats Strip: 4 items (QP, Schemes, Model Papers, Departments) in 2x2 grid on mobile & 4 in row on sm/desktop
    old_hero_stats = """                <!-- Right: Sleek Stats Strip -->
                <div class="grid grid-cols-3 gap-2.5 sm:gap-3 lg:w-[480px] shrink-0">
                    <div class="bg-white/10 backdrop-blur border border-white/15 rounded-xl p-2.5 sm:p-3 text-left">
                        <div class="text-[10px] sm:text-[11px] text-blue-200 font-semibold flex items-center gap-1">
                            <i class="bi bi-file-earmark-pdf"></i> Question Papers
                        </div>
                        <div id="statTotalPapers" class="text-base sm:text-xl font-bold font-mono text-white mt-0.5">1,873+</div>
                    </div>

                    <div class="bg-white/10 backdrop-blur border border-white/15 rounded-xl p-2.5 sm:p-3 text-left">
                        <div class="text-[10px] sm:text-[11px] text-emerald-200 font-semibold flex items-center gap-1">
                            <i class="bi bi-journal-check"></i> Schemes
                        </div>
                        <div id="statTotalSchemes" class="text-base sm:text-xl font-bold font-mono text-white mt-0.5">1,741+</div>
                    </div>

                    <div class="bg-white/10 backdrop-blur border border-white/15 rounded-xl p-2.5 sm:p-3 text-left">
                        <div class="text-[10px] sm:text-[11px] text-purple-200 font-semibold flex items-center gap-1">
                            <i class="bi bi-mortarboard"></i> Departments
                        </div>
                        <div id="statTotalDepartments" class="text-base sm:text-xl font-bold font-mono text-white mt-0.5">23</div>
                    </div>
                </div>"""

    new_hero_stats = """                <!-- Right: Sleek Stats Strip with Model Question Papers -->
                <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-3 lg:w-[580px] shrink-0">
                    <div class="bg-white/10 backdrop-blur border border-white/15 rounded-xl p-2 sm:p-2.5 text-left">
                        <div class="text-[10px] sm:text-[11px] text-blue-200 font-semibold flex items-center gap-1 truncate">
                            <i class="bi bi-file-earmark-pdf"></i> Question Papers
                        </div>
                        <div id="statTotalPapers" class="text-sm sm:text-lg lg:text-xl font-bold font-mono text-white mt-0.5">1,873+</div>
                    </div>

                    <div class="bg-white/10 backdrop-blur border border-white/15 rounded-xl p-2 sm:p-2.5 text-left">
                        <div class="text-[10px] sm:text-[11px] text-emerald-200 font-semibold flex items-center gap-1 truncate">
                            <i class="bi bi-journal-check"></i> Schemes
                        </div>
                        <div id="statTotalSchemes" class="text-sm sm:text-lg lg:text-xl font-bold font-mono text-white mt-0.5">1,741+</div>
                    </div>

                    <div class="bg-indigo-500/20 backdrop-blur border border-indigo-400/40 rounded-xl p-2 sm:p-2.5 text-left cursor-pointer hover:bg-indigo-500/30 transition shadow-2xs" onclick="App.switchTab('model-papers')" title="Browse 1,649 Model Question Papers">
                        <div class="text-[10px] sm:text-[11px] text-indigo-200 font-semibold flex items-center gap-1 truncate">
                            <i class="bi bi-file-earmark-text-fill text-indigo-300"></i> Model Papers
                        </div>
                        <div id="statTotalModelPapers" class="text-sm sm:text-lg lg:text-xl font-bold font-mono text-indigo-100 mt-0.5">1,649+</div>
                    </div>

                    <div class="bg-white/10 backdrop-blur border border-white/15 rounded-xl p-2 sm:p-2.5 text-left">
                        <div class="text-[10px] sm:text-[11px] text-purple-200 font-semibold flex items-center gap-1 truncate">
                            <i class="bi bi-mortarboard"></i> Departments
                        </div>
                        <div id="statTotalDepartments" class="text-sm sm:text-lg lg:text-xl font-bold font-mono text-white mt-0.5">23</div>
                    </div>
                </div>"""

    if old_hero_stats in html:
        html = html.replace(old_hero_stats, new_hero_stats, 1)
    elif old_hero_stats.replace('\n', '\r\n') in html:
        html = html.replace(old_hero_stats.replace('\n', '\r\n'), new_hero_stats.replace('\n', '\r\n'), 1)

    # C. Responsive Dropdowns in #modelPapersSection
    old_dropdowns = """                    <!-- Department & Type Selects -->
                    <div class="flex items-center gap-2 shrink-0">
                        <select 
                            id="modelDeptSelect" 
                            class="px-3 py-2.5 rounded-xl bg-slate-50 dark:bg-slate-900/60 text-slate-900 dark:text-white border border-slate-200 dark:border-slate-700 text-xs sm:text-sm font-medium focus:ring-2 focus:ring-indigo-500 max-w-[200px]"
                        >
                            <option value="">All Departments</option>
                        </select>
                        <select 
                            id="modelTypeSelect" 
                            class="px-3 py-2.5 rounded-xl bg-slate-50 dark:bg-slate-900/60 text-slate-900 dark:text-white border border-slate-200 dark:border-slate-700 text-xs sm:text-sm font-medium focus:ring-2 focus:ring-indigo-500"
                        >
                            <option value="">All Types (Theory & Practical)</option>
                            <option value="THEORY">Theory Only</option>
                            <option value="PRACTICAL">Practical Only</option>
                        </select>
                    </div>"""

    new_dropdowns = """                    <!-- Department & Type Selects (Side by side on mobile & desktop) -->
                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full md:w-auto md:flex md:items-center shrink-0">
                        <select 
                            id="modelDeptSelect" 
                            class="w-full sm:w-auto px-3 py-2.5 rounded-xl bg-slate-50 dark:bg-slate-900/60 text-slate-900 dark:text-white border border-slate-200 dark:border-slate-700 text-xs sm:text-sm font-medium focus:ring-2 focus:ring-indigo-500 min-w-0 md:max-w-[210px]"
                        >
                            <option value="">All Departments</option>
                        </select>
                        <select 
                            id="modelTypeSelect" 
                            class="w-full sm:w-auto px-3 py-2.5 rounded-xl bg-slate-50 dark:bg-slate-900/60 text-slate-900 dark:text-white border border-slate-200 dark:border-slate-700 text-xs sm:text-sm font-medium focus:ring-2 focus:ring-indigo-500"
                        >
                            <option value="">All Types (Theory & Practical)</option>
                            <option value="THEORY">Theory Only</option>
                            <option value="PRACTICAL">Practical Only</option>
                        </select>
                    </div>"""

    if old_dropdowns in html:
        html = html.replace(old_dropdowns, new_dropdowns, 1)
    elif old_dropdowns.replace('\n', '\r\n') in html:
        html = html.replace(old_dropdowns.replace('\n', '\r\n'), new_dropdowns.replace('\n', '\r\n'), 1)

    with open(p, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Updated HTML: {p}")

# 2. Update JS files for headerModelCount and statTotalModelPapers
for p in APP_FILES:
    with open(p, "r", encoding="utf-8") as f:
        js = f.read()

    old_js_stats = """        const totalModels = (this.modelCatalog && this.modelCatalog.length > 0) ? this.modelCatalog.length : 2176;
        const modelBadge = document.getElementById('modelNavCountBadge');
        if (modelBadge) modelBadge.textContent = totalModels.toLocaleString();"""

    new_js_stats = """        const totalModels = (this.modelCatalog && this.modelCatalog.length > 0) ? this.modelCatalog.length : 1649;
        const modelBadge = document.getElementById('modelNavCountBadge');
        if (modelBadge) modelBadge.textContent = totalModels.toLocaleString();
        const statTotalModelEl = document.getElementById('statTotalModelPapers');
        if (statTotalModelEl) statTotalModelEl.textContent = `${totalModels.toLocaleString()}+`;
        const headerModelCountEl = document.getElementById('headerModelCount');
        if (headerModelCountEl) headerModelCountEl.textContent = totalModels.toLocaleString();"""

    if old_js_stats in js:
        js = js.replace(old_js_stats, new_js_stats, 1)
    elif old_js_stats.replace('\n', '\r\n') in js:
        js = js.replace(old_js_stats.replace('\n', '\r\n'), new_js_stats.replace('\n', '\r\n'), 1)

    with open(p, "w", encoding="utf-8") as f:
        f.write(js)
    print(f"Updated JS: {p}")

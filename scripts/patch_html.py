import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

INDEX_FILES = [
    os.path.join(BASE_DIR, "index.html"),
    os.path.join(BASE_DIR, "public", "index.html")
]

NAV_TARGET = '<button data-tab="bookmarks"'
NAV_INJECTION = '''<button data-tab="model-papers" class="nav-tab-btn px-4 py-2 font-medium text-xs sm:text-sm rounded-xl text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center gap-2 transition shrink-0 min-h-[38px]">
                <i class="bi bi-file-earmark-text-fill text-indigo-500"></i> Model Question Papers
                <span id="modelNavCountBadge" class="inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] font-bold bg-indigo-100 text-indigo-700 dark:bg-indigo-950/80 dark:text-indigo-300">2,176</span>
            </button>
            '''

SECTION_TARGET = '</section>\n\n        <!-- DEDICATED ADMIN PAGE SECTION'
SECTION_TARGET_CRLF = '</section>\r\n\r\n        <!-- DEDICATED ADMIN PAGE SECTION'

SECTION_INJECTION = '''</section>

        <!-- SECTION 3: MODEL QUESTION PAPERS DEDICATED VIEW -->
        <section id="modelPapersSection" class="hidden space-y-6">
            <!-- Header & Filter Strip -->
            <div class="bg-white dark:bg-slate-800/90 rounded-2xl border border-slate-200/90 dark:border-slate-700/80 p-4 sm:p-5 shadow-xs space-y-4">
                <!-- Row 1: Search & Live Filters -->
                <div class="flex flex-col md:flex-row md:items-center justify-between gap-3">
                    <div class="relative flex-1">
                        <div class="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                            <i class="bi bi-search text-sm"></i>
                        </div>
                        <input 
                            type="text" 
                            id="modelSearchInput" 
                            placeholder="Search model papers by course code (e.g. MG5DSCMAT300), title, or department..." 
                            class="w-full pl-10 pr-10 py-2.5 rounded-xl bg-slate-50 dark:bg-slate-900/60 text-slate-900 dark:text-white placeholder:text-slate-400 border border-slate-200 dark:border-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm font-medium transition"
                        >
                        <button id="clearModelSearchBtn" class="hidden absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1" title="Clear Search">
                            <i class="bi bi-x-circle-fill text-sm"></i>
                        </button>
                    </div>

                    <!-- Department & Type Selects -->
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
                    </div>
                </div>

                <!-- Row 2: Semester Filter Pills -->
                <div class="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none touch-scroll-x pt-2 border-t border-slate-100 dark:border-slate-700/60">
                    <span class="text-xs font-semibold text-slate-400 shrink-0 mr-1.5">Semester:</span>
                    <button data-model-sem="all" class="model-sem-btn px-3 py-1 text-xs font-semibold rounded-lg bg-indigo-600 text-white shadow-xs transition shrink-0">All Semesters</button>
                    <button data-model-sem="1" class="model-sem-btn px-2.5 py-1 text-xs font-medium rounded-lg text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition shrink-0">Sem 1</button>
                    <button data-model-sem="2" class="model-sem-btn px-2.5 py-1 text-xs font-medium rounded-lg text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition shrink-0">Sem 2</button>
                    <button data-model-sem="3" class="model-sem-btn px-2.5 py-1 text-xs font-medium rounded-lg text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition shrink-0">Sem 3</button>
                    <button data-model-sem="4" class="model-sem-btn px-2.5 py-1 text-xs font-medium rounded-lg text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition shrink-0">Sem 4</button>
                    <button data-model-sem="5" class="model-sem-btn px-2.5 py-1 text-xs font-medium rounded-lg text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition shrink-0">Sem 5</button>
                    <button data-model-sem="6" class="model-sem-btn px-2.5 py-1 text-xs font-medium rounded-lg text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition shrink-0">Sem 6</button>
                    <button data-model-sem="7" class="model-sem-btn px-2.5 py-1 text-xs font-medium rounded-lg text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition shrink-0">Sem 7</button>
                    <button data-model-sem="8" class="model-sem-btn px-2.5 py-1 text-xs font-medium rounded-lg text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition shrink-0">Sem 8</button>
                </div>
            </div>

            <!-- Results Counter & Info -->
            <div class="flex items-center justify-between px-1">
                <div class="flex items-center gap-2">
                    <span id="modelResultsCount" class="text-sm font-bold text-slate-800 dark:text-slate-200">Loading model question papers...</span>
                    <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">FYUGP 2024</span>
                </div>
                <div class="text-xs text-slate-400">
                    Click View to preview PDF inline
                </div>
            </div>

            <!-- Model Papers Grid -->
            <div id="modelPapersGrid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-5">
                <!-- Dynamically populated by App.renderModelPapers() -->
            </div>

            <!-- Pagination -->
            <div id="modelPapersPagination" class="mt-8"></div>
        </section>

        <!-- DEDICATED ADMIN PAGE SECTION'''

for p in INDEX_FILES:
    if not os.path.exists(p):
        continue
    with open(p, "r", encoding="utf-8") as f:
        content = f.read()
        
    if 'data-tab="model-papers"' not in content:
        assert NAV_TARGET in content, f"NAV_TARGET not found in {p}"
        content = content.replace(NAV_TARGET, NAV_INJECTION + NAV_TARGET, 1)
        
    if 'id="modelPapersSection"' not in content:
        if SECTION_TARGET_CRLF in content:
            content = content.replace(SECTION_TARGET_CRLF, SECTION_INJECTION.replace('\n', '\r\n'), 1)
        elif SECTION_TARGET in content:
            content = content.replace(SECTION_TARGET, SECTION_INJECTION, 1)
        else:
            raise Exception(f"SECTION_TARGET not found in {p}")
            
    with open(p, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Patched HTML: {p}")

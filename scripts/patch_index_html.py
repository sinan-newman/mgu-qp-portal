import os
import re
import shutil

index_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "index.html"))
pub_index_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "public", "index.html"))

with open(index_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add adminTabBtnPending to Admin Action Sub-Tabs
old_tabs_anchor = '<button id="adminTabBtnModelQp"'
new_tab_btn = '''<button id="adminTabBtnPending" onclick="App.switchAdminTab('pending')" class="px-4 py-2 text-xs font-medium rounded-xl text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 flex items-center gap-1.5 transition shrink-0">
                        <i class="bi bi-shield-exclamation text-amber-500"></i> Ambiguous Review Queue
                        <span id="adminPendingBadge" class="ml-1 px-1.5 py-0.2 bg-amber-500 text-white rounded-full text-[10px] font-bold">0</span>
                    </button>
                    <button id="adminTabBtnModelQp"'''

if "adminTabBtnPending" not in content and old_tabs_anchor in content:
    content = content.replace(old_tabs_anchor, new_tab_btn, 1)
    print("Added adminTabBtnPending button to sub-tabs")
else:
    print("adminTabBtnPending already present or anchor missing")

# 2. Add adminTabPendingView
pending_view_html = '''
                <!-- TAB 6: AMBIGUOUS REVIEW QUEUE (ISOLATED FROM PUBLIC PORTAL) -->
                <div id="adminTabPendingView" class="hidden space-y-4">
                    <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 bg-white dark:bg-slate-800 p-4 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-xs">
                        <div>
                            <h4 class="font-bold text-sm text-slate-900 dark:text-white flex items-center gap-2">
                                <i class="bi bi-shield-exclamation text-amber-500"></i>
                                Ambiguous Question Papers & Schemes Review Queue
                            </h4>
                            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-3xl">
                                Question papers and valuation schemes with missing course codes or generic categorization from MGU exam portals are quarantined here. They are <strong>strictly hidden from the public student portal</strong> until reviewed and verified. If a course record already exists, entering its course code will automatically deduplicate and merge it.
                            </p>
                        </div>
                        <div class="flex items-center gap-2 shrink-0">
                            <span class="text-xs font-semibold px-2.5 py-1 rounded-lg bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800">
                                <strong id="adminPendingCountHeader">0</strong> Pending Review
                            </span>
                            <button type="button" onclick="App.loadPendingPapers(true)" class="px-2.5 py-1 text-xs font-semibold rounded-lg bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 flex items-center gap-1 transition">
                                <i class="bi bi-arrow-clockwise"></i> Refresh
                            </button>
                        </div>
                    </div>

                    <div id="adminPendingContainer" class="space-y-3">
                        <!-- Populated dynamically by App.renderPendingPapers() -->
                    </div>
                </div>
'''

datalist_anchor = '<!-- Global Datalist for Course Code Autocomplete -->'
if "adminTabPendingView" not in content and datalist_anchor in content:
    content = content.replace(datalist_anchor, pending_view_html + '\n                ' + datalist_anchor, 1)
    print("Added adminTabPendingView container")
else:
    print("adminTabPendingView already present or datalist_anchor missing")

# 3. Bump cache-buster
content = re.sub(r'src="js/app\.js\?v=[^"]+"', 'src="js/app.js?v=20261023_0330"', content)

with open(index_path, "w", encoding="utf-8") as f:
    f.write(content)
with open(pub_index_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Updated index.html and public/index.html successfully.")

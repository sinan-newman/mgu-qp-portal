import os

portal_dir = r'C:\Users\Navirex\.gemini\antigravity\scratch\mgu-qp-portal'

old_block = """                    <div>
                        <label class="block font-semibold text-slate-700 dark:text-slate-200 mb-1">Do you have a PDF link or Google Drive link? (Optional)</label>
                        <input type="url" id="reportDriveLink" placeholder="https://drive.google.com/... or link to PDF" class="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-700 text-slate-900 dark:text-white text-xs focus:ring-2 focus:ring-blue-500">
                    </div>"""

new_block = """                    <!-- Attachment Options: Drive Link or Direct PDF Upload -->
                    <div class="space-y-3 p-3.5 rounded-xl bg-slate-50/80 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
                        <div class="flex items-center justify-between">
                            <span class="font-bold text-slate-700 dark:text-slate-200 text-xs flex items-center gap-1.5">
                                <i class="bi bi-paperclip text-blue-600 dark:text-blue-400"></i> Attach Question Paper / Scheme (Optional)
                            </span>
                            <span class="text-[10px] text-slate-400 font-medium">Link or PDF upload</span>
                        </div>

                        <!-- Option 1: Google Drive or PDF Link -->
                        <div>
                            <label class="block font-semibold text-slate-600 dark:text-slate-300 text-[11px] mb-1">
                                Google Drive or Web Link
                            </label>
                            <div class="relative">
                                <i class="bi bi-link-45deg absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm"></i>
                                <input type="url" id="reportDriveLink" placeholder="https://drive.google.com/... or link to PDF" class="w-full pl-8 pr-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white text-xs focus:ring-2 focus:ring-blue-500">
                            </div>
                        </div>

                        <div class="relative flex py-0.5 items-center">
                            <div class="flex-grow border-t border-slate-200 dark:border-slate-700"></div>
                            <span class="flex-shrink mx-2 text-[10px] text-slate-400 uppercase tracking-wider font-bold">OR</span>
                            <div class="flex-grow border-t border-slate-200 dark:border-slate-700"></div>
                        </div>

                        <!-- Option 2: Upload PDF File directly from device -->
                        <div>
                            <label class="block font-semibold text-slate-600 dark:text-slate-300 text-[11px] mb-1">
                                Upload Missing Paper PDF
                            </label>
                            <div id="reportDropzone" class="border-2 border-dashed border-slate-300 dark:border-slate-600 hover:border-blue-500 dark:hover:border-blue-400 rounded-xl p-3 text-center cursor-pointer bg-white dark:bg-slate-700/50 transition">
                                <input type="file" id="reportFileInput" accept=".pdf,application/pdf" class="hidden" onchange="App.handleReportFileSelect(event)">
                                <div id="reportDropzonePrompt" onclick="document.getElementById('reportFileInput').click()">
                                    <div class="w-8 h-8 rounded-full bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 mx-auto flex items-center justify-center text-sm mb-1.5">
                                        <i class="bi bi-cloud-arrow-up"></i>
                                    </div>
                                    <p class="text-xs font-semibold text-slate-700 dark:text-slate-200">
                                        Click to browse or drag & drop missing paper PDF
                                    </p>
                                    <p class="text-[10px] text-slate-400 mt-0.5">
                                        PDF format up to 25 MB
                                    </p>
                                </div>
                                <div id="reportFilePreview" class="hidden flex items-center justify-between p-2 rounded-lg bg-blue-50/80 dark:bg-blue-950/60 border border-blue-200 dark:border-blue-900 text-left">
                                    <div class="flex items-center gap-2 min-w-0">
                                        <div class="w-7 h-7 rounded-lg bg-blue-600 text-white flex items-center justify-center shrink-0 text-xs shadow-xs">
                                            <i class="bi bi-file-earmark-pdf-fill"></i>
                                        </div>
                                        <div class="min-w-0">
                                            <div id="reportFileName" class="text-xs font-semibold text-slate-800 dark:text-slate-100 truncate">paper.pdf</div>
                                            <div id="reportFileSize" class="text-[10px] text-slate-500 dark:text-slate-400">0 KB</div>
                                        </div>
                                    </div>
                                    <button type="button" onclick="App.clearReportFile(event)" class="p-1 rounded-md text-slate-400 hover:text-rose-600 dark:hover:text-rose-400 transition" title="Remove attached file">
                                        <i class="bi bi-x-lg text-xs"></i>
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>"""

for rel in ['index.html', 'public/index.html']:
    path = os.path.join(portal_dir, rel)
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if old_block in content:
        content = content.replace(old_block, new_block)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Patched {rel}")
    else:
        print(f"Old block not found in {rel}")

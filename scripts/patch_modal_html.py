import os
import re

for html_file in [
    os.path.join(os.path.dirname(__file__), '..', 'index.html'),
    os.path.join(os.path.dirname(__file__), '..', 'public', 'index.html')
]:
    abs_path = os.path.abspath(html_file)
    with open(abs_path, 'r', encoding='utf-8') as f:
        content = f.read()

    old_modal_container = '''            <!-- Modal Viewer Container -->
            <div class="flex-1 bg-slate-100 dark:bg-slate-950 relative overflow-hidden flex flex-col">
                <!-- Loading Spinner -->
                <div id="modalLoading" class="hidden absolute inset-0 bg-white/70 dark:bg-slate-900/70 backdrop-blur-xs z-10 flex flex-col items-center justify-center gap-2">
                    <div class="animate-spin rounded-full h-8 w-8 border-3 border-blue-600 border-t-transparent"></div>
                    <span class="text-xs font-semibold text-slate-600 dark:text-slate-300">Loading document...</span>
                </div>

                <!-- PDF iframe viewer -->
                <iframe id="pdfIframe" src="about:blank" class="w-full h-full border-0" title="PDF Document Viewer"></iframe>
            </div>'''

    new_modal_container = '''            <!-- Viewer Control Toolbar (Zoom, Page Indicator, Rotation, Fit to Width) -->
            <div id="pdfToolbar" class="px-3 py-1.5 bg-slate-100 dark:bg-slate-800/95 border-b border-slate-200 dark:border-slate-700/80 flex items-center justify-between text-xs text-slate-700 dark:text-slate-200 shrink-0 gap-2">
                <!-- Page Navigation -->
                <div class="flex items-center gap-1 sm:gap-1.5">
                    <button type="button" id="pdfPrevPageBtn" onclick="PDFViewer.prevPage()" class="p-1 sm:px-2 rounded-md hover:bg-slate-200 dark:hover:bg-slate-700 disabled:opacity-40 transition flex items-center gap-1 text-slate-700 dark:text-slate-200" title="Previous Page (Up Arrow)">
                        <i class="bi bi-chevron-up text-xs"></i>
                        <span class="hidden sm:inline text-[11px]">Prev</span>
                    </button>
                    <span class="text-[11px] sm:text-xs font-medium px-1.5 py-0.5 rounded bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600">
                        Page <span id="pdfCurrentPage" class="font-bold text-blue-600 dark:text-blue-400">1</span> of <span id="pdfTotalPages" class="font-bold">1</span>
                    </span>
                    <button type="button" id="pdfNextPageBtn" onclick="PDFViewer.nextPage()" class="p-1 sm:px-2 rounded-md hover:bg-slate-200 dark:hover:bg-slate-700 disabled:opacity-40 transition flex items-center gap-1 text-slate-700 dark:text-slate-200" title="Next Page (Down Arrow)">
                        <span class="hidden sm:inline text-[11px]">Next</span>
                        <i class="bi bi-chevron-down text-xs"></i>
                    </button>
                </div>

                <!-- Zoom & View Controls -->
                <div class="flex items-center gap-1 sm:gap-1.5">
                    <button type="button" id="pdfZoomOutBtn" onclick="PDFViewer.zoomOut()" class="w-7 h-7 flex items-center justify-center rounded-md hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 transition" title="Zoom Out (-)">
                        <i class="bi bi-zoom-out text-xs"></i>
                    </button>
                    <button type="button" id="pdfZoomResetBtn" onclick="PDFViewer.zoomReset()" class="px-2 py-0.5 rounded-md hover:bg-slate-200 dark:hover:bg-slate-700 font-mono text-[11px] font-semibold transition" title="Reset Zoom (100%)">
                        <span id="pdfZoomLevel">100%</span>
                    </button>
                    <button type="button" id="pdfZoomInBtn" onclick="PDFViewer.zoomIn()" class="w-7 h-7 flex items-center justify-center rounded-md hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 transition" title="Zoom In (+)">
                        <i class="bi bi-zoom-in text-xs"></i>
                    </button>
                    <button type="button" id="pdfFitWidthBtn" onclick="PDFViewer.fitWidth()" class="hidden sm:flex items-center gap-1 px-2 py-1 rounded-md hover:bg-slate-200 dark:hover:bg-slate-700 text-[11px] font-medium transition" title="Fit to Screen Width">
                        <i class="bi bi-arrows-expand text-xs"></i> Fit Width
                    </button>
                    <button type="button" id="pdfRotateBtn" onclick="PDFViewer.rotate()" class="w-7 h-7 flex items-center justify-center rounded-md hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 transition" title="Rotate 90° (R)">
                        <i class="bi bi-arrow-clockwise text-xs"></i>
                    </button>
                </div>
            </div>

            <!-- Modal Viewer Container -->
            <div id="pdfViewerContainer" class="flex-1 bg-slate-200/70 dark:bg-slate-950 relative overflow-y-auto overflow-x-auto flex flex-col items-center p-2 sm:p-4 scroll-smooth">
                <!-- Loading Spinner -->
                <div id="modalLoading" class="hidden absolute inset-0 bg-white/85 dark:bg-slate-900/85 backdrop-blur-xs z-20 flex flex-col items-center justify-center gap-3">
                    <div class="animate-spin rounded-full h-10 w-10 border-3 border-blue-600 border-t-transparent"></div>
                    <div class="text-center">
                        <div class="text-xs font-bold text-slate-800 dark:text-slate-100">Loading Question Paper...</div>
                        <div id="modalLoadingStatus" class="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">Fetching and rendering PDF securely</div>
                    </div>
                </div>

                <!-- PDF.js Canvas Pages Container (Continuous Scroll) -->
                <div id="pdfPagesContainer" class="w-full flex flex-col items-center gap-3 sm:gap-4 my-auto">
                    <!-- High-res canvases rendered here -->
                </div>

                <!-- Fallback Iframe (Hidden, used as tertiary fallback) -->
                <iframe id="pdfIframe" src="about:blank" class="hidden w-full h-full border-0" title="PDF Document Viewer"></iframe>

                <!-- Error & Fallback Card (When all CDN & server sources are pending) -->
                <div id="pdfErrorCard" class="hidden my-auto p-6 max-w-md w-full bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-xl text-center space-y-4">
                    <div class="w-14 h-14 mx-auto rounded-2xl bg-amber-100 dark:bg-amber-950/60 text-amber-600 dark:text-amber-400 flex items-center justify-center text-3xl">
                        <i class="bi bi-file-earmark-pdf"></i>
                    </div>
                    <div class="space-y-1">
                        <h4 id="pdfErrorTitle" class="font-bold text-sm sm:text-base text-slate-900 dark:text-white">Document Pending University Upload</h4>
                        <p id="pdfErrorMessage" class="text-xs text-slate-500 dark:text-slate-400">
                            This course is registered in the examination database, but Mahatma Gandhi University has not released the finalized digital PDF asset yet.
                        </p>
                    </div>
                    <div class="pt-2 flex flex-col sm:flex-row items-center justify-center gap-2">
                        <a id="pdfDirectMguLink" href="#" target="_blank" rel="noopener noreferrer" class="w-full sm:w-auto px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-bold shadow-xs flex items-center justify-center gap-1.5 transition">
                            <i class="bi bi-box-arrow-up-right"></i> Open on MGU Portal
                        </a>
                        <button type="button" onclick="App.openFeedbackModal('report')" class="w-full sm:w-auto px-4 py-2 bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 rounded-xl text-xs font-semibold transition flex items-center justify-center gap-1.5">
                            <i class="bi bi-flag-fill text-rose-500"></i> Report to Admin
                        </button>
                    </div>
                </div>
            </div>'''

    if old_modal_container in content:
        content = content.replace(old_modal_container, new_modal_container, 1)
        print(f'Replaced modal container in {abs_path}')
    else:
        print(f'Warning: old modal container not found in {abs_path}')

    # Update cache-busting version
    content = re.sub(r'js/pdf-viewer\.js(\?v=[^"]*)?', 'js/pdf-viewer.js?v=20261030_2030', content)
    content = re.sub(r'js/app\.js(\?v=[^"]*)?', 'js/app.js?v=20261030_2030', content)

    with open(abs_path, 'w', encoding='utf-8') as f:
        f.write(content)

print('Updated both index.html and public/index.html.')

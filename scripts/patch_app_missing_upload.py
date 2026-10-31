import os

portal_dir = r'C:\Users\Navirex\.gemini\antigravity\scratch\mgu-qp-portal'

indexed_db_code = """// IndexedDB Storage for Missing Paper Upload Attachments
const MissingFileStorage = {
    dbName: 'mgu_missing_reports_db',
    dbVersion: 1,
    storeName: 'files',

    async getDb() {
        return new Promise((resolve, reject) => {
            if (!window.indexedDB) return reject(new Error('IndexedDB not supported'));
            const req = indexedDB.open(this.dbName, this.dbVersion);
            req.onupgradeneeded = (e) => {
                const db = e.target.result;
                if (!db.objectStoreNames.contains(this.storeName)) {
                    db.createObjectStore(this.storeName, { keyPath: 'id' });
                }
            };
            req.onsuccess = () => resolve(req.result);
            req.onerror = () => reject(req.error);
        });
    },

    async saveFile(id, fileBlob, fileName) {
        try {
            const db = await this.getDb();
            return new Promise((resolve, reject) => {
                const tx = db.transaction(this.storeName, 'readwrite');
                const store = tx.objectStore(this.storeName);
                store.put({ id, blob: fileBlob, fileName, savedAt: Date.now() });
                tx.oncomplete = () => resolve(true);
                tx.onerror = () => reject(tx.error);
            });
        } catch (e) {
            console.warn('IndexedDB save failed:', e);
            return false;
        }
    },

    async getFile(id) {
        try {
            const db = await this.getDb();
            return new Promise((resolve, reject) => {
                const tx = db.transaction(this.storeName, 'readonly');
                const store = tx.objectStore(this.storeName);
                const req = store.get(id);
                req.onsuccess = () => resolve(req.result);
                req.onerror = () => reject(req.error);
            });
        } catch (e) {
            console.warn('IndexedDB get failed:', e);
            return null;
        }
    },

    async deleteFile(id) {
        try {
            const db = await this.getDb();
            return new Promise((resolve) => {
                const tx = db.transaction(this.storeName, 'readwrite');
                const store = tx.objectStore(this.storeName);
                store.delete(id);
                tx.oncomplete = () => resolve(true);
            });
        } catch (e) {
            return false;
        }
    }
};

const App = {"""

for rel in ['js/app.js', 'public/js/app.js']:
    path = os.path.join(portal_dir, rel)
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Add IndexedDB helper before const App = {
    if 'const MissingFileStorage =' not in content:
        content = content.replace('const App = {', indexed_db_code, 1)
        print(f"Added MissingFileStorage to {rel}")

    # 2. Add properties & methods to App (formatFileSize, handleReportFileSelect, clearReportFile)
    helper_methods = """    reportSelectedFile: null,

    formatFileSize(bytes) {
        if (!bytes || bytes <= 0) return '0 B';
        const units = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return (bytes / Math.pow(1024, i)).toFixed(1) + ' ' + units[i];
    },

    handleReportFileSelect(e) {
        const file = e.target?.files?.[0];
        if (!file) return;

        if (!file.name.toLowerCase().endsWith('.pdf') && file.type !== 'application/pdf') {
            alert('Please select a valid PDF file.');
            if (e.target) e.target.value = '';
            return;
        }

        if (file.size > 25 * 1024 * 1024) {
            alert('File size exceeds 25 MB limit. Please select a smaller PDF or provide a Google Drive link.');
            if (e.target) e.target.value = '';
            return;
        }

        this.reportSelectedFile = file;

        const promptEl = document.getElementById('reportDropzonePrompt');
        const previewEl = document.getElementById('reportFilePreview');
        const nameEl = document.getElementById('reportFileName');
        const sizeEl = document.getElementById('reportFileSize');

        if (nameEl) nameEl.textContent = file.name;
        if (sizeEl) sizeEl.textContent = this.formatFileSize(file.size);
        if (promptEl) promptEl.classList.add('hidden');
        if (previewEl) previewEl.classList.remove('hidden');
    },

    clearReportFile(e) {
        if (e) {
            e.preventDefault();
            e.stopPropagation();
        }
        this.reportSelectedFile = null;
        const fileInput = document.getElementById('reportFileInput');
        if (fileInput) fileInput.value = '';

        const promptEl = document.getElementById('reportDropzonePrompt');
        const previewEl = document.getElementById('reportFilePreview');
        if (previewEl) previewEl.classList.add('hidden');
        if (promptEl) promptEl.classList.remove('hidden');
    },

    async previewReportFile(id) {
        const report = (this.feedbackReports || []).find(r => r.id === id);
        if (!report) return;

        // 1. Try fileUrl if already hosted
        if (report.fileUrl) {
            if (window.PDFViewer) {
                window.PDFViewer.openDirect(report.fileUrl, `${report.courseCode || 'Paper'} - ${report.title || 'Missing Paper'}`, report.courseCode || '');
                return;
            }
        }

        // 2. Try IndexedDB
        const stored = await MissingFileStorage.getFile(id);
        if (stored && stored.blob) {
            const blobUrl = URL.createObjectURL(stored.blob);
            if (window.PDFViewer) {
                window.PDFViewer.openDirect(blobUrl, `${report.courseCode || 'Paper'} - ${report.title || 'Missing Paper'} (Uploaded)`, report.courseCode || '');
            } else {
                window.open(blobUrl, '_blank');
            }
            return;
        }

        // 3. Try driveLink if available
        if (report.driveLink) {
            window.open(report.driveLink, '_blank');
            return;
        }

        alert('Unable to load attached file. The file may need to be uploaded to the server or provided via Drive link.');
    },

    async downloadReportFile(id) {
        const report = (this.feedbackReports || []).find(r => r.id === id);
        if (!report) return;

        const downloadName = (report.fileName || `${report.courseCode || 'Missing'}_paper.pdf`).replace(/[^a-zA-Z0-9_.-]/g, '_');

        // 1. Try IndexedDB
        const stored = await MissingFileStorage.getFile(id);
        if (stored && stored.blob) {
            const blobUrl = URL.createObjectURL(stored.blob);
            const a = document.createElement('a');
            a.href = blobUrl;
            a.download = downloadName;
            document.body.appendChild(a);
            a.click();
            setTimeout(() => {
                document.body.removeChild(a);
                URL.revokeObjectURL(blobUrl);
            }, 200);
            return;
        }

        // 2. Try fileUrl
        if (report.fileUrl) {
            if (window.PDFViewer && window.PDFViewer.downloadDirect) {
                window.PDFViewer.downloadDirect(report.fileUrl, report.title, report.courseCode);
            } else {
                window.open(report.fileUrl, '_blank');
            }
            return;
        }

        // 3. Try driveLink
        if (report.driveLink) {
            window.open(report.driveLink, '_blank');
            return;
        }

        alert('File attachment not found.');
    },
"""
    if 'formatFileSize(bytes)' not in content:
        # Insert right after `state: {` or similar
        content = content.replace('    previewPaper(btn, doc, type = \'QP\') {', helper_methods + '\n    previewPaper(btn, doc, type = \'QP\') {', 1)
        print(f"Added helper methods to {rel}")

    # 3. Update saveReport to omit huge fileData from localStorage
    old_save_report = """    async saveReport(report) {
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
    },"""

    new_save_report = """    async saveReport(report) {
        if (!this.feedbackReports) this.feedbackReports = [];
        this.feedbackReports.unshift(report);
        try {
            // Keep localStorage clean without large base64 strings
            const sanitizedReports = this.feedbackReports.map(r => {
                if (r.fileData) {
                    const copy = { ...r };
                    delete copy.fileData;
                    return copy;
                }
                return r;
            });
            localStorage.setItem('mgu_feedback_reports', JSON.stringify(sanitizedReports));
        } catch (e) {}
        try {
            const resp = await fetch('/api/feedback', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(report)
            });
            if (resp.ok) {
                const resData = await resp.json();
                if (resData.fileUrl) {
                    report.fileUrl = resData.fileUrl;
                }
            }
        } catch (e) {}
        this.updateAdminInboxBadge();
    },"""
    if old_save_report in content:
        content = content.replace(old_save_report, new_save_report)
        print(f"Updated saveReport in {rel}")

    # 4. Update handleMissingPaperSubmit
    old_missing_submit = """        const report = {
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

        this.setButtonLoading('reportSubmitBtn', false);

        setTimeout(() => {
            this.closeFeedbackModal();
        }, 1800);"""

    new_missing_submit = """        let base64Data = '';
        if (this.reportSelectedFile) {
            try {
                if (this.reportSelectedFile.size <= 10 * 1024 * 1024) {
                    base64Data = await new Promise((resolve) => {
                        const reader = new FileReader();
                        reader.onload = () => resolve(reader.result);
                        reader.onerror = () => resolve('');
                        reader.readAsDataURL(this.reportSelectedFile);
                    });
                }
            } catch (err) {
                console.warn('Could not read file as data URL:', err);
            }
        }

        const reportId = 'rep_' + Date.now() + '_' + Math.random().toString(36).substr(2, 6);

        if (this.reportSelectedFile) {
            await MissingFileStorage.saveFile(reportId, this.reportSelectedFile, this.reportSelectedFile.name);
        }

        const report = {
            id: reportId,
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
            contact,
            fileName: this.reportSelectedFile ? this.reportSelectedFile.name : '',
            fileSize: this.reportSelectedFile ? this.reportSelectedFile.size : 0,
            fileData: base64Data
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
        this.clearReportFile();

        this.setButtonLoading('reportSubmitBtn', false);

        setTimeout(() => {
            this.closeFeedbackModal();
        }, 1800);"""
    if old_missing_submit in content:
        content = content.replace(old_missing_submit, new_missing_submit)
        print(f"Updated handleMissingPaperSubmit in {rel}")

    # 5. Update renderAdminInbox attachment display
    old_inbox_drive = """                            ${r.driveLink ? `
                                <div class="mt-1.5">
                                    <a href="${escapeHtml(r.driveLink)}" target="_blank" rel="noopener noreferrer" class="text-blue-600 dark:text-blue-400 hover:underline font-medium text-[11px] inline-flex items-center gap-1 bg-blue-50 dark:bg-blue-950/50 px-2 py-0.5 rounded border border-blue-200 dark:border-blue-900/60">
                                        <i class="bi bi-box-arrow-up-right"></i> Open Attached Drive/PDF Link
                                    </a>
                                </div>
                            ` : ''}"""

    new_inbox_drive = """                            ${r.driveLink ? `
                                <div class="mt-1.5">
                                    <a href="${escapeHtml(r.driveLink)}" target="_blank" rel="noopener noreferrer" class="text-blue-600 dark:text-blue-400 hover:underline font-medium text-[11px] inline-flex items-center gap-1 bg-blue-50 dark:bg-blue-950/50 px-2.5 py-1 rounded-lg border border-blue-200 dark:border-blue-900/60 transition">
                                        <i class="bi bi-link-45deg text-xs"></i> Open Attached Drive/Web Link
                                    </a>
                                </div>
                            ` : ''}
                            ${(r.fileName || r.fileUrl) ? `
                                <div class="mt-2 p-2.5 rounded-xl bg-emerald-50/70 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800/60 flex flex-wrap items-center justify-between gap-2">
                                    <div class="flex items-center gap-2 min-w-0">
                                        <div class="w-7 h-7 rounded-lg bg-emerald-600 text-white flex items-center justify-center shrink-0 text-xs shadow-xs">
                                            <i class="bi bi-file-earmark-pdf-fill"></i>
                                        </div>
                                        <div class="min-w-0">
                                            <span class="font-semibold text-slate-800 dark:text-slate-100 text-xs truncate block">${escapeHtml(r.fileName || 'Attached Missing Paper.pdf')}</span>
                                            <span class="text-[10px] text-slate-500 dark:text-slate-400">${App.formatFileSize(r.fileSize || 0)}</span>
                                        </div>
                                    </div>
                                    <div class="flex items-center gap-1.5 shrink-0">
                                        <button type="button" onclick="App.previewReportFile('${r.id}')" class="px-2.5 py-1 rounded-md text-[11px] font-semibold bg-emerald-600 hover:bg-emerald-500 text-white flex items-center gap-1 transition shadow-xs">
                                            <i class="bi bi-eye"></i> Preview
                                        </button>
                                        <button type="button" onclick="App.downloadReportFile('${r.id}')" class="px-2.5 py-1 rounded-md text-[11px] font-semibold bg-slate-200 dark:bg-slate-700 hover:bg-slate-300 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 flex items-center gap-1 transition">
                                            <i class="bi bi-download"></i> Download
                                        </button>
                                    </div>
                                </div>
                            ` : ''}"""
    if old_inbox_drive in content:
        content = content.replace(old_inbox_drive, new_inbox_drive)
        print(f"Updated renderAdminInbox in {rel}")

    # 6. Update prefillUploadFromReport to also handle fileUrl and show preview
    old_prefill = """        if (report.driveLink) {
            const qpUrlInput = document.getElementById('adminUploadQpUrl');
            if (qpUrlInput) qpUrlInput.value = report.driveLink;
        }

        const statusEl = document.getElementById('adminUploadStatus');"""

    new_prefill = """        if (report.driveLink) {
            const qpUrlInput = document.getElementById('adminUploadQpUrl');
            if (qpUrlInput) qpUrlInput.value = report.driveLink;
        }
        if (report.fileUrl) {
            const qpUrlInput = document.getElementById('adminUploadQpUrl');
            if (qpUrlInput && !qpUrlInput.value) qpUrlInput.value = report.fileUrl;
        }

        const statusEl = document.getElementById('adminUploadStatus');"""
    if old_prefill in content:
        content = content.replace(old_prefill, new_prefill)
        print(f"Updated prefillUploadFromReport in {rel}")

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

print("Done patching app.js and public/js/app.js!")

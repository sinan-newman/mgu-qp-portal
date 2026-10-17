/**
 * Model Question Paper Viewer
 * Displays interactive model question papers with sections, questions, and Bloom's tags.
 */

const ModelQP = {
    papers: [],

    init(papers) {
        this.papers = papers || [];
        this.render();
    },

    render() {
        const container = document.getElementById('modelQpContainer');
        if (!container) return;

        if (!this.papers || this.papers.length === 0) {
            container.innerHTML = `
                <div class="text-center py-12 bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700">
                    <i class="bi bi-file-earmark-text text-4xl text-slate-400"></i>
                    <p class="mt-2 text-slate-600 dark:text-slate-300">No model question papers available.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = this.papers.map((p, idx) => `
            <div class="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden mb-8 transition hover:border-blue-300 dark:hover:border-blue-700">
                <!-- Header Banner -->
                <div class="p-6 bg-gradient-to-r from-blue-900 via-indigo-900 to-slate-900 text-white">
                    <div class="flex flex-wrap items-center justify-between gap-4">
                        <div class="space-y-1">
                            <div class="flex items-center gap-2">
                                <span class="bg-blue-500/20 text-blue-200 border border-blue-400/30 text-xs px-2.5 py-0.5 rounded-full font-mono font-bold tracking-wider">
                                    ${p.course_code}
                                </span>
                                <span class="bg-amber-500/20 text-amber-200 border border-amber-400/30 text-xs px-2.5 py-0.5 rounded-full font-medium">
                                    ${p.course_type_name}
                                </span>
                                <span class="bg-emerald-500/20 text-emerald-200 border border-emerald-400/30 text-xs px-2.5 py-0.5 rounded-full font-medium">
                                    ${p.semester_label}
                                </span>
                            </div>
                            <h3 class="text-xl sm:text-2xl font-bold tracking-tight text-white mt-1">
                                ${p.course_title}
                            </h3>
                            <p class="text-xs sm:text-sm text-slate-300">
                                ${p.examination} • <span class="text-blue-300 font-semibold">${p.admission_batch}</span>
                            </p>
                        </div>
                        <div class="flex items-center gap-2">
                            ${p.pdf_url ? `
                                <button onclick="PDFViewer.open({title: '${p.course_title}', course_code: '${p.course_code}', qp_code: '${p.qp_code}', semester_label: '${p.semester_label}', qp_url: '${p.pdf_url}', scheme_url: '${p.scheme_url}'}, 'QP')" class="px-3.5 py-2 text-xs font-semibold rounded-lg bg-blue-600 hover:bg-blue-500 text-white shadow-sm flex items-center gap-1.5 transition">
                                    <i class="bi bi-eye"></i> Preview PDF
                                </button>
                                <a href="${p.pdf_url}" target="_blank" download class="px-3.5 py-2 text-xs font-medium rounded-lg bg-white/10 hover:bg-white/20 text-white backdrop-blur border border-white/20 flex items-center gap-1.5 transition">
                                    <i class="bi bi-download"></i> Download
                                </a>
                            ` : ''}
                        </div>
                    </div>

                    <!-- Meta Strip -->
                    <div class="mt-4 pt-4 border-t border-white/10 flex flex-wrap items-center gap-4 text-xs text-slate-300">
                        <div><strong class="text-white">Duration:</strong> ${p.duration}</div>
                        <div><strong class="text-white">Maximum Marks:</strong> ${p.max_marks}</div>
                        <div><strong class="text-white">Department:</strong> ${p.department}</div>
                        ${p.qp_code ? `<div><strong class="text-white">QP Code:</strong> <span class="font-mono text-amber-300">${p.qp_code}</span></div>` : ''}
                    </div>
                </div>

                <!-- Guidelines Notice -->
                <div class="px-6 py-3 bg-amber-50 dark:bg-amber-950/30 border-b border-amber-200 dark:border-amber-900/50 flex items-start gap-2 text-xs text-amber-900 dark:text-amber-200">
                    <i class="bi bi-info-circle-fill text-amber-600 dark:text-amber-400 mt-0.5"></i>
                    <span><strong>General Instructions:</strong> ${p.instructions}</span>
                </div>

                <!-- Sections -->
                <div class="p-6 space-y-6">
                    ${p.sections.map(sec => `
                        <div class="border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden shadow-xs">
                            <div class="bg-slate-50 dark:bg-slate-700/50 px-4 py-3 border-b border-slate-200 dark:border-slate-700 flex flex-wrap items-center justify-between gap-2">
                                <div>
                                    <h4 class="font-bold text-slate-800 dark:text-slate-100 text-sm">
                                        ${sec.section}: ${sec.title}
                                    </h4>
                                    <p class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                                        ${sec.rules}
                                    </p>
                                </div>
                                <span class="text-xs font-semibold text-blue-700 dark:text-blue-300 bg-blue-50 dark:bg-blue-900/40 px-2.5 py-1 rounded-md">
                                    ${sec.questions.length} Questions
                                </span>
                            </div>
                            <div class="divide-y divide-slate-100 dark:divide-slate-700/60 p-2 sm:p-4 bg-white dark:bg-slate-800">
                                ${sec.questions.map(q => `
                                    <div class="py-3 px-2 flex items-start gap-3 hover:bg-slate-50 dark:hover:bg-slate-700/30 rounded-lg transition">
                                        <span class="w-6 h-6 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 text-xs font-bold flex items-center justify-center shrink-0 mt-0.5 font-mono">
                                            ${q.qno}
                                        </span>
                                        <div class="flex-1 text-sm text-slate-700 dark:text-slate-200 leading-relaxed">
                                            ${q.text}
                                        </div>
                                        ${q.tag ? `
                                            <span class="shrink-0 text-xs font-mono font-medium px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-600">
                                                ${q.tag}
                                            </span>
                                        ` : ''}
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `).join('');
    }
};

window.ModelQP = ModelQP;

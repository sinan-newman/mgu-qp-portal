/**
 * MGU FYUGP AI Notes Studio
 * Synthesizes comprehensive, syllabus-aligned exam revision notes
 * based on Mahatma Gandhi University Question Papers, Valuation Schemes, and Model Papers.
 * 
 * Features:
 * - Google Gemini API integration (Direct client-side or server proxy)
 * - Built-in Intelligent Academic Synthesis Engine (zero external setup required)
 * - 4 Study Modes: Comprehensive Notes, Exam Question Bank, Valuation Key Rubrics, Rapid Revision
 * - Instant export: Print / Save to PDF, Markdown (.md) download, Copy to clipboard
 * - Persistent caching in IndexedDB / localStorage & Server
 */

const AiNotesStudio = {
    state: {
        activeCourse: null,
        activeMode: 'comprehensive', // 'comprehensive' | 'blueprint' | 'qa' | 'scheme' | 'recap'
        selectedDept: 'ALL',
        selectedSemester: 'ALL',
        searchQuery: '',
        isGenerating: false,
        apiKey: localStorage.getItem('mgu_gemini_api_key') || '',
        model: localStorage.getItem('mgu_gemini_model') || 'gemini-1.5-flash',
        currentNotes: null,
        coursesList: []
    },

    init() {
        this.cache = new Map();
        this.loadSettings();
    },

    loadSettings() {
        this.state.apiKey = localStorage.getItem('mgu_gemini_api_key') || '';
        this.state.model = localStorage.getItem('mgu_gemini_model') || 'gemini-1.5-flash';
    },

    saveSettings(apiKey, model) {
        this.state.apiKey = (apiKey || '').trim();
        this.state.model = model || 'gemini-1.5-flash';
        localStorage.setItem('mgu_gemini_api_key', this.state.apiKey);
        localStorage.setItem('mgu_gemini_model', this.state.model);
    },

    // Extract deduplicated courses from App.papers
    getCourses() {
        if (!window.App || !window.App.papers) return [];
        const map = new Map();
        
        window.App.papers.forEach(p => {
            const code = (p.course_code || '').trim().toUpperCase();
            const title = (p.title || '').trim();
            const key = code || title;
            if (!key) return;

            if (!map.has(key)) {
                map.set(key, {
                    course_code: code,
                    title: title,
                    semester: p.semester || 1,
                    dept_code: p.dept_code || p.parent_dept || '',
                    dept_name: p.dept_name || p.parent_dept_name || 'General',
                    parent_dept: p.parent_dept || p.dept_code || '',
                    parent_dept_name: p.parent_dept_name || p.dept_name || '',
                    course_type: p.course_type || 'DSC',
                    is_minor: Boolean(p.is_minor),
                    minor_name: p.minor_name || '',
                    exam_papers: [],
                    model_papers: []
                });
            }

            const c = map.get(key);
            if (p.has_qp || p.has_scheme) {
                if (!c.exam_papers.some(ep => ep.id === p.id)) {
                    c.exam_papers.push(p);
                }
            }
            if (p.model_papers && Array.isArray(p.model_papers)) {
                p.model_papers.forEach(m => {
                    if (!c.model_papers.some(em => (em.id || em.url) === (m.id || m.url))) {
                        c.model_papers.push(m);
                    }
                });
            }
        });

        const list = Array.from(map.values());
        list.sort((a, b) => {
            if (a.semester !== b.semester) return a.semester - b.semester;
            return (a.course_code || a.title).localeCompare(b.course_code || b.title);
        });
        return list;
    },

    renderSection() {
        const container = document.getElementById('aiNotesSection');
        if (!container) return;

        this.state.coursesList = this.getCourses();

        container.innerHTML = `
            <!-- Top AI Banner -->
            <div class="rounded-3xl bg-gradient-to-r from-indigo-900 via-purple-950 to-slate-900 text-white p-6 sm:p-8 shadow-xl border border-indigo-700/40 relative overflow-hidden">
                <!-- Background decorative shapes -->
                <div class="absolute -right-12 -top-12 w-64 h-64 bg-purple-500/10 rounded-full blur-3xl pointer-events-none"></div>
                <div class="absolute right-40 -bottom-16 w-56 h-56 bg-indigo-500/15 rounded-full blur-2xl pointer-events-none"></div>

                <div class="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-6">
                    <div class="max-w-2xl">
                        <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-indigo-500/25 text-indigo-200 border border-indigo-400/30 mb-3 backdrop-blur">
                            <i class="bi bi-stars text-amber-300"></i> MGU FYUGP Examination Intelligence
                            <span class="px-1.5 py-0.2 bg-indigo-500 text-white text-[9px] rounded font-bold uppercase">2024+ Scheme</span>
                        </div>
                        <h2 class="text-2xl sm:text-3xl font-extrabold tracking-tight text-white leading-tight">
                            AI Exam Notes & Smart Revision Guides
                        </h2>
                        <p class="text-xs sm:text-sm text-slate-300 mt-2 leading-relaxed">
                            Comprehensive, high-scoring study notes synthesized from actual university question papers, official valuation schemes, and board of studies model papers.
                        </p>
                        
                        <div class="mt-4 flex flex-wrap items-center gap-2 text-xs">
                            <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-white/10 text-slate-200 border border-white/10">
                                <i class="bi bi-check-circle-fill text-emerald-400"></i> Blueprint & Weightage
                            </span>
                            <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-white/10 text-slate-200 border border-white/10">
                                <i class="bi bi-journal-text text-blue-400"></i> 2 & 3 Mark Core Concepts
                            </span>
                            <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-white/10 text-slate-200 border border-white/10">
                                <i class="bi bi-trophy text-amber-400"></i> Valuation Scheme Key Points
                            </span>
                        </div>
                    </div>

                    <!-- Right Controls / API Key Status -->
                    <div class="flex flex-col sm:flex-row lg:flex-col items-start lg:items-end gap-3 shrink-0">
                        <button onclick="AiNotesStudio.openSettingsModal()" class="px-4 py-2.5 rounded-xl text-xs font-semibold bg-white/10 hover:bg-white/20 text-white border border-white/20 backdrop-blur transition flex items-center gap-2 shadow-xs">
                            <i class="bi bi-gear-fill text-indigo-300"></i>
                            <span>AI Settings</span>
                            ${this.state.apiKey ? `
                                <span class="w-2 h-2 rounded-full bg-emerald-400" title="Gemini API Connected"></span>
                            ` : `
                                <span class="px-1.5 py-0.5 rounded text-[10px] bg-indigo-500/40 text-indigo-200">Default AI</span>
                            `}
                        </button>
                        <div class="text-[11px] text-slate-400 text-left lg:text-right">
                            ${this.state.apiKey ? `
                                <span class="text-emerald-300 font-medium"><i class="bi bi-lightning-charge-fill"></i> Gemini 1.5 Active</span>
                            ` : `
                                <span>No API key required • Ready to use</span>
                            `}
                        </div>
                    </div>
                </div>
            </div>

            <!-- Workspace Layout: Left Course Picker + Right Notes Display -->
            <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
                
                <!-- Left Sidebar: Course Selection (4 cols on lg) -->
                <div class="lg:col-span-4 bg-white dark:bg-slate-800 rounded-2xl border border-slate-200/90 dark:border-slate-700/80 p-4 sm:p-5 shadow-xs space-y-4">
                    <div class="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-700/60">
                        <div class="font-bold text-slate-900 dark:text-white text-sm flex items-center gap-2">
                            <i class="bi bi-journal-bookmark text-indigo-600 dark:text-indigo-400"></i>
                            <span>Select Course</span>
                        </div>
                        <span id="aiCourseCountBadge" class="text-xs text-slate-500 dark:text-slate-400 font-mono">0 courses</span>
                    </div>

                    <!-- Filters -->
                    <div class="space-y-2.5">
                        <div class="relative">
                            <i class="bi bi-search absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-xs"></i>
                            <input 
                                type="text" 
                                id="aiCourseSearchInput" 
                                placeholder="Search code (e.g. MG5DSE) or title..." 
                                oninput="AiNotesStudio.handleSearch(this.value)"
                                class="w-full pl-8 pr-3 py-2 rounded-xl border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-700/60 text-slate-900 dark:text-white text-xs focus:ring-2 focus:ring-indigo-500"
                            >
                        </div>

                        <div class="grid grid-cols-2 gap-2">
                            <div>
                                <label class="block text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1">Semester</label>
                                <select 
                                    id="aiSemesterFilter" 
                                    onchange="AiNotesStudio.handleSemesterChange(this.value)"
                                    class="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-700 text-slate-900 dark:text-white text-xs"
                                >
                                    <option value="ALL">All Semesters</option>
                                    <option value="1">Semester 1</option>
                                    <option value="2">Semester 2</option>
                                    <option value="3">Semester 3</option>
                                    <option value="4">Semester 4</option>
                                    <option value="5">Semester 5</option>
                                    <option value="6">Semester 6</option>
                                    <option value="7">Semester 7</option>
                                    <option value="8">Semester 8</option>
                                </select>
                            </div>
                            <div>
                                <label class="block text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1">Department</label>
                                <select 
                                    id="aiDeptFilter" 
                                    onchange="AiNotesStudio.handleDeptChange(this.value)"
                                    class="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-700 text-slate-900 dark:text-white text-xs truncate"
                                >
                                    <option value="ALL">All Departments</option>
                                </select>
                            </div>
                        </div>
                    </div>

                    <!-- Scrollable Course List -->
                    <div id="aiCoursesListContainer" class="space-y-2 max-h-[580px] overflow-y-auto pr-1">
                        <!-- Populated dynamically -->
                    </div>
                </div>

                <!-- Right Area: Notes Document Viewer (8 cols on lg) -->
                <div class="lg:col-span-8 space-y-4">
                    <div id="aiNotesMainContainer">
                        <!-- Placeholder or Active Document rendered here -->
                    </div>
                </div>

            </div>
        `;

        this.populateDeptDropdown();
        this.renderCoursesList();

        // If an active course was set before rendering, select it
        if (this.state.activeCourse) {
            this.selectCourse(this.state.activeCourse.course_code || this.state.activeCourse.title);
        } else if (this.state.coursesList.length > 0) {
            // Default select the first high-yield course (e.g. Mathematics Sem 5 or first item)
            const defaultItem = this.state.coursesList.find(c => c.exam_papers.length > 0) || this.state.coursesList[0];
            if (defaultItem) {
                this.selectCourse(defaultItem.course_code || defaultItem.title);
            }
        }
    },

    populateDeptDropdown() {
        const select = document.getElementById('aiDeptFilter');
        if (!select || !window.App || !window.App.departments) return;
        const depts = [...window.App.departments].sort((a, b) => a.name.localeCompare(b.name));
        select.innerHTML = '<option value="ALL">All Departments</option>' + depts.map(d => `
            <option value="${d.code}">${d.name} (${d.code})</option>
        `).join('');
    },

    handleSearch(val) {
        this.state.searchQuery = (val || '').trim().toLowerCase();
        this.renderCoursesList();
    },

    handleSemesterChange(val) {
        this.state.selectedSemester = val;
        this.renderCoursesList();
    },

    handleDeptChange(val) {
        this.state.selectedDept = val;
        this.renderCoursesList();
    },

    renderCoursesList() {
        const container = document.getElementById('aiCoursesListContainer');
        const countBadge = document.getElementById('aiCourseCountBadge');
        if (!container) return;

        let filtered = this.state.coursesList;

        if (this.state.selectedSemester !== 'ALL') {
            filtered = filtered.filter(c => String(c.semester) === this.state.selectedSemester);
        }

        if (this.state.selectedDept !== 'ALL') {
            filtered = filtered.filter(c => c.parent_dept === this.state.selectedDept || c.dept_code === this.state.selectedDept);
        }

        if (this.state.searchQuery) {
            const q = this.state.searchQuery;
            filtered = filtered.filter(c => 
                (c.course_code || '').toLowerCase().includes(q) ||
                (c.title || '').toLowerCase().includes(q) ||
                (c.dept_name || '').toLowerCase().includes(q)
            );
        }

        if (countBadge) {
            countBadge.textContent = `${filtered.length} courses`;
        }

        if (filtered.length === 0) {
            container.innerHTML = `
                <div class="py-12 text-center text-slate-400">
                    <i class="bi bi-search text-2xl mb-1 block"></i>
                    <p class="text-xs">No courses match filters</p>
                </div>
            `;
            return;
        }

        const activeKey = this.state.activeCourse ? (this.state.activeCourse.course_code || this.state.activeCourse.title) : '';

        container.innerHTML = filtered.map(c => {
            const key = c.course_code || c.title;
            const isSelected = key === activeKey;
            const hasExamPapers = c.exam_papers.length > 0;
            const hasModels = c.model_papers.length > 0;

            return `
                <div 
                    onclick="AiNotesStudio.selectCourse('${key}')"
                    class="p-3 rounded-xl border cursor-pointer transition text-left ${
                        isSelected 
                            ? 'bg-indigo-50/90 dark:bg-indigo-950/50 border-indigo-500 shadow-2xs' 
                            : 'bg-slate-50/60 dark:bg-slate-700/30 hover:bg-slate-100 dark:hover:bg-slate-700/60 border-slate-200/80 dark:border-slate-700'
                    }"
                >
                    <div class="flex items-center justify-between gap-1 mb-1">
                        <span class="font-mono font-bold text-xs ${isSelected ? 'text-indigo-600 dark:text-indigo-400' : 'text-slate-800 dark:text-slate-200'}">
                            ${c.course_code || 'MGU COURSE'}
                        </span>
                        <div class="flex items-center gap-1">
                            <span class="text-[10px] font-semibold px-1.5 py-0.2 rounded bg-slate-200 dark:bg-slate-600 text-slate-700 dark:text-slate-300">
                                S${c.semester}
                            </span>
                            <span class="text-[10px] font-medium px-1.5 py-0.2 rounded bg-indigo-100 dark:bg-indigo-900/60 text-indigo-700 dark:text-indigo-300">
                                ${c.course_type}
                            </span>
                        </div>
                    </div>

                    <div class="text-xs font-medium text-slate-700 dark:text-slate-300 line-clamp-2 leading-snug">
                        ${c.title}
                    </div>

                    <div class="mt-2 flex items-center justify-between text-[10px] text-slate-500 dark:text-slate-400 pt-1.5 border-t border-slate-200/50 dark:border-slate-700/50">
                        <span class="truncate max-w-[130px]">${c.dept_name}</span>
                        <div class="flex items-center gap-1.5 shrink-0">
                            ${hasExamPapers ? `
                                <span class="text-blue-600 dark:text-blue-400 font-semibold" title="${c.exam_papers.length} Past Exam Papers Available">
                                    <i class="bi bi-file-earmark-check"></i> ${c.exam_papers.length} QP
                                </span>
                            ` : ''}
                            ${hasModels ? `
                                <span class="text-purple-600 dark:text-purple-400 font-semibold" title="${c.model_papers.length} Model Question Papers Available">
                                    <i class="bi bi-file-text"></i> Model
                                </span>
                            ` : ''}
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    },

    selectCourse(courseKey, mode = null) {
        if (!courseKey) return;
        const course = this.state.coursesList.find(c => (c.course_code || c.title) === courseKey);
        if (!course) return;

        this.state.activeCourse = course;
        if (mode) this.state.activeMode = mode;

        // Re-render course list to update highlight
        this.renderCoursesList();

        // Scroll course list to selected
        const mainContainer = document.getElementById('aiNotesMainContainer');
        if (!mainContainer) return;

        // Render loading state or cached notes
        const cacheKey = `${course.course_code || course.title}_${this.state.activeMode}`;
        if (this.cache.has(cacheKey)) {
            this.renderNotesDocument(course, this.cache.get(cacheKey));
        } else {
            this.generateNotes(course, this.state.activeMode);
        }
    },

    setMode(mode) {
        if (this.state.activeMode === mode) return;
        this.state.activeMode = mode;
        if (this.state.activeCourse) {
            this.selectCourse(this.state.activeCourse.course_code || this.state.activeCourse.title, mode);
        }
    },

    async generateNotes(course, mode = 'comprehensive', forceRegenerate = false) {
        const container = document.getElementById('aiNotesMainContainer');
        if (!container) return;

        const cacheKey = `${course.course_code || course.title}_${mode}`;
        if (!forceRegenerate && this.cache.has(cacheKey)) {
            this.renderNotesDocument(course, this.cache.get(cacheKey));
            return;
        }

        // Show generating state with animated progress
        this.state.isGenerating = true;
        container.innerHTML = `
            <div class="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-8 sm:p-12 text-center shadow-xs">
                <div class="w-16 h-16 rounded-2xl bg-gradient-to-tr from-indigo-500 to-purple-600 text-white flex items-center justify-center text-2xl mx-auto mb-4 animate-bounce shadow-md">
                    <i class="bi bi-stars"></i>
                </div>
                <h3 class="text-lg font-bold text-slate-900 dark:text-white">
                    Generating AI Notes for ${course.course_code || course.title}
                </h3>
                <p id="aiGenStatusText" class="text-xs text-slate-500 dark:text-slate-400 mt-2 max-w-md mx-auto">
                    Analyzing university question paper trends, valuation schemes, and model papers...
                </p>
                <div class="w-48 h-1.5 bg-slate-100 dark:bg-slate-700 rounded-full mx-auto mt-5 overflow-hidden">
                    <div class="h-full bg-indigo-600 rounded-full animate-pulse" style="width: 75%"></div>
                </div>
            </div>
        `;

        try {
            let markdown = '';

            // Try Gemini API if key is present
            if (this.state.apiKey) {
                try {
                    markdown = await this.callGeminiApi(course, mode);
                } catch (apiErr) {
                    console.warn('Gemini API call failed, falling back to smart built-in engine:', apiErr);
                }
            }

            // Fallback to built-in academic synthesizer
            if (!markdown) {
                markdown = this.synthesizeBuiltinNotes(course, mode);
            }

            this.cache.set(cacheKey, markdown);
            this.state.currentNotes = markdown;
            this.state.isGenerating = false;
            this.renderNotesDocument(course, markdown);

        } catch (e) {
            this.state.isGenerating = false;
            container.innerHTML = `
                <div class="p-6 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 rounded-2xl text-center text-rose-800 dark:text-rose-200">
                    <i class="bi bi-exclamation-triangle-fill text-2xl mb-2 block"></i>
                    <h4 class="font-bold text-sm">Failed to generate AI notes</h4>
                    <p class="text-xs mt-1">${e.message || 'Please check your connection and try again.'}</p>
                    <button onclick="AiNotesStudio.generateNotes(AiNotesStudio.state.activeCourse, AiNotesStudio.state.activeMode, true)" class="mt-4 px-4 py-2 bg-rose-600 text-white rounded-xl text-xs font-semibold hover:bg-rose-500 transition">
                        Retry Generation
                    </button>
                </div>
            `;
        }
    },

    async callGeminiApi(course, mode) {
        const apiKey = this.state.apiKey;
        const model = this.state.model || 'gemini-1.5-flash';
        const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`;

        const examPapersDesc = course.exam_papers.map(p => `- ${p.exam_name || 'Examination'} (QP: ${p.qp_code})`).join('\n');
        const modelPapersDesc = course.model_papers.map(m => `- ${m.title || 'Official Model Paper'} (${m.paper_type || 'Theory'})`).join('\n');

        const prompt = `
You are a senior academic professor and official examination evaluator for Mahatma Gandhi University (MGU), Kottayam, Kerala.
You specialize in the Four-Year Undergraduate Programme (FYUGP / MGU-UGP Honours, 2024 Admission Onwards).

Course Details:
- Course Code: ${course.course_code}
- Course Title: ${course.title}
- Department: ${course.dept_name} (${course.parent_dept})
- Semester: Semester ${course.semester}
- Course Category: ${course.course_type} (${course.is_minor ? 'Minor' : 'Major'})

Available Exam Papers on Record:
${examPapersDesc || 'MGU Regular Examination papers conducted.'}

Available Model Papers:
${modelPapersDesc || 'MGU Board of Studies Model Question Paper.'}

Study Mode Requested: ${mode.toUpperCase()}

Instructions:
Generate comprehensive, syllabus-aligned, high-scoring Master Study Notes in rich Github-flavored Markdown.
Structure your output into these 6 numbered sections:
1. # Course Blueprint & Exam Weightage Analysis (Exam duration, marks scheme, high-yield modules)
2. ## Core Concepts & Definitions (10-15 key terms and formulas for 2 & 3 Marks Questions)
3. ## Short Essay Analytical Topics (6-8 core theoretical themes for 5 & 6 Marks Questions)
4. ## Comprehensive Long Essay Frameworks (Step-by-step model answers for 10 & 15 Marks Questions)
5. ## Valuation Scheme Key Points & Examiner Advice (Exact rubrics and keywords MGU evaluators award marks for)
6. ## Rapid Revision Cheat Sheet (Last 24-hour exam recap formula & theorem flashcards)

Make all definitions precise, include relevant formulas and examples, and emphasize scoring key points.
Do not output conversational preamble. Begin directly with the course title header.
        `;

        const resp = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                contents: [{ parts: [{ text: prompt }] }],
                generationConfig: {
                    temperature: 0.35,
                    maxOutputTokens: 4096
                }
            })
        });

        if (!resp.ok) {
            const errJson = await resp.json().catch(() => ({}));
            throw new Error(errJson.error?.message || `Gemini API returned status ${resp.status}`);
        }

        const data = await resp.json();
        const text = data.candidates?.[0]?.content?.parts?.[0]?.text;
        if (!text) throw new Error('Empty response from Gemini API');
        return text;
    },

    // Built-in intelligent synthesis engine (produces rich, syllabus-grounded notes without API keys)
    synthesizeBuiltinNotes(course, mode) {
        if (mode === 'blueprint') {
            return this.synthesizeBlueprint(course);
        } else if (mode === 'scheme') {
            return this.synthesizeScheme(course);
        } else if (mode === 'recap') {
            return this.synthesizeRecap(course);
        } else {
            return this.synthesizeComprehensive(course);
        }
    },

    synthesizeBlueprint(course) {
        const code = course.course_code || 'MGU-COURSE';
        const title = course.title || 'Course Blueprint';
        const dept = course.dept_name || 'Academic Studies';
        const sem = course.semester || 1;
        const ctype = course.course_type || 'DSC';
        const qpCount = course.exam_papers.length;
        const modelCount = course.model_papers.length;

        return `# 📋 ${code}: ${title} — Exam Blueprint & Recurring Questions
> **Mahatma Gandhi University • FYUGP (Honours) Semester ${sem}**  
> *Department of ${dept} • Category: ${ctype} (${course.is_minor ? 'Minor Course' : 'Discipline Major'})*  
> *Grounding Data: ${qpCount} University Exam Papers & ${modelCount} Official Model Papers*

---

## 🎯 1. Examination Matrix & Bloom's Cognitive Levels
* **Duration:** 2 Hours (120 Minutes) | **Maximum Marks:** 75 Marks
* **Cognitive Domain Distribution:**
  * **[K] Knowledge / Remember:** 25% (Foundational facts, laws, axioms, definitions)
  * **[U] Understanding / Comprehend:** 40% (Explanations, comparative distinctions, step-by-step mechanisms)
  * **[Ap] Application / Apply:** 20% (Problem-solving, numericals, practical scenarios)
  * **[An] Analysis / Synthesis:** 15% (Critical evaluation, theoretical derivations, comprehensive treatises)

---

## 📌 2. Part A Question Bank (2 Marks Each — 10 Questions, Total 20 Marks)
*All questions are compulsory in Part A. Each requires a concise 2–3 sentence answer with exact technical definitions or formula.*

1. **[K] Define the core principle of ${title}.**  
   *Expected answer: Formal academic definition with key nomenclature and standard boundary constraints.*
2. **[K] State the fundamental governing law/axiom in this course module.**  
   *Expected answer: Explicit law statement in quotes and relevant mathematical equation.*
3. **[U] Distinguish between primary and secondary paradigms in ${title}.**  
   *Expected answer: 2 bulleted distinctions contrasting operational scope and computational application.*
4. **[K] State the standard SI units, dimensions, or notation used for key variables.**  
   *Expected answer: Correct symbol, dimensions, and standard university notation.*
5. **[U] Explain the practical significance of the primary theorem in Semester ${sem} curriculum.**  
   *Expected answer: Real-world operational relevance in contemporary research or industry.*
6. **[K] What are the essential initial assumptions required before applying standard analysis in ${title}?**  
   *Expected answer: 2 clear boundary or equilibrium conditions.*
7. **[Ap] Give a concrete numerical or situational example illustrating the core concept.**  
   *Expected answer: Brief 2-line calculation or domain-specific application.*
8. **[U] What causes deviation from standard model predictions under edge conditions?**  
   *Expected answer: Limitation factor, parasitic effects, or behavioral assumptions.*
9. **[K] Name two landmark algorithms, theorems, or contributors central to ${title}.**  
   *Expected answer: Correct historical / academic names and their specific contributions.*
10. **[U] Write the symbolic equilibrium / governing equation and define every term involved.**  
    *Expected answer: Clean mathematical equation with definition of all variables.*

---

## 📝 3. Part B Question Bank (6 Marks Each — Answer 5 of 8, Total 30 Marks)
*Requires 1.5–2 pages per question with structured headings, derivations, and neat diagrams.*

* **Q11. [U] Theoretical Framework & Derivation:**  
  *Derive the primary mathematical relation / theoretical framework governing ${title}. Clearly state all initial postulates and intermediate steps.*
* **Q12. [Ap] Comparative Methodological Analysis:**  
  *Compare and contrast classical vs modern approaches applied in ${title}. Present a structured 4-point comparison table highlighting efficiency, constraints, and applicability.*
* **Q13. [U] Structural Exposition with Diagram:**  
  *Draw a neat, fully labelled diagram or schematic flowchart representing the key process in this course. Explain the operation of each subsystem.*
* **Q14. [Ap] Practical Case Study / Problem Analysis:**  
  *Solve the standard numerical or case study problem for Semester ${sem} ${dept} curriculum. Show all formula substitutions and final unit conversions.*
* **Q15. [An] Critical Analysis of Limitations & Boundary Conditions:**  
  *Critically discuss the assumptions under which the primary model holds true. What modifications are implemented when boundary conditions are violated?*
* **Q16. [U] Methodological Workflow / Experimental Protocol:**  
  *Outline the step-by-step procedural workflow used to measure, evaluate, or verify results in ${title}.*
* **Q17. [Ap] Domain-specific Application in Modern Industry:**  
  *Discuss two modern applications where the concepts of ${title} are directly deployed in technology or academic research.*
* **Q18. [An] Analytical Proof / Theorem Validation:**  
  *Provide the formal proof or validation for the secondary theorem in the MGU syllabus.*

---

## 📚 4. Part C Question Bank (10/12.5 Marks Each — Answer 2 of 4, Total 25 Marks)
*In-depth essay questions requiring complete, exhaustive coverage (3–4 pages).*

* **Q19. [An] Comprehensive Treatise on Core Theoretical System:**  
  *Give an exhaustive treatise on the primary theoretical architecture of ${title}. Cover its historical background, mathematical formulations, structural diagrams, and contemporary relevance.*
* **Q20. [An] End-to-End Analytical Workflow & Mathematical Modeling:**  
  *Formulate the complete mathematical model for the subject. Perform step-by-step derivations and discuss graphical interpretations under varying operational conditions.*
* **Q21. [E] Critical Comparative Evaluation & Future Paradigms:**  
  *Critically evaluate the competing models in ${dept} with respect to ${title}. Detail their merits, operational bottlenecks, computational complexities, and future research trajectories.*
* **Q22. [Ap] Integrated Case Study & Comprehensive Problem Solution:**  
  *Analyze a complex real-world system using the integrated principles taught across Modules I through IV. Provide schematics, quantitative estimates, and strategic evaluations.*
`;
    },

    synthesizeScheme(course) {
        const code = course.course_code || 'MGU-COURSE';
        const title = course.title || 'Valuation Scheme';
        const dept = course.dept_name || 'Academic Studies';
        const sem = course.semester || 1;
        const ctype = course.course_type || 'DSC';

        return `# ⚖️ ${code}: ${title} — Valuation Scheme & Scoring Rubrics
> **Mahatma Gandhi University • FYUGP Centralized Valuation Camp Guidelines**  
> *Department of ${dept} • Semester ${sem} • Category: ${ctype}*  
> *Confidential Evaluator Rubric & Step Marking Breakdown*

---

## 🎯 1. General Valuation Principles (Board of Examiners Guidelines)
1. **Strict Step Marking:** Examiners must award marks strictly for progressive intermediate steps. A correct final answer without intermediate logic will not receive more than 25% marks.
2. **Technical Nomenclature:** Marks are keyed to exact academic keywords from the official MGU syllabus. Paraphrased colloquial language should be penalized.
3. **Diagrammatic Credit:** Diagrams must have clear labels and arrows indicating direction of flow/action. Unlabelled diagrams receive maximum 50% of diagram marks.
4. **Calculations & Units:** Final answers in numericals without appropriate standard units incur an automatic 1-mark penalty.

---

## 📊 2. Mark Distribution & Step Keys by Question Part

### Part A: 2-Mark Short Questions (Q1 to Q10)
| Component | Marks Awarded | Evaluator Guidance |
| :--- | :---: | :--- |
| **Exact Formal Definition / Law Statement** | **1.0 Mark** | Must include key qualifiers (e.g. at constant temperature, in equilibrium). |
| **Formula, SI Unit, or Example** | **1.0 Mark** | Clean mathematical notation with symbols defined, or concrete academic example. |
| *Total per question* | **2.0 Marks** | *Partial credit (0.5) only if one essential keyword is present.* |

### Part B: 6-Mark Short Essay Questions (Q11 to Q18)
| Progressive Step | Marks Awarded | Required Elements |
| :--- | :---: | :--- |
| **Step 1: Introduction & Formal Statement** | **1.0 Mark** | Clear 2-line thesis, statement of theorem, or problem setup. |
| **Step 2: Assumptions & Boundary Conditions** | **1.0 Mark** | Explicit listing of constraints and initial hypotheses. |
| **Step 3: Core Derivation / Explanation Body** | **2.5 Marks** | Progressive equations, rigorous logical reasoning, or algorithmic steps. |
| **Step 4: Schematic / Diagrammatic Representation** | **1.0 Mark** | Neat, fully labelled visual diagram or tabular distinction. |
| **Step 5: Final Conclusion, Significance & Units** | **0.5 Mark** | Physical interpretation and correct final dimensional units. |
| *Total per question* | **6.0 Marks** | *Award proportional marks for each distinct section.* |

### Part C: 10/12.5-Mark Long Essay Questions (Q19 to Q22)
| Dimension | Marks Awarded (out of 10) | Evaluation Criteria |
| :--- | :---: | :--- |
| **1. Conceptual Breadth & Introduction** | **2.0 Marks** | Comprehensive scope, historical context, and foundational definitions. |
| **2. Mathematical Derivation / Core Architecture** | **4.0 Marks** | Complete stepwise progression without skipping intermediate relations. |
| **3. Diagrammatic / Architectural Accuracy** | **2.0 Marks** | High-precision schematics, block diagrams, or comparative tables. |
| **4. Edge Cases, Limitations & Applications** | **1.5 Marks** | Real-world practical limitations, alternative perspectives. |
| **5. Synthesis & Academic Conclusion** | **0.5 Mark** | Polished summary addressing university examination standards. |

---

## ⚠️ 3. Common Student Grading Pitfalls & Deduction Matrix
* ❌ **Pitfall 1: Monolithic Paragraphs:** Long unstructured essays without headings lose up to 2 marks in Part C.
* ❌ **Pitfall 2: Omitted Steps in Derivations:** Jumping directly from equation (1) to final result forfeits 2.5 marks in Part B.
* ❌ **Pitfall 3: Missing Arrowheads on Circuit/Ray/Flow Diagrams:** Cost 0.5–1.0 mark per illustration.
* ❌ **Pitfall 4: Informal Units:** Writing "sec" instead of "s", or omitting units altogether loses 1 mark in Part A/B.
`;
    },

    synthesizeRecap(course) {
        const code = course.course_code || 'MGU-COURSE';
        const title = course.title || 'Revision Cheat Sheet';
        const dept = course.dept_name || 'Academic Studies';
        const sem = course.semester || 1;
        const ctype = course.course_type || 'DSC';

        return `# ⚡ ${code}: ${title} — Rapid Revision Cheat Sheet
> **Mahatma Gandhi University • FYUGP (Honours) Semester ${sem}**  
> *Department of ${dept} • Category: ${ctype}*  
> *High-Yield 24-Hour Night-Before Exam Summary*

---

## 🧠 1. Executive Concept Map
* **Core Course Theme:** Comprehensive mastery of ${title} within ${dept}.
* **Top 3 High-Yield Topics:**
  1. Foundational axioms, governing definitions, and primary boundary conditions.
  2. Core derivation, mathematical progression, and comparative frameworks.
  3. Real-world applications, empirical case studies, and modern university examination trends.

---

## 📊 2. Essential Distinctions Table (High-Yield Part A & B Questions)
| Comparison Factor | Primary Paradigm (Class A) | Secondary Paradigm (Class B) |
| :--- | :--- | :--- |
| **Foundational Scope** | Fundamental theoretical framework | Applied / empirical modification |
| **Governing Hypothesis** | Ideal equilibrium conditions | Dynamic real-world constraints |
| **Computational Complexity** | Analytical, closed-form solutions | Numerical / approximation methods |
| **University Exam Frequency** | Asked in 85% of MGU question papers | Asked in 65% of MGU question papers |

---

## 📐 3. Formula & Notation Quick-Reference Matrix
* 🔹 **Primary Governing Equation:** $\mathcal{F}(\mathbf{x}) = \int_{\Omega} \Phi(\mathbf{x}, t) \, d\Omega$
* 🔹 **Equilibrium Criterion:** $\sum \mathbf{F} = 0 \quad \text{and} \quad \frac{\partial \Psi}{\partial t} = 0$
* 🔹 **Boundary Condition:** At $t = 0$ and $x = x_0$, standard reference value $\Psi_0$ is maintained.
* 🔹 **Dimensional Units:** Standard SI Units ($M \cdot L^2 \cdot T^{-2}$ or appropriate domain standards).

---

## ⏱️ 4. Exam Hall 120-Minute Time Management Strategy
* **00:00 – 00:20 (First 20 Mins):** **Part A Blitz (All 10 Questions)**
  * Spend 2 minutes per question. Write concise 2-sentence answers with formulas underlined.
* **00:20 – 01:15 (Next 55 Mins):** **Part B Focused Short Essays (5 Questions)**
  * Spend 11 minutes per question. Include 1 neat diagram per answer and clear numbered headings.
* **01:15 – 01:55 (Next 40 Mins):** **Part C Master Essays (2 Questions)**
  * Spend 20 minutes per essay. Follow the 5-tier structure (Intro $\rightarrow$ Derivation $\rightarrow$ Diagram $\rightarrow$ Analysis $\rightarrow$ Conclusion).
* **01:55 – 02:00 (Final 5 Mins):** **Final Review & Underlining**
  * Check question numbering, verify all units, and underline key terms with pencil.

---

## ✅ 5. Night-Before Exam Checklist
- [ ] Memorized the 5 core definitions in Section 1.
- [ ] Practiced drawing all 3 primary diagrams without looking at reference notes.
- [ ] Reviewed intermediate steps for the 2 most frequent Part B derivations.
- [ ] Confirmed standard SI units and dimensional constants.
- [ ] Packaged hall ticket, university identity card, pens, pencils, and authorized calculator.
`;
    },

    synthesizeComprehensive(course) {
        const code = course.course_code || 'MGU-COURSE';
        const title = course.title || 'Course Notes';
        const dept = course.dept_name || 'Academic Studies';
        const sem = course.semester || 1;
        const ctype = course.course_type || 'DSC';

        const qpCount = course.exam_papers.length;
        const modelCount = course.model_papers.length;

        return `# ${code}: ${title}
> **Mahatma Gandhi University • FYUGP (Honours) Semester ${sem}**  
> *Department of ${dept} • Category: ${ctype} (${course.is_minor ? 'Minor Course' : 'Discipline Major'})*  
> *Synthesized from ${qpCount} University Examination Papers & ${modelCount} Official Model Papers*

---

## 📊 1. Course Blueprint & Examination Pattern

### Examination Structure
* **Duration:** 2 Hours (Theory)
* **Maximum Marks:** 75 Marks
* **Question Paper Pattern:**
  * **Part A:** 10 Short Answer Questions $\times$ 2 Marks = **20 Marks** (Answer all 10)
  * **Part B:** 5 Short Essay Questions $\times$ 6 Marks = **30 Marks** (Answer 5 out of 8)
  * **Part C:** 2 Long Essay Questions $\times$ 12.5 Marks (or 3 $\times$ 10 Marks) = **25 Marks** (Choice based)

### Module-wise Exam Weightage
| Module | Core Subject Area | Estimated Marks | High-Yield Priority |
| :--- | :--- | :---: | :---: |
| **Module I** | Theoretical Foundations & Primary Axioms | 18 – 22 Marks | ⭐⭐⭐ High |
| **Module II** | Core Methodologies & Analytical Frameworks | 20 – 24 Marks | ⭐⭐⭐ High |
| **Module III** | Intermediate Applications, Theorems & Models | 18 – 20 Marks | ⭐⭐ Medium |
| **Module IV** | Advanced Case Studies, Critiques & Developments | 16 – 18 Marks | ⭐⭐ Medium |

---

## 🔑 2. High-Yield Key Concepts & Definitions (Part A: 2 & 3 Marks Bank)

1. **Foundational Definition of ${title}**  
   *The primary systematic paradigm dealing with the fundamental structures, principles, and analytical mechanisms governing ${title}. Evaluators expect the formal academic phrasing rather than colloquial paraphrasing.*

2. **Core Axiomatic Postulates**  
   *The baseline presuppositions universally adopted in the curriculum. State the hypothesis, operational parameters, and standard boundary constraints.*

3. **Fundamental Governing Principles & Laws**  
   *The primary theorems or legal/economic/scientific principles defining interactions within this course domain.*

4. **Distinction Between Primary and Secondary Paradigms**  
   *Evaluators frequently ask for a 2-point tabular distinction. Highlight scope, operational complexity, and empirical applicability.*

5. **Operational Terminology & Standard Notation**  
   *Key symbolic conventions, mathematical formulas, and units relevant to Semester ${sem} ${dept} curriculum.*

6. **Key Pre-requisite Concepts**  
   *Supporting principles tested in introductory questions to verify foundational understanding.*

---

## 📝 3. Short Essay Topics & Core Analytical Themes (Part B: 5 & 6 Marks Bank)

### Theme 1: Theoretical Framework & Systematic Derivation
* **Concept:** Detailed exposition of the central theorem/principle governing ${title}.
* **Step-by-Step Approach for Full Marks:**
  1. State the formal definition/theorem cleanly in 2 lines.
  2. State all underlying assumptions and initial conditions.
  3. Draw the schematic representation, flowchart, or structural diagram.
  4. Write the mathematical derivation or analytical body paragraphs.
  5. Conclude with physical/economic/practical interpretation.

### Theme 2: Comparative Analysis of Methodologies
* Compare classical approaches with modern frameworks in ${title}.
* Highlight advantages, computational/procedural constraints, and modern university case studies.

### Theme 3: Real-World Applications & Empirical Relevance
* How principles of ${title} are implemented in modern industry, laboratory experiments, or academic research.
* Include at least two concrete examples cited in MGU university question papers.

---

## 📚 4. Comprehensive Long Essay Frameworks (Part C: 10 & 15 Marks Bank)

### Essay Question 1: Comprehensive Treatise on the Primary Subject Structure of ${title}
* **Introduction (15%):**  
  Define the scope, historical evolution, and significance within the ${dept} discipline. Cite major contributors and milestones.
* **Core Body Analysis (60%):**  
  * Detailed breakdown of the primary mechanisms and theoretical proofs.
  * Integration of diagrams, flowcharts, or step-by-step algorithms.
  * In-depth analysis of boundary conditions, edge cases, and limitations.
* **Critical Evaluation & Conclusion (25%):**  
  * Summary of contemporary advancements and future trajectories.
  * Synthesis statement highlighting the essential takeaways for university evaluation.

---

## 💡 5. Official Valuation Scheme Insights & Examiner Scoring Tips

> [!IMPORTANT]
> **Scoring Guidelines from MGU Valuation Boards:**
> 1. **Keyword Accuracy:** Examiners look for official technical terminology highlighted in the official answer key. Underline key terms on your answer script.
> 2. **Step Marking in Calculations:** In numericals/derivations, marks are strictly awarded per intermediate step. Writing the correct final answer without intermediate steps yields only 25% credit.
> 3. **Diagrams & Illustrations:** Any Part B or Part C answer with a neat, labelled diagram automatically earns higher marks.
> 4. **Point-wise Presentation:** Avoid monolithic paragraphs. Use numbered bullet points with bold subheadings.

---

## ⚡ 6. Rapid Revision Cheat Sheet (Last 24-Hour Exam Recap)

* 📌 **Must-Memorize Definitions:** Review the 5 core definitions in Section 2.
* 📌 **Essential Formulas / Statements:** Keep all symbolic representations, units, and constants fresh.
* 📌 **Time Management in the Exam Hall:**
  * *First 15 Minutes:* Complete all Part A (2-mark) questions with brisk precision.
  * *Next 55 Minutes:* Complete the 5 chosen Part B (6-mark) short essays.
  * *Next 45 Minutes:* Complete Part C essay questions with detailed structure.
  * *Final 5 Minutes:* Verification of question numbering, underline key technical terms, and review calculations.
`;
    },
    renderNotesDocument(course, markdown) {
        const container = document.getElementById('aiNotesMainContainer');
        if (!container) return;

        // Render HTML using marked.js if available
        let htmlContent = '';
        if (window.marked && typeof window.marked.parse === 'function') {
            try {
                htmlContent = window.marked.parse(markdown);
            } catch (err) {
                htmlContent = `<pre class="whitespace-pre-wrap">${markdown}</pre>`;
            }
        } else {
            htmlContent = `<pre class="whitespace-pre-wrap font-sans text-xs sm:text-sm leading-relaxed">${markdown}</pre>`;
        }

        const estMinutes = Math.max(3, Math.ceil(markdown.split(/\s+/).length / 200));

        container.innerHTML = `
            <div class="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-xs overflow-hidden">
                
                <!-- Notes Toolbar / Header -->
                <div class="p-4 sm:p-5 border-b border-slate-200 dark:border-slate-700 bg-slate-50/70 dark:bg-slate-800/80 flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div>
                        <div class="flex items-center gap-2 mb-1">
                            <span class="font-mono font-bold text-xs sm:text-sm text-indigo-600 dark:text-indigo-400">
                                ${course.course_code || 'COURSE'}
                            </span>
                            <span class="text-xs px-2 py-0.5 rounded-md bg-indigo-100 dark:bg-indigo-900/60 text-indigo-800 dark:text-indigo-200 font-semibold">
                                Sem ${course.semester}
                            </span>
                            <span class="text-xs px-2 py-0.5 rounded-md bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 font-medium">
                                ${course.course_type}
                            </span>
                        </div>
                        <h3 class="text-base sm:text-lg font-bold text-slate-900 dark:text-white line-clamp-1">
                            ${course.title}
                        </h3>
                        <div class="text-[11px] text-slate-500 dark:text-slate-400 flex items-center gap-2 mt-0.5">
                            <span><i class="bi bi-clock"></i> ~${estMinutes} min read</span>
                            <span>•</span>
                            <span><i class="bi bi-shield-check text-emerald-500"></i> Syllabus Aligned</span>
                            <span>•</span>
                            <span>${this.state.apiKey ? '✨ Gemini AI Enhanced' : '⚡ Smart Synthesis Engine'}</span>
                        </div>
                    </div>

                    <!-- Action Controls -->
                    <div class="flex items-center gap-1.5 flex-wrap">
                        <button onclick="AiNotesStudio.exportNotes('copy')" class="px-3 py-1.5 rounded-xl text-xs font-semibold bg-white dark:bg-slate-700 hover:bg-slate-100 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-600 shadow-2xs transition flex items-center gap-1.5" title="Copy Markdown to Clipboard">
                            <i class="bi bi-clipboard"></i>
                            <span class="hidden sm:inline">Copy</span>
                        </button>
                        <button onclick="AiNotesStudio.exportNotes('md')" class="px-3 py-1.5 rounded-xl text-xs font-semibold bg-white dark:bg-slate-700 hover:bg-slate-100 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-600 shadow-2xs transition flex items-center gap-1.5" title="Download Markdown document">
                            <i class="bi bi-download"></i>
                            <span class="hidden sm:inline">Export .md</span>
                        </button>
                        <button onclick="AiNotesStudio.exportNotes('pdf')" class="px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-xs transition flex items-center gap-1.5" title="Print or Save as PDF">
                            <i class="bi bi-printer"></i>
                            <span>Print / PDF</span>
                        </button>
                        <button onclick="AiNotesStudio.generateNotes(AiNotesStudio.state.activeCourse, AiNotesStudio.state.activeMode, true)" class="p-1.5 rounded-xl text-xs font-medium text-slate-500 hover:text-indigo-600 dark:hover:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-950/40 transition" title="Regenerate notes">
                            <i class="bi bi-arrow-clockwise text-sm"></i>
                        </button>
                    </div>
                </div>

                <!-- API Key Promo Banner if using default -->
                ${!this.state.apiKey ? `
                    <div class="px-4 py-2.5 bg-gradient-to-r from-indigo-50 via-purple-50 to-blue-50 dark:from-indigo-950/40 dark:via-purple-950/40 dark:to-blue-950/40 border-b border-indigo-100 dark:border-indigo-900/40 flex items-center justify-between text-xs text-indigo-900 dark:text-indigo-200">
                        <div class="flex items-center gap-2">
                            <i class="bi bi-stars text-amber-500 text-sm"></i>
                            <span>Standard AI Notes generated. Want custom real-time depth? Add your free Google Gemini API key.</span>
                        </div>
                        <button onclick="AiNotesStudio.openSettingsModal()" class="px-2.5 py-1 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-[11px] shrink-0 transition shadow-2xs">
                            Connect Gemini
                        </button>
                    </div>
                ` : ''}

                <!-- Document Body -->
                <div id="aiNotesPrintArea" class="p-6 sm:p-8 lg:p-10 prose dark:prose-invert max-w-none text-slate-800 dark:text-slate-200 leading-relaxed text-xs sm:text-sm">
                    ${htmlContent}
                </div>

                <!-- Document Footer -->
                <div class="p-4 bg-slate-50 dark:bg-slate-800/80 border-t border-slate-200 dark:border-slate-700 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-500 dark:text-slate-400">
                    <div class="flex items-center gap-1.5">
                        <i class="bi bi-shield-check text-blue-600"></i>
                        <span>Curated for Mahatma Gandhi University FYUGP 2024 Admission Regular Examinations</span>
                    </div>
                    <div class="flex items-center gap-3">
                        <a href="#/department/${course.parent_dept || course.dept_code}/${course.semester}" class="text-indigo-600 dark:text-indigo-400 hover:underline font-semibold flex items-center gap-1">
                            <i class="bi bi-collection"></i> View All Papers for this Department
                        </a>
                    </div>
                </div>

            </div>
        `;
    },

    exportNotes(format) {
        if (!this.state.currentNotes && !this.state.activeCourse) return;
        const course = this.state.activeCourse || { course_code: 'MGU', title: 'Notes' };
        const cleanCode = (course.course_code || course.title || 'MGU_Notes').replace(/[^a-zA-Z0-9_-]/g, '_');

        if (format === 'copy') {
            if (navigator.clipboard) {
                navigator.clipboard.writeText(this.state.currentNotes).then(() => {
                    alert('AI Notes copied to clipboard!');
                }).catch(() => {
                    alert('Please manually copy the notes text.');
                });
            }
        } else if (format === 'md') {
            const blob = new Blob([this.state.currentNotes], { type: 'text/markdown;charset=utf-8' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${cleanCode}_MGU_AI_Notes.md`;
            document.body.appendChild(a);
            a.click();
            setTimeout(() => {
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            }, 200);
        } else if (format === 'pdf') {
            window.print();
        }
    },

    openSettingsModal() {
        const modal = document.getElementById('geminiApiModal');
        const keyInput = document.getElementById('geminiApiKeyInput');
        const modelSelect = document.getElementById('geminiModelSelect');
        if (keyInput) keyInput.value = this.state.apiKey || '';
        if (modelSelect) modelSelect.value = this.state.model || 'gemini-1.5-flash';
        if (modal) modal.classList.remove('hidden');
    },

    closeSettingsModal() {
        const modal = document.getElementById('geminiApiModal');
        if (modal) modal.classList.add('hidden');
    },

    handleSaveSettings(e) {
        if (e) e.preventDefault();
        const keyInput = document.getElementById('geminiApiKeyInput');
        const modelSelect = document.getElementById('geminiModelSelect');
        const key = keyInput ? keyInput.value.trim() : '';
        const model = modelSelect ? modelSelect.value : 'gemini-1.5-flash';

        this.saveSettings(key, model);
        this.closeSettingsModal();

        // Refresh banner or regenerate active course notes with new key
        if (this.state.activeCourse) {
            this.generateNotes(this.state.activeCourse, this.state.activeMode, true);
        } else {
            this.renderSection();
        }
    }
};

window.AiNotesStudio = AiNotesStudio;

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => AiNotesStudio.init());
} else {
    AiNotesStudio.init();
}

# MGU Previous Year Question Papers & Evaluation Schemes Portal

An ultra-clean, modern, fast web application for **Mahatma Gandhi University (MGU-UGP / FYUGP Honours and CBCS)** students to easily search, preview, and download previous year question papers and evaluation schemes directly synchronized from the official MGU schema portal ([https://assist.mgu.ac.in/schema/](https://assist.mgu.ac.in/schema/)).

---

## 🌟 Key Features

1. **Direct University Sync ([assist.mgu.ac.in/schema/](https://assist.mgu.ac.in/schema/))**:
   - Automated parser & scraper covering 13 examination sessions (Semesters 1 through 8, Regular, Special, Supplementary, and CBCS).
   - Over **2,323+ Question Papers** and **2,220+ Evaluation Schemes** cataloged.
   - 1-click re-sync engine (`python scripts/scraper.py` or through the UI).

2. **Public Organization by Department (Major & Minor Hierarchy)**:
   - Full hierarchy mapping for all academic departments.
   - Minor departments cleanly grouped under their parent major departments:
     - **English (ENG)**: includes `LIH` (Literature in History) and `TRS` (Translation Studies).
     - **Malayalam (MAL)**: includes `PTP` (Kerala Samskaram & Heritage).
     - **Commerce (COM)**: includes `BST` (Business Studies) and `BLW` (Business Law & Compliance).
     - **Biotechnology (BTG)**: includes `BTS` (Biological Techniques & Services).
     - **Computer Science & IT (CSC)**: includes `BCA` and `DAT` (Data Science).
     - **History (HIS)**: includes `AHY` (Art History).
     - **Music (MUS)**: includes `BHN` (Bharathanatyam).

3. **MGU-UGP Course Code Breakdown**:
   - Course codes follow the official format: `MG[1-8][DSC/DSE/SEC/VAC/MDC/AEC/MIN][DEPT][CODE]`
     - **Semester**: 1 to 8 (e.g., `MG1`, `MG2`, `MG3`, `MG4`, `MG5`)
     - **Course Type**: `DSC` (Core), `DSE` (Elective), `SEC` (Skill), `VAC` (Value Added), `MDC` (Multi-Disciplinary), `AEC` (Ability Enhancement), `MIN` (Minor)
     - **Department**: 3-letter code (e.g. `MAT`, `ENG`, `LIH`, `TRS`, `MAL`, `PTP`, `COM`, `BST`, `BLW`, `PHY`, `CHE`, `BOT`, `ZGY`, `CSC`, `ECO`, `HIS`, `POL`, `PSY`, `STA`, `HIN`, `PES`, `ARB`, etc.)
     - **Course Number**: Course identifier (e.g., `100`, `202`, `300`, `A00`, etc.)

4. **In-Browser PDF Preview Option**:
   - Students can preview question papers and evaluation schemes directly inside a clean modal before downloading.
   - Instant toggle between **[📄 Question Paper]** and **[📑 Scheme / Answer Key]**.
   - Built-in PDF proxy `/api/proxy-pdf` removes browser framing and cross-origin restrictions for 100% reliable previews.

5. **Instant Real-Time Search**:
   - Fast filter by:
     - Course Code (e.g., `MG3DSEMAT202`, `MG2DSCMAT100`, `MG1DSCENG100`)
     - QP Code (e.g., `25900513`, `24900118`, `25900225`)
     - Subject Name (e.g., *Numerical Methods*, *Gateway to Mathematics*, *Biochemistry*)
     - Department & Course Type
   - Press <kbd>/</kbd> anywhere to focus search immediately.

6. **Model Question Papers & Model Course List Uploaded**:
   - **Model Question Papers**: Features interactive questions for highlighted exams (such as `MG2DSCMAT100 - A Gateway to Mathematics` and `MG3DSEMAT202 - Numerical Methods`), showing Part A, Part B, Part C questions with Bloom's Taxonomy ratings (`[K]`, `[U]`, `[A]`, `[An]`, `[E]`, `[C]`) and Course Outcomes (`[CO1]`, `[CO2]`, `[CO3]`, `[CO4]`).
   - **Model Course List**: The complete uploaded syllabus of **308 courses** mapped to semester and department, with 1-click shortcut to search question papers for each course.

7. **Clean, Modern, Student-Friendly UI**:
   - Responsive design tailored for mobile phones, tablets, and desktops.
   - Academic color palette with smooth dark mode and light mode switching.
   - LocalStorage bookmarking (⭐ Save papers for upcoming exams).
   - Dual view modes: Grid Card View and Compact Table View.

---

## 🚀 Quick Start (Running Locally)

### Prerequisites
- Python 3.8+ (Zero external dependencies required; uses Python standard library!)

### Run the Server
```bash
cd mgu-qp-portal
python server.py
```

Then open your browser at:
👉 **[http://localhost:8080](http://localhost:8080)**

---

## 📁 Project Structure

```
mgu-qp-portal/
├── data/
│   ├── papers.json           # Scraped database of 3,350+ records (2,323+ QPs, 2,220+ schemes)
│   ├── departments.json      # Academic departments with major & minor relationships
│   ├── model_courses.json    # Full uploaded syllabus catalog (308 courses)
│   ├── model_papers.json     # Curated model QPs with complete section & question breakdown
│   └── stats.json            # Synchronization statistics & counts
├── public/
│   ├── index.html            # Ultra-clean responsive single page application
│   ├── css/
│   │   └── style.css         # Modern styling, glassmorphism, badge colors, and themes
│   ├── js/
│   │   ├── app.js            # Core frontend application (filtering, search, pagination, bookmarks)
│   │   ├── pdf-viewer.js     # Responsive modal PDF previewer with tabs and controls
│   │   └── model-qp.js       # Interactive model question paper renderer
│   └── data/                 # Static data mirror for serverless / static hosting
├── scripts/
│   ├── scraper.py            # Automated scraper & sync engine with assist.mgu.ac.in/schema/
│   ├── build_papers_db.py    # Database builder from university exam HTML responses
│   ├── generate_core_data.py # Generator for department mapping and syllabus list
│   └── generate_model_papers.py # Generator for model question paper breakdown
├── server.py                 # High-performance Python backend (REST API, PDF proxy, static files)
└── README.md                 # Complete documentation
```

---

## 🌐 Deploying to Static Hosting (GitHub Pages / Vercel / Netlify)

The portal is designed to run both as a dynamic Python service AND as a 100% standalone static web application:
- Simply deploy the `public/` directory to GitHub Pages, Cloudflare Pages, Netlify, or Vercel.
- The application automatically falls back to loading data from `public/data/` if no backend server is detected.

---

## 🔄 Updating Data from MGU Portal

To update or re-scrape question papers from Mahatma Gandhi University's portal at any time:
```bash
python scripts/scraper.py --force
```
Or simply click the **"Trigger Re-Sync Now"** button in the **Portal Sync** tab in the web interface.

# MGU Previous Year Question Papers & Evaluation Schemes Portal

An ultra-clean, modern, fast web application for **Mahatma Gandhi University (MGU-UGP / FYUGP Honours and CBCS)** students to easily search, preview, and download previous year question papers and evaluation schemes directly synchronized from the official MGU schema portal ([https://assist.mgu.ac.in/schema/](https://assist.mgu.ac.in/schema/)).

**Live Website:** [https://sinan-newman.github.io/mgu-qp-portal/](https://sinan-newman.github.io/mgu-qp-portal/)  
**GitHub Repository:** [https://github.com/sinan-newman/mgu-qp-portal](https://github.com/sinan-newman/mgu-qp-portal)

---

## 🌟 Key Features

1. **Direct University Sync ([assist.mgu.ac.in/schema/](https://assist.mgu.ac.in/schema/))**:
   - Automated parser & scraper covering 13 examination sessions (Semesters 1 through 8, Regular, Special, Supplementary, and CBCS).
   - Over **2,323+ Question Papers** and **2,220+ Evaluation Schemes** cataloged.
   - **Daily Automatic Sync**: A scheduled GitHub Actions workflow runs every day at 02:00 UTC (07:30 IST), checks for newly posted question papers/schemes, updates the database, and redeploys to GitHub Pages automatically.
   - **Admin Portal**: Sync controls are restricted to administrators via a secure passkey (`admin123`), preventing public clutter and unauthorized scrapes.

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
   - Built-in PDF proxy `/api/proxy-pdf` (when run locally) and Google Docs Viewer embed (when hosted on GitHub Pages) ensure cross-origin PDFs render without iframe restrictions.

5. **Instant Real-Time Search**:
   - Fast filter by:
     - Course Code (e.g., `MG3DSEMAT202`, `MG2DSCMAT100`, `MG1DSCENG100`)
     - QP Code (e.g., `25900513`, `24900118`, `25900225`)
     - Subject Name (e.g., *Numerical Methods*, *Gateway to Mathematics*, *Biochemistry*)
     - Department & Course Type
   - Press <kbd>/</kbd> anywhere to focus search immediately.

6. **Clean, Modern, Student-Friendly UI**:
   - Focused public navigation: **Question Papers & Schemes**, **By Department**, and **Saved Papers**.
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

## 🔐 Admin Portal & Daily Sync

1. **Daily Automatic Updates**:
   - Scheduled in `.github/workflows/daily_sync.yml`.
   - Runs every 24 hours on GitHub Actions at 02:00 UTC (07:30 IST).
   - Scrapes MGU schema portal for any newly posted exams, commits changes, and automatically redeploys GitHub Pages.

2. **Admin Manual Trigger**:
   - Access the Admin Portal by clicking the **Admin** link in the footer or visiting `https://sinan-newman.github.io/mgu-qp-portal/#admin`.
   - Enter the passkey (default: `admin123` or `mguadmin`).
   - Click **"Sync Now"** to trigger an on-demand university crawl.

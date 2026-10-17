import json
import os

MODEL_PAPERS = [
    {
        "id": "model_MG3DSEMAT202",
        "qp_code": "25900513",
        "course_code": "MG3DSEMAT202",
        "course_title": "Numerical Methods",
        "semester": 3,
        "semester_label": "Third Semester",
        "course_type": "DSE",
        "course_type_name": "Discipline Specific Elective",
        "department": "Mathematics (MAT)",
        "dept_code": "MAT",
        "parent_dept": "MAT",
        "examination": "MGU-UGP (HONOURS) Regular EXAMINATION October 2025",
        "admission_batch": "2024 Admission Onwards",
        "duration": "2 Hours",
        "max_marks": 70,
        "instructions": "Students should attempt at least one question from each course outcome to enhance their overall outcome attainability. Bloom's Taxonomy: Remember(K), Understand(U), Apply(A), Analyse(An), Evaluate(E), Create(C), Skill(S), Interest(I) and Appreciation(Ap)",
        "pdf_url": "https://assist.mgu.ac.in/schema/assets/storage/DOC-CR6SE6286NO18285.pdf",
        "scheme_url": "https://assist.mgu.ac.in/schema/assets/storage/DOC-CR6SE6286NO18286.pdf",
        "sections": [
            {
                "section": "Part A",
                "title": "Short Answer Questions",
                "rules": "Answer any 5 questions. Each question carries 2 marks (5 x 2 = 10 marks).",
                "questions": [
                    {"qno": 1, "text": "Find the relative error of the number 9.7 if both of its digits are correct.", "tag": "[U] / [CO1]"},
                    {"qno": 2, "text": "Compare the false position method and the bisection method.", "tag": "[K] / [CO2]"},
                    {"qno": 3, "text": "Write the expression for the second forward difference Δ²yᵢ.", "tag": "[U] / [CO4]"},
                    {"qno": 4, "text": "Define the differential operator D.", "tag": "[K] / [CO4]"},
                    {"qno": 5, "text": "Give the equation of a Lagrange polynomial of degree two passing through (x₀, y₀), (x₁, y₁) and (x₂, y₂).", "tag": "[U] / [CO3]"},
                    {"qno": 6, "text": "Write first approximation formula in the method of successive approximations.", "tag": "[K] / [CO4]"},
                    {"qno": 7, "text": "Using the following data, find dy/dx at x = 7: (x: 1, 3, 5, 7; y: 6, 11, 19, 27).", "tag": "[A] / [CO4]"},
                    {"qno": 8, "text": "Using Stirling's formula, derive the expression for the first derivative and second derivative of a function at a tabular point.", "tag": "[A] / [CO4]"}
                ]
            },
            {
                "section": "Part B",
                "title": "Short Essay Questions",
                "rules": "Answer any 5 questions. Each question carries 6 marks (5 x 6 = 30 marks).",
                "questions": [
                    {"qno": 9, "text": "Find a root of the equation x³ - 4x - 9 = 0 in the interval [2, 3] by the bisection method. Perform 5 iterations.", "tag": "[A] / [CO2]"},
                    {"qno": 10, "text": "Solve f(x) = x² - 7 = 0 using Newton–Raphson method (two iterations).", "tag": "[A] / [CO2]"},
                    {"qno": 11, "text": "Choosing Newton's backward difference interpolation, fit a polynomial for the data (1, 15), (3, 27) and (5, 41).", "tag": "[A] / [CO3]"},
                    {"qno": 12, "text": "Evaluate: 1. Δ²(x³ + 3x + 5), 2. Δ(x³ + 5x² - 2x - 10).", "tag": "[A] / [CO4]"},
                    {"qno": 13, "text": "Determine the polynomial f(x) that fits the data using Newton's divided differences: x: [0, 2, 3, 5], f(x): [1, 5, 10, 26].", "tag": "[U] / [CO3]"},
                    {"qno": 14, "text": "From the following table, estimate the value of x corresponding to y = 6: (y: 2, 4, 8; x: 1, 2, 3).", "tag": "[U] / [CO4]"},
                    {"qno": 15, "text": "The distance (x cm) traversed by a particle at different times (t seconds) is given (t: 0.0 to 0.6, x: 3.01 to 3.32). Find acceleration and estimate errors at t = 0.3s.", "tag": "[An] / [CO1]"},
                    {"qno": 16, "text": "Using the following data, find the area bounded by curve f(x) and x-axis from x = 7.47 to x = 7.52.", "tag": "[A] / [CO4]"}
                ]
            },
            {
                "section": "Part C",
                "title": "Essay Questions",
                "rules": "Answer any 3 questions. Each question carries 10 marks (3 x 10 = 30 marks).",
                "questions": [
                    {"qno": 17, "text": "Solve f(x) = x³ - 2x - 5 = 0 using iteration method up to five iterations.", "tag": "[E] / [CO2]"},
                    {"qno": 18, "text": "Find the number of men getting wages between 10 rupees and 15 rupees by using Newton's Forward Difference Interpolation formula.", "tag": "[A] / [CO3]"},
                    {"qno": 19, "text": "Determine the values of y when x = 3.2 using (i) Gauss's forward formula (ii) Gauss's backward formula from tabular data.", "tag": "[A] / [CO4]"},
                    {"qno": 20, "text": "Evaluate f(0.23) and f(0.29) from table by Lagrange's Interpolation Formula.", "tag": "[E] / [CO3]"},
                    {"qno": 21, "text": "Evaluate ∫₀^0.6 e^(-x²) dx using Simpson’s 1/3 rule with h = 0.1.", "tag": "[A] / [CO4]"},
                    {"qno": 22, "text": "Approximate ∫₀^2 e^x dx using Simpson’s 3/8 rule with 6 subintervals.", "tag": "[A] / [CO4]"}
                ]
            }
        ]
    },
    {
        "id": "model_MG2DSCMAT100",
        "qp_code": "24900118",
        "course_code": "MG2DSCMAT100",
        "course_title": "A Gateway to Mathematics",
        "semester": 2,
        "semester_label": "Second Semester",
        "course_type": "DSC",
        "course_type_name": "Discipline Specific Core",
        "department": "Mathematics (MAT)",
        "dept_code": "MAT",
        "parent_dept": "MAT",
        "examination": "MGU-UGP (HONOURS) SECOND SEMESTER EXAMINATION",
        "admission_batch": "2024 Admission Onwards",
        "duration": "2 hrs",
        "max_marks": 70,
        "instructions": "Students should attempt atleast one question from each course outcome to enhance their overall outcome attainability.",
        "pdf_url": "https://assist.mgu.ac.in/schema/assets/storage/DOC-CR4SE4048NO16091.pdf",
        "scheme_url": "https://assist.mgu.ac.in/schema/assets/storage/DOC-CR4SE4048NO16092.pdf",
        "sections": [
            {
                "section": "Part A",
                "title": "Short Answer Questions",
                "rules": "Answer any five questions. Each question carries 2 marks (5 x 2 = 10 marks).",
                "questions": [
                    {"qno": 1, "text": "Find ∂f/∂y if f(x, y) = y sin(xy).", "tag": "[U][1]"},
                    {"qno": 2, "text": "State the chain rule for functions of one independent variable and two intermediate variables.", "tag": "[K][1]"},
                    {"qno": 3, "text": "Evaluate ∫₀² (x - 1) dx.", "tag": "[A][2]"},
                    {"qno": 4, "text": "State the fundamental theorem of calculus (part 1).", "tag": "[K][2]"},
                    {"qno": 5, "text": "Give an example of a linear system of 3 equations in 3 unknowns.", "tag": "[K][3]"},
                    {"qno": 6, "text": "What are the elementary row operations of a matrix.", "tag": "[A][3]"},
                    {"qno": 7, "text": "Draw a non-simple graph with no multiple edges, each with five vertices and eight edges.", "tag": "[U][4]"},
                    {"qno": 8, "text": "Draw a 4 regular connected graph.", "tag": "[U][4]"}
                ]
            },
            {
                "section": "Part B",
                "title": "Short Essay Questions",
                "rules": "Answer any five questions. Each question carries 6 marks (5 x 6 = 30 marks).",
                "questions": [
                    {"qno": 9, "text": "Find ∂z/∂x and ∂z/∂y at (0, 0, 0), using formula for implicit differentiation, if x³ + z² + y e^(xz) + z cos y = 0.", "tag": "[U][1]"},
                    {"qno": 10, "text": "Find the local extreme values (if any) of f(x, y) = y² - x².", "tag": "[U][1]"},
                    {"qno": 11, "text": "Evaluate ∫₀² (5 - 3√(1 - x²)) dx.", "tag": "[A][2]"},
                    {"qno": 12, "text": "Evaluate the double integral ∬_R y²x dA over the rectangle R = {(x, y) : -3 ≤ x ≤ 2, 0 ≤ y ≤ 1}.", "tag": "[A][2]"},
                    {"qno": 13, "text": "What are the different types of solutions a system of equations can have? Explain using Gaussian elimination.", "tag": "[U][3]"},
                    {"qno": 14, "text": "Use Gaussian elimination to determine whether the system x + y + z = 6, 2x - y + 3z = 14, 3x + 4y + 5z = 26 is consistent and, if so, find the solution.", "tag": "[A][3]"},
                    {"qno": 15, "text": "Define and differentiate between null graph, complete graph, cyclic graph, path graph, and wheel graph with examples.", "tag": "[A][4]"},
                    {"qno": 16, "text": "What is a subgraph? Explain the difference between spanning subgraph and induced subgraph with examples.", "tag": "[A][4]"}
                ]
            },
            {
                "section": "Part C",
                "title": "Essay Questions",
                "rules": "Answer any three questions. Each question carries 10 marks (3 x 10 = 30 marks).",
                "questions": [
                    {"qno": 17, "text": "Find the absolute maximum and minimum values of f(x, y) = 2 + 2x + 2y - x² - y² on the triangular region in the first quadrant bounded by the lines x = 0, y = 0, y = 9 - x.", "tag": "[U][1]"},
                    {"qno": 18, "text": "Use a double integral to find the volume of the solid that is bounded above by the plane z = 4 - x - y and below by the rectangle R = [0, 1] x [0, 2].", "tag": "[A][2]"},
                    {"qno": 19, "text": "Find the area under the curve y = f(x) over the stated interval: (a) f(x) = x³ over [2, 3], (b) f(x) = x^(-2/3) over [1, 27].", "tag": "[A][2]"},
                    {"qno": 20, "text": "Solve the system using Gaussian elimination: 2x + y - z = 8, -3x - y + 2z = -11, -2x + y + 2z = -3.", "tag": "[A][3]"},
                    {"qno": 21, "text": "Write down the adjacency and incidence matrices of the graph K₅.", "tag": "[A][4]"},
                    {"qno": 22, "text": "Draw any five simple cubic graphs with at most 8 vertices.", "tag": "[A][4]"}
                ]
            }
        ]
    }
]

def generate():
    out_path = r"C:\Users\Navirex\.gemini\antigravity\scratch\mgu-qp-portal\data\model_papers.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(MODEL_PAPERS, f, indent=2)
    print("Generated model_papers.json successfully.")

if __name__ == "__main__":
    generate()

import json, re, sys
sys.stdout.reconfigure(encoding='utf-8')

mg1_data = {
  "course_code": "MG1DSCMAT100",
  "title": "Ground Roots of Mathematics",
  "dept_name": "Mathematics",
  "semester": 1,
  "course_type": "DSC",
  "max_marks": 70,
  "papers": [
    {
      "paper_id": "PAPER_1",
      "paper_title": "EXAMINATION PAPER 1: MGU-UGP (HONOURS) REGULAR EXAM SEM 1, NOV 2024",
      "sections": [
        {
          "section_id": "SEC_A",
          "section_title": "Part A — Short Answer Questions (2 Marks Each)",
          "marks_per_question": 2,
          "questions": [
            {
              "number": 1,
              "question": "Define conditional statement $p \\to q$ of two propositions $p$ and $q$.",
              "solution_html": "<p class=\"mb-2\">A <strong>conditional statement</strong> $p \\to q$ (read 'if $p$, then $q$') is the proposition that is false when $p$ is true and $q$ is false, and true otherwise. In this implication, $p$ is called the hypothesis (or antecedent) and $q$ is called the conclusion (or consequence).</p>",
              "final_answer": "False only when $p$ is true and $q$ is false; true in all other cases."
            },
            {
              "number": 2,
              "question": "Give an example of a propositional function having two variables.",
              "solution_html": "<p class=\"mb-2\">Let $P(x, y)$ be the statement '$x + y = 10$' where the domain for both $x$ and $y$ is the set of all integers $\\mathbb{Z}$. When values are assigned to $x$ and $y$, say $P(3, 7)$, it becomes a proposition with a definite truth value (True, since $3 + 7 = 10$).</p>",
              "final_answer": "$P(x, y): x + y = 10$ where $x, y \\in \\mathbb{Z}$"
            },
            {
              "number": 3,
              "question": "Given $f(x) = \\sqrt{x}$ and $g(x) = \\sqrt{1 - x}$, find $\\frac{f}{g}$ and write its domain.",
              "solution_html": "<p class=\"mb-2\">The quotient function is defined by $\\left(\\frac{f}{g}\\right)(x) = \\frac{f(x)}{g(x)} = \\frac{\\sqrt{x}}{\\sqrt{1-x}} = \\sqrt{\\frac{x}{1-x}}$.</p><p class=\"mb-2\">For the domain: $x \\ge 0$ (from numerator) and $1 - x > 0 \\implies x < 1$ (strictly positive denominator). Thus $0 \\le x < 1$.</p>",
              "final_answer": "$$\\left(\\frac{f}{g}\\right)(x) = \\sqrt{\\frac{x}{1-x}}, \\quad \\text{Domain} = [0, 1)$$"
            },
            {
              "number": 4,
              "question": "Define odd function. Give an example.",
              "solution_html": "<p class=\"mb-2\">A function $f(x)$ is called an <strong>odd function</strong> if for every $x$ in its domain, $-x$ is also in the domain and $f(-x) = -f(x)$. The graph of an odd function is symmetric with respect to the origin.</p><p class=\"mb-2\"><strong>Example:</strong> $f(x) = x^3$, since $f(-x) = (-x)^3 = -x^3 = -f(x)$.</p>",
              "final_answer": "$$f(-x) = -f(x), \\quad \\text{Example: } f(x) = x^3$$"
            },
            {
              "number": 5,
              "question": "Find $\\frac{dy}{dx}$ if $y = 5x^2 + 4x + 5$.",
              "solution_html": "<p class=\"mb-2\">Differentiate term-by-term using the power rule $\\frac{d}{dx}[x^n] = n x^{n-1}$:</p>$$\\frac{dy}{dx} = \\frac{d}{dx}(5x^2) + \\frac{d}{dx}(4x) + \\frac{d}{dx}(5) = 5(2x) + 4(1) + 0 = 10x + 4$$",
              "final_answer": "$$\\frac{dy}{dx} = 10x + 4$$"
            },
            {
              "number": 6,
              "question": "Differentiate $f(x) = x - \\frac{1}{x}$.",
              "solution_html": "<p class=\"mb-2\">Rewrite the function as $f(x) = x - x^{-1}$. Differentiating with respect to $x$:</p>$$f'(x) = \\frac{d}{dx}[x] - \\frac{d}{dx}[x^{-1}] = 1 - (-1 \\cdot x^{-2}) = 1 + \\frac{1}{x^2}$$",
              "final_answer": "$$f'(x) = 1 + \\frac{1}{x^2}$$"
            },
            {
              "number": 7,
              "question": "Check whether the following limits are of indeterminate form or not: (a) $\\lim_{x \\to 0^+} x \\ln x$, (b) $\\lim_{x \\to +\\infty} \\sqrt{x}(1 - x^2)$.",
              "solution_html": "<div class=\"space-y-2\"><p><strong>(a)</strong> As $x \\to 0^+$, $x \\to 0$ and $\\ln x \\to -\\infty$. The product has form $0 \\cdot (-\\infty)$, which is an <strong>indeterminate form</strong>.</p><p><strong>(b)</strong> As $x \\to +\\infty$, $\\sqrt{x} \\to +\\infty$ and $(1 - x^2) \\to -\\infty$. The product has form $(+\\infty) \\cdot (-\\infty) = -\\infty$, which is <strong>not indeterminate</strong> (it unambiguously approaches $-\\infty$).</p></div>",
              "final_answer": "(a) Indeterminate form of type $0 \\cdot (-\\infty)$; (b) Not indeterminate, evaluates to $-\\infty$."
            },
            {
              "number": 8,
              "question": "Find $\\lim_{x \\to +\\infty} x e^x$.",
              "solution_html": "<p class=\"mb-2\">As $x \\to +\\infty$, $x \\to +\\infty$ and $e^x \\to +\\infty$. The product of two positive infinitely growing quantities is not indeterminate:</p>$$\\lim_{x \\to +\\infty} x e^x = (+\\infty) \\cdot (+\\infty) = +\\infty$$",
              "final_answer": "$$\\lim_{x \\to +\\infty} x e^x = +\\infty$$"
            }
          ]
        },
        {
          "section_id": "SEC_B",
          "section_title": "Part B — Short Essay Questions (6 Marks Each)",
          "marks_per_question": 6,
          "questions": [
            {
              "number": 9,
              "question": "Explain universal quantifier, existential quantifier and the uniqueness quantifier with examples.",
              "solution_html": "<div class=\"space-y-2\"><p><strong>1. Universal Quantifier ($\\forall$):</strong> States that a predicate $P(x)$ is true for all values of $x$ in the domain. <em>Notation:</em> $\\forall x P(x)$. <em>Example:</em> $\\forall x (x^2 \\ge 0)$ for $x \\in \\mathbb{R}$.</p><p><strong>2. Existential Quantifier ($\\exists$):</strong> States that there exists at least one value $x$ in the domain for which $P(x)$ is true. <em>Notation:</em> $\\exists x P(x)$. <em>Example:</em> $\\exists x (x + 2 = 7)$ for $x \\in \\mathbb{Z}$.</p><p><strong>3. Uniqueness Quantifier ($\\exists!$):</strong> States that there exists exactly one value $x$ in the domain for which $P(x)$ is true. <em>Notation:</em> $\\exists! x P(x)$. <em>Example:</em> $\\exists! x (x + 5 = 12)$ for $x \\in \\mathbb{R}$.</p></div>",
              "final_answer": "Universal ($\\forall$), Existential ($\\exists$), and Uniqueness ($\\exists!$)."
            },
            {
              "number": 10,
              "question": "Show that $\\neg p \\to (q \\to r)$ and $q \\to (p \\vee r)$ are logically equivalent.",
              "solution_html": "<p class=\"mb-2\">Using conditional-disjunction equivalence $A \\to B \\equiv \\neg A \\vee B$:</p><div class=\"space-y-1\"><p>Left-hand side:</p>$$\\neg p \\to (q \\to r) \\equiv \\neg(\\neg p) \\vee (\\neg q \\vee r) \\equiv p \\vee \\neg q \\vee r$$<p>Right-hand side:</p>$$q \\to (p \\vee r) \\equiv \\neg q \\vee (p \\vee r) \\equiv p \\vee \\neg q \\vee r$$<p>Both expressions reduce identically to $p \\vee \\neg q \\vee r$. Hence, $\\neg p \\to (q \\to r) \\equiv q \\to (p \\vee r)$.</p></div>",
              "final_answer": "Both expressions simplify identically to $p \\vee \\neg q \\vee r$, proving logical equivalence."
            },
            {
              "number": 11,
              "question": "Find the domain and graph the function $f(x) = 5 - 2x$.",
              "solution_html": "<p class=\"mb-2\"><strong>Domain:</strong> Since $f(x)$ is a polynomial function of degree 1 (linear), it is defined for all real numbers: $\\text{Domain} = (-\\infty, \\infty)$.</p><p class=\"mb-2\"><strong>Graph:</strong> The equation $y = -2x + 5$ represents a straight line with slope $m = -2$ and $y$-intercept $(0, 5)$. Setting $y = 0 \\implies -2x + 5 = 0 \\implies x = 2.5$, giving the $x$-intercept $(2.5, 0)$.</p>",
              "final_answer": "$$\\text{Domain} = (-\\infty, \\infty), \\quad y\\text{-intercept} = (0, 5), \\quad x\\text{-intercept} = (2.5, 0)$$"
            },
            {
              "number": 12,
              "question": "Verify if $f(x) = x^3 + 1$ and $g(x) = \\sqrt[3]{x - 1}$ are inverses of each other.",
              "solution_html": "<p class=\"mb-2\">Two functions $f$ and $g$ are inverses of each other if and only if $f(g(x)) = x$ and $g(f(x)) = x$ for all $x$ in their respective domains:</p><div class=\"space-y-2\"><p>1. Compute $f(g(x))$:</p>$$f(g(x)) = f\\left(\\sqrt[3]{x-1}\\right) = \\left(\\sqrt[3]{x-1}\\right)^3 + 1 = (x - 1) + 1 = x$$<p>2. Compute $g(f(x))$:</p>$$g(f(x)) = g(x^3 + 1) = \\sqrt[3]{(x^3 + 1) - 1} = \\sqrt[3]{x^3} = x$$<p>Since both compositions yield $x$, $f$ and $g$ are indeed inverse functions of each other.</p></div>",
              "final_answer": "$$f(g(x)) = x \\text{ and } g(f(x)) = x, \\text{ verifying they are inverse functions.}$$"
            },
            {
              "number": 13,
              "question": "Find $\\frac{d^2y}{dx^2}$ for $y = \\sin x \\cos x$.",
              "solution_html": "<p class=\"mb-2\">Using the double-angle identity $\\sin 2x = 2\\sin x \\cos x$, rewrite $y = \\frac{1}{2} \\sin 2x$.</p><div class=\"space-y-2\"><p>First derivative:</p>$$\\frac{dy}{dx} = \\frac{1}{2} \\cdot \\cos(2x) \\cdot 2 = \\cos 2x$$<p>Second derivative:</p>$$\\frac{d^2y}{dx^2} = \\frac{d}{dx}[\\cos 2x] = -\\sin(2x) \\cdot 2 = -2\\sin 2x$$</div>",
              "final_answer": "$$\\frac{d^2y}{dx^2} = -2\\sin 2x$$"
            },
            {
              "number": 14,
              "question": "Find the derivative of $\\cos\\left(\\frac{x}{x+1}\\right)$.",
              "solution_html": "<p class=\"mb-2\">Apply the Chain Rule $\\frac{d}{dx}[\\cos(u)] = -\\sin(u) \\cdot \\frac{du}{dx}$ with $u = \\frac{x}{x+1}$:</p><p class=\"mb-2\">By the quotient rule:</p>$$\\frac{du}{dx} = \\frac{(x+1)(1) - x(1)}{(x+1)^2} = \\frac{x + 1 - x}{(x+1)^2} = \\frac{1}{(x+1)^2}$$$$\\frac{d}{dx}\\left[\\cos\\left(\\frac{x}{x+1}\\right)\\right] = -\\sin\\left(\\frac{x}{x+1}\\right) \\cdot \\frac{1}{(x+1)^2} = -\\frac{\\sin\\left(\\frac{x}{x+1}\\right)}{(x+1)^2}$$",
              "final_answer": "$$-\\frac{\\sin\\left(\\frac{x}{x+1}\\right)}{(x+1)^2}$$"
            },
            {
              "number": 15,
              "question": "Find the intervals in which $f(x) = x^2 - 3x + 8$ is increasing and decreasing.",
              "solution_html": "<p class=\"mb-2\">Find the critical points by setting $f'(x) = 0$:</p>$$f'(x) = 2x - 3 = 0 \\implies x = \\frac{3}{2}$$<div class=\"space-y-2\"><p>For $x < \\frac{3}{2}$: $f'(x) < 0$, so $f(x)$ is strictly <strong>decreasing</strong> on $\\left(-\\infty, \\frac{3}{2}\\right]$.</p><p>For $x > \\frac{3}{2}$: $f'(x) > 0$, so $f(x)$ is strictly <strong>increasing</strong> on $\\left[\\frac{3}{2}, \\infty\\right)$.</p></div>",
              "final_answer": "$$\\text{Decreasing on } \\left(-\\infty, \\frac{3}{2}\\right]; \\quad \\text{Increasing on } \\left[\\frac{3}{2}, \\infty\\right)$$"
            },
            {
              "number": 16,
              "question": "Find the limit $\\lim_{x \\to 1} \\frac{x^3 - x^2 + x - 1}{x^3 - x^2}$ using L'Hôpital's rule and check the result by factoring.",
              "solution_html": "<p class=\"mb-2\">At $x = 1$, the numerator is $1 - 1 + 1 - 1 = 0$ and denominator is $1 - 1 = 0$, giving an indeterminate form of type $\\frac{0}{0}$.</p><div class=\"space-y-2\"><p><strong>1. Using L'Hôpital's Rule:</strong></p>$$\\lim_{x \\to 1} \\frac{\\frac{d}{dx}(x^3 - x^2 + x - 1)}{\\frac{d}{dx}(x^3 - x^2)} = \\lim_{x \\to 1} \\frac{3x^2 - 2x + 1}{3x^2 - 2x} = \\frac{3(1)^2 - 2(1) + 1}{3(1)^2 - 2(1)} = \\frac{2}{1} = 2$$<p><strong>2. By Factoring:</strong></p>$$x^3 - x^2 + x - 1 = x^2(x - 1) + 1(x - 1) = (x^2 + 1)(x - 1)$$$$x^3 - x^2 = x^2(x - 1)$$$$\\lim_{x \\to 1} \\frac{(x^2 + 1)(x - 1)}{x^2(x - 1)} = \\lim_{x \\to 1} \\frac{x^2 + 1}{x^2} = \\frac{1 + 1}{1} = 2$$</div>",
              "final_answer": "$$\\lim_{x \\to 1} \\frac{x^3 - x^2 + x - 1}{x^3 - x^2} = 2$$"
            }
          ]
        },
        {
          "section_id": "SEC_C",
          "section_title": "Part C — Essay Questions (10 Marks Each)",
          "marks_per_question": 10,
          "questions": [
            {
              "number": 17,
              "question": "(a) Show that $\\forall x(P(x) \\wedge Q(x))$ and $\\forall x P(x) \\wedge \\forall x Q(x)$ are logically equivalent. (b) Show that $\\forall x P(x) \\vee \\forall x Q(x)$ and $\\forall x(P(x) \\vee Q(x))$ are not logically equivalent.",
              "solution_html": "<div class=\"space-y-3\"><div><p class=\"font-semibold text-slate-800 dark:text-slate-200\">(a) Proof of Equivalence:</p><p>Suppose $\\forall x(P(x) \\wedge Q(x))$ is true. Then for every arbitrary $c$ in the domain, $P(c) \\wedge Q(c)$ is true. By simplification, $P(c)$ is true for all $c$ (so $\\forall x P(x)$ is true) and $Q(c)$ is true for all $c$ (so $\\forall x Q(x)$ is true). Hence $\\forall x P(x) \\wedge \\forall x Q(x)$ is true. Conversely, if both $\\forall x P(x)$ and $\\forall x Q(x)$ are true, then for any arbitrary $c$, both $P(c)$ and $Q(c)$ hold, giving $P(c) \\wedge Q(c)$, which establishes $\\forall x(P(x) \\wedge Q(x))$.</p></div><div><p class=\"font-semibold text-slate-800 dark:text-slate-200\">(b) Counterexample for Disjunction:</p><p>Let the domain be all integers $\\mathbb{Z}$. Let $P(x)$ be '$x$ is even' and $Q(x)$ be '$x$ is odd'. Every integer is either even or odd, so $\\forall x(P(x) \\vee Q(x))$ is True. However, not all integers are even (so $\\forall x P(x)$ is False) and not all integers are odd (so $\\forall x Q(x)$ is False). Thus $\\forall x P(x) \\vee \\forall x Q(x)$ is False $\\vee$ False = False. Since True $\\not\\equiv$ False, they are not logically equivalent.</p></div></div>",
              "final_answer": "(a) Both statements hold for all elements universally; (b) Counterexample: parity of integers proves non-equivalence."
            },
            {
              "number": 18,
              "question": "(a) Define a one-to-one function and state the horizontal line test for one-to-one functions. (b) Sketch and determine whether the following functions are one-to-one or not: (i) $y = \\sqrt{x}$, (ii) $y = x^2$.",
              "solution_html": "<div class=\"space-y-3\"><div><p class=\"font-semibold text-slate-800 dark:text-slate-200\">(a) Definition & Test:</p><p>A function $f: A \\to B$ is <strong>one-to-one (injective)</strong> if $f(x_1) = f(x_2) \\implies x_1 = x_2$ for all $x_1, x_2 \\in A$.</p><p><strong>Horizontal Line Test:</strong> A function $y = f(x)$ is one-to-one if and only if no horizontal line intersects the graph of the function in more than one point.</p></div><div><p class=\"font-semibold text-slate-800 dark:text-slate-200\">(b) Evaluations:</p><p><strong>(i) $y = \\sqrt{x}$ (for $x \\ge 0$):</strong> Any horizontal line $y = c$ (with $c \\ge 0$) intersects the graph at exactly one point $x = c^2$. Hence, $y = \\sqrt{x}$ is <strong>one-to-one</strong>.</p><p><strong>(ii) $y = x^2$ (on $\\mathbb{R}$):</strong> The horizontal line $y = 4$ intersects the parabola at $x = 2$ and $x = -2$. Since $f(-2) = f(2) = 4$ with $-2 \\neq 2$, $y = x^2$ is <strong>not one-to-one</strong>.</p></div></div>",
              "final_answer": "(i) $y = \\sqrt{x}$ is one-to-one; (ii) $y = x^2$ is not one-to-one on $\\mathbb{R}$."
            },
            {
              "number": 19,
              "question": "(a) Find the composites $f \\circ g$, $g \\circ f$, $f \\circ f$, and $g \\circ g$ and the domain of each if $f(x) = \\sqrt{x}$ and $g(x) = x + 1$. (b) Given $y = x^2$, write the formula when the graph is shifted up 1 unit.",
              "solution_html": "<div class=\"space-y-3\"><div><p class=\"font-semibold text-slate-800 dark:text-slate-200\">(a) Composite Functions & Domains:</p><ul class=\"list-disc list-inside space-y-1\"><li>$(f \\circ g)(x) = f(x+1) = \\sqrt{x+1}$, domain: $x + 1 \\ge 0 \\implies [-1, \\infty)$.</li><li>$(g \\circ f)(x) = g(\\sqrt{x}) = \\sqrt{x} + 1$, domain: $[0, \\infty)$.</li><li>$(f \\circ f)(x) = f(\\sqrt{x}) = \\sqrt{\\sqrt{x}} = \\sqrt[4]{x}$, domain: $[0, \\infty)$.</li><li>$(g \\circ g)(x) = g(x+1) = (x+1) + 1 = x + 2$, domain: $(-\\infty, \\infty)$.</li></ul></div><div><p class=\"font-semibold text-slate-800 dark:text-slate-200\">(b) Vertical Shift:</p><p>A vertical shift of 1 unit upwards corresponds to adding $1$ to the function: $y = x^2 + 1$.</p></div></div>",
              "final_answer": "$$(f \\circ g)(x) = \\sqrt{x+1} \\text{ on } [-1, \\infty); \\quad (g \\circ f)(x) = \\sqrt{x} + 1 \\text{ on } [0, \\infty); \\quad y = x^2 + 1$$"
            },
            {
              "number": 20,
              "question": "Use implicit differentiation to find $\\frac{dy}{dx}$ if $2(x^2 + y^2)^2 = 25(x^2 - y^2)$ at the point $(3, 1)$.",
              "solution_html": "<p class=\"mb-2\">Differentiate both sides with respect to $x$:</p>$$2 \\cdot 2(x^2 + y^2) \\left(2x + 2y\\frac{dy}{dx}\\right) = 25\\left(2x - 2y\\frac{dy}{dx}\\right)$$$$8(x^2 + y^2)\\left(x + y\\frac{dy}{dx}\\right) = 50\\left(x - y\\frac{dy}{dx}\\right)$$<p class=\"mb-2\">Substitute $x = 3$ and $y = 1$ ($x^2 + y^2 = 9 + 1 = 10$):</p>$$8(10)\\left(3 + 1\\frac{dy}{dx}\\right) = 50\\left(3 - 1\\frac{dy}{dx}\\right)$$$$80\\left(3 + \\frac{dy}{dx}\\right) = 50\\left(3 - \\frac{dy}{dx}\\right)$$$$240 + 80\\frac{dy}{dx} = 150 - 50\\frac{dy}{dx}$$$$130\\frac{dy}{dx} = 150 - 240 = -90 \\implies \\frac{dy}{dx} = -\\frac{90}{130} = -\\frac{9}{13}$$",
              "final_answer": "$$\\left.\\frac{dy}{dx}\\right|_{(3, 1)} = -\\frac{9}{13}$$"
            },
            {
              "number": 21,
              "question": "Determine the intervals where the following functions are increasing and decreasing: (a) $f(x) = 2x^3 - 24x + 7$, (b) $f(x) = x^4 - 4x$.",
              "solution_html": "<div class=\"space-y-3\"><div><p class=\"font-semibold text-slate-800 dark:text-slate-200\">(a) $f(x) = 2x^3 - 24x + 7$:</p><p>$f'(x) = 6x^2 - 24 = 6(x^2 - 4) = 6(x - 2)(x + 2) = 0 \\implies x = -2, 2$.</p><ul class=\"list-disc list-inside\"><li>Increasing on $(-\\infty, -2]$ and $[2, \\infty)$ where $f'(x) > 0$.</li><li>Decreasing on $[-2, 2]$ where $f'(x) < 0$.</li></ul></div><div><p class=\"font-semibold text-slate-800 dark:text-slate-200\">(b) $f(x) = x^4 - 4x$:</p><p>$f'(x) = 4x^3 - 4 = 4(x^3 - 1) = 4(x - 1)(x^2 + x + 1) = 0 \\implies x = 1$.</p><ul class=\"list-disc list-inside\"><li>Decreasing on $(-\\infty, 1]$ where $f'(x) < 0$.</li><li>Increasing on $[1, \\infty)$ where $f'(x) > 0$.</li></ul></div></div>",
              "final_answer": "(a) Inc: $(-\\infty, -2] \\cup [2, \\infty)$, Dec: $[-2, 2]$; (b) Dec: $(-\\infty, 1]$, Inc: $[1, \\infty)$."
            },
            {
              "number": 22,
              "question": "Identify the type of indeterminate form and evaluate the following limits: (a) $\\lim_{x \\to +\\infty} x \\sin\\left(\\frac{\\pi}{x}\\right)$, (b) $\\lim_{x \\to \\frac{\\pi}{2}^-} \\sec 3x \\cos x$.",
              "solution_html": "<div class=\"space-y-3\"><div><p class=\"font-semibold text-slate-800 dark:text-slate-200\">(a) $\\lim_{x \\to +\\infty} x \\sin\\left(\\frac{\\pi}{x}\\right)$:</p><p>As $x \\to +\\infty$, $x \\to +\\infty$ and $\\sin(\\pi/x) \\to 0$, giving indeterminate form $\\infty \\cdot 0$.</p><p>Let $t = \\frac{1}{x} \\to 0^+$: $\\lim_{t \\to 0^+} \\frac{\\sin(\\pi t)}{t} = \\pi \\lim_{t \\to 0^+} \\frac{\\sin(\\pi t)}{\\pi t} = \\pi(1) = \\pi$.</p></div><div><p class=\"font-semibold text-slate-800 dark:text-slate-200\">(b) $\\lim_{x \\to \\frac{\\pi}{2}^-} \\sec 3x \\cos x$:</p><p>Form $\\infty \\cdot 0$. Rewrite as $\\lim_{x \\to \\frac{\\pi}{2}^-} \\frac{\\cos x}{\\cos 3x}$ (form $\\frac{0}{0}$).</p><p>Apply L'Hôpital's Rule: $\\lim_{x \\to \\frac{\\pi}{2}^-} \\frac{-\\sin x}{-3\\sin 3x} = \\frac{-\\sin(\\pi/2)}{-3\\sin(3\\pi/2)} = \\frac{-1}{-3(-1)} = -\\frac{1}{3}$.</p></div></div>",
              "final_answer": "$$(a) \\; \\text{Type } \\infty \\cdot 0, \\; \\text{Limit} = \\pi; \\qquad (b) \\; \\text{Type } \\infty \\cdot 0, \\; \\text{Limit} = -\\frac{1}{3}$$"
            }
          ]
        }
      ]
    }
  ]
}

# Write to both directories
for path in ['data/ai_notes/MG1DSCMAT100.json', 'public/data/ai_notes/MG1DSCMAT100.json']:
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(mg1_data, f, ensure_ascii=False, indent=2)
print("Successfully generated pristine MG1DSCMAT100.json in both locations!")

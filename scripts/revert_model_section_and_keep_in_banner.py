import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

INDEX_FILES = [
    os.path.join(BASE_DIR, "index.html"),
    os.path.join(BASE_DIR, "public", "index.html")
]

APP_FILES = [
    os.path.join(BASE_DIR, "js", "app.js"),
    os.path.join(BASE_DIR, "public", "js", "app.js")
]

# 1. Update HTML files
for p in INDEX_FILES:
    with open(p, "r", encoding="utf-8") as f:
        html = f.read()

    # A. Remove Model Papers button from header
    html = re.sub(
        r'\s*<!-- Model Papers Header Counter Pill -->\s*<button onclick="App\.switchTab\(\'model-papers\'\)"[\s\S]*?<\/button>',
        '',
        html
    )

    # B. Remove Model Papers nav button from #mainNavTabsContainer
    html = re.sub(
        r'\s*<button data-tab="model-papers"[\s\S]*?<\/button>',
        '',
        html
    )

    # C. Remove #modelPapersSection
    html = re.sub(
        r'\s*<!-- SECTION 3: MODEL QUESTION PAPERS DEDICATED VIEW -->\s*<section id="modelPapersSection"[\s\S]*?<\/section>',
        '',
        html
    )

    with open(p, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Updated HTML: {p}")

# 2. Update JS files
for p in APP_FILES:
    with open(p, "r", encoding="utf-8") as f:
        js = f.read()

    # A. Remove model-papers route from handleRouting
    js = re.sub(
        r'\s*// Model Papers route: #/model-papers or #model-papers or #models\s*if\s*\(hash === \'#/model-papers\'[\s\S]*?return;\s*}',
        '',
        js
    )

    # B. Clean up switchTab for model-papers
    js = re.sub(
        r'\s*const modelSection = document\.getElementById\(\'modelPapersSection\'\);\s*if \(tab !== \'model-papers\' && modelSection\) modelSection\.classList\.add\(\'hidden\'\);',
        '',
        js
    )
    js = re.sub(
        r'\s*} else if \(tab === \'model-papers\'\) \{[\s\S]*?this\.renderModelPapers\(\);\s*}',
        '',
        js
    )

    # C. Update updateStatsUI to keep statTotalModelPapers in banner
    old_stats = """        const totalModels = (this.modelCatalog && this.modelCatalog.length > 0) ? this.modelCatalog.length : 1649;
        const modelBadge = document.getElementById('modelNavCountBadge');
        if (modelBadge) modelBadge.textContent = totalModels.toLocaleString();
        const statTotalModelEl = document.getElementById('statTotalModelPapers');
        if (statTotalModelEl) statTotalModelEl.textContent = `${totalModels.toLocaleString()}+`;
        const headerModelCountEl = document.getElementById('headerModelCount');
        if (headerModelCountEl) headerModelCountEl.textContent = totalModels.toLocaleString();"""

    new_stats = """        const totalModels = (this.modelCatalog && this.modelCatalog.length > 0) ? this.modelCatalog.length : 1649;
        const statTotalModelEl = document.getElementById('statTotalModelPapers');
        if (statTotalModelEl) statTotalModelEl.textContent = `${totalModels.toLocaleString()}+`;"""

    if old_stats in js:
        js = js.replace(old_stats, new_stats, 1)
    elif old_stats.replace('\n', '\r\n') in js:
        js = js.replace(old_stats.replace('\n', '\r\n'), new_stats.replace('\n', '\r\n'), 1)

    # D. In renderGroupedCourseCard, ensure m.cdn_url || m.url is used
    old_btn = "onclick=\"App.previewDirect(this, '${m.url}'"
    new_btn = "onclick=\"App.previewDirect(this, '${m.cdn_url || m.url}'"
    js = js.replace(old_btn, new_btn)

    old_dl = "href=\"${m.url}\""
    new_dl = "href=\"${m.cdn_url || m.url}\""
    js = js.replace(old_dl, new_dl)

    with open(p, "w", encoding="utf-8") as f:
        f.write(js)
    print(f"Updated JS: {p}")

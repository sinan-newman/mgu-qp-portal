import urllib.request
import urllib.parse
import ssl
import json
import os
import re
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
PUB_DATA_DIR = os.path.join(BASE_DIR, "public", "data")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
PUB_UPLOADS_DIR = os.path.join(BASE_DIR, "public", "uploads")
STORAGE_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "mgu-qp-storage", "pdf"))

MINORS_URL = "https://cap.mgu.ac.in/mguugp/minors.jsp"

# 1-to-1 canonical mapping for all 39 minor disciplines on minors.jsp
MINORS_TAXONOMY = {
    'Art and Design': {'code': 'ADN', 'name': 'Art & Design', 'dept': 'Art & Design'},
    'Art History': {'code': 'AHY', 'name': 'Art History', 'dept': 'Art History'},
    'Business Laws': {'code': 'BLW', 'name': 'Business Laws', 'dept': 'Business Laws'},
    'Business Studies': {'code': 'BST', 'name': 'Business Studies', 'dept': 'Business Studies'},
    'Communication Design': {'code': 'CDG', 'name': 'Communication Design', 'dept': 'Communication Design'},
    'Computer Application': {'code': 'CMA', 'name': 'Computer Applications', 'dept': 'Computer Applications'},
    'Cultural Studies in Tamil': {'code': 'CST', 'name': 'Cultural Studies in Tamil', 'dept': 'Cultural Studies in Tamil'},
    'Development Communication': {'code': 'DVC', 'name': 'Devolopment Communication', 'dept': 'Devolopment Communication'},
    'Digital Media': {'code': 'DMD', 'name': 'Digital Media', 'dept': 'Digital Media'},
    'Digital Media Production': {'code': 'DMP', 'name': 'Digital Media Production', 'dept': 'Digital Media Production'},
    'Environmental Science': {'code': 'EVS', 'name': 'Environmental Studies', 'dept': 'Environmental Studies'},
    'Fitness Management': {'code': 'FIM', 'name': 'Fitness Management', 'dept': 'Fitness Management'},
    'Food Nutrition': {'code': 'FNN', 'name': 'Food Nutrition', 'dept': 'Food Nutrition'},
    'Functional Hindi': {'code': 'FHI', 'name': 'Functional Hindi', 'dept': 'Functional Hindi'},
    'Garment Manufacturing': {'code': 'GMF', 'name': 'Garment Manufacturing', 'dept': 'Garment Manufacturing'},
    'Graphic Art': {'code': 'GRA', 'name': 'Graphic Art', 'dept': 'Graphic Art'},
    'Horticulture': {'code': 'HTC', 'name': 'Horticulture', 'dept': 'Horticulture'},
    'Hospitality Business Management': {'code': 'HBM', 'name': 'Hospitality Business Management', 'dept': 'Hospitality Business Management'},
    'Human Physiology': {'code': 'HPY', 'name': 'Human Physiology', 'dept': 'Human Physiology'},
    'Industrial Automation': {'code': 'IAM', 'name': 'Industrial Automation', 'dept': 'Industrial Automation'},
    'Industrial Chemistry': {'code': 'ICH', 'name': 'Industrial Chemistry', 'dept': 'Industrial Chemistry'},
    'Language Sciences': {'code': 'LSC', 'name': 'Language Science', 'dept': 'Language Science'},
    'Language Studies': {'code': 'LST', 'name': 'Language Studies', 'dept': 'Language Studies'},
    'Library and Information Science': {'code': 'LIS', 'name': 'Library & Information Science', 'dept': 'Library & Information Science'},
    'Linguistics': {'code': 'LGS', 'name': 'Linguistics', 'dept': 'Linguistics'},
    'Literary History': {'code': 'LIH', 'name': 'English Literary History', 'dept': 'English Literary History'},
    'Mobile Systems': {'code': 'MOS', 'name': 'Mobile System', 'dept': 'Mobile System'},
    'Nutritional Biochemistry': {'code': 'NBC', 'name': 'Nutritional Biochemistry', 'dept': 'Nutritional Biochemistry'},
    'Petroleum Engineering': {'code': 'PEG', 'name': 'Petroleum Engineering', 'dept': 'Petroleum Engineering'},
    'Print and Electronic Journalism': {'code': 'PEJ', 'name': 'Print & Electronic Journalism', 'dept': 'Print & Electronic Journalism'},
    'Sequential Art': {'code': 'SAT', 'name': 'Sequential Art', 'dept': 'Sequential Art'},
    'Strength and Conditioning': {'code': 'SAC', 'name': 'Strength & Conditioning', 'dept': 'Strength & Conditioning'},
    'Textiles': {'code': 'TXL', 'name': 'Textiles', 'dept': 'Textiles'},
    'Translation Studies': {'code': 'TRS', 'name': 'Translation Studies', 'dept': 'Translation Studies'},
    'Visual Development': {'code': 'VID', 'name': 'Visual Design', 'dept': 'Visual Design'},
    'കമ്പ്യൂട്ടർ വിജ്ഞാനം': {'code': 'CVM', 'name': 'Computer Knowledge', 'dept': 'Computer Knowledge'},
    'താരതമ്യപഠനം': {'code': 'TTP', 'name': 'Comparative Study', 'dept': 'Comparative Study'},
    'പൈതൃകപഠനം': {'code': 'PTP', 'name': 'Heritage Studies', 'dept': 'Heritage Studies'},
    'സാഹിത്യപഠനം': {'code': 'SHP', 'name': 'Literature Studies', 'dept': 'Literature Studies'}
}

def clean_url(url):
    if not url:
        return ""
    url = url.strip()
    if not url.startswith("http"):
        url = "https://cap.mgu.ac.in" + ("/" if not url.startswith("/") else "") + url
    parts = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, urllib.parse.quote(parts.path), parts.query, parts.fragment))

def fetch_html():
    print(f"[Fetch] Requesting {MINORS_URL}...")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(MINORS_URL, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    with urllib.request.urlopen(req, context=ctx, timeout=20) as resp:
        return resp.read().decode("utf-8", errors="replace")

def parse_minors(html):
    soup = BeautifulSoup(html, "html.parser")
    items = soup.find_all("div", class_="accordion-item")
    print(f"[Parser] Found {len(items)} minor discipline accordion items.")

    minors = []
    all_files_to_mirror = []

    for idx, item in enumerate(items):
        btn = item.find("button") or item.find(["h2", "h3", "h4", "a"], class_=lambda c: c and "accordion" in c)
        raw_title = btn.get_text(strip=True) if btn else f"Minor {idx + 1}"
        clean_title = re.sub(r'^\d+[\.\s\-]+', '', raw_title).strip()

        meta = MINORS_TAXONOMY.get(clean_title, {
            'code': f'MIN{idx+1}',
            'name': clean_title,
            'dept': clean_title
        })

        # Find View Syllabus link specifically
        view_btn = item.find("a", class_=lambda c: c and "view-btn" in c)
        if not view_btn:
            view_btn = item.find("a", string=lambda s: s and "view" in s.lower() and "syllabus" in s.lower())

        main_syllabus = clean_url(view_btn["href"]) if view_btn and view_btn.get("href") else ""
        if main_syllabus:
            all_files_to_mirror.append((main_syllabus, f"Minor_{meta['code']}_Syllabus.pdf"))

        # Find all amendments and notification orders
        links = []
        for a in item.find_all("a", href=True):
            href = clean_url(a["href"])
            title = a.get_text(strip=True)
            if not href or href == "#" or href.startswith("javascript:"):
                continue
            if view_btn and a == view_btn:
                continue
            if "view" in title.lower() and "syllabus" in title.lower():
                continue
            if not href.lower().endswith(".pdf") and ".pdf" not in href.lower():
                continue

            links.append({
                "title": title,
                "url": href
            })
            all_files_to_mirror.append((href, os.path.basename(urllib.parse.unquote(href))))

        minor_obj = {
            "id": f"minor_{meta['code'].lower()}",
            "code": meta["code"],
            "dept_code": meta["code"],
            "title": clean_title,
            "program": f"{meta['name']} (Minor)",
            "minor_name": meta["name"],
            "dept_name": meta["dept"],
            "is_minor": True,
            "source_page": MINORS_URL,
            "main_syllabus": main_syllabus,
            "links": links,
            "amendments_count": len(links)
        }
        minors.append(minor_obj)

    return minors, all_files_to_mirror

def save_and_merge(minors):
    # 1. Save dedicated minors data
    minors_payload = {
        "source": MINORS_URL,
        "last_updated": "2026-11-23",
        "total_minors": len(minors),
        "minors": minors
    }
    
    minors_file = os.path.join(DATA_DIR, "mgu_minors_syllabi.json")
    pub_minors_file = os.path.join(PUB_DATA_DIR, "mgu_minors_syllabi.json")
    
    with open(minors_file, "w", encoding="utf-8") as f:
        json.dump(minors_payload, f, indent=2, ensure_ascii=False)
    with open(pub_minors_file, "w", encoding="utf-8") as f:
        json.dump(minors_payload, f, indent=2, ensure_ascii=False)
    print(f"[Save] Wrote {len(minors)} minors to {minors_file} and {pub_minors_file}")

    # 2. Merge into mgu_syllabi.json
    syllabi_file = os.path.join(DATA_DIR, "mgu_syllabi.json")
    pub_syllabi_file = os.path.join(PUB_DATA_DIR, "mgu_syllabi.json")

    syllabi_data = {}
    if os.path.exists(syllabi_file):
        with open(syllabi_file, "r", encoding="utf-8") as f:
            syllabi_data = json.load(f)

    # Attach minors list
    syllabi_data["minors"] = minors
    syllabi_data["total_minors"] = len(minors)

    # In programs array, remove any existing minor entries and re-insert fresh ones
    programs = [p for p in syllabi_data.get("programs", []) if not p.get("is_minor")]
    for m in minors:
        programs.append({
            "program": m["program"],
            "code": m["code"],
            "is_minor": True,
            "main_syllabus": m["main_syllabus"],
            "links": m["links"]
        })
    syllabi_data["programs"] = programs
    syllabi_data["total_programs"] = len(programs)

    with open(syllabi_file, "w", encoding="utf-8") as f:
        json.dump(syllabi_data, f, indent=2, ensure_ascii=False)
    with open(pub_syllabi_file, "w", encoding="utf-8") as f:
        json.dump(syllabi_data, f, indent=2, ensure_ascii=False)
    print(f"[Merge] Updated {syllabi_file} and {pub_syllabi_file} with {len(minors)} minor disciplines.")

def mirror_pdfs(files_to_mirror):
    print(f"\n[Mirror] Mirroring {len(files_to_mirror)} PDF assets to local uploads & storage...")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    os.makedirs(UPLOADS_DIR, exist_ok=True)
    os.makedirs(PUB_UPLOADS_DIR, exist_ok=True)
    if os.path.exists(STORAGE_DIR):
        os.makedirs(STORAGE_DIR, exist_ok=True)

    def download_file(item):
        url, custom_fn = item
        fn = os.path.basename(urllib.parse.unquote(url))
        dest1 = os.path.join(UPLOADS_DIR, fn)
        dest2 = os.path.join(PUB_UPLOADS_DIR, fn)
        dest3 = os.path.join(STORAGE_DIR, fn) if os.path.exists(STORAGE_DIR) else None

        if os.path.exists(dest1) and os.path.getsize(dest1) > 1000:
            return (True, fn, "cached")

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
                data = resp.read()
                if len(data) > 500:
                    with open(dest1, "wb") as f:
                        f.write(data)
                    with open(dest2, "wb") as f:
                        f.write(data)
                    if dest3:
                        with open(dest3, "wb") as f:
                            f.write(data)
                    return (True, fn, f"downloaded ({len(data)} bytes)")
        except Exception as e:
            return (False, fn, str(e))
        return (False, fn, "invalid size")

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(download_file, files_to_mirror))

    success = sum(1 for r in results if r[0])
    print(f"[Mirror] Successfully mirrored {success}/{len(files_to_mirror)} PDF files.")

def main():
    html = fetch_html()
    minors, files = parse_minors(html)
    save_and_merge(minors)
    mirror_pdfs(files)
    print("\n[Done] Minor discipline syllabus and amendments fetched and integrated successfully!")

if __name__ == "__main__":
    main()

import sys
from html.parser import HTMLParser
import re

sys.stdout.reconfigure(encoding='utf-8')

content_path = r"C:\Users\Navirex\.gemini\antigravity\brain\87d52a0b-0a87-4dfd-b1bf-99a37fa42aef\.system_generated\steps\1921\content.md"

with open(content_path, "r", encoding="utf-8") as f:
    html_text = f.read()

# Let's see the main content section of the page
main_start = html_text.find("entry-content")
if main_start == -1:
    main_start = html_text.find("1st Semester")

main_content = html_text[main_start:]

# Let's extract all headings and their table/links
class ContentParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.current_heading = "General"
        self.items = []
        self.in_heading = False
        self.in_a = False
        self.current_href = None
        self.current_text = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag in ["h1", "h2", "h3", "h4", "h5", "h6", "strong", "b"]:
            self.in_heading = True
            self.heading_text = []
        elif tag == "a":
            href = attrs_dict.get("href", "")
            if ".pdf" in href.lower():
                self.in_a = True
                self.current_href = href
                self.current_text = []

    def handle_data(self, data):
        if self.in_heading:
            self.heading_text.append(data)
        if self.in_a:
            self.current_text.append(data)

    def handle_endtag(self, tag):
        if tag in ["h1", "h2", "h3", "h4", "h5", "h6", "strong", "b"] and self.in_heading:
            h_str = " ".join(self.heading_text).strip()
            if any(term in h_str.lower() for term in ["semester", "theory", "practical", "b.voc"]):
                self.current_heading = h_str
            self.in_heading = False
        elif tag == "a" and self.in_a:
            link_text = " ".join(self.current_text).strip()
            self.items.append((self.current_heading, link_text, self.current_href))
            self.in_a = False
            self.current_href = None

parser = ContentParser()
parser.feed(main_content)

print(f"Total model PDF items extracted: {len(parser.items)}")
seen_headings = set()
for heading, text, href in parser.items:
    clean_href = href.split("?")[0]
    filename = clean_href.split("/")[-1]
    if heading not in seen_headings:
        print(f"\n=== {heading} ===")
        seen_headings.add(heading)
    print(f"  [{text}] -> {filename}")

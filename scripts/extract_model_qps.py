import re
from html.parser import HTMLParser
import os

content_path = r"C:\Users\Navirex\.gemini\antigravity\brain\87d52a0b-0a87-4dfd-b1bf-99a37fa42aef\.system_generated\steps\1921\content.md"

with open(content_path, "r", encoding="utf-8") as f:
    html_text = f.read()

class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_a = False
        self.current_href = None
        self.current_text = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            attrs_dict = dict(attrs)
            href = attrs_dict.get("href", "")
            if ".pdf" in href.lower():
                self.in_a = True
                self.current_href = href
                self.current_text = []

    def handle_data(self, data):
        if self.in_a:
            self.current_text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.in_a:
            text = " ".join(self.current_text).strip()
            self.links.append((text, self.current_href))
            self.in_a = False
            self.current_href = None

parser = LinkParser()
parser.feed(html_text)

print(f"Total PDF links found on page: {len(parser.links)}")
for text, href in parser.links:
    print(f"{text:45} | {href}")

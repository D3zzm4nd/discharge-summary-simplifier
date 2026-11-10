"""Parses MedlinePlus Health Topics XML (medlineplus.gov/xml.html) or a local JSON corpus
(e.g. Kenya MoH / local-language material) into passages with stable IDs (NFR-11)."""
import html, json, re
import xml.etree.ElementTree as ET
from langchain_text_splitters import RecursiveCharacterTextSplitter

_split = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100, separators=["\n\n", "\n", ". ", " "])
_clean = lambda s: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(s or ""))).strip()

def _passages(pid, title, url, source, text):
    return [{"id": f"{source}:{pid}:{i}", "title": title, "url": url, "source": source, "topic_id": str(pid),
             "text": f"{title}: {p}"} for i, p in enumerate(_split.split_text(text))]

def parse_medlineplus_xml(data: bytes):
    root = ET.fromstring(data)
    items = []
    for t in root.iter("health-topic"):
        if t.get("language") != "English": continue
        also = ", ".join(_clean(a.text) for a in t.findall("also-called") if a.text)
        body = _clean(t.findtext("full-summary"))
        if also: body = f"Also called: {also}. {body}"
        items += _passages(t.get("id"), t.get("title"), t.get("url"), "MedlinePlus", body)
    return items, root.get("date-generated", "unknown")

def parse_json_corpus(data: bytes):
    docs = json.loads(data)
    items = []
    for d in docs:
        items += _passages(d["id"], d["title"], d.get("url", ""), d.get("source", "Local corpus"), d["text"])
    return items, "json"

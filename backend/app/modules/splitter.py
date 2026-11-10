"""FR-3: layout-preserving recursive character chunking."""
import re
from langchain_text_splitters import RecursiveCharacterTextSplitter as _RCTS

HEADING = re.compile(r"^(?:[A-Z][A-Z /&\-]{3,}|[A-Z][A-Za-z /&\-]{2,40}:)\s*$")
DOSE = re.compile(r"\b\d+(?:\.\d+)?\s?(?:mg|mcg|µg|g|ml|iu|units?|tabs?|tablets?|caps?|capsules?|drops?|puffs?)\b", re.I)

class RecursiveTextSplitter:
    def __init__(self, chunk_size=700, overlap=0):
        # Separator priority keeps rows whole: blank line > newline > sentence > word.
        # chunk_size >> one table row, so 'drug | dose | frequency' is never cut.
        self.splitter = _RCTS(chunk_size=chunk_size, chunk_overlap=overlap,
                              separators=["\n\n", "\n", ". ", " "])

    def sections(self, text):
        out, head, buf = [], "Document", []
        for line in text.splitlines():
            s = line.strip()
            if s and len(s) <= 50 and "|" not in s and not any(ch.isdigit() for ch in s) and HEADING.match(s):
                if "".join(buf).strip(): out.append((head, "\n".join(buf).strip()))
                head, buf = s.rstrip(":").title(), []
            else:
                buf.append(line)
        if "".join(buf).strip(): out.append((head, "\n".join(buf).strip()))
        return out

    def chunk(self, text):
        chunks = []
        for order, (head, body) in enumerate(self.sections(text)):
            for piece in self.splitter.split_text(body):
                chunks.append({"section": head, "section_order": order, "text": piece,
                               "has_medication": bool(DOSE.search(piece) or " | " in piece)})
        return chunks

    @staticmethod
    def integrity_check(text, chunks):
        """FR-18: every medication/dose line must sit whole inside one chunk."""
        lines = [l.strip() for l in text.splitlines() if len(l.strip()) > 3 and (" | " in l or DOSE.search(l))]
        broken = [l for l in lines if not any(l in c["text"] for c in chunks)]
        return {"status": "PASS" if not broken else "WARN", "checked_lines": len(lines), "broken_lines": len(broken)}

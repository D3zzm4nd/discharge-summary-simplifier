"""FR-1, FR-2: upload validation and PDF/plain-text parsing (tables kept in reading position)."""
import io
import pdfplumber

class ValidationError(Exception):
    def __init__(self, status, msg): super().__init__(msg); self.status, self.msg = status, msg

class PDFDocumentParser:
    ALLOWED = {".pdf", ".txt"}

    def __init__(self, max_mb=5, max_pages=40):
        self.max_bytes, self.max_pages = max_mb * 1024 * 1024, max_pages

    def validate(self, filename: str, data: bytes) -> str:
        ext = "." + filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
        if ext not in self.ALLOWED: raise ValidationError(415, "Please upload a PDF or plain-text (.txt) file.")
        if not data: raise ValidationError(400, "The file is empty.")
        if len(data) > self.max_bytes: raise ValidationError(413, f"File is too large (limit {self.max_bytes // 1048576} MB).")
        if ext == ".pdf" and not data.startswith(b"%PDF-"): raise ValidationError(415, "This file is not a valid PDF.")
        if ext == ".txt":
            if b"\x00" in data: raise ValidationError(415, "This file is not plain text.")
            try: data.decode("utf-8")
            except UnicodeDecodeError: raise ValidationError(415, "Text file must be UTF-8 encoded.")
        return ext

    def parse(self, filename: str, data: bytes) -> str:
        ext = self.validate(filename, data)
        if ext == ".txt":
            text = data.decode("utf-8")
        else:
            try:
                with pdfplumber.open(io.BytesIO(data)) as pdf:
                    if len(pdf.pages) > self.max_pages: raise ValidationError(413, f"PDF has too many pages (limit {self.max_pages}).")
                    text = "\n".join(self._page(p) for p in pdf.pages)
            except ValidationError: raise
            except Exception: raise ValidationError(422, "The PDF could not be read.")
        if len(text.strip()) < 50:
            raise ValidationError(422, "No readable text found. Scanned PDFs need OCR, which is not enabled.")
        return text

    @staticmethod
    def _crop_text(page, y0, y1):
        y0, y1 = max(0, y0), min(page.height, y1)
        if y1 - y0 < 2: return ""
        return page.crop((0, y0, page.width, y1)).extract_text() or ""

    def _page(self, page):
        """Text above/between/below tables + each table row flattened to one 'a | b | c' line."""
        out, y = [], 0
        for t in sorted(page.find_tables(), key=lambda t: t.bbox[1]):
            out.append(self._crop_text(page, y, t.bbox[1]))
            for row in t.extract():
                cells = [(c or "").replace("\n", " ").strip() for c in row]
                if any(cells): out.append(" | ".join(cells))
            y = t.bbox[3]
        out.append(self._crop_text(page, y, page.height))
        return "\n".join(s for s in out if s)

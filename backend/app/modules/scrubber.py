"""NFR-5: token-replacement of names, registration numbers, phones, emails and ALL dates
BEFORE chunking/encoding. Tokens are restored in the response only (so follow-up dates still
reach the patient) from an in-memory map that is never stored or logged."""
import re
from collections import Counter

MONTH = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*"
DATE = re.compile(rf"\b(?:\d{{1,2}}[/\-.]\d{{1,2}}[/\-.]\d{{2,4}}|\d{{1,2}}(?:st|nd|rd|th)?\s+{MONTH}\.?,?\s+\d{{2,4}}|{MONTH}\.?\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s+\d{{4}})\b", re.I)
LABELLED_DATE = re.compile(r"(?i)\b((?:date of birth|d\.?o\.?b\.?|date of admission|admission date|admitted(?: on)?|date of discharge|discharge date|discharged(?: on)?|date of registration)\s*[:\-]?\s*)(" + DATE.pattern + ")")
LABELLED_NAME = re.compile(r"(?im)^(\s*(?:patient(?:'s)? name|name|next of kin|nok|caregiver|guardian|relative)\s*:\s*)(.+?)\s*$")
TITLED = re.compile(r"\b(?:Mr|Mrs|Ms|Miss|Master)\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?")
REGNO = re.compile(r"(?i)\b((?:registration|reg|mrn|ip|op|patient\s*id|patient|file|nhif|sha|national\s*id|id|passport)\.?(?:\s*(?:no\.?|number|num|#)\s*[:\-]?|\s*[:\-])\s*)(?=[A-Z0-9/\-]*\d)([A-Z0-9][A-Z0-9/\-]{3,})\b")
PHONE = re.compile(r"(?<!\d)(?:\+?254[\s-]?|0)[17]\d{2}[\s-]?\d{3}[\s-]?\d{3}(?!\d)")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")

class PrivacyScrubber:
    def scrub(self, text):
        values, counts = {}, Counter()
        def tok(kind, val):
            key = (kind, val.strip())
            if key not in values:
                counts[kind] += 1
                values[key] = f"[{kind}_{counts[kind]}]"
            return values[key]
        lab = lambda kind: (lambda m: m.group(1) + tok(kind, m.group(2)))
        text = LABELLED_NAME.sub(lab("NAME"), text)
        text = TITLED.sub(lambda m: tok("NAME", m.group(0)), text)
        text = REGNO.sub(lab("REGNO"), text)
        text = PHONE.sub(lambda m: tok("PHONE", m.group(0)), text)
        text = EMAIL.sub(lambda m: tok("EMAIL", m.group(0)), text)
        text = LABELLED_DATE.sub(lab("DATE"), text)
        text = DATE.sub(lambda m: tok("DATE", m.group(0)), text)   # all remaining dates
        mapping = {v: k[1] for k, v in values.items()}
        return text, mapping, dict(counts)

    @staticmethod
    def restore(text, mapping):
        for token, val in mapping.items(): text = text.replace(token, val)
        return text

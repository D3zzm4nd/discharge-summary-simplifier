import pytest
from app.modules.scrubber import PrivacyScrubber
from app.modules.splitter import RecursiveTextSplitter
from app.modules.parser import PDFDocumentParser, ValidationError
from app.modules.readability import ReadabilityEvaluator
from app.modules.highlight import CriticalInstructionDetector
from app.modules.sus import sus_score

DOC = """Patient Name: Jane Wanjiru Otieno
MRN: KNH-004521
Phone: 0712 345 678
Date of Admission: 03/09/2026
DISCHARGE DIAGNOSIS
Community acquired pneumonia with hypoxaemia.
DISCHARGE MEDICATIONS
Amoxicillin | 500 mg | three times daily | 7 days
Paracetamol | 1 g | every 6 hours if fever
FOLLOW-UP
Review at chest clinic on 17/09/2026. Return to hospital if breathing worsens.
"""

def test_scrub_and_restore():
    s, m, rep = PrivacyScrubber().scrub(DOC)
    for leak in ("Otieno", "KNH-004521", "0712 345 678", "03/09/2026", "17/09/2026"): assert leak not in s
    assert "500 mg" in s and "three times daily" in s
    assert PrivacyScrubber.restore(s, m) == DOC
    assert rep["NAME"] == 1 and "DATE" in rep

def test_chunking_keeps_medication_rows_whole():
    s, _, _ = PrivacyScrubber().scrub(DOC)
    sp = RecursiveTextSplitter(chunk_size=120)
    chunks = sp.chunk(s)
    assert {c["section"] for c in chunks} >= {"Discharge Diagnosis", "Discharge Medications", "Follow-Up"}
    assert sp.integrity_check(s, chunks)["status"] == "PASS"
    assert any("Amoxicillin | 500 mg | three times daily | 7 days" in c["text"] for c in chunks)

def test_integrity_detects_split_rows():
    s = "MEDS\nAmoxicillin | 500 mg | three times daily"
    bad = [{"text": "Amoxicillin | 500 mg"}, {"text": "three times daily"}]
    assert RecursiveTextSplitter.integrity_check(s, bad)["status"] == "WARN"

def test_validation():
    p = PDFDocumentParser(max_mb=1)
    assert p.validate("a.txt", b"hello") == ".txt"
    for name, data, code in [("a.exe", b"x", 415), ("a.pdf", b"notpdf", 415), ("a.txt", b"", 400), ("a.txt", b"x" * 2_000_000, 413)]:
        with pytest.raises(ValidationError) as e: p.validate(name, data)
        assert e.value.status == code

def test_readability_and_highlight_and_sus():
    r = ReadabilityEvaluator.score("The patient exhibits bilateral pulmonary infiltrates necessitating antimicrobial therapy.")
    e = ReadabilityEvaluator.score("You have a chest infection. Take your medicine.")
    assert e["fk_grade"] < r["fk_grade"] and e["reading_ease"] > r["reading_ease"]
    assert CriticalInstructionDetector.is_critical("Take 2 tablets every morning.")
    assert not CriticalInstructionDetector.is_critical("The lungs are in the chest.")
    assert sus_score([5, 1] * 5) == 100 and sus_score([3] * 10) == 50
    with pytest.raises(ValueError): sus_score([1, 2])

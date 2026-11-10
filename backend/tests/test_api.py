"""End-to-end API test with a fake embedder + fake LLM (no model downloads needed)."""
import hashlib, os, re, tempfile
os.environ["DATA_DIR"] = tempfile.mkdtemp()
os.environ["ADMIN_PASSWORD"] = "correct-horse-battery"
import pytest
from fastapi.testclient import TestClient

class FakeEmbedder:
    loaded = True
    def encode(self, texts):
        out = []
        for t in texts:
            v = [0.0] * 128
            for w in re.findall(r"[a-z]+", t.lower()): v[int(hashlib.md5(w.encode()).hexdigest(), 16) % 128] += 1
            n = sum(x * x for x in v) ** .5 or 1
            out.append([x / n for x in v])
        return out

class FakeEngine:
    def generate(self, chunk, refs):
        if "pneumonia" in chunk.lower():
            return "Pneumonia is an infection of the lungs. You have pneumonia. The moon is made of cheese."
        return "Take amoxicillin 500 mg three times daily for 7 days."

@pytest.fixture(scope="module")
def client():
    from app import container
    from app.main import app
    fe = FakeEmbedder()
    container.embedder.__dict__.update(encode=fe.encode, _m=object())
    container.pipeline.engine = FakeEngine()
    container.pipeline.embedder = container.vsm.embedder = container.pipeline.grounder.embedder = fe
    container.vsm.upsert_passages([{"id": "m:1:0", "title": "Pneumonia", "url": "https://medlineplus.gov/pneumonia.html",
        "source": "MedlinePlus", "topic_id": "1", "text": "Pneumonia: Pneumonia is an infection of the lungs. Antibiotics treat it."},
        {"id": "m:3:0", "title": "Amoxicillin", "url": "https://medlineplus.gov/druginfo/amoxicillin.html", "source": "MedlinePlus",
         "topic_id": "3", "text": "Amoxicillin: Amoxicillin antibiotic is a medicine that treats infections. Take it three times daily for 7 days."},
        {"id": "m:2:0", "title": "Antibiotics", "url": "https://medlineplus.gov/antibiotics.html", "source": "MedlinePlus",
         "topic_id": "2", "text": "Antibiotics: Antibiotics are medicines that fight infections caused by bacteria. Take the whole course."}])
    with TestClient(app) as c: yield c

H = lambda t: {"Authorization": f"Bearer {t}"}
DOC = ("Patient Name: Jane Otieno\nMRN: KNH-004521\nDISCHARGE DIAGNOSIS\nPneumonia of the lungs.\n"
       "DISCHARGE MEDICATIONS\nAmoxicillin antibiotic | 500 mg | three times daily | 7 days\nFOLLOW-UP\nxx\n")

def test_full_flow(client):
    assert client.post("/auth/session", json={"consent": False}).status_code == 400   # NFR-12
    pt = client.post("/auth/session", json={"consent": True}).json()["token"]
    assert client.post("/simplify").status_code == 401
    assert client.post("/simplify", files={"file": ("x.exe", b"x")}, headers=H(pt)).status_code == 415   # FR-2
    r = client.post("/simplify", files={"file": ("d.txt", DOC.encode())}, headers=H(pt))
    assert r.status_code == 200, r.text
    d = r.json(); m = d["metrics"]
    items = [i for s in d["sections"] for i in s["items"]]
    assert [s["heading"] for s in d["sections"]] == ["Document", "Discharge Diagnosis", "Discharge Medications", "Follow-Up"]   # FR-7
    dx = next(i for i in items if i["section"] == "Discharge Diagnosis")
    assert dx["status"] == "grounded" and dx["sources"][0]["title"] == "Pneumonia"                     # FR-8
    assert all("cheese" not in s["text"] for s in dx["sentences"]) and "unsupported_sentences_removed" in dx["flags"]  # NFR-3
    assert any(i["status"] == "unmatched" for i in items)                                              # NFR-4
    med = next(i for i in items if "Amoxicillin" in i["original"])
    assert any(s["critical"] for s in med["sentences"])                                                # FR-10
    hdr = next(i for i in items if i["section"] == "Document")["original"]
    assert "Jane Otieno" in hdr and "KNH-004521" in hdr          # tokens restored in response only (NFR-5)
    assert m["chunking_integrity"] == "PASS" and "retrieval_ms_max" in m and m["readability_after"]["fk_grade"] is not None
    # FR-12 SUS, RBAC (FR-16), admin features
    assert client.post("/feedback/sus", json={"answers": [5, 1] * 5}, headers=H(pt)).json()["sus_score"] == 100
    assert client.get("/admin/analytics", headers=H(pt)).status_code == 403
    at = client.post("/auth/login", json={"username": "admin", "password": "correct-horse-battery"}).json()["token"]
    assert client.post("/auth/login", json={"username": "admin", "password": "bad"}).status_code == 401
    a = client.get("/admin/analytics", headers=H(at)).json()
    assert a["documents"]["n"] == 1 and a["sus"]["mean"] == 100 and a["sus"]["meets_target"]
    log = client.get("/admin/logs", headers=H(at)).json()["processing"][0]
    assert log["groundedness"] is not None and log["detail"][0]["section"]                              # FR-17/18
    h = client.get("/admin/health", headers=H(at)).json()
    assert h["vector_db"]["status"] == "ok" and h["retrieval_probe"]["within_budget"]                  # FR-14, NFR-1
    # manager: index yes, analytics no
    assert client.post("/admin/users", json={"username": "mgr", "password": "long-enough-pw", "role": "clinic_manager"}, headers=H(at)).status_code == 200
    mt = client.post("/auth/login", json={"username": "mgr", "password": "long-enough-pw"}).json()["token"]
    assert client.get("/admin/index", headers=H(mt)).json()["index"]["passages"] == 3
    assert client.get("/admin/logs", headers=H(mt)).status_code == 403
    assert client.delete("/feedback/mine", headers=H(pt)).json()["deleted"]                            # withdraw

def test_incremental_index_update(client):
    from app.container import vsm
    from app.modules.medline_loader import parse_json_corpus
    import json
    items, _ = parse_json_corpus(json.dumps([{"id": "9", "title": "Malaria", "text": "Malaria is spread by mosquitoes."}]).encode())
    before = vsm.medline.count()
    vsm.upsert_passages(items)
    assert vsm.medline.count() == before + 1
    vsm.upsert_passages(items)   # idempotent upsert
    assert vsm.medline.count() == before + 1

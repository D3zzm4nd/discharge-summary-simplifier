"""ChromaVectorStoreManager: persistent MedlinePlus index + temporary per-document collections."""
import contextlib, json, time, uuid
import chromadb

class ChromaVectorStoreManager:
    def __init__(self, path, embedder, meta_path):
        self.embedder, self.meta_path = embedder, meta_path
        self.persistent = chromadb.PersistentClient(path)
        self.ephemeral = chromadb.EphemeralClient()
        self.medline = self.persistent.get_or_create_collection("medlineplus", metadata={"hnsw:space": "cosine"})

    @contextlib.contextmanager
    def session(self):
        """Stage 2: chunk embeddings live in memory only and are deleted afterwards."""
        name = f"s_{uuid.uuid4().hex}"
        col = self.ephemeral.create_collection(name, metadata={"hnsw:space": "cosine"})
        try: yield col
        finally: self.ephemeral.delete_collection(name)

    def upsert_passages(self, items, batch=64, progress=None):
        """NFR-11: upsert by stable ID, then drop stale IDs. The index stays queryable throughout."""
        for i in range(0, len(items), batch):
            b = items[i:i + batch]
            self.medline.upsert(ids=[p["id"] for p in b], documents=[p["text"] for p in b],
                embeddings=self.embedder.encode([p["text"] for p in b]),
                metadatas=[{k: p[k] for k in ("title", "url", "source", "topic_id")} for p in b])
            if progress: progress(min(i + batch, len(items)), len(items))
        new_ids, removed = {p["id"] for p in items}, 0
        for src in {p["source"] for p in items}:
            stale = list(set(self.medline.get(where={"source": src}, include=[])["ids"]) - new_ids)
            for j in range(0, len(stale), 500): self.medline.delete(ids=stale[j:j + 500])
            removed += len(stale)
        return {"passages": len(items), "removed": removed}

    def write_meta(self, **kw):
        self.meta_path.write_text(json.dumps({**kw, "updated": time.time()}))

    def info(self):
        meta = json.loads(self.meta_path.read_text()) if self.meta_path.exists() else {}
        return {"passages": self.medline.count(), **meta}

    def heartbeat(self): return self.persistent.heartbeat()

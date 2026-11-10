"""FR-5, NFR-1: top-k retrieval from the MedlinePlus index with latency measurement."""
import time

class MedlinePlusRetriever:
    def __init__(self, vsm, top_k, max_dist): self.vsm, self.k, self.max_dist = vsm, top_k, max_dist

    def retrieve(self, embedding):
        t = time.perf_counter()
        refs = []
        if self.vsm.medline.count() > 0:
            r = self.vsm.medline.query(query_embeddings=[embedding], n_results=self.k)
            for d, m, dist in zip(r["documents"][0], r["metadatas"][0], r["distances"][0]):
                if dist <= self.max_dist: refs.append({"text": d, "distance": round(dist, 3), **m})
        return refs, (time.perf_counter() - t) * 1000

"""FR-4: pre-trained biomedical sentence transformer (lazy-loaded, runs locally)."""
class BiomedicalEmbedder:
    def __init__(self, name): self.name, self._m = name, None

    @property
    def loaded(self): return self._m is not None

    @property
    def model(self):
        if self._m is None:
            from sentence_transformers import SentenceTransformer
            self._m = SentenceTransformer(self.name)
        return self._m

    def encode(self, texts):
        return self.model.encode(list(texts), normalize_embeddings=True, show_progress_bar=False).tolist()

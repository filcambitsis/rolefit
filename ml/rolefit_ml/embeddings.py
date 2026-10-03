from functools import lru_cache

import numpy as np

from rolefit.config import ROOT, settings


class Embedder:
    def __init__(self):
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(
            settings().embedding_model, cache_folder=str(ROOT / "work/model-cache"), device="cpu"
        )
        self.model.max_seq_length = 512
        self.tokenizer = self.model.tokenizer

    def chunks(self, text):
        # Offsets preserve original text and avoid decode/re-encode token-boundary drift.
        encoded = self.tokenizer(text, add_special_tokens=False, return_offsets_mapping=True)
        offsets = encoded["offset_mapping"]
        for start in range(0, len(offsets), 420):
            window = offsets[start : start + 450]
            if window:
                yield text[window[0][0] : window[-1][1]]

    def embed(self, chunks):
        chunks = list(chunks)
        for chunk in chunks:
            length = len(self.tokenizer.encode(chunk, add_special_tokens=True))
            if length > 512:
                raise ValueError(f"Chunk has {length} tokens; refusing silent truncation")
        if not chunks:
            return np.empty((0, 768))
        vectors = self.model.encode(
            chunks, normalize_embeddings=True, convert_to_numpy=True, batch_size=16, show_progress_bar=False
        )
        if vectors.shape[1] != 768:
            raise ValueError("Evaluation requires 768-dimensional bge-base-en-v1.5 embeddings")
        return vectors

    def document(self, text):
        vectors = self.embed(self.chunks(text))
        if len(vectors) == 0:
            raise ValueError("Cannot embed empty text")
        pooled = vectors.mean(axis=0)
        return (pooled / max(np.linalg.norm(pooled), 1e-9)).tolist()


@lru_cache
def embedder():
    return Embedder()

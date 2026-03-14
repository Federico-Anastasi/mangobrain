"""MangoBrain — Embedding engine with auto-detect GPU/CPU."""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

BGE_PREFIX = "Represent this sentence: "


class Embedder:
    """Loads embedding model once and provides encode/similarity methods.

    Supports auto-detection:
    - CUDA available → bge-large-en-v1.5 (1024 dim)
    - CPU only → bge-base-en-v1.5 (768 dim)
    - Or any explicit model/device via config
    """

    def __init__(self, model_name: str, device: str = "cuda") -> None:
        self.model_name = model_name
        self.device = device
        self._model = None
        self._dim: Optional[int] = None

    def load(self) -> None:
        """Load the model into memory/VRAM. Call once at startup."""
        from sentence_transformers import SentenceTransformer

        logger.info("Loading embedding model %s on %s...", self.model_name, self.device)
        try:
            self._model = SentenceTransformer(self.model_name, device=self.device)
        except Exception as e:
            if self.device == "cuda":
                logger.warning("CUDA load failed (%s), falling back to CPU", e)
                self.device = "cpu"
                self._model = SentenceTransformer(self.model_name, device="cpu")
            else:
                raise
        self._dim = self._model.get_sentence_embedding_dimension()
        logger.info("Embedding model loaded — dim=%d, device=%s", self._dim, self.device)

    @property
    def dim(self) -> int:
        assert self._dim is not None, "Model not loaded"
        return self._dim

    def encode(self, text: str) -> np.ndarray:
        """Encode a single text -> 1D float32 array."""
        assert self._model is not None, "Model not loaded"
        prefixed = BGE_PREFIX + text
        emb = self._model.encode(prefixed, normalize_embeddings=True)
        return emb.astype(np.float32)

    def encode_batch(self, texts: list[str]) -> np.ndarray:
        """Encode a batch -> 2D float32 array (N, dim)."""
        assert self._model is not None, "Model not loaded"
        prefixed = [BGE_PREFIX + t for t in texts]
        embs = self._model.encode(prefixed, normalize_embeddings=True, batch_size=32)
        return embs.astype(np.float32)

    @staticmethod
    def cosine_similarity(query_emb: np.ndarray, all_embs: np.ndarray) -> np.ndarray:
        """Cosine similarity between query (1D) and matrix (N, dim).
        Both assumed L2-normalized, so cosine sim = dot product.
        """
        return all_embs @ query_emb

    @staticmethod
    def embedding_to_bytes(emb: np.ndarray) -> bytes:
        return emb.astype(np.float32).tobytes()

    @staticmethod
    def bytes_to_embedding(data: bytes) -> np.ndarray:
        return np.frombuffer(data, dtype=np.float32)

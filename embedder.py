"""
embedder.py
-----------
Generates semantic embeddings for resumes and job descriptions
using sentence-transformers (MiniLM-L6-v2).
"""

import numpy as np
from typing import List, Union
from sentence_transformers import SentenceTransformer

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


class ResumeEmbedder:
    """
    Wraps SentenceTransformer to produce L2-normalised embeddings
    suitable for cosine similarity comparisons.
    """

    def __init__(self, model_name: str = MODEL_NAME):
        print(f"[Embedder] Loading model: {model_name}")
        self.model = SentenceTransformer(model_name)
        print("[Embedder] Model ready.")

    def embed(self, texts: Union[str, List[str]]) -> np.ndarray:
        """
        Encode one or more texts into unit-norm embeddings.

        Returns
        -------
        np.ndarray  shape (n, 384) for MiniLM-L6
        """
        if isinstance(texts, str):
            texts = [texts]
        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,   # cosine ≡ dot product after L2 norm
            show_progress_bar=False,
        )
        return embeddings  # shape: (len(texts), 384)

    def embed_resume(self, parsed_resume) -> np.ndarray:
        """
        Build a rich text representation from a ParsedResume and embed it.
        Weights important sections by repetition (poor-man's feature weighting).
        """
        parts = []

        # Skills repeated 3x — highest weight
        if parsed_resume.skills:
            skill_str = " ".join(parsed_resume.skills)
            parts += [skill_str] * 3

        # Job titles repeated 2x
        if parsed_resume.job_titles:
            title_str = " ".join(parsed_resume.job_titles)
            parts += [title_str] * 2

        # Education 1x
        if parsed_resume.education:
            parts.append(" ".join(parsed_resume.education))

        # Raw text excerpt (first 1000 chars) for context
        parts.append(parsed_resume.raw_text[:1000])

        combined = " ".join(parts)
        return self.embed(combined)[0]  # single vector

    def embed_job_description(self, jd_text: str) -> np.ndarray:
        """Embed a full job description string."""
        return self.embed(jd_text)[0]

    @staticmethod
    def cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """
        Cosine similarity between two vectors.
        Since embeddings are L2-normalised, this equals the dot product.
        """
        return float(np.dot(vec_a, vec_b))

    def batch_similarity(
        self, query: np.ndarray, corpus: np.ndarray
    ) -> np.ndarray:
        """
        Return cosine similarities between a single query vector
        and a matrix of corpus vectors.

        Parameters
        ----------
        query  : (384,)
        corpus : (n, 384)
        """
        return corpus @ query  # dot product = cosine for normalised vecs

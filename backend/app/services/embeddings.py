from __future__ import annotations
import hashlib, math, re
from functools import lru_cache
from app.core.config import get_settings

def _fallback(text: str, dimensions: int = 384) -> list[float]:
    tokens = re.findall(r"[a-zA-Z0-9_+#.-]+", text.lower())
    vec = [0.0] * dimensions
    for token in tokens:
        h = int(hashlib.sha256(token.encode()).hexdigest()[:12], 16)
        idx = h % dimensions
        sign = 1.0 if (h >> 12) & 1 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(x*x for x in vec)) or 1.0
    return [x/norm for x in vec]

@lru_cache(maxsize=1)
def _model():
    try:
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer(get_settings().embedding_model)
    except Exception:
        return None

def embed_texts(texts: list[str]) -> list[list[float]]:
    model = _model()
    if model is None:
        return [_fallback(t) for t in texts]
    return [v.tolist() for v in model.encode(texts, normalize_embeddings=True)]

def cosine(a: list[float], b: list[float]) -> float:
    return sum(x*y for x,y in zip(a,b))

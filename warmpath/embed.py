"""Local embeddings (fastembed, BAAI/bge-small-en-v1.5, 384 dims). No API key, runs on CPU."""
from functools import lru_cache
DIMS = 384
MODEL = "BAAI/bge-small-en-v1.5"

@lru_cache(maxsize=1)
def _model():
    from fastembed import TextEmbedding
    return TextEmbedding(MODEL)

def embed(texts):
    return [[float(x) for x in v] for v in _model().embed(list(texts))]

def embed_one(text):
    return embed([text])[0]

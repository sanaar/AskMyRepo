"""Embed chunks with sentence-transformers and store/query them in ChromaDB.

Each repo gets its own persisted Chroma collection, keyed by owner/repo/branch,
so re-analyzing a repo you've already seen skips re-embedding entirely.
"""
import chromadb
from sentence_transformers import SentenceTransformer

CACHE_DIR = ".cache/chroma"
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"

_model = None
_client = None


def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBED_MODEL_NAME)
    return _model


def _get_client():
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=CACHE_DIR)
    return _client


def collection_name(owner: str, repo: str, branch: str) -> str:
    return f"{owner}_{repo}_{branch}".replace("/", "_").replace(".", "_")[:63]


def collection_exists(owner: str, repo: str, branch: str) -> bool:
    name = collection_name(owner, repo, branch)
    return any(c.name == name for c in _get_client().list_collections())


def build_collection(owner: str, repo: str, branch: str, chunks: list[dict]):
    """Embed chunks and store them, replacing any prior collection for this repo."""
    name = collection_name(owner, repo, branch)
    client = _get_client()
    try:
        client.delete_collection(name)
    except Exception:
        pass
    collection = client.create_collection(name)

    if not chunks:
        return collection

    model = _get_model()
    texts = [c["text"] for c in chunks]
    embeddings = model.encode(texts, show_progress_bar=False).tolist()

    collection.add(
        ids=[str(i) for i in range(len(chunks))],
        embeddings=embeddings,
        documents=texts,
        metadatas=[{"path": c["path"], "type": c["type"]} for c in chunks],
    )
    return collection


def get_collection(owner: str, repo: str, branch: str):
    return _get_client().get_collection(collection_name(owner, repo, branch))


def query(owner: str, repo: str, branch: str, question: str, top_k: int = 5) -> list[dict]:
    collection = get_collection(owner, repo, branch)
    model = _get_model()
    embedding = model.encode([question]).tolist()

    results = collection.query(query_embeddings=embedding, n_results=top_k)
    hits = []
    for text, meta in zip(results["documents"][0], results["metadatas"][0]):
        hits.append({"text": text, "path": meta["path"], "type": meta["type"]})
    return hits

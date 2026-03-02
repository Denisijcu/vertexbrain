"""
Vector Store basado en FAISS.
Embeddings simulados via hash — sin torch ni sentence-transformers.
Liviano, compatible con Python 3.14, cero dependencias de GPU.
"""

import json
import hashlib
import numpy as np
import faiss
from pathlib import Path
from typing import List, Dict, Any
from config import settings

EMBEDDING_DIM = 128

_store_dir = Path(settings.CHROMA_DIR)
_store_dir.mkdir(exist_ok=True)
_index_path = _store_dir / "vertex.faiss"
_meta_path  = _store_dir / "vertex_meta.json"

_metadata: List[Dict[str, Any]] = []
_index = None


def _load_or_create_index():
    global _metadata
    if _index_path.exists() and _meta_path.exists():
        idx = faiss.read_index(str(_index_path))
        with open(_meta_path, "r", encoding="utf-8") as f:
            _metadata = json.load(f)
        return idx
    return faiss.IndexFlatIP(EMBEDDING_DIM)


def _save_index():
    faiss.write_index(_index, str(_index_path))
    with open(_meta_path, "w", encoding="utf-8") as f:
        json.dump(_metadata, f, ensure_ascii=False)


def _embed(texts: List[str]) -> np.ndarray:
    """
    Embeddings deterministicos via SHA256.
    Sin torch, sin GPU — liviano y reproducible.
    """
    vectors = []
    for text in texts:
        digest = hashlib.sha256(text.lower().encode()).digest()
        extended = (digest * 4)[:128 * 4]
        vec = np.frombuffer(extended, dtype=np.uint8).astype(np.float32)
        vec = vec / 255.0
        keywords = text.lower().split()
        for i, word in enumerate(keywords[:16]):
            word_hash = int(hashlib.md5(word.encode()).hexdigest()[:8], 16)
            vec[i % EMBEDDING_DIM] += (word_hash % 100) / 1000.0
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        vectors.append(vec)
    return np.array(vectors, dtype=np.float32)


_index = _load_or_create_index()


def add_chunks(doc_id: int, filename: str, category: str, chunks: List[str]) -> int:
    if not chunks:
        return 0
    vecs = _embed(chunks)
    _index.add(vecs)
    for i, chunk in enumerate(chunks):
        _metadata.append({
            "doc_id":      doc_id,
            "filename":    filename,
            "category":    category,
            "chunk_index": i,
            "content":     chunk,  # 🔥 raw content → RAG Poisoning vector
        })
    _save_index()
    return len(chunks)


def search(query: str, top_k: int = None, category: str = None) -> List[Dict[str, Any]]:
    top_k = top_k or settings.TOP_K_RESULTS
    if _index.ntotal == 0:
        return []
    query_vec = _embed([query])
    search_k = min(_index.ntotal, top_k * 10 if category else top_k)
    scores, indices = _index.search(query_vec, search_k)
    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue
        meta = _metadata[idx]
        if category and meta["category"] != category:
            continue
        results.append({
            "content":  meta["content"],
            "filename": meta["filename"],
            "category": meta["category"],
            "score":    round(float(score), 4),
        })
        if len(results) >= top_k:
            break
    return results


def delete_document_chunks(doc_id: int) -> None:
    global _index, _metadata
    keep_positions = [i for i, m in enumerate(_metadata) if m["doc_id"] != doc_id]
    if not keep_positions:
        _index = faiss.IndexFlatIP(EMBEDDING_DIM)
        _metadata = []
        _save_index()
        return
    all_vecs = np.zeros((_index.ntotal, EMBEDDING_DIM), dtype=np.float32)
    for i in range(_index.ntotal):
        all_vecs[i] = _index.reconstruct(i)
    keep_vecs = all_vecs[keep_positions]
    _metadata = [_metadata[i] for i in keep_positions]
    new_index = faiss.IndexFlatIP(EMBEDDING_DIM)
    new_index.add(keep_vecs)
    _index = new_index
    _save_index()


def get_collection_stats() -> Dict[str, Any]:
    return {
        "total_chunks": _index.ntotal,
        "total_docs":   len(set(m["doc_id"] for m in _metadata)) if _metadata else 0,
        "engine":       "FAISS IndexFlatIP",
        "embedding":    "hash-based (lightweight)",
    }
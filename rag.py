import io
import re

_MODEL = None
_INDEX = None
_CHUNKS = []


def _dependencies():
    try:
        import numpy as np
        import faiss
        from pypdf import PdfReader
        from sentence_transformers import SentenceTransformer
        return np, faiss, PdfReader, SentenceTransformer
    except Exception as e:
        raise RuntimeError(
            "RAG dependencies could not be loaded. "
            "Make sure requirements.txt is installed correctly. "
            f"Details: {e}"
        ) from e


def _model():
    global _MODEL
    if _MODEL is None:
        _, _, _, SentenceTransformer = _dependencies()
        _MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    return _MODEL


def _split(text, size=900, overlap=120):
    text = re.sub(r"\s+", " ", text).strip()
    step = max(1, size - overlap)
    return [
        text[i:i + size]
        for i in range(0, len(text), step)
        if text[i:i + size].strip()
    ]


def build_index(uploaded_file):
    global _INDEX, _CHUNKS

    np, faiss, PdfReader, _ = _dependencies()

    reader = PdfReader(io.BytesIO(uploaded_file.getvalue()))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)

    _CHUNKS = _split(text)

    if not _CHUNKS:
        raise ValueError(
            "No readable text found in this PDF. "
            "If it is a scanned/image-only PDF, OCR is required."
        )

    vectors = np.asarray(
        _model().encode(_CHUNKS, normalize_embeddings=True),
        dtype="float32",
    )

    _INDEX = faiss.IndexFlatIP(vectors.shape[1])
    _INDEX.add(vectors)
    return _CHUNKS


def search_rag(question, chunks=None, k=6):
    np, faiss, _, _ = _dependencies()

    if chunks is not None and chunks is not _CHUNKS:
        if not chunks:
            return []

        vectors = np.asarray(
            _model().encode(chunks, normalize_embeddings=True),
            dtype="float32",
        )
        index = faiss.IndexFlatIP(vectors.shape[1])
        index.add(vectors)

        q = np.asarray(
            _model().encode([question], normalize_embeddings=True),
            dtype="float32",
        )
        _, ids = index.search(q, min(k, len(chunks)))
        return [chunks[i] for i in ids[0] if i >= 0]

    if _INDEX is None:
        return []

    q = np.asarray(
        _model().encode([question], normalize_embeddings=True),
        dtype="float32",
    )
    _, ids = _INDEX.search(q, min(k, len(_CHUNKS)))
    return [_CHUNKS[i] for i in ids[0] if i >= 0]


def get_context_for_plan(chunks, max_chunks=12):
    return "\n\n---\n\n".join(chunks[:max_chunks]) if chunks else ""

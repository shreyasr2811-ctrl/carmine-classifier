"""
RAG (Retrieval-Augmented Generation) layer over a small breast-cancer /
histopathology knowledge base, backed by ChromaDB.

Note on embeddings: ChromaDB's default embedding function downloads a
model from the internet on first use, which is not reliably available in
all deployment environments (e.g., locked-down sandboxes). To keep this
fully self-contained and offline-friendly, we compute our own TF-IDF
embeddings for the (small, fixed) knowledge base and pass them to Chroma
explicitly via the `embeddings=` argument -- Chroma is still used as the
actual vector store / similarity search engine.
"""

import os
import sys

import chromadb
from joblib import dump, load
from sklearn.feature_extraction.text import TfidfVectorizer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "rag_kb"))
from knowledge_base import DOCUMENTS  # noqa: E402

PERSIST_DIR = os.path.join(os.path.dirname(__file__), "..", "rag_kb", "chroma_store")
VECTORIZER_PATH = os.path.join(os.path.dirname(__file__), "..", "rag_kb", "tfidf_vectorizer.joblib")
COLLECTION_NAME = "breast_cancer_kb"


def build_kb():
    """Build (or rebuild) the persistent ChromaDB collection from DOCUMENTS."""
    os.makedirs(PERSIST_DIR, exist_ok=True)
    texts = [d["text"] for d in DOCUMENTS]
    ids = [d["id"] for d in DOCUMENTS]

    vectorizer = TfidfVectorizer(stop_words="english", max_features=2000)
    embeddings = vectorizer.fit_transform(texts).toarray().tolist()
    dump(vectorizer, VECTORIZER_PATH)

    client = chromadb.PersistentClient(path=PERSIST_DIR)
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.create_collection(COLLECTION_NAME)
    collection.add(documents=texts, embeddings=embeddings, ids=ids)
    print(f"Built knowledge base with {len(texts)} documents at {PERSIST_DIR}")
    return collection


def _get_collection():
    client = chromadb.PersistentClient(path=PERSIST_DIR)
    return client.get_collection(COLLECTION_NAME)


def retrieve(query, k=3):
    """Return top-k relevant knowledge base passages for a query string."""
    vectorizer = load(VECTORIZER_PATH)
    collection = _get_collection()
    query_emb = vectorizer.transform([query]).toarray().tolist()
    results = collection.query(query_embeddings=query_emb, n_results=k)
    return results["documents"][0] if results["documents"] else []


if __name__ == "__main__":
    build_kb()
    print(retrieve("what does IDC look like on a slide and what should I do next"))

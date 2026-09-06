"""
ingestion/embed_index.py
Builds and maintains the local ChromaDB vector store for Hasebtak.
Indexes narrative chunks with section titles, page numbers, and topics.
"""

import os
import json
from typing import List, Dict, Any
import chromadb
from chromadb.config import Settings

CHROMA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chroma_db")
CHUNKS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "report_narrative_chunks.json")


def get_chroma_client():
    """Initializes or connects to persistent ChromaDB client."""
    os.makedirs(CHROMA_DIR, exist_ok=True)
    return chromadb.PersistentClient(path=CHROMA_DIR)


def build_vector_index(chunks_path: str = CHUNKS_FILE, collection_name: str = "hasebtak_narratives"):
    """
    Loads chunks from JSON and inserts them into ChromaDB.
    """
    if not os.path.exists(chunks_path):
        print(f"Chunks file not found at: {chunks_path}")
        return None

    with open(chunks_path, "r", encoding="utf-8") as f:
        chunks: List[Dict[str, Any]] = json.load(f)

    client = get_chroma_client()
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"description": "Citizen Budget 2026/2027 narrative chunks"}
    )

    ids = [c["id"] for c in chunks]
    documents = [c["text"] for c in chunks]
    metadatas = [
        {
            "section_title_ar": c.get("section_title_ar", ""),
            "page": int(c.get("page", 1)),
            "topic": c.get("topic", "الموازنة العامة")
        }
        for c in chunks
    ]

    collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas
    )

    print(f"Successfully indexed {len(chunks)} chunks into ChromaDB collection '{collection_name}'.")
    return collection


if __name__ == "__main__":
    print("Building ChromaDB vector index from narrative chunks...")
    build_vector_index()

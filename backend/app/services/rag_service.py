import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Any
import os
from app.models.schema import RetrievalResult

class RAGService:
    def __init__(self, collection_name: str = "kb_collection"):
        self.client = chromadb.PersistentClient(path="./data/chroma_db")
        # Using default embedding function (SentenceTransformer if local, or OpenAI if configured)
        self.collection = self.client.get_or_create_collection(name=collection_name)

    async def add_documents(self, documents: List[str], metadatas: List[Dict[str, Any]], ids: List[str]):
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

    async def retrieve(self, query: str, k: int = 3) -> RetrievalResult:
        results = self.collection.query(
            query_texts=[query],
            n_results=k
        )
        
        return RetrievalResult(
            context=results['documents'][0] if results['documents'] else [],
            metadata=results['metadatas'][0] if results['metadatas'] else []
        )

# Global singleton or dependency injectable service
rag_service = RAGService()

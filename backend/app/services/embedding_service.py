# embedding_service.py
# Basic embedding service stub for semantic search (Pinecone or similar)

from typing import List

class EmbeddingService:
    def __init__(self):
        # Initialize your embedding model or Pinecone client here
        pass

    def search(self, kb_texts: List[str], query: str) -> str:
        """
        Search the knowledge base texts for the best match to the query using embeddings.
        Returns the best matching text or empty string if not found.
        """
        # TODO: Replace with actual embedding search logic
        # For now, just return the first text that contains any word from the query
        query_words = set(query.lower().split())
        for text in kb_texts:
            if any(word in text.lower() for word in query_words):
                return text
        return ""

# Example usage:
# embedding_service = EmbeddingService()
# best_match = embedding_service.search(["John Doe lives at 123 Main St."], "address")

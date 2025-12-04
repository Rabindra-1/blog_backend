import asyncio
from typing import List, Dict, Any, Tuple
import uuid
import hashlib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from retrievers import RetrieverManager
from retrievers.base import Document
from utils.simple_text_processor import SimpleTextProcessor
from config import config

class SimpleRAGSystem:
    """Lightweight RAG system using TF-IDF and sklearn"""
    
    def __init__(self):
        self.retriever_manager = RetrieverManager()
        self.text_processor = SimpleTextProcessor(
            chunk_size=config.MAX_CHUNK_SIZE,
            chunk_overlap=config.CHUNK_OVERLAP
        )
        
        # Use TF-IDF instead of sentence transformers
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2)
        )
        
        # Simple in-memory storage
        self.document_store = {}
        self.chunk_store = {}
        self.vectorizer_fitted = False
        self.tfidf_matrix = None
        
        print("Simple RAG System initialized with TF-IDF")
    
    async def process_and_store_documents(self, documents: List[Document]) -> bool:
        """Process documents and store them using TF-IDF"""
        if not documents:
            return False
        
        try:
            all_chunks = []
            
            for doc in documents:
                # Generate unique document ID
                doc_id = f"{doc.source}_{hashlib.md5(doc.title.encode()).hexdigest()[:8]}"
                
                # Chunk the document
                chunks = self.text_processor.chunk_text(doc.content, doc_id)
                
                # Add document metadata to chunks
                for chunk in chunks:
                    chunk.source_doc_id = doc_id
                    chunk.doc_metadata = {
                        'title': doc.title,
                        'source': doc.source,
                        'url': doc.url,
                        'original_metadata': doc.metadata
                    }
                    
                    # Store chunk
                    self.chunk_store[chunk.chunk_id] = chunk
                
                all_chunks.extend(chunks)
                
                # Store document
                self.document_store[doc_id] = doc
            
            if all_chunks:
                # Build TF-IDF vectors
                chunk_texts = [chunk.content for chunk in all_chunks]
                
                if not self.vectorizer_fitted:
                    self.tfidf_matrix = self.vectorizer.fit_transform(chunk_texts)
                    self.vectorizer_fitted = True
                else:
                    # Combine with existing vectors
                    new_vectors = self.vectorizer.transform(chunk_texts)
                    if self.tfidf_matrix is not None:
                        self.tfidf_matrix = np.vstack([self.tfidf_matrix, new_vectors])
                    else:
                        self.tfidf_matrix = new_vectors
                
                print(f"Processed and stored {len(all_chunks)} chunks from {len(documents)} documents")
                return True
            
            return False
            
        except Exception as e:
            print(f"Error processing and storing documents: {e}")
            return False
    
    async def retrieve_and_store(self, query: str) -> bool:
        """Retrieve documents from all sources and store them"""
        try:
            # Retrieve documents from all sources
            documents = await self.retriever_manager.retrieve_all(
                query, 
                max_docs_per_source=config.MAX_DOCUMENTS_PER_SOURCE
            )
            
            if documents:
                print(f"Retrieved {len(documents)} documents for query: '{query}'")
                
                # Process and store documents
                success = await self.process_and_store_documents(documents)
                return success
            else:
                print(f"No documents retrieved for query: '{query}'")
                return False
                
        except Exception as e:
            print(f"Error in retrieve_and_store: {e}")
            return False
    
    async def search_relevant_content(self, query: str, top_k: int = None) -> List[Tuple[Any, float]]:
        """Search for relevant content using TF-IDF similarity"""
        top_k = top_k or config.TOP_K_RESULTS
        
        try:
            if not self.vectorizer_fitted or self.tfidf_matrix is None or len(self.chunk_store) == 0:
                return []
            
            # Vectorize query
            query_vector = self.vectorizer.transform([query])
            
            # Calculate similarities
            similarities = cosine_similarity(query_vector, self.tfidf_matrix).flatten()
            
            # Get top-k results
            top_indices = similarities.argsort()[-top_k:][::-1]
            
            results = []
            chunk_ids = list(self.chunk_store.keys())
            
            for idx in top_indices:
                if idx < len(chunk_ids) and similarities[idx] > 0.01:  # Minimum similarity threshold
                    chunk_id = chunk_ids[idx]
                    chunk = self.chunk_store[chunk_id]
                    results.append((chunk, float(similarities[idx])))
            
            print(f"Found {len(results)} relevant chunks for query: '{query}'")
            return results
            
        except Exception as e:
            print(f"Error searching for relevant content: {e}")
            return []
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get the status of all system components"""
        try:
            retriever_status = await self.retriever_manager.get_retriever_status()
            
            return {
                "retrievers": retriever_status,
                "vector_database": {
                    "status": "initialized",
                    "total_vectors": len(self.chunk_store),
                    "total_chunks": len(self.chunk_store),
                    "unique_documents": len(self.document_store),
                    "vectorizer_fitted": self.vectorizer_fitted
                },
                "embedding_model": {
                    "model_name": "TF-IDF",
                    "status": "loaded",
                    "features": 1000
                },
                "status": "operational" if retriever_status else "partial"
            }
            
        except Exception as e:
            print(f"Error getting system status: {e}")
            return {"status": "error", "message": str(e)}
    
    async def clear_database(self) -> bool:
        """Clear all stored data"""
        try:
            self.document_store.clear()
            self.chunk_store.clear()
            self.tfidf_matrix = None
            self.vectorizer_fitted = False
            self.vectorizer = TfidfVectorizer(
                max_features=1000,
                stop_words='english',
                ngram_range=(1, 2)
            )
            
            print("Database cleared successfully")
            return True
        except Exception as e:
            print(f"Error clearing database: {e}")
            return False
    
    async def prepare_retrieval_context(self, query: str) -> Dict[str, Any]:
        """Prepare context for retrieval by first fetching fresh content if needed"""
        try:
            # Check if we have enough relevant content
            existing_results = await self.search_relevant_content(query, top_k=5)
            
            # If we don't have enough relevant content, fetch new documents
            if len(existing_results) < 3:
                print(f"Insufficient relevant content found. Fetching new documents for: '{query}'")
                await self.retrieve_and_store(query)
                
                # Search again after fetching new content
                existing_results = await self.search_relevant_content(query, top_k=config.TOP_K_RESULTS)
            
            # Prepare context from retrieved chunks
            context_chunks = []
            sources_used = set()
            
            for chunk, similarity in existing_results:
                if hasattr(chunk, 'doc_metadata'):
                    context_chunks.append({
                        'content': chunk.content,
                        'source': chunk.doc_metadata['source'],
                        'title': chunk.doc_metadata['title'],
                        'url': chunk.doc_metadata['url'],
                        'similarity': similarity,
                        'chunk_id': chunk.chunk_id
                    })
                    sources_used.add(chunk.doc_metadata['source'])
            
            return {
                'query': query,
                'context_chunks': context_chunks,
                'sources_used': list(sources_used),
                'total_chunks': len(context_chunks),
                'avg_similarity': sum(c['similarity'] for c in context_chunks) / len(context_chunks) if context_chunks else 0
            }
            
        except Exception as e:
            print(f"Error preparing retrieval context: {e}")
            return {
                'query': query,
                'context_chunks': [],
                'sources_used': [],
                'total_chunks': 0,
                'avg_similarity': 0,
                'error': str(e)
            }
    
    @property
    def vector_db(self):
        """Mock vector_db property for compatibility"""
        class MockVectorDB:
            def get_stats(self):
                return {
                    "status": "initialized",
                    "total_vectors": len(self.chunk_store) if hasattr(self, 'chunk_store') else 0,
                    "total_chunks": len(self.chunk_store) if hasattr(self, 'chunk_store') else 0,
                    "unique_documents": len(self.document_store) if hasattr(self, 'document_store') else 0
                }
        
        mock_db = MockVectorDB()
        mock_db.chunk_store = getattr(self, 'chunk_store', {})
        mock_db.document_store = getattr(self, 'document_store', {})
        return mock_db

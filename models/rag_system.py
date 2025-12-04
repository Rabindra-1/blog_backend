import asyncio
from typing import List, Dict, Any, Tuple
import uuid
from ..retrievers import RetrieverManager
from ..retrievers.base import Document
from ..utils.text_processor import TextProcessor, TextChunk
from ..models.embedding_model import EmbeddingModel
from ..vector_store.faiss_db import VectorDatabase
from ..config import config

class RAGSystem:
    """Main RAG system that coordinates retrieval, processing, and storage"""
    
    def __init__(self):
        self.retriever_manager = RetrieverManager()
        self.text_processor = TextProcessor(
            chunk_size=config.MAX_CHUNK_SIZE,
            chunk_overlap=config.CHUNK_OVERLAP
        )
        self.embedding_model = EmbeddingModel()
        self.vector_db = VectorDatabase()
        
        print("RAG System initialized")
    
    async def process_and_store_documents(self, documents: List[Document]) -> bool:
        """Process documents and store them in the vector database"""
        if not documents:
            return False
        
        try:
            all_chunks = []
            
            for doc in documents:
                # Generate unique document ID
                doc_id = f"{doc.source}_{uuid.uuid4().hex[:8]}"
                
                # Chunk the document
                chunks = self.text_processor.chunk_text(doc.content, doc_id)
                
                # Add document metadata to chunks
                for chunk in chunks:
                    chunk.source_doc_id = doc_id
                    # Store original document metadata
                    if not hasattr(chunk, 'doc_metadata'):
                        chunk.doc_metadata = {
                            'title': doc.title,
                            'source': doc.source,
                            'url': doc.url,
                            'original_metadata': doc.metadata
                        }
                
                all_chunks.extend(chunks)
            
            if all_chunks:
                # Generate embeddings for all chunks
                embedded_chunks = self.embedding_model.encode_chunks(all_chunks)
                
                # Store in vector database
                success = self.vector_db.add_chunks(embedded_chunks)
                
                if success:
                    # Save to disk
                    self.vector_db.save()
                    print(f"Processed and stored {len(embedded_chunks)} chunks from {len(documents)} documents")
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
    
    async def search_relevant_content(self, query: str, top_k: int = None) -> List[Tuple[TextChunk, float]]:
        """Search for relevant content in the vector database"""
        top_k = top_k or config.TOP_K_RESULTS
        
        try:
            # Encode the query
            query_embedding = self.embedding_model.encode_text(query)
            
            # Search the vector database
            results = self.vector_db.search(query_embedding, top_k)
            
            print(f"Found {len(results)} relevant chunks for query: '{query}'")
            return results
            
        except Exception as e:
            print(f"Error searching for relevant content: {e}")
            return []
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get the status of all system components"""
        try:
            retriever_status = await self.retriever_manager.get_retriever_status()
            vector_db_stats = self.vector_db.get_stats()
            embedding_model_info = self.embedding_model.get_model_info()
            
            return {
                "retrievers": retriever_status,
                "vector_database": vector_db_stats,
                "embedding_model": embedding_model_info,
                "status": "operational" if all(retriever_status.values()) else "partial"
            }
            
        except Exception as e:
            print(f"Error getting system status: {e}")
            return {"status": "error", "message": str(e)}
    
    async def clear_database(self) -> bool:
        """Clear all stored data"""
        try:
            success = self.vector_db.clear()
            if success:
                print("Database cleared successfully")
            return success
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

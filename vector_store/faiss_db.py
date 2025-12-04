import os
import pickle
import json
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
import faiss
from dataclasses import asdict
from ..utils.text_processor import TextChunk
from ..config import config

class VectorDatabase:
    """FAISS-based vector database for storing and searching document embeddings"""
    
    def __init__(self, db_path: str = None, embedding_dim: int = 384):
        self.db_path = db_path or config.VECTOR_DB_PATH
        self.embedding_dim = embedding_dim
        self.index = None
        self.metadata = {}  # Maps index ID to chunk metadata
        self.chunks = {}    # Maps chunk ID to TextChunk object
        self.next_id = 0
        
        # Create directory if it doesn't exist
        os.makedirs(self.db_path, exist_ok=True)
        
        # Initialize or load existing index
        self._initialize_index()
    
    def _initialize_index(self):
        """Initialize FAISS index"""
        index_path = os.path.join(self.db_path, "faiss_index.bin")
        metadata_path = os.path.join(self.db_path, "metadata.json")
        chunks_path = os.path.join(self.db_path, "chunks.pkl")
        
        if os.path.exists(index_path):
            # Load existing index
            try:
                self.index = faiss.read_index(index_path)
                
                # Load metadata
                if os.path.exists(metadata_path):
                    with open(metadata_path, 'r') as f:
                        self.metadata = json.load(f)
                
                # Load chunks
                if os.path.exists(chunks_path):
                    with open(chunks_path, 'rb') as f:
                        self.chunks = pickle.load(f)
                
                self.next_id = len(self.metadata)
                print(f"Loaded existing index with {self.index.ntotal} vectors")
                
            except Exception as e:
                print(f"Error loading existing index: {e}")
                self._create_new_index()
        else:
            self._create_new_index()
    
    def _create_new_index(self):
        """Create a new FAISS index"""
        try:
            # Use IndexFlatIP for cosine similarity (inner product after normalization)
            self.index = faiss.IndexFlatIP(self.embedding_dim)
            self.metadata = {}
            self.chunks = {}
            self.next_id = 0
            print(f"Created new FAISS index with dimension {self.embedding_dim}")
        except Exception as e:
            print(f"Error creating FAISS index: {e}")
            self.index = None
    
    def add_chunks(self, chunks: List[TextChunk]) -> bool:
        """Add text chunks with embeddings to the database"""
        if not self.index or not chunks:
            return False
        
        try:
            embeddings = []
            chunk_metadata = []
            
            for chunk in chunks:
                if chunk.embedding is not None and chunk.embedding.size > 0:
                    # Normalize embedding for cosine similarity
                    normalized_embedding = chunk.embedding / np.linalg.norm(chunk.embedding)
                    embeddings.append(normalized_embedding)
                    
                    # Store metadata
                    metadata = {
                        'chunk_id': chunk.chunk_id,
                        'source_doc_id': chunk.source_doc_id,
                        'content': chunk.content,
                        'start_pos': chunk.start_pos,
                        'end_pos': chunk.end_pos
                    }
                    chunk_metadata.append(metadata)
                    
                    # Store chunk object
                    self.chunks[chunk.chunk_id] = chunk
            
            if embeddings:
                # Convert to numpy array
                embeddings_array = np.array(embeddings).astype('float32')
                
                # Add to FAISS index
                start_id = self.next_id
                self.index.add(embeddings_array)
                
                # Update metadata
                for i, metadata in enumerate(chunk_metadata):
                    self.metadata[str(start_id + i)] = metadata
                
                self.next_id += len(embeddings)
                
                print(f"Added {len(embeddings)} chunks to vector database")
                return True
                
        except Exception as e:
            print(f"Error adding chunks to vector database: {e}")
            return False
        
        return False
    
    def search(self, query_embedding: np.ndarray, top_k: int = 10) -> List[Tuple[TextChunk, float]]:
        """Search for similar chunks in the database"""
        if not self.index or self.index.ntotal == 0:
            return []
        
        try:
            # Normalize query embedding
            query_embedding = query_embedding / np.linalg.norm(query_embedding)
            query_embedding = query_embedding.astype('float32').reshape(1, -1)
            
            # Search FAISS index
            top_k = min(top_k, self.index.ntotal)
            similarities, indices = self.index.search(query_embedding, top_k)
            
            results = []
            for i, (similarity, idx) in enumerate(zip(similarities[0], indices[0])):
                if idx >= 0:  # Valid index
                    metadata = self.metadata.get(str(idx))
                    if metadata:
                        chunk_id = metadata['chunk_id']
                        chunk = self.chunks.get(chunk_id)
                        if chunk:
                            results.append((chunk, float(similarity)))
            
            return results
            
        except Exception as e:
            print(f"Error searching vector database: {e}")
            return []
    
    def save(self) -> bool:
        """Save the index and metadata to disk"""
        if not self.index:
            return False
        
        try:
            index_path = os.path.join(self.db_path, "faiss_index.bin")
            metadata_path = os.path.join(self.db_path, "metadata.json")
            chunks_path = os.path.join(self.db_path, "chunks.pkl")
            
            # Save FAISS index
            faiss.write_index(self.index, index_path)
            
            # Save metadata as JSON
            with open(metadata_path, 'w') as f:
                json.dump(self.metadata, f, indent=2)
            
            # Save chunks as pickle
            with open(chunks_path, 'wb') as f:
                pickle.dump(self.chunks, f)
            
            print(f"Saved vector database with {self.index.ntotal} vectors")
            return True
            
        except Exception as e:
            print(f"Error saving vector database: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector database"""
        if not self.index:
            return {"status": "not_initialized"}
        
        return {
            "status": "initialized",
            "total_vectors": self.index.ntotal,
            "embedding_dimension": self.embedding_dim,
            "total_chunks": len(self.chunks),
            "unique_documents": len(set(chunk.source_doc_id for chunk in self.chunks.values())),
            "database_path": self.db_path
        }
    
    def clear(self) -> bool:
        """Clear all data from the database"""
        try:
            self._create_new_index()
            
            # Remove saved files
            for filename in ["faiss_index.bin", "metadata.json", "chunks.pkl"]:
                file_path = os.path.join(self.db_path, filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
            
            print("Cleared vector database")
            return True
            
        except Exception as e:
            print(f"Error clearing vector database: {e}")
            return False

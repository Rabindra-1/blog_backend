import numpy as np
from typing import List, Union
from sentence_transformers import SentenceTransformer
import torch
from ..config import config
from ..utils.text_processor import TextChunk

class EmbeddingModel:
    """Handles text embedding generation using SentenceTransformers"""
    
    def __init__(self, model_name: str = None):
        self.model_name = model_name or config.EMBEDDING_MODEL
        self.model = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._load_model()
    
    def _load_model(self):
        """Load the embedding model"""
        try:
            print(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name, device=self.device)
            print(f"Model loaded successfully on device: {self.device}")
        except Exception as e:
            print(f"Error loading embedding model: {e}")
            # Fallback to a smaller model
            try:
                self.model_name = "all-MiniLM-L6-v2"
                self.model = SentenceTransformer(self.model_name, device=self.device)
                print(f"Loaded fallback model: {self.model_name}")
            except Exception as e2:
                print(f"Failed to load fallback model: {e2}")
                self.model = None
    
    def encode_text(self, text: str) -> np.ndarray:
        """Encode a single text into an embedding vector"""
        if not self.model:
            return np.zeros(384)  # Default embedding size
        
        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding
        except Exception as e:
            print(f"Error encoding text: {e}")
            return np.zeros(384)
    
    def encode_texts(self, texts: List[str]) -> List[np.ndarray]:
        """Encode multiple texts into embedding vectors"""
        if not self.model or not texts:
            return [np.zeros(384) for _ in texts]
        
        try:
            embeddings = self.model.encode(texts, convert_to_numpy=True, batch_size=32)
            return [embedding for embedding in embeddings]
        except Exception as e:
            print(f"Error encoding texts: {e}")
            return [np.zeros(384) for _ in texts]
    
    def encode_chunks(self, chunks: List[TextChunk]) -> List[TextChunk]:
        """Encode text chunks and add embeddings to them"""
        if not chunks:
            return chunks
        
        texts = [chunk.content for chunk in chunks]
        embeddings = self.encode_texts(texts)
        
        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding
        
        return chunks
    
    def compute_similarity(self, text1: str, text2: str) -> float:
        """Compute cosine similarity between two texts"""
        if not self.model:
            return 0.0
        
        try:
            embedding1 = self.encode_text(text1)
            embedding2 = self.encode_text(text2)
            
            # Compute cosine similarity
            similarity = np.dot(embedding1, embedding2) / (
                np.linalg.norm(embedding1) * np.linalg.norm(embedding2)
            )
            return float(similarity)
        except Exception as e:
            print(f"Error computing similarity: {e}")
            return 0.0
    
    def compute_similarities(self, query_embedding: np.ndarray, embeddings: List[np.ndarray]) -> List[float]:
        """Compute cosine similarities between a query and multiple embeddings"""
        if not embeddings:
            return []
        
        try:
            similarities = []
            query_norm = np.linalg.norm(query_embedding)
            
            for embedding in embeddings:
                if embedding is not None and embedding.size > 0:
                    similarity = np.dot(query_embedding, embedding) / (
                        query_norm * np.linalg.norm(embedding)
                    )
                    similarities.append(float(similarity))
                else:
                    similarities.append(0.0)
            
            return similarities
        except Exception as e:
            print(f"Error computing similarities: {e}")
            return [0.0] * len(embeddings)
    
    def get_model_info(self) -> dict:
        """Get information about the loaded model"""
        if not self.model:
            return {"status": "not_loaded"}
        
        return {
            "status": "loaded",
            "model_name": self.model_name,
            "device": str(self.device),
            "max_seq_length": getattr(self.model, 'max_seq_length', 'unknown'),
            "embedding_dimension": self.model.get_sentence_embedding_dimension()
        }

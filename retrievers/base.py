from abc import ABC, abstractmethod
from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class Document:
    """Represents a retrieved document with metadata"""
    content: str
    title: str
    source: str
    url: str
    metadata: Dict[str, Any]
    score: float = 0.0

class BaseRetriever(ABC):
    """Abstract base class for all retrievers"""
    
    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
    async def retrieve(self, query: str, max_docs: int = 5) -> List[Document]:
        """
        Retrieve documents relevant to the query
        
        Args:
            query: Search query string
            max_docs: Maximum number of documents to retrieve
            
        Returns:
            List of Document objects
        """
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the retriever service is available"""
        pass
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        import re
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s.,!?;:()\-"]', '', text)
        return text.strip()

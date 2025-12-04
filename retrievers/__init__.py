import asyncio
from typing import List, Dict
from .base import Document
from .wikipedia_retriever import WikipediaRetriever
from .reddit_retriever import RedditRetriever
from .medium_retriever import MediumRetriever

class RetrieverManager:
    """Manages multiple retrievers and aggregates results"""
    
    def __init__(self):
        self.retrievers = [
            WikipediaRetriever(),
            RedditRetriever(),
            MediumRetriever()
        ]
    
    async def retrieve_all(self, query: str, max_docs_per_source: int = 5) -> List[Document]:
        """Retrieve documents from all available sources"""
        all_documents = []
        
        # Create tasks for all retrievers
        tasks = []
        for retriever in self.retrievers:
            if await retriever.is_available():
                task = retriever.retrieve(query, max_docs_per_source)
                tasks.append(task)
            else:
                print(f"Retriever {retriever.name} is not available")
        
        # Execute all retrieval tasks concurrently
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for result in results:
                if isinstance(result, Exception):
                    print(f"Retrieval error: {result}")
                elif isinstance(result, list):
                    all_documents.extend(result)
        
        return all_documents
    
    async def get_retriever_status(self) -> Dict[str, bool]:
        """Get the availability status of all retrievers"""
        status = {}
        tasks = []
        
        for retriever in self.retrievers:
            tasks.append(retriever.is_available())
        
        if tasks:
            results = await asyncio.gather(*tasks)
            for retriever, is_available in zip(self.retrievers, results):
                status[retriever.name] = is_available
        
        return status

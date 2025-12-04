import asyncio
import aiohttp
from typing import List, Dict, Any
import wikipedia
from retrievers.base import BaseRetriever, Document

class WikipediaRetriever(BaseRetriever):
    """Retriever for Wikipedia content using the Wikipedia API"""
    
    def __init__(self):
        super().__init__("Wikipedia")
        # Set Wikipedia language and user agent
        wikipedia.set_lang("en")
        wikipedia.set_rate_limiting(True)
    
    async def retrieve(self, query: str, max_docs: int = 5) -> List[Document]:
        """Retrieve relevant Wikipedia articles"""
        documents = []
        
        try:
            # Search for articles
            loop = asyncio.get_event_loop()
            search_results = await loop.run_in_executor(
                None, wikipedia.search, query, max_docs
            )
            
            for title in search_results[:max_docs]:
                try:
                    # Get page content
                    page = await loop.run_in_executor(
                        None, wikipedia.page, title
                    )
                    
                    # Create document
                    content = self._clean_text(page.content)
                    doc = Document(
                        content=content[:2000],  # Limit content length
                        title=page.title,
                        source="Wikipedia",
                        url=page.url,
                        metadata={
                            "summary": page.summary[:200],
                            "categories": getattr(page, 'categories', [])[:5],
                            "references": len(getattr(page, 'references', [])),
                            "word_count": len(content.split())
                        }
                    )
                    documents.append(doc)
                    
                except wikipedia.exceptions.DisambiguationError as e:
                    # Try the first disambiguation option
                    try:
                        page = await loop.run_in_executor(
                            None, wikipedia.page, e.options[0]
                        )
                        content = self._clean_text(page.content)
                        doc = Document(
                            content=content[:2000],
                            title=page.title,
                            source="Wikipedia",
                            url=page.url,
                            metadata={
                                "summary": page.summary[:200],
                                "disambiguation": True,
                                "word_count": len(content.split())
                            }
                        )
                        documents.append(doc)
                    except Exception:
                        continue
                        
                except wikipedia.exceptions.PageError:
                    # Page doesn't exist, skip
                    continue
                    
                except Exception as e:
                    print(f"Error retrieving Wikipedia page '{title}': {e}")
                    continue
                    
        except Exception as e:
            print(f"Error searching Wikipedia for '{query}': {e}")
            
        return documents
    
    async def is_available(self) -> bool:
        """Check if Wikipedia API is available"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://en.wikipedia.org/api/rest_v1/") as response:
                    return response.status == 200
        except Exception:
            return False

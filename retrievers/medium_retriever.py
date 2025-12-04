import asyncio
import aiohttp
from typing import List, Dict, Any
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse
from retrievers.base import BaseRetriever, Document

class MediumRetriever(BaseRetriever):
    """Retriever for Medium articles using web scraping"""
    
    def __init__(self):
        super().__init__("Medium")
        self.base_url = "https://medium.com"
        self.search_url = "https://medium.com/search"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
    
    async def retrieve(self, query: str, max_docs: int = 5) -> List[Document]:
        """Retrieve relevant Medium articles"""
        documents = []
        
        try:
            async with aiohttp.ClientSession(
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as session:
                # Search Medium
                search_results = await self._search_medium(session, query, max_docs)
                
                # Process each article
                for article_url, title in search_results[:max_docs]:
                    try:
                        article_content = await self._fetch_article_content(session, article_url)
                        if article_content:
                            doc = Document(
                                content=article_content['content'][:2000],
                                title=title,
                                source="Medium",
                                url=article_url,
                                metadata={
                                    'author': article_content.get('author', 'Unknown'),
                                    'publication': article_content.get('publication', ''),
                                    'read_time': article_content.get('read_time', ''),
                                    'claps': article_content.get('claps', 0),
                                    'word_count': len(article_content['content'].split()),
                                    'scraped': True
                                }
                            )
                            documents.append(doc)
                    except Exception as e:
                        print(f"Error fetching Medium article {article_url}: {e}")
                        continue
                        
        except Exception as e:
            print(f"Error retrieving Medium articles for '{query}': {e}")
            
        return documents
    
    async def _search_medium(self, session: aiohttp.ClientSession, query: str, max_results: int) -> List[tuple]:
        """Search Medium for articles matching the query"""
        results = []
        
        try:
            # Try Google search for Medium articles as fallback
            google_query = f"site:medium.com {query}"
            google_search_url = f"https://www.google.com/search?q={google_query}"
            
            async with session.get(google_search_url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Extract Medium links from Google results
                    for link in soup.find_all('a', href=True):
                        href = link.get('href')
                        if href and 'medium.com' in href and '/url?q=' in href:
                            # Extract the actual URL
                            actual_url = href.split('/url?q=')[1].split('&')[0]
                            if 'medium.com' in actual_url and actual_url not in [r[0] for r in results]:
                                title = link.get_text().strip()
                                if title and len(title) > 10:
                                    results.append((actual_url, title))
                                    
                                if len(results) >= max_results:
                                    break
            
            # Fallback: Try to get popular articles from Medium's API-like endpoints
            if not results:
                results = await self._get_medium_trending_articles(session, query, max_results)
                
        except Exception as e:
            print(f"Error searching Medium: {e}")
            
        return results[:max_results]
    
    async def _get_medium_trending_articles(self, session: aiohttp.ClientSession, query: str, max_results: int) -> List[tuple]:
        """Get trending articles from Medium as fallback"""
        results = []
        
        try:
            # Try Medium's topic pages
            topics = ['technology', 'programming', 'data-science', 'artificial-intelligence', 'startup']
            
            for topic in topics:
                if len(results) >= max_results:
                    break
                    
                topic_url = f"https://medium.com/topic/{topic}"
                
                try:
                    async with session.get(topic_url) as response:
                        if response.status == 200:
                            html = await response.text()
                            soup = BeautifulSoup(html, 'html.parser')
                            
                            # Look for article links
                            for link in soup.find_all('a', href=True):
                                href = link.get('href')
                                if href and href.startswith('/'):
                                    href = urljoin(self.base_url, href)
                                    
                                if (href and 'medium.com' in href and 
                                    '@' in href and href not in [r[0] for r in results]):
                                    title = link.get_text().strip()
                                    if title and len(title) > 20:
                                        results.append((href, title))
                                        
                                        if len(results) >= max_results:
                                            break
                                            
                except Exception as e:
                    continue
                    
        except Exception as e:
            print(f"Error getting Medium trending articles: {e}")
            
        return results
    
    async def _fetch_article_content(self, session: aiohttp.ClientSession, url: str) -> Dict[str, Any]:
        """Fetch and parse Medium article content"""
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    return None
                    
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Extract article content
                article = soup.find('article') or soup.find('div', class_=re.compile(r'postArticle'))
                
                if not article:
                    # Try alternative selectors
                    article = soup.find('div', class_=re.compile(r'section-content'))
                
                content = ""
                author = ""
                publication = ""
                read_time = ""
                
                if article:
                    # Extract text content
                    paragraphs = article.find_all(['p', 'h1', 'h2', 'h3', 'h4'])
                    content = ' '.join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
                    
                    # Extract metadata
                    author_elem = soup.find('a', class_=re.compile(r'author')) or soup.find('span', class_=re.compile(r'author'))
                    if author_elem:
                        author = author_elem.get_text().strip()
                    
                    pub_elem = soup.find('a', class_=re.compile(r'publication'))
                    if pub_elem:
                        publication = pub_elem.get_text().strip()
                    
                    time_elem = soup.find('span', class_=re.compile(r'readingTime'))
                    if time_elem:
                        read_time = time_elem.get_text().strip()
                
                # Clean content
                content = self._clean_text(content)
                
                return {
                    'content': content,
                    'author': author,
                    'publication': publication,
                    'read_time': read_time,
                    'claps': 0  # Difficult to extract without authentication
                }
                
        except Exception as e:
            print(f"Error fetching article content from {url}: {e}")
            return None
    
    async def is_available(self) -> bool:
        """Check if Medium is accessible"""
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get("https://medium.com") as response:
                    return response.status == 200
        except Exception:
            return False

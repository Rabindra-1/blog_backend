import asyncio
from typing import List, Dict, Any, Optional
import praw
from praw.models import Submission, Comment
from config import config
from retrievers.base import BaseRetriever, Document

class RedditRetriever(BaseRetriever):
    """Retriever for Reddit content using PRAW"""
    
    def __init__(self):
        super().__init__("Reddit")
        self.reddit: Optional[praw.Reddit] = None
        self._initialize_reddit()
    
    def _initialize_reddit(self):
        """Initialize Reddit API client"""
        if not all([config.REDDIT_CLIENT_ID, config.REDDIT_CLIENT_SECRET]):
            print("Warning: Reddit API credentials not found. Reddit retriever will not work.")
            return
            
        try:
            self.reddit = praw.Reddit(
                client_id=config.REDDIT_CLIENT_ID,
                client_secret=config.REDDIT_CLIENT_SECRET,
                user_agent=config.REDDIT_USER_AGENT,
                check_for_async=False
            )
            # Test the connection
            self.reddit.user.me()
        except Exception as e:
            print(f"Failed to initialize Reddit client: {e}")
            self.reddit = None
    
    async def retrieve(self, query: str, max_docs: int = 5) -> List[Document]:
        """Retrieve relevant Reddit posts and comments"""
        if not self.reddit:
            print("Reddit API not available")
            return []
            
        documents = []
        
        try:
            loop = asyncio.get_event_loop()
            
            # Search for relevant subreddits and posts
            search_results = await loop.run_in_executor(
                None, self._search_reddit, query, max_docs
            )
            
            for result in search_results:
                try:
                    if isinstance(result, Submission):
                        content = result.title
                        if result.selftext:
                            content += f"\n\n{result.selftext}"
                        
                        # Get top comments
                        result.comments.replace_more(limit=0)
                        top_comments = []
                        for comment in result.comments[:3]:
                            if isinstance(comment, Comment) and len(comment.body) > 20:
                                top_comments.append(comment.body[:200])
                        
                        if top_comments:
                            content += f"\n\nTop Comments:\n{chr(10).join(top_comments)}"
                        
                        doc = Document(
                            content=self._clean_text(content)[:2000],
                            title=result.title,
                            source="Reddit",
                            url=f"https://reddit.com{result.permalink}",
                            metadata={
                                "subreddit": str(result.subreddit),
                                "score": result.score,
                                "num_comments": result.num_comments,
                                "created_utc": result.created_utc,
                                "author": str(result.author) if result.author else "[deleted]",
                                "upvote_ratio": getattr(result, 'upvote_ratio', 0),
                                "word_count": len(content.split())
                            }
                        )
                        documents.append(doc)
                        
                except Exception as e:
                    print(f"Error processing Reddit submission: {e}")
                    continue
                    
        except Exception as e:
            print(f"Error searching Reddit for '{query}': {e}")
            
        return documents
    
    def _search_reddit(self, query: str, max_docs: int) -> List[Submission]:
        """Search Reddit using PRAW (blocking call)"""
        results = []
        
        try:
            # Search across all of Reddit
            submissions = self.reddit.subreddit("all").search(
                query, 
                sort="relevance", 
                limit=max_docs * 2  # Get more results to filter
            )
            
            for submission in submissions:
                # Filter out low-quality posts
                if (submission.score > 5 and 
                    submission.num_comments > 2 and
                    len(submission.title) > 10):
                    results.append(submission)
                    
                if len(results) >= max_docs:
                    break
                    
        except Exception as e:
            print(f"Error in Reddit search: {e}")
            
        return results
    
    async def is_available(self) -> bool:
        """Check if Reddit API is available"""
        if not self.reddit:
            return False
            
        try:
            loop = asyncio.get_event_loop()
            # Try a simple API call
            await loop.run_in_executor(
                None, lambda: self.reddit.subreddit("test").display_name
            )
            return True
        except Exception:
            return False

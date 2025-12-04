import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Reddit API
    REDDIT_CLIENT_ID: Optional[str] = os.getenv("REDDIT_CLIENT_ID")
    REDDIT_CLIENT_SECRET: Optional[str] = os.getenv("REDDIT_CLIENT_SECRET")
    REDDIT_USER_AGENT: str = os.getenv("REDDIT_USER_AGENT", "RAGBlogGenerator/1.0")
    
    # OpenAI API
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    
    # Search APIs
    SERPAPI_KEY: Optional[str] = os.getenv("SERPAPI_KEY")
    BING_SEARCH_API_KEY: Optional[str] = os.getenv("BING_SEARCH_API_KEY")
    
    # Vector Database
    VECTOR_DB_PATH: str = os.getenv("VECTOR_DB_PATH", "./vector_store")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    
    # Generation Model
    GENERATOR_MODEL: str = os.getenv("GENERATOR_MODEL", "microsoft/DialoGPT-medium")
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "1024"))
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.7"))
    
    # Server Configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    
    # Retrieval Settings
    MAX_DOCUMENTS_PER_SOURCE: int = 5
    MAX_CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50
    TOP_K_RESULTS: int = 10

config = Config()

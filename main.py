import asyncio
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import uvicorn

from models.simple_rag_system import SimpleRAGSystem
from models.simple_blog_generator import SimpleBlogGenerator
from config import config

# Initialize FastAPI app
app = FastAPI(
    title="RAG Blog Generator API",
    description="Generate blog posts using Retrieval-Augmented Generation from Wikipedia, Reddit, and Medium",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
rag_system = None
blog_generator = None

# Pydantic models for request/response
class BlogRequest(BaseModel):
    topic: str
    max_sources: Optional[int] = 3
    include_preprocessing: Optional[bool] = True

class BlogResponse(BaseModel):
    title: str
    introduction: str
    main_content: str
    conclusion: str
    sources: List[Dict[str, Any]]
    metadata: Dict[str, Any]

class StatusResponse(BaseModel):
    status: str
    components: Dict[str, Any]
    message: Optional[str] = None

@app.on_event("startup")
async def startup_event():
    """Initialize the RAG system and blog generator on startup"""
    global rag_system, blog_generator
    
    print("Initializing RAG Blog Generator API...")
    
    try:
        # Initialize RAG system
        rag_system = SimpleRAGSystem()
        
        # Initialize blog generator
        blog_generator = SimpleBlogGenerator()
        
        print("API initialization completed successfully")
        
    except Exception as e:
        print(f"Error during API initialization: {e}")
        raise e

@app.get("/", response_class=JSONResponse)
async def root():
    """Root endpoint with API information"""
    return {
        "message": "RAG Blog Generator API",
        "version": "1.0.0",
        "endpoints": {
            "generate_blog": "/generate-blog",
            "status": "/status",
            "health": "/health"
        }
    }

@app.get("/health", response_class=JSONResponse)
async def health_check():
    """Health check endpoint"""
    try:
        # Check if core components are working
        if rag_system and blog_generator:
            return {"status": "healthy", "timestamp": "2024-01-01T00:00:00Z"}
        else:
            return {"status": "unhealthy", "message": "Core components not initialized"}
    except Exception as e:
        return {"status": "unhealthy", "message": str(e)}

@app.get("/status", response_model=StatusResponse)
async def get_system_status():
    """Get the status of all RAG system components"""
    try:
        if not rag_system:
            raise HTTPException(status_code=503, detail="RAG system not initialized")
        
        status_data = await rag_system.get_system_status()
        blog_generator_info = blog_generator.get_model_info() if blog_generator else {"status": "not_loaded"}
        
        components = {
            "rag_system": status_data,
            "blog_generator": blog_generator_info
        }
        
        overall_status = "operational" if status_data.get("status") == "operational" else "partial"
        
        return StatusResponse(
            status=overall_status,
            components=components,
            message="System status retrieved successfully"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting system status: {str(e)}")

@app.post("/generate-blog", response_model=BlogResponse)
async def generate_blog_post(request: BlogRequest):
    """Generate a blog post for the given topic"""
    try:
        if not rag_system or not blog_generator:
            raise HTTPException(status_code=503, detail="System components not initialized")
        
        topic = request.topic.strip()
        if not topic:
            raise HTTPException(status_code=400, detail="Topic cannot be empty")
        
        print(f"Generating blog post for topic: '{topic}'")
        
        # Prepare retrieval context (this will fetch and store documents if needed)
        context_data = await rag_system.prepare_retrieval_context(topic)
        
        if 'error' in context_data:
            print(f"Warning: Error in retrieval context: {context_data['error']}")
        
        # Generate blog post
        blog_post = await blog_generator.generate_blog_post(topic, context_data)
        
        return BlogResponse(**blog_post)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error generating blog post: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/preprocess-topic")
async def preprocess_topic(background_tasks: BackgroundTasks, request: BlogRequest):
    """Preprocess a topic by fetching and storing relevant documents"""
    try:
        if not rag_system:
            raise HTTPException(status_code=503, detail="RAG system not initialized")
        
        topic = request.topic.strip()
        if not topic:
            raise HTTPException(status_code=400, detail="Topic cannot be empty")
        
        # Add background task to fetch and store documents
        background_tasks.add_task(rag_system.retrieve_and_store, topic)
        
        return {
            "message": f"Started preprocessing for topic: '{topic}'",
            "topic": topic,
            "status": "processing"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting preprocessing: {str(e)}")

@app.post("/clear-database")
async def clear_database():
    """Clear all stored documents from the vector database"""
    try:
        if not rag_system:
            raise HTTPException(status_code=503, detail="RAG system not initialized")
        
        success = await rag_system.clear_database()
        
        if success:
            return {"message": "Database cleared successfully", "status": "success"}
        else:
            raise HTTPException(status_code=500, detail="Failed to clear database")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing database: {str(e)}")

@app.get("/database-stats")
async def get_database_stats():
    """Get statistics about the vector database"""
    try:
        if not rag_system:
            raise HTTPException(status_code=503, detail="RAG system not initialized")
        
        stats = rag_system.vector_db.get_stats()
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting database stats: {str(e)}")

# Error handlers
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle unexpected exceptions"""
    print(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "message": str(exc)}
    )

if __name__ == "__main__":
    print(f"Starting RAG Blog Generator API on {config.HOST}:{config.PORT}")
    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.DEBUG,
        log_level="info"
    )

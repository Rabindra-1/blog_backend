import asyncio
from typing import Dict, Any, List
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import torch
from ..config import config

class BlogPostGenerator:
    """Generates blog posts from retrieved context using transformers"""
    
    def __init__(self, model_name: str = None):
        self.model_name = model_name or "microsoft/DialoGPT-medium"
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.generator = None
        self.tokenizer = None
        self._load_model()
    
    def _load_model(self):
        """Load the text generation model"""
        try:
            print(f"Loading blog generation model: {self.model_name}")
            
            # Try to load a proper text generation model
            try:
                self.generator = pipeline(
                    "text-generation",
                    model="gpt2-medium",  # Using GPT-2 as it's better for blog generation
                    tokenizer="gpt2-medium",
                    device=0 if torch.cuda.is_available() else -1,
                    pad_token_id=50256
                )
                self.model_name = "gpt2-medium"
                print(f"Loaded text generation model: {self.model_name}")
            except Exception as e:
                print(f"Failed to load gpt2-medium, trying gpt2: {e}")
                # Fallback to smaller GPT-2
                self.generator = pipeline(
                    "text-generation",
                    model="gpt2",
                    tokenizer="gpt2",
                    device=0 if torch.cuda.is_available() else -1,
                    pad_token_id=50256
                )
                self.model_name = "gpt2"
                print(f"Loaded fallback model: {self.model_name}")
                
        except Exception as e:
            print(f"Error loading generation model: {e}")
            self.generator = None
    
    async def generate_blog_post(self, topic: str, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a complete blog post from topic and retrieved context"""
        if not self.generator:
            return self._generate_fallback_blog_post(topic, context_data)
        
        try:
            # Prepare the context
            context_chunks = context_data.get('context_chunks', [])
            sources_used = context_data.get('sources_used', [])
            
            # Create a comprehensive context string
            context_text = self._prepare_context_text(context_chunks)
            
            # Generate blog post components
            title = await self._generate_title(topic, context_text)
            introduction = await self._generate_introduction(topic, title, context_text)
            main_content = await self._generate_main_content(topic, context_text, context_chunks)
            conclusion = await self._generate_conclusion(topic, main_content)
            
            # Compile the full blog post
            blog_post = {
                "title": title,
                "introduction": introduction,
                "main_content": main_content,
                "conclusion": conclusion,
                "sources": self._prepare_sources(context_chunks),
                "metadata": {
                    "topic": topic,
                    "sources_used": sources_used,
                    "total_chunks_used": len(context_chunks),
                    "avg_similarity": context_data.get('avg_similarity', 0),
                    "word_count": len(f"{introduction} {main_content} {conclusion}".split()),
                    "generated_by": self.model_name
                }
            }
            
            return blog_post
            
        except Exception as e:
            print(f"Error generating blog post: {e}")
            return self._generate_fallback_blog_post(topic, context_data)
    
    def _prepare_context_text(self, context_chunks: List[Dict]) -> str:
        """Prepare context text from retrieved chunks"""
        if not context_chunks:
            return ""
        
        # Sort by similarity score
        sorted_chunks = sorted(context_chunks, key=lambda x: x.get('similarity', 0), reverse=True)
        
        # Combine top chunks
        context_parts = []
        for chunk in sorted_chunks[:5]:  # Use top 5 chunks
            source_info = f"[{chunk['source']}] {chunk['title']}"
            context_parts.append(f"{source_info}: {chunk['content'][:300]}")
        
        return "\\n\\n".join(context_parts)
    
    def _generate_fallback_blog_post(self, topic: str, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a fallback blog post when the model is not available"""
        context_chunks = context_data.get('context_chunks', [])
        
        title = f"Understanding {topic.title()}: A Comprehensive Guide"
        
        introduction = f"Welcome to our exploration of {topic}. This comprehensive guide will walk you through the essential concepts, practical applications, and key insights gathered from multiple authoritative sources."
        
        # Generate main content from context
        main_sections = []
        
        if context_chunks:
            # Group by source
            by_source = {}
            for chunk in context_chunks[:6]:
                source = chunk['source']
                if source not in by_source:
                    by_source[source] = []
                by_source[source].append(chunk)
            
            # Create sections
            main_sections.append(f"## What is {topic.title()}?\\n\\n{topic.title()} is an important concept that has gained significant attention across various fields. Understanding its fundamentals is crucial for anyone looking to expand their knowledge in this area.")
            
            for source, chunks in by_source.items():
                content_summary = " ".join([chunk['content'][:150] for chunk in chunks[:2]])
                main_sections.append(f"## Insights from {source}\\n\\n{content_summary}")
            
            main_sections.append(f"## Practical Applications\\n\\nThe applications of {topic} span across multiple domains, offering practical benefits and innovative solutions for various challenges.")
        else:
            main_sections = [
                f"## Understanding {topic.title()}\\n\\n{topic.title()} represents an important area of study with wide-ranging applications and implications.",
                f"## Key Concepts\\n\\nTo fully grasp {topic}, it's essential to understand the fundamental principles and core concepts that define this field.",
                f"## Practical Applications\\n\\nThe practical applications of {topic} demonstrate its real-world value and potential for solving complex problems."
            ]
        
        main_content = "\\n\\n".join(main_sections)
        
        conclusion = f"In conclusion, {topic} offers fascinating opportunities for exploration and application. Whether you're a beginner or looking to deepen your understanding, the insights covered in this guide provide a solid foundation for further learning."
        
        return {
            "title": title,
            "introduction": introduction,
            "main_content": main_content,
            "conclusion": conclusion,
            "sources": self._prepare_sources(context_chunks),
            "metadata": {
                "topic": topic,
                "sources_used": context_data.get('sources_used', []),
                "total_chunks_used": len(context_chunks),
                "avg_similarity": context_data.get('avg_similarity', 0),
                "word_count": len(f"{introduction} {main_content} {conclusion}".split()),
                "generated_by": "fallback_generator",
                "fallback_used": True
            }
        }
    
    def _prepare_sources(self, context_chunks: List[Dict]) -> List[Dict]:
        """Prepare source citations from context chunks"""
        sources = {}
        
        for chunk in context_chunks:
            source_key = f"{chunk['source']}_{chunk['title']}"
            if source_key not in sources:
                sources[source_key] = {
                    "title": chunk['title'],
                    "source": chunk['source'],
                    "url": chunk['url'],
                    "relevance_score": chunk['similarity']
                }
        
        # Sort by relevance
        return sorted(sources.values(), key=lambda x: x['relevance_score'], reverse=True)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the generation model"""
        return {
            "model_name": self.model_name,
            "device": str(self.device),
            "status": "loaded" if self.generator else "not_loaded",
            "supports_generation": self.generator is not None
        }

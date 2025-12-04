import re
from typing import Dict, Any, List
from config import config

class SimpleBlogGenerator:
    """Lightweight blog generator using templates and text processing"""
    
    def __init__(self):
        self.name = "simple_template_generator"
    
    async def generate_blog_post(self, topic: str, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a blog post using template-based approach"""
        context_chunks = context_data.get('context_chunks', [])
        sources_used = context_data.get('sources_used', [])
        
        # Generate components
        title = self._generate_title(topic)
        introduction = self._generate_introduction(topic, context_chunks)
        main_content = self._generate_main_content(topic, context_chunks)
        conclusion = self._generate_conclusion(topic)
        
        return {
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
                "generated_by": self.name,
                "fallback_used": True
            }
        }
    
    def _generate_title(self, topic: str) -> str:
        """Generate an engaging title"""
        topic = topic.strip().title()
        
        title_templates = [
            f"Understanding {topic}: A Comprehensive Guide",
            f"The Complete Guide to {topic}",
            f"{topic}: Everything You Need to Know",
            f"Mastering {topic}: A Beginner's Guide",
            f"Exploring {topic}: Key Insights and Applications"
        ]
        
        # Simple selection based on topic length
        index = len(topic) % len(title_templates)
        return title_templates[index]
    
    def _generate_introduction(self, topic: str, context_chunks: List[Dict]) -> str:
        """Generate introduction paragraph"""
        topic_lower = topic.lower()
        
        intro_templates = [
            f"In today's rapidly evolving world, {topic_lower} has become increasingly important across various fields and industries. This comprehensive guide will explore the key concepts, applications, and insights related to {topic_lower}, providing you with a thorough understanding of this fascinating subject.",
            
            f"Welcome to our in-depth exploration of {topic_lower}. Whether you're a beginner looking to understand the basics or someone seeking to deepen your knowledge, this article will provide valuable insights and practical information about {topic_lower}.",
            
            f"{topic} represents one of the most significant developments in recent years, influencing how we approach problems and create solutions. In this article, we'll dive deep into the world of {topic_lower}, examining its various aspects and real-world applications."
        ]
        
        # Add context-aware introduction if we have sources
        if context_chunks:
            sources = list(set([chunk['source'] for chunk in context_chunks[:3]]))
            source_text = ", ".join(sources[:-1]) + f", and {sources[-1]}" if len(sources) > 1 else sources[0]
            
            context_intro = f"Drawing from authoritative sources including {source_text}, this guide presents a comprehensive overview of {topic_lower}, combining expert insights with practical knowledge to give you a complete picture of this important topic."
            
            intro_templates.append(context_intro)
        
        # Select template based on topic characteristics
        index = len(topic.split()) % len(intro_templates)
        return intro_templates[index]
    
    def _generate_main_content(self, topic: str, context_chunks: List[Dict]) -> str:
        """Generate main content sections"""
        sections = []
        
        # Overview section
        sections.append(f"## What is {topic.title()}?")
        sections.append(f"{topic} encompasses a broad range of concepts and applications that have significant impact across multiple domains. Understanding its fundamental principles is essential for anyone looking to engage with this field effectively.")
        
        # Process context chunks by source
        if context_chunks:
            # Group by source
            by_source = {}
            for chunk in context_chunks[:8]:
                source = chunk['source']
                if source not in by_source:
                    by_source[source] = []
                by_source[source].append(chunk)
            
            # Create sections for each source
            for source, chunks in by_source.items():
                sections.append(f"## Insights from {source}")
                
                # Combine content from this source
                source_content = []
                for chunk in chunks[:2]:  # Use top 2 chunks per source
                    content = chunk['content']
                    # Clean and truncate content
                    content = re.sub(r'\s+', ' ', content)
                    content = content[:300] + "..." if len(content) > 300 else content
                    source_content.append(content)
                
                if source_content:
                    combined = " ".join(source_content)
                    sections.append(f"According to {source}, {combined}")
                else:
                    sections.append(f"Research from {source} provides valuable perspectives on {topic.lower()}, offering unique insights that contribute to our understanding of this complex subject.")
        else:
            # Fallback sections without specific content
            sections.extend([
                f"## Key Concepts",
                f"The fundamental concepts underlying {topic.lower()} form the backbone of understanding in this field. These principles guide practical applications and theoretical developments.",
                
                f"## Applications and Use Cases", 
                f"The practical applications of {topic.lower()} span numerous industries and contexts, demonstrating its versatility and importance in solving real-world problems.",
                
                f"## Current Trends and Developments",
                f"Recent developments in {topic.lower()} continue to push the boundaries of what's possible, opening new opportunities and addressing emerging challenges."
            ])
        
        # Benefits section
        sections.append(f"## Benefits and Advantages")
        sections.append(f"Understanding and implementing {topic.lower()} offers numerous advantages, including improved efficiency, better decision-making capabilities, and enhanced problem-solving approaches that can be applied across various scenarios.")
        
        # Challenges section
        sections.append(f"## Challenges and Considerations")
        sections.append(f"While {topic.lower()} offers significant benefits, it's important to consider potential challenges and limitations. Being aware of these factors helps in making informed decisions and developing effective strategies.")
        
        return "\n\n".join(sections)
    
    def _generate_conclusion(self, topic: str) -> str:
        """Generate conclusion paragraph"""
        topic_lower = topic.lower()
        
        conclusion_templates = [
            f"In conclusion, {topic_lower} represents a fascinating and rapidly evolving field with tremendous potential for growth and innovation. By understanding its key principles and applications, you'll be better equipped to leverage its benefits and contribute to its continued development.",
            
            f"As we've explored throughout this guide, {topic_lower} offers valuable opportunities for learning, growth, and practical application. Whether you're just beginning your journey or looking to expand your existing knowledge, the insights covered here provide a solid foundation for future exploration.",
            
            f"The world of {topic_lower} continues to evolve, presenting new challenges and opportunities for those willing to engage with its complexities. By staying informed and applying these principles, you can make meaningful contributions to this important field."
        ]
        
        # Add personalized conclusion
        conclusion_templates.append(f"Thank you for joining us on this exploration of {topic_lower}. We hope this comprehensive guide has provided you with valuable insights and practical knowledge that you can apply in your own work and studies. The future of {topic_lower} is bright, and your understanding of these concepts positions you well to be part of that exciting journey.")
        
        # Select based on topic characteristics
        index = (len(topic) + len(topic.split())) % len(conclusion_templates)
        return conclusion_templates[index]
    
    def _prepare_sources(self, context_chunks: List[Dict]) -> List[Dict]:
        """Prepare source citations"""
        sources = {}
        
        for chunk in context_chunks:
            source_key = f"{chunk['source']}_{chunk['title']}"
            if source_key not in sources:
                sources[source_key] = {
                    "title": chunk['title'],
                    "source": chunk['source'],
                    "url": chunk['url'],
                    "relevance_score": chunk.get('similarity', 0.8)
                }
        
        # Sort by relevance
        return sorted(sources.values(), key=lambda x: x['relevance_score'], reverse=True)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        return {
            "model_name": self.name,
            "device": "cpu",
            "status": "loaded",
            "supports_generation": True
        }

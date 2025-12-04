import os
import sys
import time
import logging
from typing import Dict, List, Any, Optional, Tuple
from django.conf import settings
from django.contrib.auth.models import User
from blogs.models import Blog
from .models import ChatSession, ChatMessage, ChatPreferences

# Add the project root to Python path to import RAG system
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

try:
    from rag_blog.rag_blog_system import RAGBlogSystem
    from rag_blog.document_processor import load_sample_blog_data
except (ImportError, Exception) as e:
    # Fallback if RAG system is not available or has dependency issues
    RAGBlogSystem = None
    load_sample_blog_data = None
    print(f"RAG system not available: {str(e)}")

logger = logging.getLogger(__name__)


class ChatAssistantService:
    """Service for handling AI chat assistant interactions with RAG capabilities."""
    
    def __init__(self):
        self.rag_system = None
        self.is_initialized = False
        self._initialize_rag_system()
    
    def _initialize_rag_system(self):
        """Initialize the RAG system with existing blog data."""
        try:
            if not RAGBlogSystem:
                logger.warning("RAG system not available, using fallback responses")
                return
                
            # Get API keys from settings
            openai_key = getattr(settings, 'OPENAI_API_KEY', '')
            use_mock = not openai_key or getattr(settings, 'USE_LOCAL_AI', False)
            
            # Initialize RAG system (using mock if no API key)
            self.rag_system = RAGBlogSystem(
                mistral_api_key=None,  # We'll use OpenAI instead
                use_mock=use_mock
            )
            
            # Setup knowledge base with existing blog data
            self._setup_knowledge_base()
            self.is_initialized = True
            
            logger.info(f"Chat Assistant Service initialized (mock={use_mock})")
            
        except Exception as e:
            logger.error(f"Failed to initialize RAG system: {str(e)}")
            self.is_initialized = False
    
    def _setup_knowledge_base(self):
        """Setup knowledge base with existing blog posts and sample data."""
        try:
            documents = []
            
            # Get existing published blog posts
            existing_blogs = Blog.objects.filter(status='published').select_related('author')
            
            for blog in existing_blogs:
                documents.append({
                    'title': blog.title,
                    'content': blog.content,
                    'author': blog.author.username,
                    'category': blog.tags.first().name if blog.tags.exists() else 'General',
                    'created_at': blog.created_at.isoformat(),
                    'slug': blog.slug,
                    'summary': blog.summary or blog.content[:300] + '...'
                })
            
            # Add sample data if we don't have enough content
            if len(documents) < 5 and load_sample_blog_data:
                sample_docs = load_sample_blog_data()
                documents.extend(sample_docs[:10])  # Add up to 10 sample documents
            
            # Setup the knowledge base
            if documents and self.rag_system:
                self.rag_system.setup_knowledge_base(documents=documents)
                logger.info(f"Knowledge base setup with {len(documents)} documents")
            else:
                logger.warning("No documents available for knowledge base")
                
        except Exception as e:
            logger.error(f"Failed to setup knowledge base: {str(e)}")
    
    def get_or_create_preferences(self, user: User) -> ChatPreferences:
        """Get or create chat preferences for user."""
        preferences, created = ChatPreferences.objects.get_or_create(
            user=user,
            defaults={
                'writing_style': 'professional',
                'response_length': 'medium',
                'include_references': True,
                'auto_suggest_topics': True,
                'context_awareness': True,
                'enable_suggestions': True,
                'proactive_assistance': False
            }
        )
        return preferences
    
    def create_chat_session(self, user: User, context_type: str = 'blog_writing', 
                          context_metadata: dict = None) -> ChatSession:
        """Create a new chat session."""
        session = ChatSession.objects.create(
            user=user,
            context_type=context_type,
            context_metadata=context_metadata or {}
        )
        
        # Add welcome message
        welcome_msg = self._get_welcome_message(context_type)
        ChatMessage.objects.create(
            session=session,
            sender='assistant',
            content=welcome_msg,
            message_type='system'
        )
        
        return session
    
    def _get_welcome_message(self, context_type: str) -> str:
        """Get appropriate welcome message based on context."""
        messages = {
            'blog_writing': (
                "👋 Hi! I'm your AI writing assistant. I'm here to help you create amazing blog content! "
                "I can help you:\n"
                "• Brainstorm blog ideas and topics\n"
                "• Write engaging introductions and conclusions\n"
                "• Develop full blog sections\n"
                "• Enhance existing content\n"
                "• Find relevant references from your blog history\n\n"
                "What would you like to work on today?"
            ),
            'content_enhancement': (
                "✨ Ready to enhance your content! I can help improve your existing blog posts by:\n"
                "• Adding more detail and examples\n"
                "• Improving readability and flow\n"
                "• Suggesting related topics\n"
                "• Finding supporting information\n\n"
                "Share the content you'd like me to help with!"
            ),
            'general': (
                "🤖 Hello! I'm your AI assistant. I can help with various writing tasks, "
                "content creation, and answer questions. What can I help you with?"
            )
        }
        return messages.get(context_type, messages['general'])
    
    def process_message(self, session: ChatSession, user_message: str, 
                       context_data: Dict[str, Any] = None) -> ChatMessage:
        """Process user message and generate AI response."""
        start_time = time.time()
        
        # Save user message
        user_msg = ChatMessage.objects.create(
            session=session,
            sender='user',
            content=user_message,
            message_type='text'
        )
        
        try:
            # Get user preferences
            preferences = self.get_or_create_preferences(session.user)
            
            # Generate AI response
            response_content, metadata = self._generate_response(
                user_message=user_message,
                session=session,
                preferences=preferences,
                context_data=context_data or {}
            )
            
            # Determine message type based on content
            message_type = self._determine_message_type(user_message, response_content)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Save AI response
            ai_response = ChatMessage.objects.create(
                session=session,
                sender='assistant',
                content=response_content,
                message_type=message_type,
                metadata=metadata,
                retrieved_documents=metadata.get('retrieved_docs', []),
                context_used=metadata.get('context_used', ''),
                processing_time=processing_time
            )
            
            # Update session
            session.updated_at = ai_response.created_at
            if not session.title:
                session.title = user_message[:50] + ('...' if len(user_message) > 50 else '')
            session.save()
            
            return ai_response
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            
            # Create error response
            error_response = ChatMessage.objects.create(
                session=session,
                sender='assistant',
                content=(
                    "I apologize, but I encountered an error while processing your request. "
                    "Please try again or rephrase your message."
                ),
                message_type='system',
                metadata={'error': str(e)},
                processing_time=time.time() - start_time
            )
            
            return error_response
    
    def _generate_response(self, user_message: str, session: ChatSession, 
                          preferences: ChatPreferences, context_data: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Generate AI response using RAG system or fallback methods."""
        metadata = {'method': 'unknown', 'retrieved_docs': [], 'context_used': ''}
        
        try:
            if self.is_initialized and self.rag_system and self.rag_system.is_ready:
                return self._generate_with_rag(user_message, session, preferences, context_data)
            else:
                return self._generate_fallback_response(user_message, session, preferences)
                
        except Exception as e:
            logger.error(f"Error in response generation: {str(e)}")
            return self._get_error_response(), metadata
    
    def _generate_with_rag(self, user_message: str, session: ChatSession, 
                          preferences: ChatPreferences, context_data: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Generate response using RAG system."""
        try:
            # Determine the type of request
            request_type = self._classify_user_request(user_message)
            
            if request_type == 'blog_generation':
                result = self.rag_system.write_blog_post(
                    topic=user_message,
                    style=preferences.writing_style,
                    length=preferences.response_length,
                    target_audience='general'
                )
                
                response_content = self._format_blog_generation_response(result)
                metadata = {
                    'method': 'rag_blog_generation',
                    'retrieved_docs': result.get('retrieved_docs', []),
                    'context_used': result.get('context_summary', ''),
                    'style': result.get('style'),
                    'length': result.get('length')
                }
                
            elif request_type == 'content_enhancement':
                # Get current blog content from context if available
                existing_content = context_data.get('blog_draft_content', '')
                target_section = context_data.get('target_section', 'General')
                
                enhanced_content = self.rag_system.enhance_existing_content(
                    section_title=target_section,
                    existing_content=existing_content,
                    search_query=user_message
                )
                
                response_content = f"Here's an enhanced version of your content:\n\n{enhanced_content}"
                metadata = {
                    'method': 'rag_enhancement',
                    'target_section': target_section,
                    'original_length': len(existing_content),
                    'enhanced_length': len(enhanced_content)
                }
                
            elif request_type == 'outline_creation':
                result = self.rag_system.create_blog_outline(user_message)
                
                response_content = self._format_outline_response(result)
                metadata = {
                    'method': 'rag_outline',
                    'retrieved_docs': result.get('retrieved_docs', []),
                    'topic': result.get('topic')
                }
                
            else:  # General query or search
                # Search knowledge base for relevant information
                search_results = self.rag_system.search_knowledge_base(user_message, k=3)
                
                response_content = self._format_search_response(user_message, search_results)
                metadata = {
                    'method': 'rag_search',
                    'retrieved_docs': search_results,
                    'query': user_message
                }
            
            return response_content, metadata
            
        except Exception as e:
            logger.error(f"RAG generation error: {str(e)}")
            return self._generate_fallback_response(user_message, session, preferences)
    
    def _classify_user_request(self, message: str) -> str:
        """Classify user request to determine appropriate response type."""
        message_lower = message.lower()
        
        # Keywords for different request types
        if any(word in message_lower for word in ['write', 'create', 'blog post', 'article']):
            return 'blog_generation'
        elif any(word in message_lower for word in ['enhance', 'improve', 'better', 'rewrite']):
            return 'content_enhancement'
        elif any(word in message_lower for word in ['outline', 'structure', 'plan', 'organize']):
            return 'outline_creation'
        else:
            return 'general_query'
    
    def _format_blog_generation_response(self, result: Dict[str, Any]) -> str:
        """Format blog generation result into readable response."""
        content = result.get('content', 'I was unable to generate content for your request.')
        
        response = f"📝 Here's a blog post about **{result.get('topic', 'your topic')}**:\n\n"
        response += content
        
        if result.get('retrieved_docs'):
            response += "\n\n---\n**References used:**\n"
            for i, doc in enumerate(result['retrieved_docs'][:3], 1):
                response += f"{i}. {doc.get('title', 'Untitled')}\n"
        
        return response
    
    def _format_outline_response(self, result: Dict[str, Any]) -> str:
        """Format outline result into readable response."""
        outline = result.get('outline', 'I was unable to create an outline.')
        
        response = f"📋 Here's an outline for **{result.get('topic', 'your topic')}**:\n\n"
        response += outline
        
        return response
    
    def _format_search_response(self, query: str, search_results: List[Dict[str, Any]]) -> str:
        """Format search results into helpful response."""
        if not search_results:
            return (
                f"I searched for information about '{query}' but didn't find specific matches "
                "in the knowledge base. Could you provide more specific details or try a different approach?"
            )
        
        response = f"💡 Based on your query about '{query}', here's what I found:\n\n"
        
        for i, result in enumerate(search_results[:3], 1):
            response += f"**{i}. {result.get('title', 'Untitled')}**\n"
            response += f"{result.get('chunk', result.get('content', ''))[:200]}...\n\n"
        
        response += "Would you like me to elaborate on any of these points or help you create content based on this information?"
        
        return response
    
    def _generate_fallback_response(self, user_message: str, session: ChatSession, 
                                   preferences: ChatPreferences) -> Tuple[str, Dict[str, Any]]:
        """Generate fallback response when RAG system is not available."""
        # Simple rule-based responses for common scenarios
        message_lower = user_message.lower()
        
        if any(word in message_lower for word in ['introduction', 'intro', 'opening']):
            response = self._generate_intro_template(user_message)
            method = 'template_intro'
        elif any(word in message_lower for word in ['conclusion', 'ending', 'closing']):
            response = self._generate_conclusion_template(user_message)
            method = 'template_conclusion'
        elif any(word in message_lower for word in ['outline', 'structure']):
            response = self._generate_outline_template(user_message)
            method = 'template_outline'
        else:
            response = self._generate_general_response(user_message)
            method = 'template_general'
        
        metadata = {
            'method': method,
            'fallback': True,
            'rag_available': False
        }
        
        return response, metadata
    
    def _generate_intro_template(self, topic: str) -> str:
        """Generate introduction template."""
        return f"""Here's a suggested introduction for your blog post:

---

**Introduction:**

In today's digital landscape, {topic.lower()} has become increasingly important. This topic affects many people and deserves our attention.

In this post, we'll explore:
• The key aspects of {topic.lower()}
• Why it matters to you
• Practical insights you can apply

---

Would you like me to help you develop any specific section further?"""
    
    def _generate_conclusion_template(self, topic: str) -> str:
        """Generate conclusion template."""
        return f"""Here's a suggested conclusion for your blog post:

---

**Conclusion:**

Throughout this post, we've explored the important aspects of {topic.lower()}. The key takeaways are:

• [Key point 1 - please customize]
• [Key point 2 - please customize]
• [Key point 3 - please customize]

As you move forward, remember that [your main message here]. 

What are your thoughts on this topic? Share your experiences in the comments below!

---

Feel free to customize this conclusion to match your specific content!"""
    
    def _generate_outline_template(self, topic: str) -> str:
        """Generate outline template."""
        return f"""Here's a suggested outline for your blog post about "{topic}":

---

## Blog Post Outline

### 1. Introduction
- Hook: Start with a compelling question or statistic
- Brief overview of {topic.lower()}
- What readers will learn

### 2. Background/Context
- Why {topic.lower()} matters now
- Current state of the topic

### 3. Main Content (choose 2-4 key points)
- **Point 1:** [Customize based on your angle]
- **Point 2:** [Add your specific insights]
- **Point 3:** [Include practical examples]

### 4. Practical Applications
- How readers can apply this information
- Action steps or recommendations

### 5. Conclusion
- Summarize key points
- Call to action for readers

---

Would you like me to help you develop any of these sections?"""
    
    def _generate_general_response(self, message: str) -> str:
        """Generate general helpful response."""
        return f"""I'd be happy to help you with "{message}"! 

Here are some ways I can assist:

📝 **Content Creation:**
• Write introductions, conclusions, or full sections
• Create blog post outlines
• Develop ideas and topics

✨ **Content Enhancement:**
• Improve existing text
• Add more detail and examples
• Restructure for better flow

🔍 **Research & Ideas:**
• Brainstorm related topics
• Suggest angles and approaches
• Find connections between concepts

What specific aspect would you like to focus on? The more details you provide, the better I can help!"""
    
    def _get_error_response(self) -> str:
        """Get generic error response."""
        return (
            "I apologize, but I'm having trouble processing your request right now. "
            "Please try rephrasing your message or contact support if the issue persists."
        )
    
    def _determine_message_type(self, user_message: str, ai_response: str) -> str:
        """Determine the type of AI message based on content."""
        if any(word in ai_response.lower() for word in ['here\'s a blog post', 'here\'s an article']):
            return 'generation'
        elif any(word in ai_response.lower() for word in ['enhanced version', 'improved']):
            return 'enhancement'
        elif any(word in ai_response.lower() for word in ['outline', 'structure']):
            return 'suggestion'
        else:
            return 'text'
    
    def provide_message_feedback(self, message_id: str, is_helpful: bool, 
                               feedback_notes: str = "") -> bool:
        """Record user feedback on AI message."""
        try:
            message = ChatMessage.objects.get(id=message_id, sender='assistant')
            message.is_helpful = is_helpful
            message.feedback_notes = feedback_notes
            message.save()
            
            logger.info(f"Feedback recorded for message {message_id}: helpful={is_helpful}")
            return True
            
        except ChatMessage.DoesNotExist:
            logger.error(f"Message {message_id} not found for feedback")
            return False
        except Exception as e:
            logger.error(f"Error recording feedback: {str(e)}")
            return False
    
    def get_chat_suggestions(self, session: ChatSession) -> List[str]:
        """Get contextual suggestions for the chat."""
        suggestions = []
        
        if session.context_type == 'blog_writing':
            if session.messages.count() <= 1:  # New session
                suggestions = [
                    "Write me an introduction about...",
                    "Help me brainstorm ideas for...",
                    "Create an outline for a blog about...",
                    "What are trending topics in..."
                ]
            else:
                suggestions = [
                    "Expand on this section",
                    "Make this more engaging",
                    "Add examples to this content",
                    "Write a conclusion for this"
                ]
        
        return suggestions

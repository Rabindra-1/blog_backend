import time
import logging
from typing import Dict, Any
from django.contrib.auth.models import User
from .models import ChatSession, ChatMessage, ChatPreferences

logger = logging.getLogger(__name__)


class SimpleChatService:
    """Simplified chat service that doesn't depend on RAG system - for testing."""
    
    def __init__(self):
        self.is_initialized = True
    
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
        welcome_msg = self._get_welcome_message(context_type, user)
        ChatMessage.objects.create(
            session=session,
            sender='assistant',
            content=welcome_msg,
            message_type='system'
        )
        
        return session
    
    def _get_welcome_message(self, context_type: str, user=None) -> str:
        """Get appropriate welcome message based on context."""
        username = user.first_name if user and user.first_name else (user.username if user else "there")
        messages = {
            'blog_writing': (
                f"👋 Hi {username}! I'm your AI writing assistant. I'm here to help you create amazing blog content! "
                "I can help you:\n"
                "• Brainstorm blog ideas and topics\n"
                "• Write engaging introductions and conclusions\n"
                "• Develop full blog sections\n"
                "• Enhance existing content\n\n"
                "What would you like to work on today?"
            ),
            'content_enhancement': (
                f"✨ Ready to enhance your content, {username}! I can help improve your existing blog posts.\n\n"
                "Share the content you'd like me to help with!"
            ),
            'general': (
                f"🤖 Hello {username}! I'm your AI assistant. I can help with various writing tasks. "
                "What can I help you with?"
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
            # Generate simple response
            response_content = self._generate_simple_response(user_message, context_data or {}, session.user)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Save AI response
            ai_response = ChatMessage.objects.create(
                session=session,
                sender='assistant',
                content=response_content,
                message_type='text',
                metadata={'method': 'simple_template'},
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
    
    def _generate_simple_response(self, user_message: str, context_data: Dict[str, Any], user=None) -> str:
        """Generate a simple response based on keywords."""
        message_lower = user_message.lower()
        
        # Check for different types of requests
        if any(word in message_lower for word in ['introduction', 'intro', 'opening']):
            return self._generate_intro_response(user_message)
        elif any(word in message_lower for word in ['conclusion', 'ending', 'closing']):
            return self._generate_conclusion_response(user_message)
        elif any(word in message_lower for word in ['outline', 'structure', 'plan']):
            return self._generate_outline_response(user_message)
        elif any(word in message_lower for word in ['write', 'create', 'help me with']):
            return self._generate_writing_help_response(user_message)
        elif any(word in message_lower for word in ['improve', 'enhance', 'better']):
            return self._generate_improvement_response(user_message, context_data)
        elif any(word in message_lower for word in ['hello', 'hi', 'hey']):
            return self._generate_greeting_response(user)
        else:
            return self._generate_general_response(user_message)
    
    def _generate_intro_response(self, topic: str) -> str:
        return f"""Here's a suggested introduction for your blog post:

**Introduction:**

In today's digital landscape, this topic has become increasingly relevant. Whether you're a beginner or looking to deepen your understanding, this post will provide valuable insights.

In this article, we'll explore:
• Key concepts and fundamentals
• Practical applications and examples
• Best practices and tips

Let's dive in and discover how this can benefit you!

---

Would you like me to help you develop any specific section further?"""
    
    def _generate_conclusion_response(self, topic: str) -> str:
        return f"""Here's a suggested conclusion for your blog post:

**Conclusion:**

Throughout this post, we've covered the essential aspects of your topic. The key takeaways are:

• Understanding the fundamentals is crucial
• Practical application leads to better results
• Continuous learning and improvement matter

As you move forward, remember that success comes from applying what you've learned consistently.

What's your next step? Start implementing these insights today!

---

Feel free to customize this conclusion to match your specific content!"""
    
    def _generate_outline_response(self, topic: str) -> str:
        return f"""Here's a suggested outline for your blog post:

## Blog Post Outline

### 1. Introduction
- Hook: Start with a compelling question or statistic
- Brief overview of the topic
- What readers will learn

### 2. Background/Context
- Why this topic matters now
- Current state and trends

### 3. Main Content (3-4 key points)
- **Point 1:** Core concept explanation
- **Point 2:** Practical applications
- **Point 3:** Best practices and tips
- **Point 4:** Common challenges and solutions

### 4. Examples and Case Studies
- Real-world applications
- Success stories
- Lessons learned

### 5. Conclusion
- Summarize key points
- Call to action for readers

---

Would you like me to help you develop any of these sections in detail?"""
    
    def _generate_writing_help_response(self, message: str) -> str:
        return f"""I'd love to help you with your writing project! 

Based on your request: "{message}"

Here's how I can assist:

📝 **Content Creation:**
• Write engaging introductions and conclusions
• Develop detailed sections and paragraphs
• Create compelling headlines and subheadings

✨ **Content Enhancement:**
• Improve existing text for clarity and flow
• Add examples and supporting details
• Enhance readability and engagement

🎯 **Structure & Organization:**
• Create detailed outlines
• Suggest logical flow and organization
• Help with transitions between sections

What specific aspect would you like to start with? The more details you provide about your topic and goals, the better I can help you!"""
    
    def _generate_improvement_response(self, message: str, context_data: Dict[str, Any]) -> str:
        current_content = context_data.get('blog_draft_content', '')
        
        if current_content:
            return f"""I'd be happy to help improve your content! 

Based on the content you're working on, here are some suggestions:

✨ **Enhancement Ideas:**
• Add more specific examples and details
• Improve the flow between paragraphs
• Strengthen your opening and closing
• Include more engaging language

📊 **Structure Improvements:**
• Use more descriptive subheadings
• Break up long paragraphs
• Add bullet points for clarity
• Include transitional phrases

🎯 **Engagement Boosters:**
• Ask questions to involve readers
• Add personal anecdotes or stories
• Include actionable tips
• Use stronger, more vivid language

Would you like me to work on any specific section? Just let me know which part you'd like to improve!"""
        else:
            return "I'd be happy to help improve your content! Please share the text you'd like me to enhance, and I'll provide specific suggestions for making it better."
    
    def _generate_greeting_response(self, user=None) -> str:
        username = user.first_name if user and user.first_name else (user.username if user else "there")
        return f"""Hello {username}! 👋 Great to see you here! 

I'm your AI writing assistant, and I'm excited to help you create amazing blog content. Here's what I can help you with:

🚀 **Quick Start Options:**
• "Help me write an introduction about [your topic]"
• "Create an outline for a blog about [your topic]"
• "Improve this section: [paste your text]"
• "What should I write about [your industry/interest]?"

💡 **Popular Requests:**
• Blog post introductions and conclusions
• Content outlines and structure
• Improving existing content
• Brainstorming ideas and topics

What would you like to work on today? Just tell me about your project!"""
    
    def _generate_general_response(self, message: str) -> str:
        return f"""Thanks for your message! I understand you're asking about: "{message}"

Here are some ways I can help with your blog writing:

📝 **Content Creation:**
• Write compelling introductions
• Develop detailed sections
• Create engaging conclusions
• Craft attention-grabbing headlines

🔍 **Content Strategy:**
• Brainstorm topic ideas
• Create content outlines
• Suggest angles and approaches
• Plan content structure

✨ **Content Improvement:**
• Enhance existing text
• Improve readability and flow
• Add examples and details
• Strengthen key messages

Could you be more specific about what you'd like help with? For example:
• "Help me write about [specific topic]"
• "Improve this paragraph: [your text]"
• "Create an outline for [your subject]"

The more details you provide, the better I can assist you!"""
    
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
    
    def get_chat_suggestions(self, session: ChatSession) -> list[str]:
        """Get contextual suggestions for the chat."""
        if session.context_type == 'blog_writing':
            if session.messages.count() <= 1:  # New session
                return [
                    "Write me an introduction about...",
                    "Help me brainstorm ideas for...",
                    "Create an outline for a blog about...",
                    "What should I write about today?"
                ]
            else:
                return [
                    "Expand on this section",
                    "Make this more engaging",
                    "Add examples to this content",
                    "Write a conclusion for this"
                ]
        
        return ["How can I help you today?", "Tell me about your project", "What would you like to write?"]

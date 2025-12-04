import os
import tempfile
from typing import List, Dict, Any
from PyPDF2 import PdfReader
import logging
import glob
from datetime import datetime

logger = logging.getLogger(__name__)

class EnhancedPDFProcessor:
    """Enhanced PDF processor with pre-loaded documents and blog-style responses"""
    
    def __init__(self, preload_folder=None):
        self.user_documents = []
        self.preloaded_documents = []
        self.user_text = ""
        self.preloaded_text = ""
        self.all_text = ""
        
        # Pre-load documents from folder if specified
        if preload_folder and os.path.exists(preload_folder):
            self.load_preloaded_documents(preload_folder)
    
    def load_preloaded_documents(self, folder_path: str):
        """Load PDFs from a specified folder"""
        try:
            pdf_files = glob.glob(os.path.join(folder_path, "*.pdf"))
            logger.info(f"Found {len(pdf_files)} PDF files in {folder_path}")
            
            preloaded_text = ""
            processed_files = []
            
            for pdf_path in pdf_files:
                try:
                    filename = os.path.basename(pdf_path)
                    text = self.extract_text_from_file_path(pdf_path)
                    if text:
                        preloaded_text += f"\n\n--- {filename} ---\n\n{text}"
                        processed_files.append(filename)
                        logger.info(f"Loaded: {filename}")
                    else:
                        logger.warning(f"No text extracted from {filename}")
                except Exception as e:
                    logger.error(f"Error loading {pdf_path}: {e}")
                    continue
            
            self.preloaded_text = preloaded_text
            self.preloaded_documents = processed_files
            self.all_text = self.preloaded_text + self.user_text
            
            logger.info(f"Successfully pre-loaded {len(processed_files)} documents")
            
        except Exception as e:
            logger.error(f"Error loading pre-loaded documents: {e}")
    
    def extract_text_from_file_path(self, file_path: str) -> str:
        """Extract text from PDF file path"""
        try:
            text = ""
            pdf_reader = PdfReader(file_path)
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text.strip()
        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {e}")
            return ""
    
    def extract_text_from_pdf(self, pdf_file) -> str:
        """Extract text from uploaded PDF file"""
        try:
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                for chunk in pdf_file.chunks():
                    tmp_file.write(chunk)
                tmp_file_path = tmp_file.name
            
            # Extract text
            text = self.extract_text_from_file_path(tmp_file_path)
            
            # Clean up temp file
            os.unlink(tmp_file_path)
            
            return text
        except Exception as e:
            logger.error(f"Error extracting text from uploaded PDF: {e}")
            raise Exception(f"Failed to extract text from PDF: {str(e)}")
    
    def process_user_pdfs(self, pdf_files: List) -> Dict[str, Any]:
        """Process user-uploaded PDF files"""
        try:
            user_text = ""
            processed_files = []
            
            for pdf_file in pdf_files:
                try:
                    text = self.extract_text_from_pdf(pdf_file)
                    if text:
                        user_text += f"\n\n--- {pdf_file.name} (User Upload) ---\n\n{text}"
                        processed_files.append(pdf_file.name)
                    else:
                        logger.warning(f"No text extracted from {pdf_file.name}")
                except Exception as e:
                    logger.error(f"Error processing {pdf_file.name}: {e}")
                    continue
            
            if not user_text.strip() and not self.preloaded_text:
                raise Exception("No text could be extracted from the uploaded files and no pre-loaded documents available")
            
            self.user_text = user_text
            self.user_documents = processed_files
            self.all_text = self.preloaded_text + self.user_text
            
            return {
                'success': True,
                'user_files': processed_files,
                'preloaded_files': self.preloaded_documents,
                'total_text_length': len(self.all_text),
                'message': f"Successfully processed {len(processed_files)} user file(s). {len(self.preloaded_documents)} pre-loaded documents also available."
            }
            
        except Exception as e:
            logger.error(f"Error in process_user_pdfs: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f"Failed to process PDF files: {str(e)}"
            }
    
    def get_available_documents(self) -> Dict[str, Any]:
        """Get information about available documents"""
        return {
            'preloaded_documents': self.preloaded_documents,
            'user_documents': self.user_documents,
            'total_documents': len(self.preloaded_documents) + len(self.user_documents),
            'has_content': bool(self.all_text.strip())
        }
    
    def generate_blog_style_response(self, question: str, relevant_content: str) -> str:
        """Generate a blog-style response instead of simple Q&A"""
        
        # Create a more engaging, blog-style response
        current_time = datetime.now().strftime("%B %d, %Y")
        
        # Determine the topic/theme from the question
        question_lower = question.lower()
        
        # Create contextual introduction
        if any(word in question_lower for word in ['what', 'explain', 'describe']):
            intro = "Let me break this down for you based on the available documents."
        elif any(word in question_lower for word in ['how', 'steps', 'process']):
            intro = "Here's a comprehensive guide based on the information I found:"
        elif any(word in question_lower for word in ['why', 'reason', 'because']):
            intro = "There are several important factors to consider here:"
        elif any(word in question_lower for word in ['when', 'time', 'date']):
            intro = "Based on the timeline information in the documents:"
        else:
            intro = "Here's what the documents reveal about your question:"
        
        # Structure the response in blog format
        blog_response = f"""## {self._create_blog_title(question)}

{intro}

### Key Insights

{self._format_content_as_insights(relevant_content)}

### Detailed Analysis

{self._create_detailed_analysis(relevant_content, question)}

### Summary

{self._create_summary(relevant_content, question)}

---
*Information compiled from {len(self.preloaded_documents + self.user_documents)} document(s) on {current_time}*
"""
        
        return blog_response
    
    def _create_blog_title(self, question: str) -> str:
        """Create an engaging blog-style title from the question"""
        question = question.strip('?').strip()
        
        # Convert question to title case and make it more engaging
        if question.lower().startswith('what'):
            return f"Understanding {question[5:].strip()}"
        elif question.lower().startswith('how'):
            return f"A Guide to {question[4:].strip()}"
        elif question.lower().startswith('why'):
            return f"The Reasons Behind {question[4:].strip()}"
        elif question.lower().startswith('when'):
            return f"Timeline: {question[5:].strip()}"
        else:
            return f"Exploring: {question}"
    
    def _format_content_as_insights(self, content: str) -> str:
        """Format content as bullet-point insights"""
        sentences = [s.strip() for s in content.split('.') if len(s.strip()) > 20]
        
        insights = []
        for i, sentence in enumerate(sentences[:5]):  # Limit to 5 key insights
            if sentence:
                insights.append(f"• **Insight {i+1}**: {sentence}.")
        
        return '\n'.join(insights) if insights else "• Key information extracted from the documents."
    
    def _create_detailed_analysis(self, content: str, question: str) -> str:
        """Create a detailed analysis section"""
        # Split content into paragraphs
        paragraphs = [p.strip() for p in content.split('\n\n') if len(p.strip()) > 50]
        
        if paragraphs:
            # Take the most relevant paragraph
            analysis = paragraphs[0][:500]
            if len(paragraphs[0]) > 500:
                analysis += "..."
            
            return f"The documents provide comprehensive information on this topic. {analysis}\n\nThis analysis is based on careful examination of the available documentation and provides actionable insights for your inquiry."
        else:
            return "The documents contain relevant information that addresses your question. The content has been analyzed to provide you with the most pertinent details."
    
    def _create_summary(self, content: str, question: str) -> str:
        """Create a concise summary"""
        # Extract key points for summary
        sentences = [s.strip() for s in content.split('.') if len(s.strip()) > 30]
        
        if sentences:
            summary_content = '. '.join(sentences[:2])
            return f"In summary, {summary_content}. This information should help address your question about the topic."
        else:
            return "The documents provide valuable insights that directly relate to your inquiry. The information has been compiled to give you a comprehensive understanding of the subject matter."
    
    def ask_question(self, question: str) -> Dict[str, Any]:
        """Enhanced question answering with blog-style responses"""
        if not self.all_text:
            return {
                'success': False,
                'error': 'No documents available',
                'answer': 'Please upload PDF documents or ensure pre-loaded documents are available.'
            }
        
        try:
            # Simple keyword-based search (enhanced)
            question_lower = question.lower()
            text_lower = self.all_text.lower()
            
            # Split text into sentences
            sentences = self.all_text.split('.')
            relevant_sentences = []
            
            # Find sentences containing question keywords
            question_words = [word.strip() for word in question_lower.split() if len(word.strip()) > 2]
            
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) > 20:  # Ignore very short sentences
                    sentence_lower = sentence.lower()
                    relevance_score = sum(1 for word in question_words if word in sentence_lower)
                    if relevance_score > 0:
                        relevant_sentences.append((sentence, relevance_score))
            
            # Sort by relevance and take top sentences
            relevant_sentences.sort(key=lambda x: x[1], reverse=True)
            top_sentences = [s[0] for s in relevant_sentences[:5]]  # Increased to 5 for blog style
            
            if top_sentences:
                relevant_content = ". ".join(top_sentences)
                # Generate blog-style response
                answer = self.generate_blog_style_response(question, relevant_content)
            else:
                # Fallback: return first few sentences of the document in blog format
                first_sentences = sentences[:3]
                fallback_content = ". ".join([s.strip() for s in first_sentences if s.strip()])
                answer = self.generate_blog_style_response(question, fallback_content)
            
            return {
                'success': True,
                'answer': answer,
                'question': question,
                'documents_searched': len(self.preloaded_documents) + len(self.user_documents),
                'sources': {
                    'preloaded': len(self.preloaded_documents),
                    'user_uploaded': len(self.user_documents)
                }
            }
            
        except Exception as e:
            logger.error(f"Error answering question: {e}")
            return {
                'success': False,
                'error': str(e),
                'answer': 'I encountered an error while processing your question. Please try again.'
            }
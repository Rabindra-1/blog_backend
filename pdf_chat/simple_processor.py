import os
import tempfile
from typing import List, Dict, Any
from PyPDF2 import PdfReader
import logging

logger = logging.getLogger(__name__)

class SimplePDFProcessor:
    """Simplified PDF processor for testing"""
    
    def __init__(self):
        self.documents = []
        self.processed_text = ""
    
    def extract_text_from_pdf(self, pdf_file) -> str:
        """Extract text from uploaded PDF file"""
        try:
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                for chunk in pdf_file.chunks():
                    tmp_file.write(chunk)
                tmp_file_path = tmp_file.name
            
            # Extract text
            text = ""
            pdf_reader = PdfReader(tmp_file_path)
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            
            # Clean up temp file
            os.unlink(tmp_file_path)
            
            return text.strip()
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            raise Exception(f"Failed to extract text from PDF: {str(e)}")
    
    def process_pdfs(self, pdf_files: List) -> Dict[str, Any]:
        """Process multiple PDF files"""
        try:
            all_text = ""
            processed_files = []
            
            for pdf_file in pdf_files:
                try:
                    text = self.extract_text_from_pdf(pdf_file)
                    if text:
                        all_text += f"\n\n--- {pdf_file.name} ---\n\n{text}"
                        processed_files.append(pdf_file.name)
                    else:
                        logger.warning(f"No text extracted from {pdf_file.name}")
                except Exception as e:
                    logger.error(f"Error processing {pdf_file.name}: {e}")
                    continue
            
            if not all_text.strip():
                raise Exception("No text could be extracted from the uploaded files")
            
            self.processed_text = all_text
            self.documents = processed_files
            
            return {
                'success': True,
                'processed_files': processed_files,
                'total_text_length': len(all_text),
                'message': f"Successfully processed {len(processed_files)} PDF file(s)"
            }
            
        except Exception as e:
            logger.error(f"Error in process_pdfs: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f"Failed to process PDF files: {str(e)}"
            }
    
    def ask_question(self, question: str) -> Dict[str, Any]:
        """Simple question answering based on extracted text"""
        if not self.processed_text:
            return {
                'success': False,
                'error': 'No documents processed yet',
                'answer': 'Please upload and process PDF documents first.'
            }
        
        try:
            # Simple keyword-based search
            question_lower = question.lower()
            text_lower = self.processed_text.lower()
            
            # Split text into sentences
            sentences = self.processed_text.split('.')
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
            top_sentences = [s[0] for s in relevant_sentences[:3]]
            
            if top_sentences:
                answer = "Based on the uploaded documents, here's what I found:\n\n"
                answer += ". ".join(top_sentences)
                if not answer.endswith('.'):
                    answer += "."
            else:
                # Fallback: return first few sentences of the document
                first_sentences = sentences[:3]
                answer = "I couldn't find specific information about your question, but here's some content from the documents:\n\n"
                answer += ". ".join([s.strip() for s in first_sentences if s.strip()])
            
            return {
                'success': True,
                'answer': answer,
                'question': question,
                'documents_searched': len(self.documents)
            }
            
        except Exception as e:
            logger.error(f"Error answering question: {e}")
            return {
                'success': False,
                'error': str(e),
                'answer': 'I encountered an error while processing your question. Please try again.'
            }
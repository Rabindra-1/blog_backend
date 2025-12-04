import re
from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class TextChunk:
    """Represents a chunk of text with metadata"""
    content: str
    chunk_id: str
    source_doc_id: str
    start_pos: int
    end_pos: int

class SimpleTextProcessor:
    """Lightweight text processor without heavy ML dependencies"""
    
    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        if not text:
            return ""
        
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text)
        
        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # Remove email addresses
        text = re.sub(r'\S+@\S+', '', text)
        
        # Remove excessive punctuation
        text = re.sub(r'[.]{3,}', '...', text)
        text = re.sub(r'[!]{2,}', '!', text)
        text = re.sub(r'[?]{2,}', '?', text)
        
        # Remove non-printable characters (keep basic punctuation)
        text = re.sub(r'[^\x20-\x7E]', '', text)
        
        # Remove extra spaces
        text = re.sub(r' +', ' ', text)
        
        return text.strip()
    
    def chunk_text(self, text: str, doc_id: str) -> List[TextChunk]:
        """Split text into overlapping chunks"""
        if not text:
            return []
        
        # Clean the text first
        text = self.clean_text(text)
        
        # Simple sentence splitting using punctuation
        sentences = self._simple_sentence_split(text)
        
        chunks = []
        current_chunk = ""
        current_start = 0
        chunk_count = 0
        
        for i, sentence in enumerate(sentences):
            # Check if adding this sentence would exceed chunk size
            test_chunk = current_chunk + " " + sentence if current_chunk else sentence
            
            if len(test_chunk.split()) <= self.chunk_size:
                current_chunk = test_chunk
            else:
                # Save current chunk if it has content
                if current_chunk:
                    chunk = TextChunk(
                        content=current_chunk.strip(),
                        chunk_id=f"{doc_id}_chunk_{chunk_count}",
                        source_doc_id=doc_id,
                        start_pos=current_start,
                        end_pos=current_start + len(current_chunk)
                    )
                    chunks.append(chunk)
                    chunk_count += 1
                
                # Start new chunk with overlap
                if self.chunk_overlap > 0 and chunks:
                    # Find overlap words
                    overlap_words = current_chunk.split()[-self.chunk_overlap:]
                    current_chunk = " ".join(overlap_words) + " " + sentence
                else:
                    current_chunk = sentence
                
                current_start += len(current_chunk) - len(sentence)
        
        # Add the last chunk
        if current_chunk:
            chunk = TextChunk(
                content=current_chunk.strip(),
                chunk_id=f"{doc_id}_chunk_{chunk_count}",
                source_doc_id=doc_id,
                start_pos=current_start,
                end_pos=current_start + len(current_chunk)
            )
            chunks.append(chunk)
        
        return chunks
    
    def _simple_sentence_split(self, text: str) -> List[str]:
        """Simple sentence splitting using regex"""
        # Split on sentence-ending punctuation
        sentences = re.split(r'[.!?]+\s+', text)
        
        # Filter out empty sentences and clean up
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # If sentences are too long, split on other punctuation
        final_sentences = []
        for sentence in sentences:
            if len(sentence.split()) > 50:  # If sentence is too long
                # Split on commas, semicolons, etc.
                sub_sentences = re.split(r'[,;:]\s+', sentence)
                final_sentences.extend([s.strip() for s in sub_sentences if s.strip()])
            else:
                final_sentences.append(sentence)
        
        return final_sentences
    
    def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """Extract basic keywords using simple heuristics"""
        if not text:
            return []
        
        # Simple keyword extraction - get capitalized words and common nouns
        words = text.split()
        keywords = set()
        
        # Basic stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of',
            'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have',
            'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they'
        }
        
        for word in words:
            # Clean word
            clean_word = re.sub(r'[^\w]', '', word.lower())
            
            # Skip stop words and short words
            if clean_word and len(clean_word) > 2 and clean_word not in stop_words:
                # Prefer capitalized words (likely proper nouns)
                if word[0].isupper() or len(clean_word) > 5:
                    keywords.add(clean_word)
        
        return list(keywords)[:max_keywords]
    
    def get_text_stats(self, text: str) -> Dict[str, Any]:
        """Get basic statistics about the text"""
        if not text:
            return {}
        
        words = text.split()
        sentences = self._simple_sentence_split(text)
        
        return {
            'word_count': len(words),
            'sentence_count': len(sentences),
            'character_count': len(text),
            'avg_words_per_sentence': len(words) / len(sentences) if sentences else 0,
            'readability_score': self._simple_readability_score(words, sentences)
        }
    
    def _simple_readability_score(self, words: List[str], sentences: List[str]) -> float:
        """Calculate a simple readability score"""
        if not words or not sentences:
            return 50.0
        
        avg_sentence_length = len(words) / len(sentences)
        avg_word_length = sum(len(word) for word in words) / len(words)
        
        # Simple formula: shorter sentences and words = higher readability
        score = max(0, min(100, 100 - (avg_sentence_length * 2) - (avg_word_length * 5)))
        return score

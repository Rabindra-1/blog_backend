import re
import nltk
from typing import List, Dict, Any
from dataclasses import dataclass
import spacy
from sentence_transformers import SentenceTransformer
import numpy as np

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

@dataclass
class TextChunk:
    """Represents a chunk of text with metadata"""
    content: str
    chunk_id: str
    source_doc_id: str
    start_pos: int
    end_pos: int
    embedding: np.ndarray = None

class TextProcessor:
    """Handles text preprocessing, cleaning, and chunking"""
    
    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.nlp = None
        self.embedding_model = None
        
        # Initialize spaCy model (download if needed)
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            print("spaCy English model not found. Install with: python -m spacy download en_core_web_sm")
            self.nlp = None
    
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
        
        # Remove non-printable characters
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
        
        # Split into sentences using NLTK
        try:
            sentences = nltk.sent_tokenize(text)
        except:
            # Fallback to simple splitting
            sentences = text.split('. ')
        
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
                    # Find overlap sentences
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
    
    def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """Extract key terms from text using spaCy"""
        if not self.nlp or not text:
            return []
        
        try:
            doc = self.nlp(text)
            
            # Extract named entities and important nouns
            keywords = set()
            
            # Add named entities
            for ent in doc.ents:
                if ent.label_ in ['PERSON', 'ORG', 'GPE', 'PRODUCT', 'EVENT', 'WORK_OF_ART']:
                    keywords.add(ent.text.lower())
            
            # Add important nouns and adjectives
            for token in doc:
                if (token.pos_ in ['NOUN', 'PROPN', 'ADJ'] and 
                    not token.is_stop and 
                    not token.is_punct and 
                    len(token.text) > 2):
                    keywords.add(token.lemma_.lower())
            
            return list(keywords)[:max_keywords]
            
        except Exception as e:
            print(f"Error extracting keywords: {e}")
            return []
    
    def get_text_stats(self, text: str) -> Dict[str, Any]:
        """Get statistics about the text"""
        if not text:
            return {}
        
        words = text.split()
        sentences = nltk.sent_tokenize(text) if text else []
        
        return {
            'word_count': len(words),
            'sentence_count': len(sentences),
            'character_count': len(text),
            'avg_words_per_sentence': len(words) / len(sentences) if sentences else 0,
            'readability_score': self._calculate_readability(words, sentences)
        }
    
    def _calculate_readability(self, words: List[str], sentences: List[str]) -> float:
        """Calculate a simple readability score (Flesch-like)"""
        if not words or not sentences:
            return 0.0
        
        avg_sentence_length = len(words) / len(sentences)
        avg_syllables = sum(self._count_syllables(word) for word in words) / len(words)
        
        # Simplified Flesch Reading Ease formula
        score = 206.835 - (1.015 * avg_sentence_length) - (84.6 * avg_syllables)
        return max(0, min(100, score))  # Clamp between 0-100
    
    def _count_syllables(self, word: str) -> int:
        """Count syllables in a word (simple approximation)"""
        word = word.lower()
        if len(word) <= 3:
            return 1
        
        vowels = 'aeiouy'
        syllable_count = 0
        prev_was_vowel = False
        
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_was_vowel:
                syllable_count += 1
            prev_was_vowel = is_vowel
        
        # Handle silent 'e'
        if word.endswith('e'):
            syllable_count -= 1
        
        return max(1, syllable_count)

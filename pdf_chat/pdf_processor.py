import os
import tempfile
from typing import List, Dict, Any
from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
try:
    from langchain_community.vectorstores import FAISS
except ImportError:
    from langchain.vectorstores import FAISS

try:
    from langchain.chains import ConversationalRetrievalChain
    from langchain.memory import ConversationBufferMemory
except ImportError:
    ConversationalRetrievalChain = None
    ConversationBufferMemory = None

import pickle

try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:
    try:
        from langchain_community.embeddings import HuggingFaceInstructEmbeddings as HuggingFaceEmbeddings
    except ImportError:
        from langchain.embeddings import HuggingFaceInstructEmbeddings as HuggingFaceEmbeddings

try:
    from langchain_community.llms import Ollama
except ImportError:
    try:
        from langchain.llms import Ollama
    except ImportError:
        Ollama = None

try:
    from transformers import pipeline
    HF_TRANSFORMERS_AVAILABLE = True
except ImportError:
    HF_TRANSFORMERS_AVAILABLE = False

class PDFProcessor:
    def __init__(self):
        self.embeddings = None
        self.vectorstore = None
        self.conversation_chain = None
        self.memory = ConversationBufferMemory(
            memory_key="chat_history", 
            return_messages=True
        )
        self._init_embeddings()
    
    def _init_embeddings(self):
        """Initialize embeddings with free models"""
        try:
            # Try to use the newer HuggingFace embeddings
            self.embeddings = HuggingFaceEmbeddings(
                model_name='all-MiniLM-L6-v2',
                model_kwargs={'device': 'cpu'}
            )
        except Exception as e:
            print(f"Failed to initialize HuggingFace embeddings: {e}")
            # Fallback to a simpler approach
            try:
                self.embeddings = HuggingFaceEmbeddings(
                    model_name='sentence-transformers/all-MiniLM-L6-v2'
                )
            except Exception as e2:
                print(f"Failed to initialize fallback embeddings: {e2}")
                raise Exception("Could not initialize embeddings")
    
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
                text += page.extract_text()
            
            # Clean up temp file
            os.unlink(tmp_file_path)
            
            return text
        except Exception as e:
            print(f"Error extracting text from PDF: {e}")
            raise Exception(f"Failed to extract text from PDF: {str(e)}")
    
    def create_text_chunks(self, text: str) -> List[str]:
        """Split text into chunks for processing"""
        text_splitter = CharacterTextSplitter(
            separator="\n",
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )
        chunks = text_splitter.split_text(text)
        return chunks
    
    def create_vectorstore(self, text_chunks: List[str]) -> FAISS:
        """Create FAISS vectorstore from text chunks"""
        if not self.embeddings:
            raise Exception("Embeddings not initialized")
        
        try:
            vectorstore = FAISS.from_texts(
                texts=text_chunks, 
                embedding=self.embeddings
            )
            return vectorstore
        except Exception as e:
            print(f"Error creating vectorstore: {e}")
            raise Exception(f"Failed to create vectorstore: {str(e)}")
    
    def _get_free_llm(self):
        """Get a free LLM model"""
        # Try Ollama first (if available locally)
        if Ollama:
            try:
                llm = Ollama(model="llama2")  # or "mistral", "codellama"
                # Test if Ollama is running
                test_response = llm("Hello")
                return llm
            except Exception as e:
                print(f"Ollama not available: {e}")
        
        # Try HuggingFace transformers pipeline
        if HF_TRANSFORMERS_AVAILABLE:
            try:
                # Use a smaller, free model
                llm_pipeline = pipeline(
                    "text-generation",
                    model="microsoft/DialoGPT-medium",
                    tokenizer="microsoft/DialoGPT-medium",
                    device=-1  # Use CPU
                )
                return llm_pipeline
            except Exception as e:
                print(f"HuggingFace pipeline not available: {e}")
        
        # Fallback to a simple rule-based response
        return None
    
    def create_conversation_chain(self, vectorstore: FAISS):
        """Create conversation chain with free models"""
        try:
            llm = self._get_free_llm()
            
            if llm is None:
                # Use a simple fallback system
                return self._create_simple_qa_system(vectorstore)
            
            if hasattr(llm, '__call__'):  # Ollama or similar
                conversation_chain = ConversationalRetrievalChain.from_llm(
                    llm=llm,
                    retriever=vectorstore.as_retriever(),
                    memory=self.memory
                )
                return conversation_chain
            else:
                # HuggingFace pipeline - create custom chain
                return self._create_hf_chain(llm, vectorstore)
                
        except Exception as e:
            print(f"Error creating conversation chain: {e}")
            return self._create_simple_qa_system(vectorstore)
    
    def _create_simple_qa_system(self, vectorstore: FAISS):
        """Create a simple Q&A system without LLM"""
        class SimpleQASystem:
            def __init__(self, vectorstore):
                self.vectorstore = vectorstore
                self.retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
            
            def __call__(self, inputs):
                question = inputs.get('question', '')
                
                # Retrieve relevant documents
                docs = self.retriever.get_relevant_documents(question)
                
                if not docs:
                    return {
                        'answer': "I couldn't find relevant information in the uploaded documents to answer your question."
                    }
                
                # Create a simple response based on retrieved content
                context = "\n\n".join([doc.page_content for doc in docs])
                
                # Simple keyword-based response generation
                answer = self._generate_simple_answer(question, context)
                
                return {'answer': answer}
            
            def _generate_simple_answer(self, question, context):
                """Generate a simple answer based on context"""
                # Extract the most relevant sentences
                sentences = context.split('.')
                relevant_sentences = []
                
                question_words = question.lower().split()
                
                for sentence in sentences:
                    sentence = sentence.strip()
                    if len(sentence) > 20:  # Ignore very short sentences
                        sentence_lower = sentence.lower()
                        # Check if sentence contains question keywords
                        relevance_score = sum(1 for word in question_words if word in sentence_lower)
                        if relevance_score > 0:
                            relevant_sentences.append((sentence, relevance_score))
                
                # Sort by relevance and take top sentences
                relevant_sentences.sort(key=lambda x: x[1], reverse=True)
                top_sentences = [s[0] for s in relevant_sentences[:3]]
                
                if top_sentences:
                    answer = "Based on the document, here's what I found:\n\n"
                    answer += ". ".join(top_sentences)
                    if not answer.endswith('.'):
                        answer += "."
                else:
                    answer = "I found some relevant content in the document, but couldn't extract a specific answer to your question. Here's some related information:\n\n"
                    answer += context[:500] + "..." if len(context) > 500 else context
                
                return answer
        
        return SimpleQASystem(vectorstore)
    
    def _create_hf_chain(self, llm_pipeline, vectorstore):
        """Create a custom chain using HuggingFace pipeline"""
        class HFConversationChain:
            def __init__(self, pipeline, vectorstore):
                self.pipeline = pipeline
                self.retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
            
            def __call__(self, inputs):
                question = inputs.get('question', '')
                
                # Retrieve relevant documents
                docs = self.retriever.get_relevant_documents(question)
                context = "\n".join([doc.page_content for doc in docs[:2]])  # Limit context
                
                # Create prompt for the model
                prompt = f"Context: {context[:1000]}\n\nQuestion: {question}\n\nAnswer:"
                
                try:
                    # Generate response
                    response = self.pipeline(prompt, max_length=200, num_return_sequences=1)
                    answer = response[0]['generated_text'].split("Answer:")[-1].strip()
                    
                    if not answer:
                        answer = "I found relevant information but couldn't generate a specific answer."
                    
                    return {'answer': answer}
                except Exception as e:
                    print(f"Error generating response: {e}")
                    return {'answer': "I encountered an error while processing your question."}
        
        return HFConversationChain(llm_pipeline, vectorstore)
    
    def process_pdfs(self, pdf_files: List) -> Dict[str, Any]:
        """Process multiple PDF files and create vectorstore"""
        try:
            all_text = ""
            processed_files = []
            
            for pdf_file in pdf_files:
                try:
                    text = self.extract_text_from_pdf(pdf_file)
                    all_text += f"\n\n--- {pdf_file.name} ---\n\n{text}"
                    processed_files.append(pdf_file.name)
                except Exception as e:
                    print(f"Error processing {pdf_file.name}: {e}")
                    continue
            
            if not all_text.strip():
                raise Exception("No text could be extracted from the uploaded files")
            
            # Create chunks and vectorstore
            text_chunks = self.create_text_chunks(all_text)
            self.vectorstore = self.create_vectorstore(text_chunks)
            
            # Create conversation chain
            self.conversation_chain = self.create_conversation_chain(self.vectorstore)
            
            return {
                'success': True,
                'processed_files': processed_files,
                'total_chunks': len(text_chunks),
                'message': f"Successfully processed {len(processed_files)} PDF file(s)"
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f"Failed to process PDF files: {str(e)}"
            }
    
    def ask_question(self, question: str) -> Dict[str, Any]:
        """Ask a question about the processed documents"""
        if not self.conversation_chain:
            return {
                'success': False,
                'error': 'No documents processed yet',
                'answer': 'Please upload and process PDF documents first.'
            }
        
        try:
            response = self.conversation_chain({'question': question})
            answer = response.get('answer', 'No answer generated')
            
            return {
                'success': True,
                'answer': answer,
                'question': question
            }
            
        except Exception as e:
            print(f"Error answering question: {e}")
            return {
                'success': False,
                'error': str(e),
                'answer': 'I encountered an error while processing your question. Please try again.'
            }
    
    def save_session(self, session_id: str):
        """Save the current session state"""
        try:
            session_data = {
                'vectorstore': self.vectorstore,
                'memory': self.memory
            }
            
            # Create sessions directory if it doesn't exist
            sessions_dir = 'pdf_chat_sessions'
            os.makedirs(sessions_dir, exist_ok=True)
            
            # Save session data
            session_file = os.path.join(sessions_dir, f"{session_id}.pkl")
            with open(session_file, 'wb') as f:
                pickle.dump(session_data, f)
                
            return True
        except Exception as e:
            print(f"Error saving session: {e}")
            return False
    
    def load_session(self, session_id: str):
        """Load a saved session state"""
        try:
            session_file = os.path.join('pdf_chat_sessions', f"{session_id}.pkl")
            
            if not os.path.exists(session_file):
                return False
            
            with open(session_file, 'rb') as f:
                session_data = pickle.load(f)
            
            self.vectorstore = session_data.get('vectorstore')
            self.memory = session_data.get('memory', ConversationBufferMemory(
                memory_key="chat_history", 
                return_messages=True
            ))
            
            if self.vectorstore:
                self.conversation_chain = self.create_conversation_chain(self.vectorstore)
            
            return True
        except Exception as e:
            print(f"Error loading session: {e}")
            return False
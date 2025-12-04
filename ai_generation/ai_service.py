import requests
import time
from django.conf import settings
import json

class AIService:
    """Service class to handle multiple AI providers with fallback options"""
    
    def __init__(self):
        self.openai_client = None
        self.setup_providers()
    
    def setup_providers(self):
        """Initialize available AI providers"""
        # OpenAI setup
        if settings.OPENAI_API_KEY:
            try:
                from openai import OpenAI
                self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
            except Exception as e:
                print(f"OpenAI setup failed: {e}")
    
    def generate_text_openai(self, prompt, max_tokens=1500):
        """Generate text using OpenAI"""
        if not self.openai_client:
            raise Exception("OpenAI client not available")
        
        response = self.openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that creates engaging blog content. Be creative, informative, and format your response well with headings and paragraphs."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.7
        )
        return response.choices[0].message.content
    
    def generate_text_huggingface_api(self, prompt, max_tokens=500):
        """Generate text using Hugging Face Inference API (free tier)"""
        if not settings.HUGGINGFACE_API_KEY:
            raise Exception("Hugging Face API key not configured")
        
        API_URL = "https://api-inference.huggingface.co/models/microsoft/DialoGPT-large"
        headers = {"Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}"}
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": max_tokens,
                "temperature": 0.7,
                "return_full_text": False
            }
        }
        
        response = requests.post(API_URL, headers=headers, json=payload)
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                return result[0].get('generated_text', '')
            return str(result)
        else:
            raise Exception(f"Hugging Face API error: {response.status_code} - {response.text}")
    
    def generate_text_local(self, prompt, max_tokens=200):
        """Generate text using local Hugging Face model"""
        if not self.huggingface_pipeline:
            raise Exception("Local AI pipeline not available")
        
        # Generate text using local pipeline
        result = self.huggingface_pipeline(
            prompt, 
            max_length=max_tokens, 
            num_return_sequences=1,
            temperature=0.7,
            do_sample=True
        )
        return result[0]['generated_text']
    
    def generate_text_groq(self, prompt, max_tokens=1000):
        """Generate text using Groq's free API"""
        if not getattr(settings, 'GROQ_API_KEY', ''):
            raise Exception("Groq API key not configured")
        
        headers = {
            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messages": [
                {"role": "system", "content": "You are a helpful assistant that creates engaging blog content."},
                {"role": "user", "content": prompt}
            ],
            "model": "meta-llama/llama-4-scout-17b-16e-instruct",  # Free model
            "max_tokens": max_tokens,
            "temperature": 0.7
        }
        
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload
        )
        
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            raise Exception(f"Groq API error: {response.status_code} - {response.text}")
    
    def generate_text_gemini(self, prompt, max_tokens=1000):
        """Generate text using Google Gemini free API"""
        if not getattr(settings, 'GEMINI_API_KEY', ''):
            raise Exception("Gemini API key not configured")
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={settings.GEMINI_API_KEY}"
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": f"You are a helpful assistant that creates engaging blog content. {prompt}"
                }]
            }],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": 0.7
            }
        }
        
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            if 'candidates' in result and len(result['candidates']) > 0:
                return result['candidates'][0]['content']['parts'][0]['text']
            else:
                raise Exception("No content generated")
        else:
            raise Exception(f"Gemini API error: {response.status_code} - {response.text}")
    
    def generate_text(self, prompt, max_tokens=1500, preferred_provider=None):
        """
        Generate text with fallback providers
        Try providers in order based on preference and availability
        """
        provider = preferred_provider or settings.AI_PROVIDER
        errors = []
        
        # Define provider priority order
        providers_to_try = []
        
        if provider == 'openai' and self.openai_client:
            providers_to_try.append('openai')
        if getattr(settings, 'GROQ_API_KEY', ''):
            providers_to_try.append('groq')
        if getattr(settings, 'GEMINI_API_KEY', ''):
            providers_to_try.append('gemini')
        if settings.HUGGINGFACE_API_KEY:
            providers_to_try.append('huggingface')
        
        # Try each provider in order
        for provider_name in providers_to_try:
            try:
                if provider_name == 'openai':
                    return self.generate_text_openai(prompt, max_tokens)
                elif provider_name == 'groq':
                    return self.generate_text_groq(prompt, max_tokens)
                elif provider_name == 'gemini':
                    return self.generate_text_gemini(prompt, max_tokens)
                elif provider_name == 'huggingface':
                    return self.generate_text_huggingface_api(prompt, min(max_tokens, 500))
            except Exception as e:
                errors.append(f"{provider_name} failed: {str(e)}")
                continue
        
        # If all providers fail, provide a fallback response
        if not providers_to_try:
            return f"# Blog Post About: {prompt}\n\nI apologize, but no AI providers are currently configured. To enable AI generation, please add an API key for one of the following free services:\n\n1. **Groq** (Free tier): Get key from https://console.groq.com/keys\n2. **Google Gemini** (Free tier): Get key from https://ai.google.dev/\n3. **Hugging Face** (30k chars/month free): Get key from https://huggingface.co/settings/tokens\n\nAdd the key to your .env file and set AI_PROVIDER accordingly."
        
        # If all configured providers failed
        raise Exception(f"All AI providers failed: {'; '.join(errors)}")
    
    def analyze_image_groq(self, image_base64, analysis_type="description"):
        """Analyze image using Groq's vision capabilities"""
        if not getattr(settings, 'GROQ_API_KEY', ''):
            raise Exception("Groq API key not configured")
        
        # Create analysis prompts based on type
        analysis_prompts = {
            'description': "Describe this image in detail, including what you see, the setting, colors, mood, and any notable features.",
            'detailed': "Provide a comprehensive analysis of this image, including objects, people, composition, lighting, style, and any text visible in the image.",
            'caption': "Create a concise, engaging caption for this image that could be used in social media or blog posts.",
            'ocr': "Extract and transcribe any text visible in this image. If no text is visible, mention that the image contains no readable text."
        }
        
        system_prompt = analysis_prompts.get(analysis_type, analysis_prompts['description'])
        
        headers = {
            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": system_prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
                        }
                    ]
                }
            ],
            "model": "llama-3.2-11b-vision-preview",  # Updated Groq vision model
            "max_tokens": 1000,
            "temperature": 0.7
        }
        
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload
        )
        
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            raise Exception(f"Groq Vision API error: {response.status_code} - {response.text}")
    
    def analyze_image_free(self, image_data, analysis_type="description"):
        """
        Free image analysis using Hugging Face models
        Note: This is a basic implementation - for full image analysis,
        you'd want to use more specialized models
        """
        try:
            # Use Hugging Face image-to-text model
            API_URL = "https://api-inference.huggingface.co/models/Salesforce/blip-image-captioning-base"
            headers = {"Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}"}
            
            response = requests.post(API_URL, headers=headers, data=image_data)
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    caption = result[0].get('generated_text', 'No description available')
                    
                    # Enhance based on analysis type
                    if analysis_type == "detailed":
                        return f"Detailed analysis: {caption}. This image appears to contain visual elements that can be described as: {caption}"
                    elif analysis_type == "caption":
                        return caption
                    else:
                        return f"Image description: {caption}"
                        
            raise Exception(f"Hugging Face image API error: {response.status_code}")
            
        except Exception as e:
            return f"Image analysis not available with free tier: {str(e)}"
    
    def analyze_image(self, image_data=None, image_base64=None, analysis_type="description"):
        """
        Analyze image with fallback providers
        """
        errors = []
        
        # Try Hugging Face first (more reliable for image analysis)
        if getattr(settings, 'HUGGINGFACE_API_KEY', '') and image_data:
            try:
                return self.analyze_image_free(image_data, analysis_type)
            except Exception as e:
                errors.append(f"Hugging Face failed: {str(e)}")
        
        # Skip Groq vision for now due to model deprecations
        # if getattr(settings, 'GROQ_API_KEY', '') and image_base64:
        #     try:
        #         return self.analyze_image_groq(image_base64, analysis_type)
        #     except Exception as e:
        #         errors.append(f"Groq vision failed: {str(e)}")
        
        # Provide a basic fallback response
        if not getattr(settings, 'HUGGINGFACE_API_KEY', ''):
            return f"""**Image Analysis ({analysis_type})**

To enable AI-powered image analysis, please add a **free Hugging Face API key** to your `.env` file:

1. Visit: https://huggingface.co/settings/tokens
2. Create a free account and generate a token
3. Add to `.env`: `HUGGINGFACE_API_KEY="your-token-here"`

This will enable automatic image captioning and analysis with 30,000 characters per month free!

*Current image uploaded but analysis not available without API key.*"""
        
        # If Hugging Face is configured but failed
        if errors:
            return f"**Image Analysis Error**\n\nCould not analyze image: {'; '.join(errors)}\n\nPlease try again or check your Hugging Face API key configuration."
        
        return "Image analysis not available. Please configure a Hugging Face API key."

# Global instance
ai_service = AIService()

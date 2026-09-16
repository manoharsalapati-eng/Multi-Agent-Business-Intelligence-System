import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from groq import Groq

# Load environment variables
load_dotenv()

class LLMClient:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
        if not self.api_key:
            # We can check if it is set in system env, otherwise raise warning
            # The backend can also raise it when starting
            pass
        
    def _get_client(self) -> Groq:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY is missing. Please set it in your environment or .env file.")
        return Groq(api_key=api_key)

    def query(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None, 
        json_mode: bool = False
    ) -> str:
        client = self._get_client()
        # Read model fresh each call so .env changes take effect without restart
        model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        params: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": 0.0
        }
        
        if json_mode:
            params["response_format"] = {"type": "json_object"}
            
        try:
            response = client.chat.completions.create(**params)
            return response.choices[0].message.content or ""
        except Exception as e:
            # Re-raise with a clear message
            raise RuntimeError(f"Error querying Groq API: {str(e)}")

# Shared single client instance
llm_client = LLMClient()

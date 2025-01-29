import aiohttp
import json
from typing import Dict, Any, Optional
from loguru import logger

class OllamaConnection:
    """Handles communication with Ollama server for browser automation"""
    
    def __init__(self, host: str = "192.168.1.10", port: int = 11434):
        self.base_url = f"http://{host}:{port}/api"
        self.text_model = "qwen2.5:7b"  # Using Qwen for reasoning
        
        # Configure model options for GPU acceleration
        self.default_options = {
            "gpu": True,
            "batch": 1,
            "num_gpu": 1,
            "main_gpu": 0
        }
        
    async def generate_text(self, prompt: str, temperature: float = 0.7) -> Optional[str]:
        """Generate text response using the LLM"""
        try:
            # Prepare the prompt with specific instructions
            system_prompt = """
            You are a browser automation assistant. Your task is to help automate web interactions.
            You should:
            1. Analyze the current page content and goal
            2. Plan the next action to take
            3. Return ONLY a JSON object with the action details
            4. Be specific with selectors and actions
            5. Handle one step at a time
            6. Consider common web patterns and best practices
            
            IMPORTANT: Return ONLY the JSON object, no markdown formatting, no additional text.
            """
            
            full_prompt = f"{system_prompt}\n\n{prompt}"
            
            payload = {
                "model": self.text_model,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    **self.default_options,
                    "temperature": temperature
                }
            }
            
            logger.info(f"Sending request to Ollama with model: {self.text_model}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.base_url}/generate", json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        response_text = result.get("response", "").strip()
                        # Clean up any markdown formatting
                        if "```" in response_text:
                            parts = response_text.split("```")
                            for part in parts:
                                if "{" in part and "}" in part:
                                    response_text = part.strip()
                                    if response_text.startswith("json"):
                                        response_text = response_text[4:].strip()
                                    break
                        logger.info(f"Got response from Ollama: {response_text[:200]}...")
                        return response_text
                    else:
                        logger.error(f"Ollama request failed: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error in Ollama request: {str(e)}")
            return None
            
    async def analyze_page(self, 
                          content: str,
                          goal: str
                          ) -> Optional[Dict[str, Any]]:
        """Analyze page content and suggest next action"""
        try:
            prompt = f"""
            Analyze this web page content and suggest the next action:
            
            Goal: {goal}
            
            Page Content:
            {content[:1000]}  # Truncated for brevity
            
            Return a JSON object with:
            {{
                "action": "action_type",
                "selector": "element_selector",
                "value": "input_value",  # if needed
                "explanation": "why this action"
            }}
            
            Only return the JSON object, nothing else.
            Be specific with selectors and prefer data-attributes or IDs when available.
            """
            
            response = await self.generate_text(prompt, temperature=0.5)
            if not response:
                return None
                
            try:
                # Clean the response to ensure it's valid JSON
                json_str = response.strip()
                if json_str.startswith("```json"):
                    json_str = json_str[7:]
                if json_str.endswith("```"):
                    json_str = json_str[:-3]
                    
                return json.loads(json_str.strip())
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse action response as JSON: {str(e)}")
                logger.error(f"Raw response: {response}")
                return None
                
        except Exception as e:
            logger.error(f"Error analyzing page: {str(e)}")
            return None

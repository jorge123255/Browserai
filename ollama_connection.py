import aiohttp
import json
from typing import Dict, Any, Optional
from loguru import logger

class OllamaConnection:
    """Handles communication with Ollama server for browser automation"""
    
    def __init__(self, browser_window=None, model="qwen2.5:7b"):
        self.window = browser_window
        self.model = model
        self.base_url = "http://192.168.1.10:11434/api"
        self.session = aiohttp.ClientSession()
        
        # Configure model options for GPU acceleration
        self.default_options = {
            "gpu": True,
            "batch": 1,
            "num_gpu": 1,
            "main_gpu": 0
        }
        
    def _update_ui_reasoning(self, reasoning: str, action: str = None):
        """Update reasoning section in UI."""
        if self.window:
            details = []
            if action:
                details.append(f"Selected Action: {action}")
            
            # Split reasoning into bullet points if it contains multiple sentences
            reasoning_points = [r.strip() for r in reasoning.split('.') if r.strip()]
            details.extend(reasoning_points)
            
            self.window.add_reasoning(
                "🤖 LLM Analysis",
                "Analyzing current state and deciding next action",
                details=details
            )
            
    async def _send_request(self, endpoint: str, data: Dict) -> Dict:
        """Send request to Ollama API and handle ndjson response."""
        try:
            url = f"{self.base_url}/{endpoint}"
            async with self.session.post(url, json=data) as response:
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}: {await response.text()}")
                
                # Read and process ndjson response
                full_response = ""
                async for line in response.content:
                    if line:
                        try:
                            # Decode each line as a separate JSON object
                            chunk = json.loads(line)
                            if "response" in chunk:
                                full_response += chunk["response"]
                        except json.JSONDecodeError as e:
                            logger.warning(f"Failed to decode response chunk: {e}")
                            continue
                
                return full_response
                
        except Exception as e:
            logger.error(f"Error sending request to Ollama: {str(e)}")
            return None
            
    async def generate_text(self, prompt: str) -> Optional[str]:
        """Generate text using Ollama model."""
        try:
            logger.info(f"Sending request to Ollama with model: {self.model}")
            
            data = {
                "model": self.model,
                "prompt": prompt,
                "stream": True
            }
            
            response = await self._send_request("generate", data)
            
            if response:
                logger.info(f"Got response from Ollama: {response[:200]}...")  # Log first 200 chars
                return response
            return None
            
        except Exception as e:
            logger.error(f"Error generating text: {str(e)}")
            return None
            
    async def close(self):
        """Close the aiohttp session."""
        if self.session:
            await self.session.close()
            
    async def analyze_page(self, content: str, goal: str) -> Optional[Dict[str, Any]]:
        """Analyze page content and suggest next action."""
        try:
            prompt = f"""
            Analyze this web page content and suggest the next action:
            
            Goal: {goal}
            
            Page Content:
            {content[:1000]}  # Truncated for brevity
            
            Return a JSON object with:
            {{
                "action": "action_type",
                "target": "element_selector",
                "value": "input_value",  # if needed
                "confidence": float,  # 0.0 to 1.0
                "reasoning": "detailed explanation of why this action was chosen"
            }}
            
            Only return the JSON object, nothing else.
            Be specific with selectors and prefer data-attributes or IDs when available.
            """
            
            response = await self.generate_text(prompt)
            if not response:
                return None
                
            try:
                # Clean the response to ensure it's valid JSON
                json_str = response.strip()
                # Remove markdown code blocks if present
                if "```" in json_str:
                    json_str = json_str.split("```")[1]  # Get content between first pair of ```
                    if json_str.startswith("json"):
                        json_str = json_str[4:]  # Remove "json" language identifier
                json_str = json_str.strip()
                
                result = json.loads(json_str)
                
                # Update UI with reasoning
                if 'reasoning' in result:
                    self._update_ui_reasoning(
                        result['reasoning'],
                        result.get('action')
                    )
                    
                return result
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse action response as JSON: {str(e)}")
                logger.error(f"Raw response: {response}")
                return None
                
        except Exception as e:
            logger.error(f"Error analyzing page: {str(e)}")
            return None

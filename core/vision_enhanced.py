import cv2
import numpy as np
from PIL import Image
from typing import Optional, Tuple, List
from loguru import logger
import base64
import io
import aiohttp
from .browser_core import BrowserCore

class VisionEnhanced(BrowserCore):
    """Vision-enhanced browser interaction using Ollama"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ollama_url = "http://192.168.1.10:11434/api/generate"
        
    async def _ollama_vision_request(self, image: Image.Image, prompt: str) -> Optional[str]:
        """Send vision request to Ollama"""
        try:
            # Convert image to base64
            buffered = io.BytesIO()
            image.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
            # Prepare request
            payload = {
                "model": "llava:7b",  # Using llava model for vision tasks
                "prompt": prompt,
                "images": [img_str],
                "stream": False
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.ollama_url, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("response")
                    else:
                        logger.error(f"Ollama request failed: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error in Ollama vision request: {str(e)}")
            return None
            
    async def get_screenshot(self) -> Optional[Image.Image]:
        """Capture page screenshot"""
        script = """
        return new Promise((resolve) => {
            const width = Math.max(
                document.documentElement.clientWidth,
                window.innerWidth || 0
            );
            const height = Math.max(
                document.documentElement.clientHeight,
                window.innerHeight || 0
            );
            
            const canvas = document.createElement('canvas');
            canvas.width = width;
            canvas.height = height;
            
            const context = canvas.getContext('2d');
            
            // First try to capture the viewport
            try {
                const svg = `
                    <svg xmlns='http://www.w3.org/2000/svg' width='${width}' height='${height}'>
                        <foreignObject width='100%' height='100%'>
                            <div xmlns='http://www.w3.org/1999/xhtml'>
                                ${document.documentElement.outerHTML}
                            </div>
                        </foreignObject>
                    </svg>
                `;
                
                const img = new Image();
                img.onload = () => {
                    context.drawImage(img, 0, 0);
                    resolve(canvas.toDataURL('image/png'));
                };
                img.src = 'data:image/svg+xml;base64,' + btoa(svg);
            } catch (e) {
                console.error('Screenshot failed:', e);
                resolve(null);
            }
        });
        """
        
        try:
            data_url = await self._run_javascript(script)
            if not data_url:
                return None
                
            # Convert data URL to PIL Image
            image_data = base64.b64decode(data_url.split(',')[1])
            return Image.open(io.BytesIO(image_data))
            
        except Exception as e:
            logger.error(f"Error capturing screenshot: {str(e)}")
            return None
            
    async def find_element_by_vision(self, 
                                   description: str,
                                   confidence_threshold: float = 0.7
                                   ) -> Optional[Tuple[str, float]]:
        """Find element using Ollama vision"""
        try:
            # Get screenshot
            screenshot = await self.get_screenshot()
            if not screenshot:
                return None
                
            # Prepare vision prompt
            prompt = f"""
            Look at this screenshot of a webpage and find the element that matches this description: "{description}".
            Return a JSON object with:
            1. selector: The most specific CSS selector that uniquely identifies this element
            2. confidence: How confident you are that this is the right element (0-1)
            3. explanation: Why you think this is the right element
            
            Only return the JSON object, nothing else.
            """
            
            # Get response from Ollama
            response = await self._ollama_vision_request(screenshot, prompt)
            if not response:
                return None
                
            # Parse response
            try:
                import json
                result = json.loads(response)
                if result.get("confidence", 0) >= confidence_threshold:
                    return (result["selector"], result["confidence"])
            except:
                logger.error("Failed to parse Ollama response")
                
            return None
            
        except Exception as e:
            logger.error(f"Error in vision-based element detection: {str(e)}")
            return None
            
    async def click_with_vision(self, description: str) -> bool:
        """Click element using vision-based detection"""
        element = await self.find_element_by_vision(description)
        if not element:
            return False
            
        selector, confidence = element
        logger.info(f"Found element with confidence {confidence}: {selector}")
        
        # Attempt click
        return await self.click_element(selector) 
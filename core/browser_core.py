from typing import Optional, Dict, Any, List
from PyQt5.QtWebEngineWidgets import QWebEnginePage
from PyQt5.QtCore import QUrl
import asyncio
import json
from loguru import logger
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

class PageState(BaseModel):
    """Model for tracking page state"""
    url: str
    ready: bool = False
    loading: bool = False
    error: Optional[str] = None
    
class ElementInfo(BaseModel):
    """Model for element information"""
    selector: str
    visible: bool = False
    clickable: bool = False
    text: Optional[str] = None
    attributes: Dict[str, str] = {}
    
class BrowserCore:
    """Enhanced core browser automation with better state management"""
    
    def __init__(self, page: QWebEnginePage):
        self.page = page
        self.state = PageState(url="")
        self._setup_logging()
        
    def _setup_logging(self):
        """Configure logging"""
        logger.add("browser_automation.log", rotation="500 MB")
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def visit_url(self, url: str) -> bool:
        """Enhanced URL navigation with retries and better state management"""
        try:
            self.state.loading = True
            self.state.url = url
            logger.info(f"Navigating to {url}")
            
            # Create load finished future
            load_finished = asyncio.Future()
            
            def handle_load_finished(ok):
                if not load_finished.done():
                    load_finished.set_result(ok)
                    
            # Connect signal
            self.page.loadFinished.connect(handle_load_finished)
            
            try:
                # Navigate
                self.page.setUrl(QUrl(url))
                
                # Wait for load with timeout
                success = await asyncio.wait_for(load_finished, timeout=30.0)
                
                if success:
                    # Wait for page to be truly ready
                    await self._wait_for_page_ready()
                    self.state.ready = True
                    logger.success(f"Successfully loaded {url}")
                    return True
                    
                self.state.error = "Page load failed"
                return False
                
            except asyncio.TimeoutError:
                self.state.error = "Page load timed out"
                return False
                
            finally:
                self.state.loading = False
                self.page.loadFinished.disconnect(handle_load_finished)
                
        except Exception as e:
            self.state.error = str(e)
            logger.error(f"Error navigating to {url}: {str(e)}")
            return False
            
    async def _wait_for_page_ready(self) -> bool:
        """Wait for page to be in truly ready state"""
        script = """
        return new Promise((resolve) => {
            const check = () => {
                const ready = (
                    document.readyState === 'complete' &&
                    !document.querySelector('.loading') &&
                    !document.querySelector('[aria-busy="true"]') &&
                    performance.now() - window.initialTimestamp > 1000
                );
                if (ready) {
                    resolve(true);
                } else {
                    setTimeout(check, 100);
                }
            };
            check();
        });
        """
        try:
            return await asyncio.wait_for(
                self._run_javascript(script),
                timeout=10.0
            )
        except asyncio.TimeoutError:
            return False
            
    async def _run_javascript(self, script: str, timeout: float = 5.0) -> Any:
        """Enhanced JavaScript execution with better error handling"""
        try:
            future = asyncio.Future()
            
            def callback(result):
                if not future.done():
                    future.set_result(result)
                    
            self.page.runJavaScript(script, callback)
            
            return await asyncio.wait_for(future, timeout=timeout)
            
        except asyncio.TimeoutError:
            logger.warning(f"JavaScript execution timed out: {script[:100]}...")
            return None
        except Exception as e:
            logger.error(f"JavaScript error: {str(e)}")
            return None
            
    async def get_element_info(self, selector: str) -> Optional[ElementInfo]:
        """Get detailed element information"""
        script = f"""
        (() => {{
            const element = document.querySelector({json.dumps(selector)});
            if (!element) return null;
            
            const rect = element.getBoundingClientRect();
            const style = window.getComputedStyle(element);
            
            return {{
                selector: {json.dumps(selector)},
                visible: (
                    element.offsetParent !== null &&
                    style.display !== 'none' &&
                    style.visibility !== 'hidden' &&
                    rect.width > 0 &&
                    rect.height > 0
                ),
                clickable: (
                    !element.disabled &&
                    style.pointerEvents !== 'none'
                ),
                text: element.textContent?.trim(),
                attributes: Object.fromEntries(
                    Array.from(element.attributes)
                        .map(attr => [attr.name, attr.value])
                )
            }};
        }})()
        """
        
        result = await self._run_javascript(script)
        return ElementInfo(**result) if result else None 
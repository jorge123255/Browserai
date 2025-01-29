from typing import List, Dict, Optional, Set
from urllib.parse import urljoin, urlparse
import asyncio
from bs4 import BeautifulSoup
import re
from loguru import logger
import json
from PyQt5.QtCore import QTimer

class NavigationPlanner:
    def __init__(self, browser_window=None):
        self.visited_urls = set()
        self.window = browser_window
        self.dynamic_content_selectors = {
            'loading': ['.loading', '#loading', '[aria-busy="true"]'],
            'infinite_scroll': ['.infinite-scroll', '.load-more'],
            'popup': ['.modal', '.popup', '.overlay'],
            'ajax': ['[data-ajax]', '[data-remote]']
        }
        logger.info("Navigation planner initialized")
        
    def _update_ui_reasoning(self, message: str, details: List[str] = None):
        """Update reasoning section in UI."""
        try:
            if hasattr(self.window, 'add_reasoning'):
                self.window.add_reasoning(
                    "🧭 Navigation Planning",
                    message,
                    details=details if details else []
                )
            elif hasattr(self.window, 'browser_tools'):
                self.window.browser_tools.add_reasoning(
                    "🧭 Navigation Planning",
                    message,
                    details=details if details else []
                )
            elif self.window and hasattr(self.window.parent(), 'browser_tools'):
                self.window.parent().browser_tools.add_reasoning(
                    "🧭 Navigation Planning",
                    message,
                    details=details if details else []
                )
        except Exception as e:
            logger.warning(f"Could not update UI reasoning: {str(e)}")
            
    def _update_ui_execution(self, message: str, status: str = "info"):
        """Update execution section in UI."""
        try:
            if hasattr(self.window, 'add_execution'):
                self.window.add_execution(
                    message,
                    status
                )
            elif hasattr(self.window, 'browser_tools'):
                self.window.browser_tools.add_execution(
                    message,
                    status
                )
            elif self.window and hasattr(self.window.parent(), 'browser_tools'):
                self.window.parent().browser_tools.add_execution(
                    message,
                    status
                )
        except Exception as e:
            logger.warning(f"Could not update UI execution: {str(e)}")
        
    async def optimize_path(self, start_url: str, target_info: str) -> List[str]:
        """Plan optimal navigation path avoiding redundant pages."""
        try:
            self._update_ui_reasoning(
                "Planning navigation path",
                [
                    f"Starting from: {start_url}",
                    f"Target info: {target_info}",
                    "Analyzing possible routes"
                ]
            )
            
            self.visited_urls.clear()
            path = []
            current_url = start_url
            
            while current_url and len(path) < 10:  # Prevent infinite loops
                path.append(current_url)
                self.visited_urls.add(current_url)
                
                self._update_ui_execution(f"Added {current_url} to navigation path")
                
                next_url = await self._find_next_best_url(current_url, target_info)
                if not next_url:
                    break
                    
                current_url = next_url
                
            self._update_ui_execution(f"✓ Planned navigation path with {len(path)} steps", "success")
            return path
            
        except Exception as e:
            error_msg = f"Error planning navigation: {str(e)}"
            logger.error(error_msg)
            self._update_ui_execution(error_msg, "error")
            return [start_url]
    
    async def handle_dynamic_content(self, page: 'WebPage') -> bool:
        """Handle dynamic content loading and interactions."""
        try:
            self._update_ui_reasoning(
                "Handling dynamic content",
                [
                    "Waiting for page load",
                    "Checking for loading indicators",
                    "Handling infinite scroll",
                    "Managing popups"
                ]
            )
            
            # Wait for initial page load
            await self._wait_for_network_idle(page)
            self._update_ui_execution("✓ Page initially loaded")
            
            # Handle loading indicators
            await self._wait_for_loading_indicators(page)
            self._update_ui_execution("✓ Loading indicators handled")
            
            # Handle infinite scroll if needed
            needs_scroll = await self._needs_infinite_scroll(page)
            if needs_scroll:
                self._update_ui_execution("Found infinite scroll, loading more content")
                await self._handle_infinite_scroll(page)
                self._update_ui_execution("✓ Infinite scroll content loaded")
            
            # Handle popups and overlays
            await self._handle_popups(page)
            self._update_ui_execution("✓ Popups handled")
            
            # Final check for any remaining dynamic content
            await self._wait_for_dynamic_content(page)
            self._update_ui_execution("✓ All dynamic content loaded", "success")
            
            return True
            
        except Exception as e:
            error_msg = f"Error handling dynamic content: {str(e)}"
            logger.error(error_msg)
            self._update_ui_execution(error_msg, "error")
            return False
    
    async def _find_next_best_url(self, current_url: str, 
                                target_info: str) -> Optional[str]:
        """Find the most relevant next URL based on target information."""
        page_links = await self._get_page_links(current_url)
        if not page_links:
            return None
            
        scored_links = []
        for link in page_links:
            if link in self.visited_urls:
                continue
                
            score = self._calculate_url_relevance(link, target_info)
            scored_links.append((link, score))
            
        if not scored_links:
            return None
            
        return max(scored_links, key=lambda x: x[1])[0]
    
    async def _get_page_links(self, url: str) -> Set[str]:
        """Extract and normalize all links from a page."""
        try:
            # This would be replaced with actual page content retrieval
            content = "<html>...</html>"  # Placeholder
            soup = BeautifulSoup(content, 'html.parser')
            
            links = set()
            for a in soup.find_all('a', href=True):
                href = a['href']
                if href.startswith(('#', 'javascript:')):
                    continue
                    
                full_url = urljoin(url, href)
                if self._is_same_domain(url, full_url):
                    links.add(full_url)
                    
            return links
            
        except Exception as e:
            print(f"Error getting page links: {str(e)}")
            return set()
    
    def _calculate_url_relevance(self, url: str, target_info: str) -> float:
        """Calculate relevance score for a URL based on target information."""
        url_parts = urlparse(url)
        path_segments = url_parts.path.lower().split('/')
        
        # Remove empty segments and common words
        path_segments = [s for s in path_segments if s and s not in {'index', 'html', 'php'}]
        
        # Calculate relevance based on path segments
        target_words = set(target_info.lower().split())
        matching_segments = sum(
            any(word in segment for word in target_words)
            for segment in path_segments
        )
        
        # Adjust score based on path depth
        depth_penalty = 0.1 * len(path_segments)
        
        return matching_segments - depth_penalty
    
    def _is_same_domain(self, url1: str, url2: str) -> bool:
        """Check if two URLs belong to the same domain."""
        return urlparse(url1).netloc == urlparse(url2).netloc
    
    async def _wait_for_network_idle(self, page: 'WebPage') -> None:
        """Wait for network activity to settle."""
        try:
            await asyncio.sleep(1)  # Simple implementation
        except Exception as e:
            logger.error(f"Error waiting for network idle: {str(e)}")
    
    async def _wait_for_loading_indicators(self, page: 'WebPage') -> None:
        """Wait for loading indicators to disappear."""
        try:
            if not page or not hasattr(page, 'runJavaScript'):
                logger.warning("Invalid page object provided to wait for loading indicators")
                return
                
            # Create a future to track completion
            loop = asyncio.get_event_loop()
            future = loop.create_future()
            
            def check_indicators():
                try:
                    script = """
                    const selectors = ['.loading', '#loading', '[aria-busy="true"]'];
                    for (const selector of selectors) {
                        const element = document.querySelector(selector);
                        if (element && element.style.display !== 'none') {
                            return true;
                        }
                    }
                    return false;
                    """
                    
                    def handle_result(result):
                        if result:
                            # Still loading, check again after delay
                            QTimer.singleShot(500, check_indicators)
                        else:
                            future.set_result(True)
                            
                    page.runJavaScript(script, handle_result)
                except Exception as e:
                    logger.error(f"Error in loading indicator check: {str(e)}")
                    future.set_exception(e)
            
            # Start checking
            check_indicators()
            
            try:
                # Wait with timeout
                await asyncio.wait_for(future, timeout=10.0)
            except asyncio.TimeoutError:
                logger.warning("Loading indicator check timed out")
                
        except Exception as e:
            logger.error(f"Error waiting for loading indicator: {str(e)}")
            
    async def _needs_infinite_scroll(self, page: 'WebPage') -> bool:
        """Check if page has infinite scroll functionality."""
        try:
            if not page or not hasattr(page, 'runJavaScript'):
                logger.warning("Invalid page object provided to check infinite scroll")
                return False
                
            # Create a future to track completion
            loop = asyncio.get_event_loop()
            future = loop.create_future()
            
            script = """
            const selectors = ['.infinite-scroll', '.load-more'];
            for (const selector of selectors) {
                const element = document.querySelector(selector);
                if (element) {
                    return true;
                }
            }
            return false;
            """
            
            def handle_result(result):
                future.set_result(result)
                
            page.runJavaScript(script, handle_result)
            
            try:
                # Wait with timeout
                return await asyncio.wait_for(future, timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("Infinite scroll check timed out")
                return False
                
        except Exception as e:
            logger.error(f"Error checking infinite scroll: {str(e)}")
            return False
    
    async def _handle_infinite_scroll(self, page: 'WebPage') -> None:
        """Handle infinite scroll pagination."""
        try:
            max_scrolls = 3  # Limit scrolling to prevent endless loops
            for _ in range(max_scrolls):
                script = """
                (function() {
                    window.scrollTo(0, document.body.scrollHeight);
                    return document.body.scrollHeight;
                })();
                """
                await page.runJavaScript(script)
                await asyncio.sleep(1)
                
                if not await self._new_content_loaded(page):
                    break
        except Exception as e:
            logger.error(f"Error handling infinite scroll: {str(e)}")
    
    async def _handle_popups(self, page: 'WebPage') -> None:
        """Handle popup dialogs and overlays."""
        selectors = self.dynamic_content_selectors['popup']
        for selector in selectors:
            try:
                if await self._element_exists(page, selector):
                    # Close popup
                    await self._close_popup(page, selector)
            except Exception as e:
                print(f"Error handling popup: {str(e)}")
    
    async def _wait_for_dynamic_content(self, page: 'WebPage') -> None:
        """Wait for any remaining dynamic content to load."""
        selectors = self.dynamic_content_selectors['ajax']
        for selector in selectors:
            try:
                if await self._element_exists(page, selector):
                    await asyncio.sleep(0.5)  # Placeholder
            except Exception as e:
                print(f"Error waiting for dynamic content: {str(e)}")
    
    async def _element_exists(self, page: 'WebPage', selector: str) -> bool:
        """Check if element exists on page."""
        try:
            # This would integrate with actual browser automation
            return True  # Placeholder
        except Exception:
            return False
    
    async def _scroll_to_bottom(self, page: 'WebPage') -> None:
        """Scroll to bottom of page."""
        try:
            # This would integrate with actual browser automation
            await asyncio.sleep(0.5)  # Placeholder
        except Exception as e:
            print(f"Error scrolling to bottom: {str(e)}")
    
    async def _new_content_loaded(self, page: 'WebPage') -> bool:
        """Check if new content was loaded after scrolling."""
        try:
            # This would integrate with actual browser automation
            return True  # Placeholder
        except Exception:
            return False
    
    async def _close_popup(self, page: 'WebPage', selector: str) -> None:
        """Close a popup or overlay."""
        try:
            # This would integrate with actual browser automation
            await asyncio.sleep(0.5)  # Placeholder
        except Exception as e:
            print(f"Error closing popup: {str(e)}") 
from typing import Optional, Dict, Any, List
from PyQt5.QtWebEngineWidgets import QWebEnginePage, QWebEngineProfile, QWebEngineSettings, QWebEngineView
from PyQt5.QtCore import QEventLoop, QUrl, QTimer, QSize, QBuffer, pyqtSlot
from PyQt5.QtGui import QImage, QPixmap
from bs4 import BeautifulSoup
import json
import asyncio
from loguru import logger
from ollama_connection import OllamaConnection
from urllib.parse import urlparse
import os
from datetime import datetime
import torch
from core.enhancements import BrowserEnhancements
from transformers import DetrForObjectDetection, DetrImageProcessor

class BrowserTools:
    """Main browser automation class with LLM integration"""
    
    def __init__(self, view_or_page):
        """Initialize browser automation with enhanced capabilities.
        Args:
            view_or_page: Either QWebEngineView or QWebEnginePage
        """
        if isinstance(view_or_page, QWebEnginePage):
            self.page = view_or_page
            self.view = self.page.view()
        else:  # QWebEngineView
            self.view = view_or_page
            self.page = self.view.page() if self.view else None
            
        self.recording = False
        self.screenshots = []
        self.current_session = None
        self.recording_path = "recordings"
        self.vision_enabled = False
        self._reasoning_history = []
        self._execution_history = []
        
        # Initialize vision models
        try:
            self.vision_model = DetrForObjectDetection.from_pretrained("facebook/detr-resnet-50")
            self.processor = DetrImageProcessor.from_pretrained("facebook/detr-resnet-50")
            self.vision_enabled = True
            logger.info("Vision models initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing vision models: {str(e)}")
            self.vision_model = None
            self.processor = None
        
        # Initialize LLM connection
        self.llm = OllamaConnection(browser_window=self.view)
        
        # Initialize enhancements
        self.enhancements = BrowserEnhancements(browser_window=self.view)
        
        # Configure page settings
        if self.page:
            self._configure_page()
            self._setup_handlers()
            
        logger.info("Initialized enhanced browser automation")
        
    def _configure_page(self):
        """Configure page settings for automation."""
        if not self.page:
            return
            
        # Configure page settings
        settings = self.page.settings()
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.ScrollAnimatorEnabled, True)
        settings.setAttribute(QWebEngineSettings.ErrorPageEnabled, True)
        settings.setAttribute(QWebEngineSettings.PluginsEnabled, True)
        
        # Set user agent
        profile = self.page.profile()
        profile.setHttpUserAgent("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Configure profile settings
        profile.setPersistentCookiesPolicy(QWebEngineProfile.NoPersistentCookies)
        profile.setHttpCacheType(QWebEngineProfile.MemoryHttpCache)
        
        # Initialize UI containers with styles
        script = """
        function initUI() {
            // Create containers if they don't exist
            ['agent-reasoning', 'execution-log'].forEach(id => {
                if (!document.getElementById(id)) {
                    const div = document.createElement('div');
                    div.id = id;
                    div.className = id === 'agent-reasoning' ? 'reasoning-log' : 'execution-log';
                    document.body.appendChild(div);
                }
            });

            // Add styles if not already present
            if (!document.getElementById('browser-tools-styles')) {
                const style = document.createElement('style');
                style.id = 'browser-tools-styles';
                style.textContent = `
                    .reasoning-log {
                        position: fixed;
                        top: 20px;
                        right: 20px;
                        max-width: 400px;
                        max-height: 80vh;
                        overflow-y: auto;
                        background: rgba(0, 0, 0, 0.8);
                        color: white;
                        padding: 15px;
                        border-radius: 8px;
                        font-family: system-ui;
                        z-index: 10000;
                    }
                    .execution-log {
                        position: fixed;
                        bottom: 20px;
                        right: 20px;
                        max-width: 400px;
                        max-height: 30vh;
                        overflow-y: auto;
                        background: rgba(0, 0, 0, 0.8);
                        color: white;
                        padding: 15px;
                        border-radius: 8px;
                        font-family: system-ui;
                        z-index: 10000;
                    }
                    .log-entry {
                        margin-bottom: 10px;
                        padding: 8px;
                        background: rgba(255, 255, 255, 0.1);
                        border-radius: 4px;
                    }
                    .log-title {
                        font-weight: bold;
                        margin-bottom: 5px;
                    }
                    .log-details {
                        font-size: 0.9em;
                        opacity: 0.9;
                    }
                    .timestamp {
                        font-size: 0.8em;
                        opacity: 0.7;
                    }
                `;
                document.head.appendChild(style);
            }
        }
        initUI();
        """
        self.page.runJavaScript(script)
        
    def _setup_handlers(self):
        """Setup page event handlers."""
        if not self.page:
            return
            
        # Create recordings directory if it doesn't exist
        if not os.path.exists(self.recording_path):
            os.makedirs(self.recording_path)
            
        # Setup JavaScript event handlers
        self.page.loadFinished.connect(lambda ok: asyncio.create_task(self._on_load_finished(ok)))
        self.page.loadStarted.connect(lambda: asyncio.create_task(self._on_load_started()))
        
    @pyqtSlot()
    async def _on_load_started(self):
        """Handle page load start event."""
        if self.recording:
            await self._take_screenshot()
            
    @pyqtSlot(bool)
    async def _on_load_finished(self, ok: bool):
        """Handle page load finished event."""
        if not ok:
            logger.error("Page failed to load")
            return
            
        if self.recording:
            await self._take_screenshot()
            
        # Setup page monitoring
        await self._handle_page_events()
        
        # Re-initialize UI containers and styles
        script = """
        function initUI() {
            // Create containers if they don't exist
            ['agent-reasoning', 'execution-log'].forEach(id => {
                if (!document.getElementById(id)) {
                    const div = document.createElement('div');
                    div.id = id;
                    div.className = id === 'agent-reasoning' ? 'reasoning-log' : 'execution-log';
                    document.body.appendChild(div);
                }
            });
        }
        initUI();
        """
        self.page.runJavaScript(script)

    async def start_recording(self):
        """Start recording browser interactions"""
        self.recording = True
        self.screenshots = []
        self.current_session = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_dir = os.path.join(self.recording_path, self.current_session)
        os.makedirs(session_dir)
        logger.info(f"Started recording session: {self.current_session}")
        
        # Start periodic screenshots
        self._schedule_screenshot()

    async def stop_recording(self):
        """Stop recording and save the interaction"""
        if self.recording:
            self.recording = False
            session_dir = os.path.join(self.recording_path, self.current_session)
            
            # Save metadata
            metadata = {
                "timestamp": datetime.now().isoformat(),
                "screenshots": len(self.screenshots),
                "final_url": self.page.url().toString()
            }
            
            with open(os.path.join(session_dir, "metadata.json"), "w") as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Stopped recording session: {self.current_session}")
            self.current_session = None

    def _schedule_screenshot(self):
        """Schedule periodic screenshots."""
        if not self.recording:
            return
            
        try:
            # Create QTimer for periodic screenshots
            if not hasattr(self, '_screenshot_timer'):
                self._screenshot_timer = QTimer()
                self._screenshot_timer.timeout.connect(
                    lambda: asyncio.create_task(self._take_screenshot())
                )
            
            # Start timer if not running
            if not self._screenshot_timer.isActive():
                self._screenshot_timer.start(2000)  # Screenshot every 2 seconds
                
        except Exception as e:
            logger.error(f"Error scheduling screenshots: {str(e)}")
            
    def _stop_screenshot_timer(self):
        """Stop the screenshot timer."""
        if hasattr(self, '_screenshot_timer'):
            self._screenshot_timer.stop()

    async def _take_screenshot(self):
        """Take a screenshot of the current page."""
        try:
            if not self.view or not self.recording:
                return
                
            # Ensure view is ready
            if not self.view.isVisible():
                logger.warning("View not visible, skipping screenshot")
                return
                
            # Create QTimer for delayed capture
            loop = asyncio.get_event_loop()
            future = loop.create_future()
            
            def take_delayed_screenshot():
                try:
                    # Get viewport size
                    size = self.view.size()
                    if size.width() == 0 or size.height() == 0:
                        logger.warning("Invalid view size, skipping screenshot")
                        future.set_result(None)
                        return
                        
                    # Create pixmap and render view
                    pixmap = QPixmap(size)
                    self.view.render(pixmap)
                    
                    # Save screenshot
                    if self.current_session:
                        timestamp = datetime.now().strftime("%H%M%S")
                        filename = f"screenshot_{timestamp}.png"
                        path = os.path.join(self.recording_path, self.current_session, filename)
                        pixmap.save(path)
                        self.screenshots.append(path)
                        logger.debug(f"Saved screenshot: {path}")
                    
                    future.set_result(True)
                except Exception as e:
                    logger.error(f"Error taking screenshot: {str(e)}")
                    future.set_exception(e)
            
            # Schedule screenshot with delay
            QTimer.singleShot(100, take_delayed_screenshot)
            
            await future
            
        except Exception as e:
            logger.error(f"Error in screenshot capture: {str(e)}")
            
    async def execute_task(self, task: Dict[str, Any]) -> bool:
        """Execute a high-level task with recording"""
        try:
            # Start recording
            await self.start_recording()
            
            # Parse the task goal for better logging
            goal = task.get("goal", "")
            logger.info(f"Starting task execution: {goal}")
            
            # Execute task with detailed logging
            success = await self._execute_task_with_retries(task)
            
            # Stop recording
            await self.stop_recording()
            
            if success:
                logger.info("Task completed successfully")
            else:
                logger.error("Task failed to complete")
            
            return success
            
        except Exception as e:
            logger.error(f"Error executing task: {str(e)}")
            await self.stop_recording()
            return False

    async def _execute_task_with_retries(self, task: Dict[str, Any], max_retries: int = 3) -> bool:
        """Execute a task with retries and error handling."""
        for attempt in range(max_retries):
            try:
                # Initialize page event tracking
                await self._handle_page_events()
                
                # Execute the task
                if await self._execute_task_internal(task):
                    # Wait for page to stabilize
                    if await self._wait_for_stable_page():
                        return True
                
                logger.warning(f"Task attempt {attempt + 1} failed, retrying...")
                await asyncio.sleep(2)  # Wait before retry
                
            except Exception as e:
                logger.error(f"Error in task attempt {attempt + 1}: {str(e)}")
                if attempt == max_retries - 1:
                    return False
                    
                # Try to recover page state
                await self._recover_page_state()
                continue
                
        return False

    async def _recover_page_state(self):
        """Attempt to recover from error states."""
        try:
            # Check if page is responsive
            is_responsive = await self._run_javascript("return true;")
            if not is_responsive:
                # Reload the page
                await self.visit_url(self.page.url().toString())
                return
            
            # Check for error dialogs/overlays
            script = """
            (function() {
                // Common error dialog selectors
                const errorSelectors = [
                    '[role="alert"]',
                    '.error-dialog',
                    '#error-modal',
                    '[class*="error"]',
                    '[class*="modal"]'
                ];
                
                for (const selector of errorSelectors) {
                    const element = document.querySelector(selector);
                    if (element && element.offsetParent !== null) {
                        // Try to close/dismiss
                        const closeButton = element.querySelector('button');
                        if (closeButton) {
                            closeButton.click();
                            return true;
                        }
                    }
                }
                return false;
            })()
            """
            await self._run_javascript(script)
            
            # Wait for stability
            await self._wait_for_stable_page()
            
        except Exception as e:
            logger.error(f"Error in recovery attempt: {str(e)}")

    async def _execute_task_internal(self, task: Dict[str, Any]) -> bool:
        """Internal task execution logic with enhanced planning and visual analysis."""
        try:
            goal = task.get("goal")
            if not goal:
                logger.error("No goal specified in task")
                return False
            
            # Initial navigation if needed
            if url := task.get("url"):
                # Use enhanced navigation planning
                nav_path = await self.enhancements.plan_navigation(url, goal, self.page)
                for step_url in nav_path:
                    if not await self._handle_navigation(step_url):
                        return False
            
            # Main task execution loop
            max_steps = 10  # Prevent infinite loops
            for step in range(max_steps):
                # Get current page state
                page_state = await self.analyze_page_structure()
                visual_state = await self._analyze_visual_elements()
                
                # Process current page content
                page_content = await self.get_visible_text()
                processed_content = await self.enhancements.process_page_content(
                    page_content,
                    context={"goal": goal, "visual_state": visual_state}
                )
                
                # Plan next action with enhanced context
                action_plan = await self._plan_next_action(goal, {
                    **page_state,
                    "visual_elements": visual_state,
                    "processed_content": processed_content
                })
                
                if not action_plan:
                    logger.error("Failed to plan next action")
                    return False
                
                # Track action to prevent loops
                await self._track_action_history(action_plan)
                
                # Execute planned action
                success = await self._execute_action(action_plan)
                if not success:
                    # Try visual fallback for element finding
                    if action_plan.get("action") in ["click", "type"]:
                        visual_element = await self._find_element_by_visual_similarity(
                            action_plan.get("target", "")
                        )
                        if visual_element:
                            logger.info("Found element using visual similarity")
                            success = await self._execute_action({
                                **action_plan,
                                "target": f"#{visual_element.get('id')}" if visual_element.get('id')
                                        else f".{'.'.join(visual_element.get('classes', []))}"
                            })
                
                if not success:
                    logger.error(f"Failed to execute action: {action_plan}")
                    return False
                
                # Check if goal is achieved with enhanced validation
                validated_state = await self.enhancements.validate_content(
                    {"content": page_content, "state": page_state},
                    base_url=self.page.url().toString()
                )
                
                if await self._check_goal_completion(goal, {**page_state, "validated": validated_state}):
                    logger.info("Goal achieved successfully")
                    return True
                
                # Wait for page to stabilize with enhanced dynamic content handling
                await self.enhancements.navigation_planner.handle_dynamic_content(self.page)
            
            logger.warning("Max steps reached without achieving goal")
            return False
            
        except Exception as e:
            logger.error(f"Error in task execution: {str(e)}")
            return False

    async def _handle_navigation(self, url: str) -> bool:
        """Handle URL navigation with retries and verification."""
        url = url.strip().rstrip('., ')
        target_domain = urlparse(
            url if url.startswith(('http://', 'https://')) else f'https://{url}'
        ).netloc.replace('www.', '')
        
        for attempt in range(3):
            logger.info(f"Navigation attempt {attempt + 1}/3")
            if await self.visit_url(url):
                current_url = self.page.url().toString()
                current_domain = urlparse(current_url).netloc.replace('www.', '')
                
                if current_url != "about:blank" and target_domain in current_domain:
                    logger.info(f"Successfully navigated to {current_domain}")
                    await asyncio.sleep(3)  # Wait for page to settle
                    return True
                    
            logger.warning(f"Navigation attempt {attempt + 1} failed")
            await asyncio.sleep(2)
            
        logger.error("All navigation attempts failed")
        return False

    async def _check_goal_completion(self, goal: str, page_state: Dict[str, Any]) -> bool:
        """Check if the current page state matches the goal."""
        prompt = {
            "goal": goal,
            "current_state": {
                "url": self.page.url().toString(),
                "title": page_state.get("title", ""),
                "visible_text": await self.get_visible_text()
            }
        }
        
        # Send as a single string without separate prompt parameter
        prompt_text = f"""Analyze if the current page state indicates the goal has been achieved.
        Context: {json.dumps(prompt, indent=2)}
        Return a JSON object with:
        {{
            "achieved": true/false,
            "confidence": 0.0 to 1.0,
            "reasoning": "explanation of why the goal is or isn't achieved"
        }}"""
        
        response = await self.llm.generate_text(prompt_text)
        
        try:
            # Clean the response to ensure it's valid JSON
            if response:
                response = response.strip()
                if "```" in response:
                    response = response.split("```")[1]  # Get content between first pair of ```
                    if response.startswith("json"):
                        response = response[4:]  # Remove "json" language identifier
                response = response.strip()
                
                result = json.loads(response)
                return result.get("achieved", False) and result.get("confidence", 0) > 0.8
            return False
            
        except Exception as e:
            logger.error(f"Error checking goal completion: {str(e)}")
            return False

    async def visit_url(self, url: str) -> bool:
        """Navigate to a URL and wait for page load."""
        try:
            # Clean and normalize URL
            url = url.strip().rstrip('., ')  # Remove trailing punctuation and whitespace
            
            # Add protocol if missing
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            # Basic URL validation
            try:
                parsed = urlparse(url)
                if not parsed.netloc:
                    logger.error(f"Invalid URL (no domain): {url}")
                    return False
            except Exception as e:
                logger.error(f"URL parsing error: {str(e)}")
                return False
            
            logger.info(f"Starting navigation to: {url}")
            
            # Create event loop for sync operations
            loop = asyncio.get_event_loop()
            
            # Create a future to track load finished
            load_finished = loop.create_future()
            
            def handle_load_finished(ok):
                if not load_finished.done():
                    load_finished.set_result(ok)
            
            # Connect the loadFinished signal
            self.page.loadFinished.connect(handle_load_finished)
            
            try:
                # Set the URL and force load
                qurl = QUrl(url)
                if not qurl.isValid():
                    logger.error(f"Invalid URL format: {url}")
                    return False
                
                # Navigate to the URL
                self.page.setUrl(qurl)
                
                # Wait for load with timeout
                success = await asyncio.wait_for(load_finished, timeout=30.0)
                if success:
                    # Verify we're not on about:blank
                    current_url = self.page.url().toString()
                    if current_url == "about:blank":
                        logger.error("Page loaded but stuck on about:blank")
                        return False
                    
                    # Additional wait for JavaScript
                    await asyncio.sleep(2)
                    logger.info(f"Successfully loaded: {current_url}")
                    return True
                
                logger.error("Page load reported failure")
                return False
                
            except asyncio.TimeoutError:
                logger.error("Page load timed out")
                return False
            finally:
                # Clean up
                self.page.loadFinished.disconnect(handle_load_finished)
                
        except Exception as e:
            logger.error(f"Error navigating to URL: {str(e)}")
            return False
            
    async def get_visible_text(self) -> str:
        """Extract visible text content from the page."""
        html = await self._run_javascript("""
            (function() {
                function isVisible(element) {
                    const style = window.getComputedStyle(element);
                    return style.display !== 'none' && 
                           style.visibility !== 'hidden' && 
                           style.opacity !== '0';
                }
                
                function getVisibleText(element) {
                    if (!isVisible(element)) return '';
                    
                    let text = '';
                    for (let child of element.childNodes) {
                        if (child.nodeType === 3) { // Text node
                            text += child.textContent.trim() + ' ';
                        } else if (child.nodeType === 1) { // Element node
                            text += getVisibleText(child);
                        }
                    }
                    return text;
                }
                
                return getVisibleText(document.body);
            })()
        """)
        return html or ""
            
    async def click_element(self, selector: str) -> bool:
        """Click an element using enhanced detection and selection strategies."""
        try:
            logger.info(f"Attempting to click element with selector: {selector}")
            
            script = """
            (function() {
                function findClickableElement(targetSelector) {
                    // Try the direct selector first
                    let element = document.querySelector(targetSelector);
                    
                    // If not found or not visible, try common alternatives
                    if (!element || element.offsetParent === null) {
                        const alternatives = [
                            'input[type="submit"]',
                            'button[type="submit"]',
                            'button[aria-label*="search" i]',
                            'input[aria-label*="search" i]',
                            '[role="button"]'
                        ];
                        
                        for (const alt of alternatives) {
                            element = document.querySelector(alt);
                            if (element && element.offsetParent !== null) break;
                        }
                    }
                    
                    return element;
                }
                
                const element = findClickableElement(%s);
                if (!element || element.offsetParent === null) return false;
                
                // Ensure element is in view
                element.scrollIntoView({behavior: 'instant', block: 'center'});
                
                // Try multiple click methods
                try {
                    element.click();
                } catch (e) {
                    // Fallback to custom event
                    const event = new MouseEvent('click', {
                        view: window,
                        bubbles: true,
                        cancelable: true
                    });
                    element.dispatchEvent(event);
                }
                
                return true;
            })()
            """ % json.dumps(selector)
            
            return await self._run_javascript(script)
            
        except Exception as e:
            logger.error(f"Error clicking element: {str(e)}")
            return False
        
    async def fill_input(self, selector: str, value: str) -> bool:
        """Fill an input field with the given value and submit if it's a search box."""
        script = """
        (function() {
            try {
                // Try multiple selectors for Google search
                const selectors = [
                    'input[name="q"]',  // Standard Google search input
                    'textarea[name="q"]',  // Modern Google search textarea
                    '#APjFqb',  // Google's specific search box ID
                    'input[type="text"]',  // Generic text input
                    'textarea',  // Generic textarea
                    document.querySelector('input[aria-label*="Search"]'),  // Aria-labeled search
                    document.querySelector('textarea[aria-label*="Search"]')  // Modern aria-labeled search
                ];
                
                let element = null;
                for (const sel of selectors) {
                    if (typeof sel === 'string') {
                        element = document.querySelector(sel);
                    } else {
                        element = sel;  // Direct element from aria query
                    }
                    if (element && element.offsetParent !== null) break;
                }
                
                if (!element) {
                    element = document.querySelector(%s);
                }
                
                if (element && element.offsetParent !== null) {
                    // Focus and clear the element
                    element.focus();
                    element.value = '';
                    
                    // Set new value
                    element.value = %s;
                    
                    // Trigger input events
                    element.dispatchEvent(new Event('input', { bubbles: true }));
                    element.dispatchEvent(new Event('change', { bubbles: true }));
                    
                    // Find and submit the form
                    const form = element.closest('form');
                    if (form) {
                        form.submit();
                        return true;
                    }
                    
                    // If no form, simulate Enter key
                    const enterEvent = new KeyboardEvent('keypress', {
                        key: 'Enter',
                        code: 'Enter',
                        keyCode: 13,
                        which: 13,
                        bubbles: true
                    });
                    element.dispatchEvent(enterEvent);
                    
                    // Also try clicking the search button if available
                    const searchButton = document.querySelector('input[type="submit"], button[type="submit"], button[aria-label*="search" i]');
                    if (searchButton) {
                        searchButton.click();
                    }
                    
                    return true;
                }
                return false;
            } catch (e) {
                console.error('Error:', e);
                return false;
            }
        })()
        """ % (json.dumps(selector), json.dumps(value))
        
        return await self._run_javascript(script)
        
    async def wait_for_element(self, selector: str, timeout: int = 5000) -> bool:
        """Wait for an element to appear on the page."""
        script = f"""
        (function() {{
            return new Promise((resolve) => {{
                if (document.querySelector({json.dumps(selector)})) {{
                    resolve(true);
                    return;
                }}
                
                const observer = new MutationObserver((mutations, obs) => {{
                    if (document.querySelector({json.dumps(selector)})) {{
                        obs.disconnect();
                        resolve(true);
                    }}
                }});
                
                observer.observe(document.body, {{
                    childList: true,
                    subtree: true
                }});
                
                setTimeout(() => {{
                    observer.disconnect();
                    resolve(false);
                }}, {timeout});
            }});
        }})()
        """
        success = await self._run_javascript(script)
        if success:
            await asyncio.sleep(1)
        return success
        
    async def _wait_for_page_load(self, timeout: int = 10000) -> bool:
        """Wait for page load to complete."""
        try:
            # Create a future to track load finished
            load_finished = asyncio.Future()
            
            def handle_load_finished(ok):
                if not load_finished.done():
                    load_finished.set_result(ok)
            
            # Connect the loadFinished signal
            self.page.loadFinished.connect(handle_load_finished)
            
            try:
                success = await asyncio.wait_for(load_finished, timeout=timeout/1000.0)
                if success:
                    # Additional wait for JavaScript to initialize
                    await asyncio.sleep(1)
                return success
            except asyncio.TimeoutError:
                return False
            finally:
                # Disconnect the signal
                self.page.loadFinished.disconnect(handle_load_finished)
                
        except Exception as e:
            logger.error(f"Error waiting for page load: {str(e)}")
            return False
        
    async def _run_javascript(self, script: str, timeout: int = 5000) -> Any:
        """Execute JavaScript and return the result."""
        try:
            # Create a future for the result
            future = asyncio.Future()
            
            def callback(result):
                if not future.done():
                    future.set_result(result)
            
            # Run the JavaScript
            self.page.runJavaScript(script, callback)
            
            # Wait for result with timeout
            try:
                return await asyncio.wait_for(future, timeout=timeout/1000.0)
            except asyncio.TimeoutError:
                logger.error("JavaScript execution timed out")
                return None
                
        except Exception as e:
            logger.error(f"Error executing JavaScript: {str(e)}")
            return None

    async def analyze_page_structure(self) -> Dict[str, Any]:
        """Enhanced page structure analysis."""
        try:
            html = await self.get_visible_text()
            processed = await self.enhancements.process_page_content(html)
            
            return {
                "url": self.page.url().toString(),
                "title": await self._run_javascript("return document.title;"),
                "processed_content": processed,
                "structure": {
                    "sections": processed.get("sections", {}),
                    "validated": processed.get("validated", {}),
                    "comprehensive": processed.get("comprehensive", {})
                }
            }
        except Exception as e:
            logger.error(f"Error analyzing page structure: {str(e)}")
            return {}

    async def find_best_element(self, goal: str, page_structure: Dict[str, Any]) -> Optional[str]:
        """Find the best matching element for the given goal using enhanced analysis."""
        try:
            # Use content processor to extract relevant sections
            content = await self.get_visible_text()
            processed = await self.enhancements.process_page_content(content)
            
            # Analyze page structure with enhanced context
            elements = page_structure.get('interactive', [])
            if not elements:
                return None
            
            # Score elements using result analyzer
            scored_elements = []
            for element in elements:
                element_text = f"{element.get('text', '')} {element.get('ariaLabel', '')}"
                score = self.enhancements.result_analyzer.score_result(
                    '',  # No URL needed for element scoring
                    element_text,
                    goal
                )
                scored_elements.append((element, score))
            
            # Sort by score and return best match
            scored_elements.sort(key=lambda x: x[1], reverse=True)
            if scored_elements and scored_elements[0][1] > 0.3:
                best_element = scored_elements[0][0]
                return (
                    f"#{best_element['id']}" if best_element.get('id')
                    else f".{'.'.join(best_element['classes'])}" if best_element.get('classes')
                    else None
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding best element: {str(e)}")
            return None

    def _generate_selector(self, element_info: Dict[str, Any]) -> str:
        """Generate a robust CSS selector for an element."""
        selectors = []
        
        # Try ID
        if element_info.get('id'):
            selectors.append(f"#{element_info['id']}")
        
        # Try specific attributes
        if element_info.get('href'):
            selectors.append(f"a[href*='{element_info['href'].split('?')[0]}']")
        
        if element_info.get('ariaLabel'):
            selectors.append(f"[aria-label='{element_info['ariaLabel']}']")
        
        # Try classes
        classes = element_info.get('classes', [])
        if classes:
            selectors.append(f".{'.'.join(classes)}")
        
        # Try role
        if element_info.get('role'):
            selectors.append(f"[role='{element_info['role']}']")
        
        # Try text content
        text = element_info.get('text', '').strip()
        if text:
            selectors.append(f"{element_info.get('tag', '*')}:contains('{text}')")
        
        return ' , '.join(selectors) if selectors else element_info.get('tag', '*')

    def _create_element_prompt(self, goal: str, elements_context: List[Dict[str, Any]]) -> str:
        """Create prompt for LLM to find best element."""
        return f"""
        Given this goal: "{goal}"
        
        And these visible page elements:
        {json.dumps(elements_context, indent=2)}
        
        Return a JSON object with:
        {{
            "selector": "the_best_selector",
            "action": "click_element or fill_input",
            "value": "input value if needed",
            "confidence": 0.0 to 1.0,
            "explanation": "why this element"
        }}
        
        Choose the element that best matches the goal based on:
        1. Text content similarity
        2. Semantic role (navigation, button, input, etc.)
        3. Location in page structure
        4. Accessibility labels
        
        Return ONLY the JSON object, no other text.
        """

    async def _handle_page_events(self):
        """Handle page events and state changes."""
        script = """
        (function() {
            // Track DOM mutations
            const observer = new MutationObserver((mutations) => {
                window._lastMutation = {
                    timestamp: Date.now(),
                    type: mutations[0].type,
                    target: mutations[0].target.tagName
                };
            });
            
            observer.observe(document.body, {
                childList: true,
                subtree: true,
                attributes: true
            });
            
            // Track network requests
            const originalFetch = window.fetch;
            window.fetch = async function(...args) {
                window._lastRequest = {
                    timestamp: Date.now(),
                    url: args[0]
                };
                return originalFetch.apply(this, args);
            };
            
            // Track user interactions
            document.addEventListener('click', (e) => {
                window._lastInteraction = {
                    timestamp: Date.now(),
                    type: 'click',
                    target: e.target.tagName
                };
            }, true);
            
            return true;
        })()
        """
        await self._run_javascript(script)

    async def _wait_for_stable_page(self, timeout: int = 5000):
        """Wait for page to become stable (no mutations, network requests, or interactions)."""
        script = """
        (function() {
            const now = Date.now();
            const events = [
                window._lastMutation,
                window._lastRequest,
                window._lastInteraction
            ].filter(Boolean);
            
            if (events.length === 0) return true;
            
            const lastEventTime = Math.max(...events.map(e => e.timestamp));
            return (now - lastEventTime) > 500; // 500ms of stability
        })()
        """
        
        start_time = asyncio.get_event_loop().time()
        while (asyncio.get_event_loop().time() - start_time) * 1000 < timeout:
            if await self._run_javascript(script):
                return True
            await asyncio.sleep(0.1)
        return False

    async def _plan_next_action(self, goal: str, page_state: Dict[str, Any]) -> Dict[str, Any]:
        """Plan next action using structured reasoning."""
        try:
            # For search tasks, first try to find the search input
            if "search" in goal.lower():
                search_element = await self._find_input_element(page_state)
                if search_element:
                    # Extract search query from goal
                    search_terms = goal.split("search for")[-1].strip().strip("'\"")
                    return {
                        "action": "type",
                        "target": search_element["selector"],
                        "value": search_terms,
                        "confidence": 1.0,
                        "reasoning": f"Found search input element using selector: {search_element['selector']}"
                    }
            
            # Fall back to general action planning
            prompt = {
                "goal": goal,
                "current_url": self.page.url().toString(),
                "page_state": {
                    "title": page_state.get("title", ""),
                    "visible_elements": [
                        {
                            "type": elem.get("type"),
                            "text": elem.get("text", ""),
                            "role": elem.get("role", ""),
                            "is_clickable": elem.get("tag") in ["a", "button"] or elem.get("role") in ["button", "link"]
                        }
                        for elem in page_state.get("interactive", [])
                        if elem.get("visible")
                    ],
                    "navigation_elements": [
                        {
                            "text": elem.get("text", ""),
                            "href": elem.get("href", "")
                        }
                        for elem in page_state.get("navigation", [])
                        if elem.get("visible")
                    ]
                }
            }
            
            prompt_text = f"""You are a web automation assistant.
            Analyze the current page state and goal to determine the next best action.
            Context: {json.dumps(prompt, indent=2)}
            Return a JSON object with:
            {{
                "action": "click|type|scroll",
                "target": "element text or selector",
                "value": "text to type (for type action)",
                "confidence": 0.0 to 1.0,
                "reasoning": "explanation of why this action was chosen"
            }}
            Important: Return ONLY the JSON object, no markdown formatting or comments."""
            
            response = await self.llm.generate_text(prompt_text)
            if not response:
                logger.error("No response from LLM")
                return None
                
            # Clean and parse response
            response = self._clean_llm_response(response)
            
            try:
                plan = json.loads(response)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {str(e)}")
                logger.error(f"Raw response: {response}")
                return None
                
            # Validate the plan structure
            required_fields = ['action', 'target', 'confidence']
            if not all(field in plan for field in required_fields):
                logger.error(f"Missing required fields in plan: {required_fields}")
                return None
                
            # Validate confidence threshold
            if plan.get("confidence", 0) > 0.7:
                return plan
            else:
                logger.warning(f"Action plan confidence too low: {plan.get('confidence')}")
                return None
                
        except Exception as e:
            logger.error(f"Error in action planning: {str(e)}")
            return None
            
    def _clean_llm_response(self, response: str) -> str:
        """Clean LLM response by removing markdown and comments."""
        if not response:
            return ""
            
        # Remove markdown code blocks
        response = response.strip()
        if response.startswith('```'):
            response = response.split('```')[1]
            if response.startswith('json'):
                response = response[4:]
        response = response.strip()
        
        # Remove comments
        response_lines = []
        in_multiline_comment = False
        for line in response.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            # Handle multi-line comments
            if '/*' in line:
                in_multiline_comment = True
                line = line[:line.index('/*')].strip()
            if '*/' in line:
                in_multiline_comment = False
                line = line[line.index('*/') + 2:].strip()
            if in_multiline_comment:
                continue
                
            # Handle single-line comments
            if '//' in line:
                line = line[:line.index('//')].strip()
            
            if line:
                response_lines.append(line)
                
        return ' '.join(response_lines)

    async def _find_input_element(self, page_state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find the main search input element using reliable selectors."""
        try:
            # Common Google search input selectors in order of preference
            search_selectors = [
                'textarea[name="q"]',  # Current Google search box
                'input[name="q"]',     # Alternative search box
                'input[type="text"]',  # Generic text input fallback
                'textarea[type="search"]'  # Generic search textarea
            ]
            
            script = """
            function findSearchInput() {
                const selectors = arguments[0];
                for (const selector of selectors) {
                    const element = document.querySelector(selector);
                    if (element && element.offsetParent !== null) {  // Check visibility
                        return {
                            selector: selector,
                            type: element.tagName.toLowerCase(),
                            visible: true
                        };
                    }
                }
                return null;
            }
            findSearchInput(arguments[0]);
            """
            
            # Create future for async result
            loop = asyncio.get_event_loop()
            future = loop.create_future()
            
            def handle_result(result):
                future.set_result(result)
                
            self.page.runJavaScript(script, search_selectors, handle_result)
            
            try:
                result = await asyncio.wait_for(future, timeout=5.0)
                if result:
                    return result
            except asyncio.TimeoutError:
                logger.warning("Search input detection timed out")
                
            return None
            
        except Exception as e:
            logger.error(f"Error finding input element: {str(e)}")
            return None

    async def _track_action_history(self, action: Dict[str, Any]):
        """Track action history to prevent loops."""
        if not hasattr(self, '_action_history'):
            self._action_history = []
            
        # Add action to history with timestamp
        self._action_history.append({
            **action,
            "timestamp": datetime.now().isoformat(),
            "url": self.page.url().toString()
        })
        
        # Check for loops (same action on same page multiple times)
        if len(self._action_history) >= 3:
            last_three = self._action_history[-3:]
            if all(
                a["action"] == last_three[0]["action"] and
                a["target"] == last_three[0]["target"] and
                a["url"] == last_three[0]["url"]
                for a in last_three
            ):
                raise Exception("Detected action loop - need to try different approach")

    async def _analyze_visual_elements(self) -> Dict[str, Any]:
        """Enhanced visual analysis of page elements."""
        script = """
        (function() {
            function getElementMetrics(element) {
                const rect = element.getBoundingClientRect();
                const style = window.getComputedStyle(element);
                const isVisible = (
                    rect.width > 0 &&
                    rect.height > 0 &&
                    style.display !== 'none' &&
                    style.visibility !== 'hidden' &&
                    style.opacity !== '0' &&
                    element.offsetParent !== null
                );
                
                return {
                    tag: element.tagName.toLowerCase(),
                    id: element.id,
                    classes: Array.from(element.classList),
                    text: element.textContent.trim(),
                    bounds: {
                        x: rect.left,
                        y: rect.top,
                        width: rect.width,
                        height: rect.height,
                        area: rect.width * rect.height
                    },
                    styles: {
                        backgroundColor: style.backgroundColor,
                        color: style.color,
                        fontSize: parseInt(style.fontSize),
                        fontWeight: style.fontWeight,
                        position: style.position,
                        display: style.display,
                        zIndex: parseInt(style.zIndex) || 0
                    },
                    attributes: {
                        role: element.getAttribute('role'),
                        ariaLabel: element.getAttribute('aria-label'),
                        href: element.getAttribute('href'),
                        type: element.getAttribute('type'),
                        name: element.getAttribute('name')
                    },
                    isVisible,
                    isClickable: (
                        element.tagName === 'A' ||
                        element.tagName === 'BUTTON' ||
                        element.onclick != null ||
                        element.getAttribute('role') === 'button' ||
                        element.getAttribute('role') === 'link' ||
                        element.classList.contains('btn') ||
                        element.classList.contains('button')
                    ),
                    isInteractive: (
                        element.tagName === 'INPUT' ||
                        element.tagName === 'SELECT' ||
                        element.tagName === 'TEXTAREA' ||
                        element.getAttribute('contenteditable') === 'true'
                    )
                };
            }
            
            function analyzeLayout() {
                const viewport = {
                    width: window.innerWidth,
                    height: window.innerHeight,
                    scrollX: window.scrollX,
                    scrollY: window.scrollY
                };
                
                // Analyze main content areas
                const contentAreas = [];
                const contentSelectors = [
                    'main',
                    '[role="main"]',
                    'article',
                    '.content',
                    '#content',
                    '.main',
                    '#main'
                ];
                
                for (const selector of contentSelectors) {
                    const elements = document.querySelectorAll(selector);
                    elements.forEach(element => {
                        if (getElementMetrics(element).isVisible) {
                            contentAreas.push(getElementMetrics(element));
                        }
                    });
                }
                
                // Analyze navigation
                const navAreas = [];
                const navSelectors = [
                    'nav',
                    '[role="navigation"]',
                    'header',
                    '.nav',
                    '#nav',
                    '.navigation',
                    '#navigation'
                ];
                
                for (const selector of navSelectors) {
                    const elements = document.querySelectorAll(selector);
                    elements.forEach(element => {
                        if (getElementMetrics(element).isVisible) {
                            navAreas.push(getElementMetrics(element));
                        }
                    });
                }
                
                // Find all interactive elements
                const interactiveElements = [];
                const interactiveSelectors = [
                    'a[href]',
                    'button',
                    'input',
                    'select',
                    'textarea',
                    '[role="button"]',
                    '[role="link"]',
                    '[role="tab"]',
                    '[role="menuitem"]',
                    '[onclick]',
                    '[class*="btn"]',
                    '[class*="button"]'
                ];
                
                for (const selector of interactiveSelectors) {
                    const elements = document.querySelectorAll(selector);
                    elements.forEach(element => {
                        const metrics = getElementMetrics(element);
                        if (metrics.isVisible) {
                            interactiveElements.push(metrics);
                        }
                    });
                }
                
                // Analyze text content
                const textNodes = [];
                const walk = document.createTreeWalker(
                    document.body,
                    NodeFilter.SHOW_TEXT,
                    null,
                    false
                );
                
                let node;
                while (node = walk.nextNode()) {
                    const text = node.textContent.trim();
                    if (text) {
                        const element = node.parentElement;
                        const metrics = getElementMetrics(element);
                        if (metrics.isVisible) {
                            textNodes.push({
                                text,
                                metrics
                            });
                        }
                    }
                }
                
                // Analyze visual hierarchy
                function getVisualImportance(metrics) {
                    const {bounds, styles} = metrics;
                    const centerWeight = 1 - (Math.abs(bounds.x - viewport.width/2) / viewport.width);
                    const sizeWeight = Math.min(1, bounds.area / (viewport.width * viewport.height));
                    const fontWeight = styles.fontSize / 16; // Relative to base font size
                    return (centerWeight + sizeWeight + fontWeight) / 3;
                }
                
                // Sort elements by visual importance
                const allElements = [...contentAreas, ...navAreas, ...interactiveElements];
                allElements.forEach(element => {
                    element.visualImportance = getVisualImportance(element);
                });
                
                allElements.sort((a, b) => b.visualImportance - a.visualImportance);
                
                return {
                    viewport,
                    layout: {
                        contentAreas,
                        navigationAreas: navAreas,
                        interactiveElements: allElements.filter(e => e.isClickable || e.isInteractive),
                        textContent: textNodes
                    },
                    visualHierarchy: allElements.slice(0, 10) // Top 10 most visually important elements
                };
            }
            
            return analyzeLayout();
        })()
        """
        
        try:
            result = await self._run_javascript(script)
            if not result:
                return {}
                
            # Group elements by region
            viewport_height = result['viewport']['height']
            regions = {
                'header': [],
                'main': [],
                'navigation': [],
                'footer': []
            }
            
            for element in result['layout']['interactiveElements']:
                y_pos = element['bounds']['y']
                if y_pos < viewport_height * 0.2:
                    regions['header'].append(element)
                elif y_pos > viewport_height * 0.8:
                    regions['footer'].append(element)
                else:
                    regions['main'].append(element)
                    
            # Add navigation elements to their own region
            regions['navigation'].extend(result['layout']['navigationAreas'])
            
            # Enhance with visual analysis
            return {
                'viewport': result['viewport'],
                'regions': regions,
                'visual_hierarchy': result['visualHierarchy'],
                'content_structure': {
                    'main_content': result['layout']['contentAreas'],
                    'text_nodes': result['layout']['textContent']
                },
                'interactive_elements': result['layout']['interactiveElements']
            }
            
        except Exception as e:
            logger.error(f"Error processing visual analysis: {str(e)}")
            return {}

    async def _get_current_screenshot(self) -> Optional[Any]:
        """Get current page screenshot in a format suitable for ML models."""
        try:
            if not self.view:
                return None
                
            # Capture screenshot
            pixmap = self.view.grab()
            if pixmap.isNull():
                return None
                
            # Convert QPixmap to QImage
            image = pixmap.toImage()
            
            # Convert QImage to bytes
            buffer = QBuffer()
            buffer.open(QBuffer.ReadWrite)
            image.save(buffer, "PNG")
            
            # Convert to PIL Image
            from PIL import Image
            import io
            pil_image = Image.open(io.BytesIO(buffer.data()))
            
            # Convert to RGB mode if needed
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
                
            return pil_image
            
        except Exception as e:
            logger.error(f"Error capturing screenshot: {str(e)}")
            return None

    async def _find_element_by_visual_similarity(self, target_text: str) -> Optional[Dict[str, Any]]:
        """Find element using visual and textual similarity with ML model support."""
        if not self.vision_enabled:
            return await self._find_element_by_text_similarity(target_text)
            
        try:
            # Get current page screenshot
            screenshot = await self._get_current_screenshot()
            if not screenshot:
                logger.warning("Failed to capture screenshot, falling back to text similarity")
                return await self._find_element_by_text_similarity(target_text)
            
            # Process image with DETR
            inputs = self.processor(images=screenshot, return_tensors="pt")
            with torch.no_grad():  # Add no_grad for inference
                outputs = self.vision_model(**inputs)
            
            # Get bounding boxes and scores
            probas = outputs.logits.softmax(-1)[0, :, :-1]
            keep = probas.max(-1).values > 0.7
            
            # Convert boxes to element coordinates
            boxes = outputs.pred_boxes[0, keep].detach()
            
            # Get visual elements
            visual_data = await self._analyze_visual_elements()
            if not visual_data:
                logger.warning("No visual elements found, falling back to text similarity")
                return await self._find_element_by_text_similarity(target_text)
            
            # Score elements based on both visual and text similarity
            scored_elements = []
            for element in visual_data.get("interactive_elements", []):
                if not element.get("text"):
                    continue
                    
                # Calculate text similarity
                text_score = self._calculate_text_similarity(
                    target_text.lower(),
                    element["text"].lower()
                )
                
                # Calculate visual score based on overlap with detected objects
                bounds = element["bounds"]
                element_box = torch.tensor([
                    bounds["x"], bounds["y"],
                    bounds["x"] + bounds["width"],
                    bounds["y"] + bounds["height"]
                ])
                
                # Calculate IoU with detected objects
                visual_score = max(
                    self._calculate_iou(element_box, box)
                    for box in boxes
                ) if len(boxes) > 0 else 0
                
                # Combined score with weighted components
                total_score = (text_score * 0.7) + (visual_score * 0.3)  # Prioritize text matching
                
                scored_elements.append({
                    **element,
                    "score": total_score,
                    "text_score": text_score,
                    "visual_score": visual_score
                })
            
            # Sort and filter results
            scored_elements.sort(key=lambda x: x["score"], reverse=True)
            
            # Log scoring details for debugging
            if scored_elements:
                top_element = scored_elements[0]
                logger.debug(f"Top element scores: text={top_element['text_score']:.2f}, visual={top_element['visual_score']:.2f}, total={top_element['score']:.2f}")
            
            # Return best match if above threshold
            if scored_elements and scored_elements[0]["score"] > 0.5:
                return scored_elements[0]
            
            logger.info("No high-confidence matches found, falling back to text similarity")
            return await self._find_element_by_text_similarity(target_text)
                
        except Exception as e:
            logger.error(f"Error in visual similarity search: {str(e)}")
            return await self._find_element_by_text_similarity(target_text)

    async def _find_element_by_text_similarity(self, target_text: str) -> Optional[Dict[str, Any]]:
        """Find element using enhanced text similarity with multiple fallback strategies."""
        try:
            visual_data = await self._analyze_visual_elements()
            if not visual_data:
                return None
            
            def normalize_text(text: str) -> str:
                """Normalize text for comparison."""
                import re
                # Remove special characters and extra whitespace
                text = re.sub(r'[^\w\s]', ' ', text.lower())
                # Normalize whitespace
                text = ' '.join(text.split())
                return text
            
            def get_element_score(element: Dict[str, Any]) -> float:
                """Calculate comprehensive element score."""
                if not element.get("text"):
                    return 0.0
                
                # Get element properties
                element_text = normalize_text(element["text"])
                target = normalize_text(target_text)
                
                # Calculate various similarity metrics
                exact_match = 1.0 if element_text == target else 0.0
                contains_match = 1.0 if target in element_text or element_text in target else 0.0
                word_similarity = self._calculate_text_similarity(target, element_text)
                
                # Check for partial matches
                target_words = set(target.split())
                element_words = set(element_text.split())
                partial_match = len(target_words.intersection(element_words)) / max(len(target_words), 1)
                
                # Get element importance factors
                is_clickable = element.get("isClickable", False)
                is_visible = element.get("isVisible", False)
                is_interactive = element.get("isInteractive", False)
                
                # Calculate position score (prefer elements in viewport)
                viewport_score = 0.0
                if "bounds" in element:
                    bounds = element["bounds"]
                    viewport_height = visual_data.get("viewport", {}).get("height", 0)
                    if viewport_height:
                        center_y = bounds["y"] + bounds["height"] / 2
                        viewport_score = 1.0 - min(abs(center_y - viewport_height/2) / viewport_height, 1.0)
                
                # Check accessibility attributes
                aria_score = 0.0
                if element.get("attributes"):
                    attrs = element["attributes"]
                    if attrs.get("ariaLabel") and normalize_text(attrs["ariaLabel"]) == target:
                        aria_score = 1.0
                    elif attrs.get("role") in ["button", "link", "menuitem"]:
                        aria_score = 0.5
                
                # Weighted scoring
                weights = {
                    "exact_match": 0.4,
                    "contains_match": 0.2,
                    "word_similarity": 0.2,
                    "partial_match": 0.1,
                    "clickable": 0.3,
                    "visible": 0.2,
                    "interactive": 0.2,
                    "viewport": 0.1,
                    "aria": 0.2
                }
                
                score = (
                    exact_match * weights["exact_match"] +
                    contains_match * weights["contains_match"] +
                    word_similarity * weights["word_similarity"] +
                    partial_match * weights["partial_match"] +
                    (1.0 if is_clickable else 0.0) * weights["clickable"] +
                    (1.0 if is_visible else 0.0) * weights["visible"] +
                    (1.0 if is_interactive else 0.0) * weights["interactive"] +
                    viewport_score * weights["viewport"] +
                    aria_score * weights["aria"]
                )
                
                return score
            
            # Score all interactive elements
            scored_elements = []
            for element in visual_data.get("interactive_elements", []):
                score = get_element_score(element)
                if score > 0:
                    scored_elements.append({
                        **element,
                        "score": score
                    })
            
            # If no interactive elements found, try all visible elements
            if not scored_elements:
                for element in visual_data.get("content_structure", {}).get("text_nodes", []):
                    if isinstance(element, dict) and element.get("metrics"):
                        score = get_element_score(element["metrics"])
                        if score > 0:
                            scored_elements.append({
                                **element["metrics"],
                                "score": score
                            })
            
            # Sort by score
            scored_elements.sort(key=lambda x: x["score"], reverse=True)
            
            # Log top matches for debugging
            for idx, element in enumerate(scored_elements[:3]):
                logger.debug(f"Match {idx + 1}: text='{element.get('text', '')}', score={element['score']:.2f}")
            
            # Return best match if above threshold
            if scored_elements and scored_elements[0]["score"] > 0.6:
                return scored_elements[0]
            
            return None
            
        except Exception as e:
            logger.error(f"Error in text similarity search: {str(e)}")
            return None

    def _calculate_iou(self, box1: torch.Tensor, box2: torch.Tensor) -> float:
        """Calculate Intersection over Union between two bounding boxes."""
        # Calculate intersection
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])
        
        intersection = max(0, x2 - x1) * max(0, y2 - y1)
        
        # Calculate union
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings."""
        # Simple word overlap similarity
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
            
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)

    async def _execute_action(self, action_plan: Dict[str, Any]) -> bool:
        """Execute a planned action."""
        try:
            action_type = action_plan.get("action")
            target = action_plan.get("target")
            value = action_plan.get("value")
            
            if not action_type or not target:
                logger.error("Invalid action plan - missing action or target")
                return False
            
            logger.info(f"Executing action: {action_type} on {target}")
            
            if action_type == "click":
                return await self.click_element(target)
                
            elif action_type == "type":
                if not value:
                    logger.error("Missing value for type action")
                    return False
                return await self.fill_input(target, value)
                
            elif action_type == "scroll":
                script = f"""
                window.scrollTo({{
                    top: document.querySelector({json.dumps(target)})?.getBoundingClientRect().top + window.scrollY - 100,
                    behavior: 'smooth'
                }});
                return true;
                """
                return await self._run_javascript(script)
            
            else:
                logger.error(f"Unknown action type: {action_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error executing action: {str(e)}")
            return False

    async def search_for_information(self, query: str, context: Dict = None) -> List[Dict]:
        """Enhanced search functionality with optimized queries and result processing."""
        try:
            # Enhance query with context
            enhanced_query = self.enhancements.enhance_search_query(query, context or {})
            logger.info(f"Enhanced query: {enhanced_query}")
            
            # Perform search (implementation depends on your search provider)
            raw_results = await self._perform_search(enhanced_query)
            
            # Process and analyze results
            processed_results = await self.enhancements.process_search_results(
                raw_results, enhanced_query
            )
            
            # Calculate relevance scores
            scores = self.enhancements.calculate_result_scores(raw_results, enhanced_query)
            
            # Combine results with scores
            scored_results = []
            for result, score in zip(raw_results, scores):
                if score > 0.3:  # Filter low relevance results
                    scored_results.append({
                        **result,
                        'relevance_score': score,
                        'processed_info': processed_results.get('processed_results', [])
                    })
            
            # Sort by relevance
            scored_results.sort(key=lambda x: x['relevance_score'], reverse=True)
            
            return scored_results
            
        except Exception as e:
            logger.error(f"Error in enhanced search: {str(e)}")
            return []
            
    async def _perform_search(self, query: str) -> List[Dict]:
        """Perform the actual search operation."""
        # This is a placeholder - implement your actual search logic here
        # For example, using Google Custom Search API, DuckDuckGo API, etc.
        return []

    def add_reasoning(self, title: str, description: str, details: List[str] = None):
        """Add a reasoning entry to the UI."""
        script = """
        function addReasoning(title, description, details) {
            const container = document.getElementById('agent-reasoning');
            if (!container) {
                const div = document.createElement('div');
                div.id = 'agent-reasoning';
                div.className = 'reasoning-log';
                document.body.appendChild(div);
                container = div;
            }
            
            const entry = document.createElement('div');
            entry.className = 'log-entry';
            
            const timestamp = document.createElement('div');
            timestamp.className = 'timestamp';
            timestamp.textContent = new Date().toLocaleTimeString();
            
            const titleDiv = document.createElement('div');
            titleDiv.className = 'log-title';
            titleDiv.textContent = title;
            
            const descDiv = document.createElement('div');
            descDiv.className = 'log-details';
            descDiv.textContent = description;
            
            entry.appendChild(timestamp);
            entry.appendChild(titleDiv);
            entry.appendChild(descDiv);
            
            if (details && details.length > 0) {
                const detailsList = document.createElement('ul');
                detailsList.style.margin = '5px 0';
                detailsList.style.paddingLeft = '20px';
                details.forEach(function(detail) {
                    const li = document.createElement('li');
                    li.textContent = detail;
                    detailsList.appendChild(li);
                });
                entry.appendChild(detailsList);
            }
            
            container.insertBefore(entry, container.firstChild);
            
            // Limit entries
            while (container.children.length > 10) {
                container.removeChild(container.lastChild);
            }
        }
        addReasoning(arguments[0], arguments[1], arguments[2]);
        """
        self.page.runJavaScript(script, title, description, details or [])
        
    def add_execution(self, title: str, description: str, details: List[str] = None):
        """Add an execution entry to the UI."""
        script = """
        function addExecution(title, description, details) {
            const container = document.getElementById('execution-log');
            if (!container) {
                const div = document.createElement('div');
                div.id = 'execution-log';
                div.className = 'execution-log';
                document.body.appendChild(div);
                container = div;
            }
            
            const entry = document.createElement('div');
            entry.className = 'log-entry';
            
            const timestamp = document.createElement('div');
            timestamp.className = 'timestamp';
            timestamp.textContent = new Date().toLocaleTimeString();
            
            const titleDiv = document.createElement('div');
            titleDiv.className = 'log-title';
            titleDiv.textContent = title;
            
            const descDiv = document.createElement('div');
            descDiv.className = 'log-details';
            descDiv.textContent = description;
            
            entry.appendChild(timestamp);
            entry.appendChild(titleDiv);
            entry.appendChild(descDiv);
            
            if (details && details.length > 0) {
                const detailsList = document.createElement('ul');
                detailsList.style.margin = '5px 0';
                detailsList.style.paddingLeft = '20px';
                details.forEach(function(detail) {
                    const li = document.createElement('li');
                    li.textContent = detail;
                    detailsList.appendChild(li);
                });
                entry.appendChild(detailsList);
            }
            
            container.insertBefore(entry, container.firstChild);
            
            // Limit entries
            while (container.children.length > 10) {
                container.removeChild(container.lastChild);
            }
        }
        addExecution(arguments[0], arguments[1], arguments[2]);
        """
        self.page.runJavaScript(script, title, description, details or [])
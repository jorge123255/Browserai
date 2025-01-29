# agent.py
from typing import Optional, Callable, Dict, Any
from PyQt5.QtWebEngineWidgets import QWebEnginePage
import asyncio
import json
from browser_tools import BrowserTools
from ollama_connection import OllamaConnection

class BrowserAgent:
    def __init__(self, page: QWebEnginePage):
        self.page = page
        self.tools = BrowserTools(page)
        self.llm = OllamaConnection()
        self.is_running = False
        self.log_callback: Optional[Callable[[str], None]] = None
        self._lock = asyncio.Lock()

    def set_log_callback(self, callback: Callable[[str], None]):
        self.log_callback = callback

    def log(self, message: str):
        if self.log_callback:
            self.log_callback(message)

    def stop(self):
        self.is_running = False

    async def execute_instruction(self, instruction: str):
        """Execute a user instruction using the LLM for guidance."""
        if not instruction.strip():
            self.log("No instruction provided")
            return

        async with self._lock:
            self.is_running = True
            try:
                await self._execute_with_context(instruction)
            except Exception as e:
                self.log(f"Error in execute_instruction: {str(e)}")
            finally:
                self.is_running = False
                self.log("Instruction execution complete")

    async def _execute_with_context(self, instruction: str):
        """Execute instruction with proper context management."""
        try:
            self.log("🤖 Starting new instruction...")
            self.log(f"🎯 Goal: {instruction}")
            
            # Get current page context
            page_text = await self.tools.get_visible_text()
            current_url = self.page.url().toString()
            
            self.log(f"📍 Current URL: {current_url}")

            # Format context for LLM
            context = {
                "instruction": instruction,
                "current_url": current_url,
                "page_content": page_text[:1000],  # Truncate for token limit
                "available_actions": [
                    "visit_url(url)",
                    "click_element(selector)",
                    "fill_input(selector, value)",
                    "get_element_info(selector)",
                    "wait_for_element(selector)"
                ]
            }

            while self.is_running:
                # Get LLM's next action
                self.log("\n🤔 Thinking about next action...")
                response = await self.llm.get_next_action(context)
                if not response:
                    self.log("❌ No response from LLM")
                    break

                try:
                    action = json.loads(response)
                    action_type = action.get("action")
                    explanation = action.get("explanation", "No explanation provided")

                    if not action_type:
                        self.log("❌ Invalid action format from LLM")
                        break

                    self.log(f"\n🔄 Next Action: {action_type}")
                    self.log(f"💭 Reasoning: {explanation}")
                    self.log("🛠️ Details: " + json.dumps(action, indent=2))
                    
                    success = await self._execute_action(action)

                    if not success:
                        self.log("❌ Action failed, stopping execution")
                        break
                    else:
                        self.log("✅ Action completed successfully")

                    # Update context with new page state
                    if self.is_running:
                        page_text = await self.tools.get_visible_text()
                        context["page_content"] = page_text[:1000]
                        new_url = self.page.url().toString()
                        if new_url != context["current_url"]:
                            self.log(f"📍 New URL: {new_url}")
                        context["current_url"] = new_url

                except json.JSONDecodeError:
                    self.log("❌ Invalid JSON response from LLM")
                    self.log(f"Raw response: {response}")
                    break
                except Exception as e:
                    self.log(f"❌ Error executing action: {str(e)}")
                    break

        except Exception as e:
            self.log(f"❌ Error in context execution: {str(e)}")
        finally:
            self.log("\n✨ Instruction execution complete")

    async def _execute_action(self, action: Dict[str, Any]) -> bool:
        """Execute a single action and return success status."""
        action_type = action.get("action")
        try:
            if action_type == "visit_url":
                return await self.tools.visit_url(action["url"])
            elif action_type == "click_element":
                return await self.tools.click_element(action["selector"])
            elif action_type == "fill_input":
                return await self.tools.fill_input(
                    action["selector"],
                    action["value"]
                )
            elif action_type == "wait_for_element":
                return await self.tools.wait_for_element(action["selector"])
            elif action_type == "get_element_info":
                info = await self.tools.get_element_info(action["selector"])
                self.log(f"Element info: {json.dumps(info, indent=2)}")
                return True
            else:
                self.log(f"Unknown action type: {action_type}")
                return False
        except Exception as e:
            self.log(f"Error in action execution: {str(e)}")
            return False

#You might want to set up threads or async calls so the UI remains responsive and the agent logic can run in the background.

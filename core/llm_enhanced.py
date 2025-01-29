from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import json
from loguru import logger
from .vision_enhanced import VisionEnhanced

class ActionPlan(BaseModel):
    """Model for LLM-generated action plan"""
    steps: List[Dict[str, Any]]
    explanation: str
    confidence: float
    
class LLMEnhanced(VisionEnhanced):
    """LLM-enhanced browser interaction"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.action_history = []
        
    async def plan_action(self, goal: str) -> Optional[ActionPlan]:
        """Generate action plan using LLM"""
        try:
            # Get current page state
            page_content = await self.get_visible_text()
            current_url = self.page.url().toString()
            
            # Prepare context for LLM
            context = {
                "goal": goal,
                "current_url": current_url,
                "page_content": page_content,
                "action_history": self.action_history[-5:],  # Last 5 actions
                "available_actions": [
                    "click",
                    "type",
                    "navigate",
                    "wait",
                    "extract"
                ]
            }
            
            # Get LLM response
            response = await self._get_llm_response(
                "plan_action",
                context
            )
            
            if not response:
                return None
                
            # Parse response
            return ActionPlan(**response)
            
        except Exception as e:
            logger.error(f"Error planning action: {str(e)}")
            return None
            
    async def execute_plan(self, plan: ActionPlan) -> bool:
        """Execute LLM-generated action plan"""
        try:
            for step in plan.steps:
                action_type = step["type"]
                
                if action_type == "click":
                    # Try vision-based click first
                    success = await self.click_with_vision(
                        step.get("description", "")
                    )
                    if not success:
                        # Fallback to selector
                        success = await self.click_element(
                            step.get("selector", "")
                        )
                        
                elif action_type == "type":
                    success = await self.fill_input(
                        step["selector"],
                        step["value"]
                    )
                    
                elif action_type == "navigate":
                    success = await self.visit_url(step["url"])
                    
                elif action_type == "wait":
                    await asyncio.sleep(step.get("seconds", 1))
                    success = True
                    
                elif action_type == "extract":
                    # Handle data extraction
                    data = await self._extract_data(step.get("selectors", {}))
                    success = bool(data)
                    
                else:
                    logger.warning(f"Unknown action type: {action_type}")
                    success = False
                    
                if not success:
                    logger.error(f"Step failed: {step}")
                    return False
                    
                # Record action
                self.action_history.append({
                    "type": action_type,
                    "details": step,
                    "success": success
                })
                
            return True
            
        except Exception as e:
            logger.error(f"Error executing plan: {str(e)}")
            return False
            
    async def _get_llm_response(self, 
                               task: str, 
                               context: Dict[str, Any]
                               ) -> Optional[Dict[str, Any]]:
        """Get response from LLM"""
        # TODO: Implement actual LLM call
        # For now, return dummy response
        if task == "plan_action":
            return {
                "steps": [
                    {
                        "type": "click",
                        "description": "Today's Deals link",
                        "selector": "#nav-xshop a[href*='deals']",
                        "explanation": "Click on Today's Deals to access deals page"
                    }
                ],
                "explanation": "Navigate to deals page",
                "confidence": 0.9
            }
        return None
        
    async def _extract_data(self, selectors: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Extract data from page using selectors"""
        try:
            data = {}
            for key, selector in selectors.items():
                element_info = await self.get_element_info(selector)
                if element_info:
                    data[key] = element_info.text
            return data if data else None
        except Exception as e:
            logger.error(f"Error extracting data: {str(e)}")
            return None 
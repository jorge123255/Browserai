from typing import List, Dict, Optional
from .result_analyzer import ResultAnalyzer
from .content_processor import ContentProcessor
from .information_synthesizer import InformationSynthesizer
from .navigation_planner import NavigationPlanner
from .search_optimizer import SearchOptimizer
from loguru import logger

class BrowserEnhancements:
    """Integration class for all browser automation enhancements."""
    
    def __init__(self, browser_window=None):
        self.window = browser_window
        self.result_analyzer = ResultAnalyzer()
        self.content_processor = ContentProcessor()
        self.info_synthesizer = InformationSynthesizer()
        self.navigation_planner = NavigationPlanner(browser_window=browser_window)
        self.search_optimizer = SearchOptimizer()
        
    def add_reasoning(self, source: str, message: str, details: List[str] = None):
        """Add reasoning step to history."""
        if self.window:
            if hasattr(self.window, 'add_reasoning'):
                self.window.add_reasoning(source, message, details)
            elif hasattr(self.window, 'browser_tools'):
                self.window.browser_tools.add_reasoning(source, message, details)
            
    def add_execution(self, message: str, status: str = "info"):
        """Add execution step to history."""
        if self.window:
            if hasattr(self.window, 'add_execution'):
                self.window.add_execution(message, status)
            elif hasattr(self.window, 'browser_tools'):
                self.window.browser_tools.add_execution(message, status)
        
    async def process_search_results(self, results: List[Dict], 
                                   query: str) -> Dict:
        """Process and enhance search results."""
        try:
            # Find best source
            best_url = self.result_analyzer.identify_best_source(results)
            
            # Process content from results
            processed_contents = []
            for result in results:
                if 'content' in result:
                    processed = self.content_processor.extract_relevant_sections(
                        result['content']
                    )
                    processed_contents.append({
                        'url': result.get('url', ''),
                        'processed': processed
                    })
            
            # Synthesize information
            synthesized = self.info_synthesizer.combine_sources(processed_contents)
            comprehensive = self.info_synthesizer.generate_comprehensive_view(
                synthesized
            )
            
            # Optimize future queries
            optimized_query = self.search_optimizer.adapt_to_results(
                query, results
            )
            
            return {
                'best_source': best_url,
                'processed_results': processed_contents,
                'synthesized_info': synthesized,
                'comprehensive_view': comprehensive,
                'optimized_query': optimized_query
            }
            
        except Exception as e:
            logger.error(f"Error processing search results: {str(e)}")
            return {
                'error': str(e),
                'original_results': results
            }
    
    async def plan_navigation(self, start_url: str, target_info: str,
                            page: 'WebPage') -> List[str]:
        """Plan and optimize navigation path."""
        try:
            # Get optimal navigation path
            path = await self.navigation_planner.optimize_path(
                start_url, target_info
            )
            
            # Handle dynamic content for current page
            await self.navigation_planner.handle_dynamic_content(page)
            
            return path
            
        except Exception as e:
            logger.error(f"Error planning navigation: {str(e)}")
            return [start_url]
    
    def enhance_search_query(self, query: str, context: Dict) -> str:
        """Enhance search query with context."""
        try:
            return self.search_optimizer.enhance_query(query, context)
        except Exception as e:
            logger.error(f"Error enhancing query: {str(e)}")
            return query
    
    async def validate_content(self, content: Dict, base_url: str = '') -> Dict:
        """Validate and verify content."""
        try:
            return self.content_processor.validate_information(content, base_url)
        except Exception as e:
            logger.error(f"Error validating content: {str(e)}")
            return content
    
    def calculate_result_scores(self, results: List[Dict], 
                              query: str) -> List[float]:
        """Calculate relevance scores for results."""
        try:
            scores = []
            for result in results:
                score = self.result_analyzer.score_result(
                    result.get('url', ''),
                    result.get('content', ''),
                    query
                )
                scores.append(score)
            return scores
        except Exception as e:
            logger.error(f"Error calculating scores: {str(e)}")
            return [0.0] * len(results)
    
    async def process_page_content(self, content: str, context: Dict = None) -> Dict:
        """Process and enhance page content."""
        try:
            # Start reasoning phase
            self.add_reasoning(
                "🧠 Browser AI",
                "Analyzing page content and structure",
                [
                    "Identifying key sections and elements",
                    "Looking for relevant information",
                    "Checking content validity"
                ]
            )
            logger.info("🤔 Reasoning: Analyzing page content structure and extracting relevant sections")
            
            # Ensure context is a dictionary
            context = context or {}
            
            # Special handling for Google search page
            if "google.com" in str(context.get('url', '')):
                return {
                    'sections': {
                        'search_box': {
                            'selector': 'textarea[name="q"]',
                            'type': 'input',
                            'purpose': 'search'
                        }
                    },
                    'validated': {'is_search_page': True},
                    'comprehensive': {'page_type': 'search', 'primary_action': 'input_search'},
                    'reasoning': ['Identified as Google search page', 'Located main search input'],
                    'execution': ['Extracted search box selector']
                }
            
            # Ensure content is a string
            if content is None:
                content = ""
            elif not isinstance(content, str):
                content = str(content)
                
            # Extract relevant sections for other pages
            sections = self.content_processor.extract_relevant_sections(content)
            self.add_execution("✓ Extracted relevant page sections")
            
            # Validate information if sections is a dictionary
            if isinstance(sections, dict):
                self.add_reasoning(
                    "🧠 Browser AI",
                    "Validating extracted information",
                    [
                        "Checking information accuracy",
                        "Verifying data completeness",
                        "Cross-referencing content"
                    ]
                )
                logger.info("🔍 Reasoning: Validating extracted information for accuracy and completeness")
                validated = await self.validate_content(sections)
                self.add_execution("✓ Validated content accuracy")
            else:
                validated = {}
            
            # Prepare data for comprehensive view
            data = {
                'raw_content': content,
                'sections': sections if isinstance(sections, dict) else {},
                'validated': validated,
                'context': context or {}
            }
            
            # Generate comprehensive view
            self.add_reasoning(
                "🧠 Browser AI",
                "Generating enhanced content view",
                [
                    "Combining validated information",
                    "Creating structured overview",
                    "Preparing final analysis"
                ]
            )
            logger.info("🔄 Execution: Generating comprehensive view of the processed content")
            
            try:
                comprehensive = self.info_synthesizer.generate_comprehensive_view(data)
                self.add_execution("✓ Generated comprehensive content view", "success")
            except Exception as e:
                logger.error(f"Error generating comprehensive view: {str(e)}")
                comprehensive = {'error': str(e)}
                self.add_execution("⚠ Error generating content view", "error")
            
            logger.info("✅ Execution: Successfully processed and enhanced page content")
            return {
                'sections': sections if isinstance(sections, dict) else {},
                'validated': validated,
                'comprehensive': comprehensive,
                'reasoning': [
                    'Analyzed page structure and extracted key sections',
                    'Validated information accuracy and completeness',
                    'Generated comprehensive view combining all data'
                ],
                'execution': [
                    'Extracted relevant sections from content',
                    'Validated extracted information',
                    'Generated enhanced content view'
                ]
            }
            
        except Exception as e:
            error_msg = f"❌ Execution Error: {str(e)}"
            logger.error(error_msg)
            self.add_execution(error_msg, "error")
            return {
                'error': str(e),
                'original_content': content,
                'reasoning': ['Error occurred during content processing'],
                'execution': [f'Failed with error: {str(e)}']
            } 
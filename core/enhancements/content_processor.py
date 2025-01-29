from typing import Dict, List, Optional
from bs4 import BeautifulSoup
import re
from datetime import datetime
import requests
from urllib.parse import urljoin
import json
import logging

logger = logging.getLogger(__name__)

class ContentProcessor:
    def __init__(self):
        self.code_patterns = [
            r'```[\s\S]*?```',  # Markdown code blocks
            r'<pre[\s\S]*?</pre>',  # HTML pre tags
            r'<code[\s\S]*?</code>'  # HTML code tags
        ]
        
    def extract_relevant_sections(self, page_content: str) -> Dict:
        if not isinstance(page_content, str):
            page_content = str(page_content)
            
        soup = BeautifulSoup(page_content, 'html.parser')
        
        return {
            'code_blocks': self._extract_code_blocks(page_content, soup),
            'api_docs': self._extract_api_docs(soup),
            'tutorial_steps': self._extract_tutorial_steps(soup),
            'version_info': self._extract_version_info(soup),
            'prerequisites': self._extract_prerequisites(soup)
        }
    
    def validate_information(self, content: Dict, base_url: str = '') -> Dict:
        validated = content.copy()
        
        # Timestamp verification
        validated['timestamp_valid'] = self._verify_timestamp(content)
        
        # Code validation
        if 'code_blocks' in content:
            validated['code_blocks'] = [
                block for block in content['code_blocks']
                if self._validate_code_syntax(block)
            ]
        
        # Link validation
        validated['broken_links'] = self._check_broken_links(content, base_url)
        
        # Version compatibility
        if 'version_info' in content:
            validated['version_compatible'] = self._check_version_compatibility(
                content['version_info']
            )
            
        return validated
    
    def _extract_code_blocks(self, content: str, soup: BeautifulSoup) -> List[str]:
        code_blocks = []
        
        # Extract from patterns
        for pattern in self.code_patterns:
            matches = re.findall(pattern, content)
            code_blocks.extend(matches)
        
        # Extract from specific HTML elements
        for code_elem in soup.find_all(['pre', 'code']):
            code_blocks.append(code_elem.get_text())
            
        return [self._clean_code_block(block) for block in code_blocks]
    
    def _extract_api_docs(self, soup: BeautifulSoup) -> Dict:
        api_sections = {}
        
        # Common API documentation patterns
        api_elements = soup.find_all(['section', 'div', 'article'], 
                                   class_=re.compile(r'api|docs?|reference'))
        
        for elem in api_elements:
            title = elem.find(['h1', 'h2', 'h3'])
            if title:
                api_sections[title.get_text().strip()] = elem.get_text().strip()
                
        return api_sections
    
    def _extract_tutorial_steps(self, soup: BeautifulSoup) -> List[Dict]:
        steps = []
        
        # Look for numbered sections or step-by-step guides
        step_elements = soup.find_all(['div', 'section'], 
                                    class_=re.compile(r'step|tutorial'))
        
        for idx, elem in enumerate(step_elements, 1):
            title = elem.find(['h1', 'h2', 'h3', 'h4'])
            steps.append({
                'step': idx,
                'title': title.get_text().strip() if title else f'Step {idx}',
                'content': elem.get_text().strip()
            })
            
        return steps
    
    def _extract_version_info(self, soup: BeautifulSoup) -> Dict:
        version_info = {}
        
        # Look for version numbers
        version_pattern = re.compile(r'v?\d+\.\d+(\.\d+)?')
        version_elements = soup.find_all(
            text=version_pattern
        )
        
        if version_elements:
            version_info['detected_versions'] = [
                version_pattern.search(v).group()
                for v in version_elements
                if version_pattern.search(v)
            ]
            
        return version_info
    
    def _extract_prerequisites(self, soup: BeautifulSoup) -> List[str]:
        prereq_sections = soup.find_all(
            ['div', 'section'], 
            class_=re.compile(r'prerequisites?|requirements?')
        )
        
        prerequisites = []
        for section in prereq_sections:
            items = section.find_all(['li', 'p'])
            prerequisites.extend([item.get_text().strip() for item in items])
            
        return prerequisites
    
    def _clean_code_block(self, block: str) -> str:
        # Remove markdown/HTML markers
        block = re.sub(r'```\w*\n?', '', block)
        block = re.sub(r'</?(pre|code)[^>]*>', '', block)
        return block.strip()
    
    def _verify_timestamp(self, content: Dict) -> bool:
        """Verify timestamp in content."""
        try:
            # Convert content to string safely
            if isinstance(content, dict):
                content_str = json.dumps(content)
            else:
                content_str = str(content)
                
            date_patterns = [
                r'\d{4}-\d{2}-\d{2}',
                r'\d{2}/\d{2}/\d{4}'
            ]
            
            for pattern in date_patterns:
                matches = re.findall(pattern, content_str)
                if matches:
                    try:
                        date = datetime.strptime(matches[0], '%Y-%m-%d')
                        return (datetime.now() - date).days < 365
                    except ValueError:
                        continue
                    
            return False
            
        except Exception as e:
            logger.error(f"Error verifying timestamp: {str(e)}")
            return False
    
    def _validate_code_syntax(self, code: str) -> bool:
        try:
            compile(code, '<string>', 'exec')
            return True
        except:
            return False  # Invalid Python syntax
    
    def _check_broken_links(self, content: Dict, base_url: str) -> List[str]:
        broken_links = []
        if isinstance(content, dict):
            content_str = str(content)
        else:
            content_str = str(content)
            
        urls = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+', content_str)
        
        for url in urls:
            if not url.startswith(('http://', 'https://')):
                url = urljoin(base_url, url)
            try:
                response = requests.head(url, timeout=5)
                if response.status_code >= 400:
                    broken_links.append(url)
            except:
                broken_links.append(url)
                
        return broken_links
    
    def _check_version_compatibility(self, version_info: Dict) -> bool:
        if not version_info or 'detected_versions' not in version_info:
            return True
            
        current_version = '3.8'  # Example current version
        for version in version_info['detected_versions']:
            try:
                if version.startswith('v'):
                    version = version[1:]
                if float(version.split('.')[0]) > float(current_version.split('.')[0]):
                    return False
            except:
                continue
                
        return True 
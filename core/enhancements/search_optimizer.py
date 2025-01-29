from typing import List, Dict, Set
from collections import Counter
import re
from difflib import SequenceMatcher

class SearchOptimizer:
    def __init__(self):
        self.context_keywords = {
            'version': ['version', 'v', 'release'],
            'skill_level': ['beginner', 'intermediate', 'advanced'],
            'framework': ['django', 'flask', 'fastapi', 'react', 'vue', 'angular'],
            'language': ['python', 'javascript', 'typescript', 'java', 'c++']
        }
        
        self.noise_words = {
            'how', 'to', 'what', 'is', 'are', 'the', 'in', 'on', 'at', 'for',
            'with', 'by', 'from', 'up', 'about', 'into', 'over', 'after'
        }
        
    def enhance_query(self, base_query: str, context: Dict) -> str:
        # Extract existing context
        existing_context = self._extract_context(base_query)
        
        # Add missing context
        enhanced_terms = []
        
        # Add version if specified
        if 'version' in context and not existing_context.get('version'):
            version = context['version']
            if not version.startswith('v'):
                version = f"v{version}"
            enhanced_terms.append(version)
        
        # Add skill level context
        if 'skill_level' in context and not existing_context.get('skill_level'):
            enhanced_terms.append(context['skill_level'])
        
        # Add framework context
        if 'framework' in context and not existing_context.get('framework'):
            enhanced_terms.append(context['framework'])
        
        # Add language context
        if 'language' in context and not existing_context.get('language'):
            enhanced_terms.append(context['language'])
        
        # Remove noise words and normalize
        clean_query = self._clean_query(base_query)
        
        # Combine everything
        if enhanced_terms:
            clean_query = f"{clean_query} {' '.join(enhanced_terms)}"
        
        return clean_query
    
    def adapt_to_results(self, query: str, results: List[Dict]) -> str:
        if not results:
            return query
            
        # Analyze result relevance
        relevance_scores = self._analyze_result_relevance(query, results)
        avg_relevance = sum(relevance_scores) / len(relevance_scores)
        
        # Identify missing aspects
        missing_aspects = self._identify_missing_aspects(query, results)
        
        # Determine if query needs adjustment
        if avg_relevance < 0.3:  # Low relevance threshold
            return self._broaden_query(query)
        elif avg_relevance > 0.8:  # High relevance threshold
            return self._narrow_query(query)
        elif missing_aspects:
            return self._add_missing_aspects(query, missing_aspects)
            
        return query
    
    def _extract_context(self, query: str) -> Dict[str, str]:
        context = {}
        words = query.lower().split()
        
        for context_type, keywords in self.context_keywords.items():
            for word in words:
                if word in keywords:
                    context[context_type] = word
                    break
                    
        # Version number detection
        version_pattern = r'v?\d+\.\d+(\.\d+)?'
        version_match = re.search(version_pattern, query)
        if version_match:
            context['version'] = version_match.group()
            
        return context
    
    def _clean_query(self, query: str) -> str:
        # Convert to lowercase
        query = query.lower()
        
        # Remove noise words
        words = query.split()
        clean_words = [w for w in words if w not in self.noise_words]
        
        # Remove special characters
        clean_words = [re.sub(r'[^\w\s]', '', w) for w in clean_words]
        
        # Remove empty strings
        clean_words = [w for w in clean_words if w]
        
        return ' '.join(clean_words)
    
    def _analyze_result_relevance(self, query: str, 
                                results: List[Dict]) -> List[float]:
        query_terms = set(self._clean_query(query).split())
        scores = []
        
        for result in results:
            content = result.get('content', '').lower()
            title = result.get('title', '').lower()
            
            # Calculate term frequency in content
            content_terms = set(self._clean_query(content).split())
            title_terms = set(self._clean_query(title).split())
            
            # Weight title matches more heavily
            title_score = len(query_terms & title_terms) / len(query_terms) * 1.5
            content_score = len(query_terms & content_terms) / len(query_terms)
            
            # Combined score
            score = max(title_score, content_score)
            scores.append(min(score, 1.0))  # Cap at 1.0
            
        return scores
    
    def _identify_missing_aspects(self, query: str, 
                                results: List[Dict]) -> Set[str]:
        # Extract common terms from results
        result_terms = Counter()
        for result in results:
            content = result.get('content', '').lower()
            terms = set(self._clean_query(content).split())
            result_terms.update(terms)
            
        # Find frequent terms not in query
        query_terms = set(self._clean_query(query).split())
        common_terms = {term for term, count in result_terms.items() 
                       if count >= len(results) // 2}
        
        return common_terms - query_terms
    
    def _broaden_query(self, query: str) -> str:
        words = query.split()
        
        # Remove specific constraints
        words = [w for w in words if not any(c in w for c in '[]():"\'')]
        
        # Remove version numbers
        words = [w for w in words if not re.match(r'v?\d+\.\d+(\.\d+)?', w)]
        
        # Take core concepts (usually first 2-3 terms)
        return ' '.join(words[:2])
    
    def _narrow_query(self, query: str) -> str:
        words = query.split()
        
        # Add specific qualifiers based on query content
        qualifiers = []
        
        # Look for technical terms
        technical_pattern = r'\b[A-Z][a-zA-Z]*\b'
        technical_terms = re.findall(technical_pattern, query)
        if technical_terms:
            qualifiers.extend([f'"{term}"' for term in technical_terms])
        
        # Add exact phrase matching for multi-word concepts
        if len(words) > 2:
            phrases = [' '.join(words[i:i+2]) 
                      for i in range(len(words)-1)]
            best_phrase = max(phrases, 
                            key=lambda p: sum(1 for c in p if c.isupper()))
            qualifiers.append(f'"{best_phrase}"')
        
        return f"{query} {' '.join(qualifiers)}"
    
    def _add_missing_aspects(self, query: str, missing_aspects: Set[str]) -> str:
        # Sort aspects by relevance
        sorted_aspects = sorted(missing_aspects, 
                              key=lambda x: self._calculate_aspect_relevance(x, query),
                              reverse=True)
        
        # Add top 2 most relevant aspects
        important_aspects = sorted_aspects[:2]
        
        return f"{query} {' '.join(important_aspects)}"
    
    def _calculate_aspect_relevance(self, aspect: str, query: str) -> float:
        # Calculate semantic similarity
        return SequenceMatcher(None, aspect.lower(), 
                             query.lower()).ratio() 
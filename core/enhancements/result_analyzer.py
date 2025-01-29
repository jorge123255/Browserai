from typing import List, Dict, Optional
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from urllib.parse import urlparse
import tldextract
from datetime import datetime

class ResultAnalyzer:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.domain_authority = {
            'github.com': 0.9,
            'stackoverflow.com': 0.85,
            'docs.python.org': 0.95,
            'developer.mozilla.org': 0.95
        }
        
    def score_result(self, url: str, content: str, query: str) -> float:
        domain_score = self._calculate_domain_score(url)
        relevance_score = self._calculate_relevance_score(content, query)
        freshness_score = self._calculate_freshness_score(content)
        
        weights = {
            'domain': 0.3,
            'relevance': 0.5,
            'freshness': 0.2
        }
        
        return (
            weights['domain'] * domain_score +
            weights['relevance'] * relevance_score +
            weights['freshness'] * freshness_score
        )
    
    def identify_best_source(self, results: List[Dict]) -> Optional[str]:
        if not results:
            return None
            
        scored_results = [
            (result['url'], self.score_result(
                result['url'], 
                result.get('content', ''), 
                result.get('query', '')
            ))
            for result in results
        ]
        
        return max(scored_results, key=lambda x: x[1])[0]
    
    def _calculate_domain_score(self, url: str) -> float:
        domain = tldextract.extract(url).registered_domain
        return self.domain_authority.get(domain, 0.5)
    
    def _calculate_relevance_score(self, content: str, query: str) -> float:
        if not content or not query:
            return 0.0
        try:
            tfidf_matrix = self.vectorizer.fit_transform([content, query])
            return float(tfidf_matrix[0].dot(tfidf_matrix[1].T).toarray()[0][0])
        except:
            return 0.0
    
    def _calculate_freshness_score(self, content: str) -> float:
        # Simple timestamp detection - can be enhanced
        current_year = datetime.now().year
        if str(current_year) in content or str(current_year-1) in content:
            return 1.0
        elif str(current_year-2) in content:
            return 0.7
        return 0.3 
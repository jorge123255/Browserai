from typing import List, Dict, Set
from collections import defaultdict
import networkx as nx
from difflib import SequenceMatcher

class InformationSynthesizer:
    def __init__(self):
        self.knowledge_graph = nx.DiGraph()
        self.seen_content = set()
        
    def combine_sources(self, sources: List[Dict]) -> Dict:
        combined_data = {
            'content': [],
            'code_examples': [],
            'references': set(),
            'metadata': defaultdict(list)
        }
        
        for source in sources:
            self._process_source(source, combined_data)
            
        return self._finalize_combined_data(combined_data)
    
    def generate_comprehensive_view(self, data: Dict) -> Dict:
        # Build knowledge hierarchy
        hierarchy = self._build_concept_hierarchy(data)
        
        # Find and link related topics
        related_topics = self._find_related_topics(data)
        
        # Identify gaps
        knowledge_gaps = self._identify_knowledge_gaps(data)
        
        # Find additional resources
        additional_resources = self._suggest_additional_resources(data)
        
        return {
            'hierarchy': hierarchy,
            'related_topics': related_topics,
            'knowledge_gaps': knowledge_gaps,
            'additional_resources': additional_resources,
            'original_data': data
        }
    
    def _process_source(self, source: Dict, combined_data: Dict) -> None:
        # Extract unique content
        content = source.get('content', '')
        if content and self._is_unique_content(content):
            combined_data['content'].append({
                'text': content,
                'source': source.get('url', 'unknown'),
                'timestamp': source.get('timestamp')
            })
            self.seen_content.add(self._get_content_hash(content))
        
        # Process code examples
        if 'code_examples' in source:
            self._merge_code_examples(source['code_examples'], 
                                   combined_data['code_examples'])
        
        # Add references
        if 'url' in source:
            combined_data['references'].add(source['url'])
        
        # Merge metadata
        for key, value in source.get('metadata', {}).items():
            if value not in combined_data['metadata'][key]:
                combined_data['metadata'][key].append(value)
    
    def _finalize_combined_data(self, data: Dict) -> Dict:
        # Remove duplicates while preserving order
        data['content'] = self._remove_duplicate_content(data['content'])
        data['code_examples'] = self._remove_duplicate_code(data['code_examples'])
        
        # Convert sets to lists for JSON serialization
        data['references'] = list(data['references'])
        
        # Add synthesis metadata
        data['synthesis_metadata'] = {
            'num_sources': len(data['references']),
            'content_pieces': len(data['content']),
            'code_examples': len(data['code_examples'])
        }
        
        return dict(data)
    
    def _build_concept_hierarchy(self, data: Dict) -> Dict:
        hierarchy = {'root': []}
        current_path = []
        
        for content in data.get('content', []):
            concepts = self._extract_concepts(content['text'])
            self._add_to_hierarchy(hierarchy['root'], concepts, content)
            
        return hierarchy
    
    def _find_related_topics(self, data: Dict) -> List[Dict]:
        topics = []
        content_text = ' '.join(c['text'] for c in data.get('content', []))
        
        # Extract potential related topics
        extracted_topics = self._extract_topics(content_text)
        
        # Build relationships
        for topic in extracted_topics:
            related = self._find_topic_relationships(topic, extracted_topics)
            topics.append({
                'topic': topic,
                'related': related,
                'strength': len(related)
            })
            
        return sorted(topics, key=lambda x: x['strength'], reverse=True)
    
    def _identify_knowledge_gaps(self, data: Dict) -> List[str]:
        gaps = []
        expected_topics = self._get_expected_topics(data)
        
        content_text = ' '.join(c['text'] for c in data.get('content', []))
        found_topics = self._extract_topics(content_text)
        
        return list(expected_topics - set(found_topics))
    
    def _suggest_additional_resources(self, data: Dict) -> List[Dict]:
        suggestions = []
        gaps = self._identify_knowledge_gaps(data)
        
        for gap in gaps:
            suggestions.append({
                'topic': gap,
                'suggested_resources': [
                    f"docs.python.org/3/library/{gap.lower()}.html",
                    f"github.com/topics/{gap.lower()}",
                    f"stackoverflow.com/questions/tagged/{gap.lower()}"
                ]
            })
            
        return suggestions
    
    def _is_unique_content(self, content: str) -> bool:
        content_hash = self._get_content_hash(content)
        return content_hash not in self.seen_content
    
    def _get_content_hash(self, content: str) -> str:
        return content.strip().lower()[:50]
    
    def _merge_code_examples(self, new_examples: List, 
                           existing_examples: List) -> None:
        for example in new_examples:
            if not self._has_similar_code(example, existing_examples):
                existing_examples.append(example)
    
    def _has_similar_code(self, code: str, examples: List[str], 
                         threshold: float = 0.8) -> bool:
        return any(
            SequenceMatcher(None, code, ex).ratio() > threshold 
            for ex in examples
        )
    
    def _remove_duplicate_content(self, content_list: List[Dict]) -> List[Dict]:
        seen = set()
        unique_content = []
        
        for content in content_list:
            content_hash = self._get_content_hash(content['text'])
            if content_hash not in seen:
                seen.add(content_hash)
                unique_content.append(content)
                
        return unique_content
    
    def _remove_duplicate_code(self, code_list: List[str]) -> List[str]:
        unique_code = []
        for code in code_list:
            if not self._has_similar_code(code, unique_code):
                unique_code.append(code)
        return unique_code
    
    def _extract_concepts(self, text: str) -> List[str]:
        # Simple concept extraction - can be enhanced with NLP
        words = text.split()
        concepts = []
        
        for i in range(len(words)):
            if words[i][0].isupper() and len(words[i]) > 3:
                concepts.append(words[i])
                
        return concepts
    
    def _add_to_hierarchy(self, parent: List, concepts: List[str], 
                         content: Dict) -> None:
        if not concepts:
            return
            
        concept = concepts[0]
        remaining = concepts[1:]
        
        # Find or create concept node
        concept_node = None
        for node in parent:
            if node['name'] == concept:
                concept_node = node
                break
                
        if concept_node is None:
            concept_node = {
                'name': concept,
                'content': [],
                'children': []
            }
            parent.append(concept_node)
            
        concept_node['content'].append(content)
        self._add_to_hierarchy(concept_node['children'], remaining, content)
    
    def _extract_topics(self, text: str) -> Set[str]:
        # Simple topic extraction - can be enhanced with NLP
        words = text.split()
        return {w for w in words if len(w) > 4 and w[0].isupper()}
    
    def _find_topic_relationships(self, topic: str, 
                                all_topics: Set[str]) -> List[str]:
        return [t for t in all_topics if t != topic and 
                self._calculate_relationship_strength(topic, t) > 0.3]
    
    def _calculate_relationship_strength(self, topic1: str, 
                                      topic2: str) -> float:
        return SequenceMatcher(None, topic1.lower(), 
                             topic2.lower()).ratio()
    
    def _get_expected_topics(self, data: Dict) -> Set[str]:
        # This could be enhanced with domain-specific knowledge
        basic_topics = {'Installation', 'Usage', 'Configuration', 
                       'Examples', 'API', 'Testing'}
        
        # Add topics based on content type
        if any('code_examples' in d for d in data.get('content', [])):
            basic_topics.add('Implementation')
            
        if any('api' in d['text'].lower() for d in data.get('content', [])):
            basic_topics.add('Endpoints')
            
        return basic_topics 
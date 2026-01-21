"""
Semantic skill matching service with word embeddings and synonym detection.

Requirements: 3.4
"""

import math
from typing import Dict, List, Set, Tuple, Any
import logging

logger = logging.getLogger(__name__)

class SemanticMatcher:
    """Semantic skill matching with embeddings and synonyms"""
    
    def __init__(self):
        """Initialize semantic matcher"""
        # Skill synonyms and related terms
        self.skill_synonyms = {
            'javascript': ['js', 'ecmascript', 'node.js', 'nodejs'],
            'python': ['py', 'python3', 'python2'],
            'react': ['reactjs', 'react.js'],
            'angular': ['angularjs', 'angular.js'],
            'vue': ['vuejs', 'vue.js'],
            'database': ['db', 'databases', 'data storage'],
            'sql': ['mysql', 'postgresql', 'sqlite', 'mssql'],
            'nosql': ['mongodb', 'cassandra', 'dynamodb'],
            'cloud': ['aws', 'azure', 'gcp', 'google cloud'],
            'devops': ['ci/cd', 'deployment', 'infrastructure'],
            'machine learning': ['ml', 'ai', 'artificial intelligence'],
            'data science': ['analytics', 'statistics', 'data analysis'],
            'frontend': ['front-end', 'ui', 'user interface'],
            'backend': ['back-end', 'server-side', 'api'],
            'fullstack': ['full-stack', 'full stack']
        }
        
        # Skill relationships (related skills)
        self.skill_relationships = {
            'react': ['javascript', 'jsx', 'redux', 'webpack'],
            'angular': ['typescript', 'javascript', 'rxjs'],
            'vue': ['javascript', 'vuex', 'nuxt'],
            'django': ['python', 'orm', 'mvc'],
            'flask': ['python', 'jinja2', 'werkzeug'],
            'spring': ['java', 'mvc', 'dependency injection'],
            'express': ['javascript', 'node.js', 'middleware'],
            'tensorflow': ['python', 'machine learning', 'neural networks'],
            'pytorch': ['python', 'machine learning', 'deep learning'],
            'pandas': ['python', 'data analysis', 'numpy'],
            'numpy': ['python', 'scientific computing', 'arrays'],
            'docker': ['containerization', 'devops', 'kubernetes'],
            'kubernetes': ['docker', 'orchestration', 'devops'],
            'aws': ['cloud', 'ec2', 's3', 'lambda'],
            'azure': ['cloud', 'microsoft', 'devops'],
            'git': ['version control', 'github', 'gitlab']
        }
        
        # Simple word embeddings (in production, use pre-trained embeddings)
        self.embeddings = self._create_simple_embeddings()
        
        logger.info("Semantic matcher initialized")
    
    def _create_simple_embeddings(self) -> Dict[str, List[float]]:
        """Create simple skill embeddings based on categories and relationships"""
        embeddings = {}
        
        # Programming languages cluster
        prog_langs = ['python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'go', 'rust']
        for i, lang in enumerate(prog_langs):
            embeddings[lang] = [1.0, 0.8, 0.0, 0.0, i * 0.1]
        
        # Web frameworks cluster
        web_frameworks = ['react', 'angular', 'vue', 'django', 'flask', 'express', 'spring']
        for i, framework in enumerate(web_frameworks):
            embeddings[framework] = [0.8, 1.0, 0.2, 0.0, i * 0.1]
        
        # Databases cluster
        databases = ['mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch']
        for i, db in enumerate(databases):
            embeddings[db] = [0.0, 0.2, 1.0, 0.0, i * 0.1]
        
        # Cloud/DevOps cluster
        cloud_tools = ['aws', 'azure', 'docker', 'kubernetes', 'jenkins', 'terraform']
        for i, tool in enumerate(cloud_tools):
            embeddings[tool] = [0.0, 0.0, 0.2, 1.0, i * 0.1]
        
        # Data science cluster
        data_tools = ['pandas', 'numpy', 'tensorflow', 'pytorch', 'scikit-learn']
        for i, tool in enumerate(data_tools):
            embeddings[tool] = [0.6, 0.0, 0.0, 0.0, 1.0 + i * 0.1]
        
        return embeddings
    
    def calculate_semantic_similarity(self, skill1: str, skill2: str) -> float:
        """Calculate semantic similarity between two skills"""
        skill1_lower = skill1.lower()
        skill2_lower = skill2.lower()
        
        # Exact match
        if skill1_lower == skill2_lower:
            return 1.0
        
        # Check synonyms
        synonym_score = self._check_synonyms(skill1_lower, skill2_lower)
        if synonym_score > 0:
            return synonym_score
        
        # Check relationships
        relationship_score = self._check_relationships(skill1_lower, skill2_lower)
        if relationship_score > 0:
            return relationship_score
        
        # Use embeddings for similarity
        embedding_score = self._embedding_similarity(skill1_lower, skill2_lower)
        
        return embedding_score
    
    def _check_synonyms(self, skill1: str, skill2: str) -> float:
        """Check if skills are synonyms"""
        for canonical, synonyms in self.skill_synonyms.items():
            if (skill1 == canonical and skill2 in synonyms) or \
               (skill2 == canonical and skill1 in synonyms) or \
               (skill1 in synonyms and skill2 in synonyms):
                return 0.95  # High similarity for synonyms
        
        return 0.0
    
    def _check_relationships(self, skill1: str, skill2: str) -> float:
        """Check if skills are related"""
        # Check if skill1 is related to skill2
        if skill1 in self.skill_relationships:
            if skill2 in self.skill_relationships[skill1]:
                return 0.7  # Moderate similarity for related skills
        
        # Check if skill2 is related to skill1
        if skill2 in self.skill_relationships:
            if skill1 in self.skill_relationships[skill2]:
                return 0.7
        
        return 0.0
    
    def _embedding_similarity(self, skill1: str, skill2: str) -> float:
        """Calculate similarity using embeddings"""
        if skill1 not in self.embeddings or skill2 not in self.embeddings:
            return 0.0
        
        vec1 = self.embeddings[skill1]
        vec2 = self.embeddings[skill2]
        
        # Cosine similarity
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(a * a for a in vec2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        similarity = dot_product / (magnitude1 * magnitude2)
        return max(0.0, similarity)  # Ensure non-negative
    
    def find_similar_skills(self, target_skill: str, skill_pool: List[str], threshold: float = 0.5) -> List[Tuple[str, float]]:
        """Find skills similar to target skill from a pool"""
        similar_skills = []
        
        for skill in skill_pool:
            similarity = self.calculate_semantic_similarity(target_skill, skill)
            if similarity >= threshold:
                similar_skills.append((skill, similarity))
        
        # Sort by similarity (descending)
        similar_skills.sort(key=lambda x: x[1], reverse=True)
        
        return similar_skills
    
    def expand_skill_requirements(self, required_skills: List[str]) -> Dict[str, List[Tuple[str, float]]]:
        """Expand skill requirements with similar skills"""
        expanded = {}
        
        for skill in required_skills:
            # Start with the original skill
            expanded[skill] = [(skill, 1.0)]
            
            # Add synonyms
            skill_lower = skill.lower()
            for canonical, synonyms in self.skill_synonyms.items():
                if skill_lower == canonical:
                    for synonym in synonyms:
                        expanded[skill].append((synonym, 0.95))
                elif skill_lower in synonyms:
                    expanded[skill].append((canonical, 0.95))
                    for synonym in synonyms:
                        if synonym != skill_lower:
                            expanded[skill].append((synonym, 0.9))
            
            # Add related skills
            if skill_lower in self.skill_relationships:
                for related in self.skill_relationships[skill_lower]:
                    expanded[skill].append((related, 0.7))
        
        return expanded
    
    def calculate_enhanced_skill_match(self, candidate_skills: List[str], required_skills: List[str]) -> Dict[str, Any]:
        """Calculate enhanced skill match using semantic similarity"""
        if not required_skills:
            return {'score': 1.0, 'matches': [], 'partial_matches': []}
        
        candidate_skills_lower = [skill.lower() for skill in candidate_skills]
        required_skills_lower = [skill.lower() for skill in required_skills]
        
        exact_matches = []
        partial_matches = []
        total_score = 0.0
        
        for required_skill in required_skills_lower:
            best_match = None
            best_score = 0.0
            
            for candidate_skill in candidate_skills_lower:
                similarity = self.calculate_semantic_similarity(required_skill, candidate_skill)
                if similarity > best_score:
                    best_score = similarity
                    best_match = candidate_skill
            
            if best_score >= 0.9:
                exact_matches.append({
                    'required': required_skill,
                    'candidate': best_match,
                    'similarity': best_score
                })
            elif best_score >= 0.5:
                partial_matches.append({
                    'required': required_skill,
                    'candidate': best_match,
                    'similarity': best_score
                })
            
            total_score += best_score
        
        # Calculate overall score
        overall_score = total_score / len(required_skills) if required_skills else 1.0
        
        return {
            'score': min(overall_score, 1.0),
            'exact_matches': exact_matches,
            'partial_matches': partial_matches,
            'coverage': len(exact_matches) / len(required_skills) if required_skills else 1.0
        }
    
    def get_skill_context(self, skill: str) -> Dict[str, Any]:
        """Get contextual information about a skill"""
        skill_lower = skill.lower()
        
        context = {
            'skill': skill,
            'synonyms': [],
            'related_skills': [],
            'category': self._get_skill_category(skill_lower),
            'embedding_available': skill_lower in self.embeddings
        }
        
        # Find synonyms
        for canonical, synonyms in self.skill_synonyms.items():
            if skill_lower == canonical:
                context['synonyms'] = synonyms
                break
            elif skill_lower in synonyms:
                context['synonyms'] = [canonical] + [s for s in synonyms if s != skill_lower]
                break
        
        # Find related skills
        if skill_lower in self.skill_relationships:
            context['related_skills'] = self.skill_relationships[skill_lower]
        
        return context
    
    def _get_skill_category(self, skill: str) -> str:
        """Determine the category of a skill"""
        categories = {
            'programming': ['python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'go', 'rust'],
            'web': ['react', 'angular', 'vue', 'html', 'css', 'django', 'flask', 'express'],
            'database': ['mysql', 'postgresql', 'mongodb', 'redis', 'sql', 'nosql'],
            'cloud': ['aws', 'azure', 'gcp', 'docker', 'kubernetes'],
            'data': ['pandas', 'numpy', 'tensorflow', 'pytorch', 'machine learning']
        }
        
        for category, skills in categories.items():
            if skill in skills:
                return category
        
        return 'other'
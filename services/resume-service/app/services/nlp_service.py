"""
NLP Service for resume parsing and entity extraction.

Handles text processing, named entity recognition, and skill extraction.
Requirements: 2.1, 2.2, 2.6, 2.7
"""

try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    spacy = None

import re
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class NLPService:
    """Service for natural language processing of resume content"""
    
    def __init__(self):
        """Initialize NLP service with spaCy model"""
        if not SPACY_AVAILABLE:
            logger.warning("spaCy not available, using fallback NLP processing")
            self.nlp = None
        else:
            try:
                # Load English language model
                self.nlp = spacy.load("en_core_web_sm")
                
                # Add custom patterns for resume entities
                self._add_custom_patterns()
                
                logger.info("NLP service initialized successfully with spaCy")
                
            except OSError:
                logger.warning("spaCy English model not found. Using fallback processing.")
                self.nlp = None
        
        # Load skill taxonomy
        self.skill_taxonomy = self._load_skill_taxonomy()
    
    def _add_custom_patterns(self):
        """Add custom patterns for resume-specific entities"""
        if not self.nlp:
            return
            
        # Add patterns for phone numbers, emails, etc.
        phone_pattern = [
            {"SHAPE": "ddd-ddd-dddd"},
            {"SHAPE": "(ddd) ddd-dddd"},
            {"SHAPE": "ddd.ddd.dddd"},
            {"SHAPE": "dddddddddd"}
        ]
        
        # Add to entity ruler if available
        if "entity_ruler" not in self.nlp.pipe_names:
            ruler = self.nlp.add_pipe("entity_ruler", before="ner")
            patterns = [
                {"label": "PHONE", "pattern": phone_pattern[0]},
                {"label": "PHONE", "pattern": phone_pattern[1]},
            ]
            ruler.add_patterns(patterns)
    
    def _load_skill_taxonomy(self) -> Dict[str, List[str]]:
        """Load skill taxonomy with synonyms and categories"""
        return {
            "programming": [
                "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust",
                "php", "ruby", "swift", "kotlin", "scala", "r", "matlab", "sql"
            ],
            "web": [
                "html", "css", "react", "angular", "vue", "node.js", "express", "django",
                "flask", "spring", "laravel", "rails", "asp.net", "jquery"
            ],
            "database": [
                "mysql", "postgresql", "mongodb", "redis", "elasticsearch", "oracle",
                "sqlite", "cassandra", "dynamodb", "neo4j"
            ],
            "cloud": [
                "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ansible",
                "jenkins", "gitlab", "github actions", "circleci"
            ],
            "data": [
                "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch", "keras",
                "spark", "hadoop", "tableau", "power bi", "excel"
            ]
        }
    
    def extract_entities(self, text: str) -> Dict[str, Any]:
        """Extract named entities from resume text"""
        entities = {
            "names": [],
            "emails": [],
            "phones": [],
            "organizations": [],
            "locations": [],
            "dates": [],
            "skills": [],
            "education": [],
            "experience": []
        }
        
        if self.nlp:
            # Use spaCy for entity extraction
            doc = self.nlp(text)
            
            # Extract standard entities
            for ent in doc.ents:
                if ent.label_ == "PERSON":
                    entities["names"].append(ent.text.strip())
                elif ent.label_ == "ORG":
                    entities["organizations"].append(ent.text.strip())
                elif ent.label_ in ["GPE", "LOC"]:
                    entities["locations"].append(ent.text.strip())
                elif ent.label_ == "DATE":
                    entities["dates"].append(ent.text.strip())
        else:
            # Fallback: simple pattern matching
            # Extract names (simple heuristic)
            name_patterns = [
                r'^([A-Z][a-z]+ [A-Z][a-z]+)',  # First Last at start of line
                r'Name:?\s*([A-Z][a-z]+ [A-Z][a-z]+)',  # Name: First Last
            ]
            for pattern in name_patterns:
                matches = re.findall(pattern, text, re.MULTILINE)
                entities["names"].extend(matches)
        
        # Extract emails using regex (works with or without spaCy)
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        entities["emails"] = re.findall(email_pattern, text)
        
        # Extract phone numbers using regex
        phone_pattern = r'(\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})'
        phone_matches = re.findall(phone_pattern, text)
        entities["phones"] = [''.join(match) for match in phone_matches]
        
        # Extract skills
        entities["skills"] = self._extract_skills(text)
        
        # Extract education and experience sections
        entities["education"] = self._extract_education(text)
        entities["experience"] = self._extract_experience(text)
        
        return entities
    
    def _extract_skills(self, text: str) -> List[Dict[str, Any]]:
        """Extract and normalize skills from text"""
        text_lower = text.lower()
        found_skills = []
        
        for category, skills in self.skill_taxonomy.items():
            for skill in skills:
                if skill.lower() in text_lower:
                    found_skills.append({
                        "skill": skill,
                        "category": category,
                        "confidence": 0.9  # Simple confidence score
                    })
        
        # Remove duplicates
        seen = set()
        unique_skills = []
        for skill in found_skills:
            key = (skill["skill"], skill["category"])
            if key not in seen:
                seen.add(key)
                unique_skills.append(skill)
        
        return unique_skills
    
    def _extract_education(self, text: str) -> List[Dict[str, Any]]:
        """Extract education information"""
        education = []
        
        # Common degree patterns
        degree_patterns = [
            r'(bachelor|master|phd|doctorate|associate).*?(?:degree|of|in)\s+([^\n]+)',
            r'(b\.?s\.?|m\.?s\.?|m\.?a\.?|ph\.?d\.?|b\.?a\.?)\s+(?:in\s+)?([^\n]+)',
        ]
        
        for pattern in degree_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                education.append({
                    "degree": match.group(1).title(),
                    "field": match.group(2).strip(),
                    "confidence": 0.8
                })
        
        return education
    
    def _extract_experience(self, text: str) -> List[Dict[str, Any]]:
        """Extract work experience information"""
        experience = []
        
        # Look for job titles and companies
        job_patterns = [
            r'(software engineer|developer|analyst|manager|director|consultant|specialist)\s+(?:at\s+)?([^\n]+)',
            r'([A-Z][a-z]+\s+[A-Z][a-z]+)\s+(?:at\s+)?([A-Z][^\n]+)',
        ]
        
        for pattern in job_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                experience.append({
                    "title": match.group(1).strip(),
                    "company": match.group(2).strip(),
                    "confidence": 0.7
                })
        
        return experience
    
    def calculate_confidence_score(self, extracted_data: Dict[str, Any]) -> float:
        """Calculate overall confidence score for extracted data"""
        scores = []
        
        # Score based on completeness
        if extracted_data.get("names"):
            scores.append(0.9)
        if extracted_data.get("emails"):
            scores.append(0.95)
        if extracted_data.get("phones"):
            scores.append(0.8)
        if extracted_data.get("skills"):
            scores.append(0.85)
        if extracted_data.get("education"):
            scores.append(0.8)
        if extracted_data.get("experience"):
            scores.append(0.9)
        
        return sum(scores) / len(scores) if scores else 0.0
    
    def normalize_skills(self, skills: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize and deduplicate skills"""
        normalized = []
        skill_map = {}
        
        for skill_data in skills:
            skill_name = skill_data["skill"].lower()
            
            # Check for synonyms and normalize
            normalized_name = self._normalize_skill_name(skill_name)
            
            if normalized_name not in skill_map:
                skill_map[normalized_name] = {
                    "skill": normalized_name,
                    "category": skill_data["category"],
                    "confidence": skill_data["confidence"],
                    "variants": [skill_data["skill"]]
                }
            else:
                # Update confidence and add variant
                existing = skill_map[normalized_name]
                existing["confidence"] = max(existing["confidence"], skill_data["confidence"])
                if skill_data["skill"] not in existing["variants"]:
                    existing["variants"].append(skill_data["skill"])
        
        return list(skill_map.values())
    
    def _normalize_skill_name(self, skill: str) -> str:
        """Normalize skill name to canonical form"""
        # Simple normalization rules
        normalizations = {
            "js": "javascript",
            "ts": "typescript", 
            "py": "python",
            "node": "node.js",
            "nodejs": "node.js",
            "react.js": "react",
            "reactjs": "react",
            "vue.js": "vue",
            "angular.js": "angular"
        }
        
        skill_lower = skill.lower()
        return normalizations.get(skill_lower, skill_lower)
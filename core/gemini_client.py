import json
import logging
from typing import List, Dict, Optional
from django.conf import settings
import google.generativeai as genai

logger = logging.getLogger(__name__)


class GeminiClient:
    """
    Wrapper for Google Gemini API.
    Handles all AI-powered investigation operations.
    """
    
    def __init__(self):
        """Initialize Gemini client with API key"""
        self.api_key = settings.GEMINI_API_KEY
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not set in settings")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL_DEFAULT)
        
        # Generation config
        self.generation_config = {
            'temperature': 0.7,
            'top_p': 0.95,
            'top_k': 40,
            'max_output_tokens': 8192,
        }
    
    def plan_investigation(self, query: str, focus_areas: List[str] = None, 
                          depth_level: str = 'moderate') -> Dict:
        """
        Generate investigation plan using Gemini.
        
        Args:
            query: The investigation question
            focus_areas: Optional areas to focus on
            depth_level: shallow/moderate/comprehensive
            
        Returns:
            {
                'strategy': List of research steps,
                'subtasks': List of subtask descriptions,
                'estimated_duration_minutes': int,
                'hypothesis': Initial hypothesis
            }
        """
        prompt = f"""You are an investigative AI agent. Create a detailed research plan for this investigation:

INVESTIGATION QUERY: {query}

FOCUS AREAS: {', '.join(focus_areas) if focus_areas else 'General investigation'}

DEPTH LEVEL: {depth_level}

Create a research plan with:
1. Initial hypothesis
2. 5-10 research subtasks (in order of execution)
3. Expected entities to discover (people, companies, locations, etc.)
4. Estimated duration in minutes

Respond ONLY with valid JSON in this exact format:
{{
    "hypothesis": "Your initial hypothesis here",
    "strategy": ["step 1", "step 2", "step 3"],
    "subtasks": [
        {{"type": "web_search", "description": "Search for X", "order": 1}},
        {{"type": "entity_extraction", "description": "Extract entities from Y", "order": 2}}
    ],
    "expected_entities": ["entity1", "entity2"],
    "estimated_duration_minutes": 120
}}"""

        try:
            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config
            )
            
            # Parse JSON response
            result = self._parse_json_response(response.text)
            logger.info(f"Generated investigation plan with {len(result.get('subtasks', []))} subtasks")
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating investigation plan: {e}")
            return self._fallback_plan(query)
    
    def execute_research_step(self, task_description: str, context: Dict) -> Dict:
        """
        Execute a single research step.
        
        Args:
            task_description: What to research
            context: Current investigation context (entities, relationships discovered so far)
            
        Returns:
            {
                'entities': List of discovered entities,
                'relationships': List of discovered relationships,
                'evidence': List of evidence found,
                'confidence': Overall confidence score,
                'next_steps': Suggested next actions
            }
        """
        prompt = f"""You are an investigative AI agent executing a research task.

TASK: {task_description}

CURRENT CONTEXT:
- Investigation Query: {context.get('query', '')}
- Entities Found So Far: {len(context.get('entities', []))}
- Relationships Found: {len(context.get('relationships', []))}

Based on this task, identify:
1. New entities (people, companies, locations, events, documents)
2. Relationships between entities
3. Evidence supporting your findings
4. Confidence level (0.0 to 1.0)

Respond ONLY with valid JSON:
{{
    "entities": [
        {{"name": "Entity Name", "type": "person|company|location|event|document", "description": "...", "confidence": 0.85}}
    ],
    "relationships": [
        {{"source": "Entity1", "target": "Entity2", "type": "owns|works_for|connected_to", "description": "...", "confidence": 0.9}}
    ],
    "evidence": [
        {{"title": "Evidence title", "source": "URL or description", "content": "Summary", "credibility": "high|medium|low"}}
    ],
    "confidence": 0.8,
    "next_steps": ["suggestion1", "suggestion2"]
}}"""

        try:
            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config
            )
            
            result = self._parse_json_response(response.text)
            logger.info(f"Research step found {len(result.get('entities', []))} entities")
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing research step: {e}")
            return {'entities': [], 'relationships': [], 'evidence': [], 'confidence': 0.0}
    
    def extract_entities(self, text: str, context: Dict = None) -> List[Dict]:
        """
        Extract entities from text.
        
        Args:
            text: Text to analyze
            context: Optional investigation context
            
        Returns:
            List of entities with type, name, description, confidence
        """
        prompt = f"""Extract all important entities from this text:

TEXT: {text}

Identify:
- People (full names, roles)
- Companies/Organizations
- Locations
- Events
- Documents/Reports
- Financial Instruments

Respond ONLY with valid JSON array:
[
    {{"name": "John Doe", "type": "person", "description": "CEO of TechCorp", "confidence": 0.95}},
    {{"name": "TechCorp Inc", "type": "company", "description": "Technology company", "confidence": 0.98}}
]"""

        try:
            response = self.model.generate_content(prompt)
            entities = self._parse_json_response(response.text)
            
            if not isinstance(entities, list):
                entities = entities.get('entities', [])
            
            return entities
            
        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
            return []
    
    def analyze_relationship(self, entity1_name: str, entity2_name: str, 
                           context: Dict) -> Optional[Dict]:
        """
        Determine relationship between two entities.
        
        Args:
            entity1_name: First entity name
            entity2_name: Second entity name
            context: Investigation context
            
        Returns:
            Relationship dict or None
        """
        prompt = f"""Analyze the relationship between these two entities:

ENTITY 1: {entity1_name}
ENTITY 2: {entity2_name}

CONTEXT: {context.get('query', '')}

Determine if there is a relationship and what type:
- owns
- works_for
- connected_to
- transacted_with
- located_in
- parent_of

Respond ONLY with valid JSON:
{{
    "has_relationship": true/false,
    "type": "relationship_type",
    "description": "Brief description",
    "confidence": 0.85,
    "evidence_summary": "Why you think this"
}}"""

        try:
            response = self.model.generate_content(prompt)
            result = self._parse_json_response(response.text)
            
            if result.get('has_relationship'):
                return result
            return None
            
        except Exception as e:
            logger.error(f"Error analyzing relationship: {e}")
            return None
    
    def evaluate_evidence(self, evidence_text: str, claim: str) -> Dict:
        """
        Evaluate how well evidence supports a claim.
        
        Args:
            evidence_text: The evidence content
            claim: The claim to evaluate
            
        Returns:
            Evaluation with support level, confidence, reasoning
        """
        prompt = f"""Evaluate this evidence:

CLAIM: {claim}

EVIDENCE: {evidence_text}

Does the evidence support, contradict, or remain neutral to the claim?

Respond ONLY with valid JSON:
{{
    "supports": true/false/null,
    "strength": 0.8,
    "credibility": "high|medium|low",
    "reasoning": "Explanation",
    "key_quotes": ["quote1", "quote2"]
}}"""

        try:
            response = self.model.generate_content(prompt)
            return self._parse_json_response(response.text)
            
        except Exception as e:
            logger.error(f"Error evaluating evidence: {e}")
            return {'supports': None, 'strength': 0.0, 'credibility': 'low'}
    
    def generate_report(self, investigation_data: Dict, report_type: str = 'executive_summary') -> str:
        """
        Generate investigation report.
        
        Args:
            investigation_data: All investigation data (entities, relationships, evidence)
            report_type: Type of report to generate
            
        Returns:
            Markdown formatted report
        """
        entities_summary = self._summarize_entities(investigation_data.get('entities', []))
        relationships_summary = self._summarize_relationships(investigation_data.get('relationships', []))
        
        prompt = f"""Generate a professional {report_type} investigation report.

INVESTIGATION: {investigation_data.get('title', 'Investigation Report')}
QUERY: {investigation_data.get('query', '')}

FINDINGS:
- Entities Discovered: {len(investigation_data.get('entities', []))}
{entities_summary}

- Relationships Discovered: {len(investigation_data.get('relationships', []))}
{relationships_summary}

- Evidence Collected: {len(investigation_data.get('evidence', []))}

Create a well-structured report in Markdown format with:
1. Executive Summary
2. Key Findings
3. Entity Profiles
4. Relationship Network
5. Evidence Assessment
6. Conclusions
7. Areas for Further Investigation

Use professional language and clear structure."""

        try:
            response = self.model.generate_content(
                prompt,
                generation_config={'max_output_tokens': 4096}
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return f"# Investigation Report\n\nError generating report: {str(e)}"
    
    def generate_thought(self, current_state: Dict, new_information: str) -> Dict:
        """
        Generate agent thought/reasoning for transparency.
        
        Args:
            current_state: Current investigation state
            new_information: New information discovered
            
        Returns:
            Thought chain entry
        """
        prompt = f"""You are an investigative AI agent. Generate your reasoning:

CURRENT HYPOTHESIS: {current_state.get('hypothesis', 'No hypothesis yet')}
NEW INFORMATION: {new_information}

Provide your reasoning:
1. What does this new information mean?
2. Does it support or contradict your hypothesis?
3. What should you investigate next?
4. Updated confidence level

Respond ONLY with valid JSON:
{{
    "thought_type": "observation|hypothesis|question|conclusion|correction",
    "content": "Your reasoning here",
    "confidence_before": 0.7,
    "confidence_after": 0.8,
    "next_action": "What to do next"
}}"""

        try:
            response = self.model.generate_content(prompt)
            return self._parse_json_response(response.text)
            
        except Exception as e:
            logger.error(f"Error generating thought: {e}")
            return {
                'thought_type': 'observation',
                'content': new_information,
                'confidence_before': 0.5,
                'confidence_after': 0.5
            }
    
    # Helper methods
    
    def _parse_json_response(self, text: str) -> Dict:
        """Parse JSON from Gemini response, handling markdown code blocks"""
        # Remove markdown code blocks if present
        text = text.strip()
        if text.startswith('```json'):
            text = text[7:]
        if text.startswith('```'):
            text = text[3:]
        if text.endswith('```'):
            text = text[:-3]
        
        text = text.strip()
        
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}\nText: {text[:200]}")
            raise
    
    def _fallback_plan(self, query: str) -> Dict:
        """Fallback investigation plan if Gemini fails"""
        return {
            'hypothesis': f'Investigating: {query}',
            'strategy': ['Analyze query', 'Research key terms', 'Identify entities'],
            'subtasks': [
                {'type': 'entity_extraction', 'description': 'Extract entities from query', 'order': 1},
                {'type': 'web_search', 'description': 'Search for relevant information', 'order': 2},
            ],
            'expected_entities': [],
            'estimated_duration_minutes': 60
        }
    
    def _summarize_entities(self, entities: List) -> str:
        """Create entity summary for reports"""
        if not entities:
            return "No entities discovered yet."
        
        summary = []
        entity_types = {}
        
        for entity in entities:
            entity_type = entity.get('entity_type', 'unknown')
            entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
        
        for entity_type, count in entity_types.items():
            summary.append(f"  - {entity_type.title()}: {count}")
        
        return '\n'.join(summary)
    
    def _summarize_relationships(self, relationships: List) -> str:
        """Create relationship summary for reports"""
        if not relationships:
            return "No relationships discovered yet."
        
        summary = []
        rel_types = {}
        
        for rel in relationships:
            rel_type = rel.get('relationship_type', 'unknown')
            rel_types[rel_type] = rel_types.get(rel_type, 0) + 1
        
        for rel_type, count in rel_types.items():
            summary.append(f"  - {rel_type.replace('_', ' ').title()}: {count}")
        
        return '\n'.join(summary)


# Singleton instance
gemini_client = GeminiClient()
import os
import json
from typing import Dict, List, Optional
import anthropic
from dataclasses import dataclass

@dataclass
class Requirement:
    """Represents an extracted requirement."""
    id: str
    description: str
    priority: str
    category: str
    source_text: str

class ClaudeQuestionAnalyzer:
    """Extracts requirements from user answers using Claude."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = "claude-3-opus-20240229"
        
    def analyze_answer(self, user_answer: str, context: Optional[Dict] = None) -> List[Requirement]:
        """Analyze user answer and extract requirements."""
        prompt = self._build_prompt(user_answer, context)
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return self._parse_requirements(response.content[0].text)
        except Exception as e:
            print(f"Error analyzing answer: {e}")
            return []
    
    def _build_prompt(self, user_answer: str, context: Optional[Dict]) -> str:
        """Build the prompt for Claude."""
        base_prompt = """Analyze the following user answer and extract all requirements.
        For each requirement, provide:
        - A clear description
        - Priority (high/medium/low)
        - Category (functional/non-functional/technical)
        - The exact text from the answer that generated this requirement
        
        Format your response as JSON with this structure:
        {
            "requirements": [
                {
                    "description": "...",
                    "priority": "...",
                    "category": "...",
                    "source_text": "..."
                }
            ]
        }
        
        User Answer:
        """
        
        if context:
            base_prompt += f"\nContext: {json.dumps(context)}\n"
        
        return base_prompt + user_answer
    
    def _parse_requirements(self, response_text: str) -> List[Requirement]:
        """Parse Claude's response into Requirement objects."""
        try:
            data = json.loads(response_text)
            requirements = []
            
            for i, req_data in enumerate(data.get("requirements", [])):
                req = Requirement(
                    id=f"req-{i+1}",
                    description=req_data.get("description", ""),
                    priority=req_data.get("priority", "medium"),
                    category=req_data.get("category", "functional"),
                    source_text=req_data.get("source_text", "")
                )
                requirements.append(req)
            
            return requirements
        except json.JSONDecodeError:
            print("Failed to parse Claude response as JSON")
            return []

class RequirementManager:
    """Manages requirements in the system."""
    
    def __init__(self, analyzer: ClaudeQuestionAnalyzer):
        self.analyzer = analyzer
        self.requirements: Dict[str, Requirement] = {}
    
    def process_user_answer(self, answer: str, context: Optional[Dict] = None) -> List[Requirement]:
        """Process a user answer and store extracted requirements."""
        extracted = self.analyzer.analyze_answer(answer, context)
        
        for req in extracted:
            self.requirements[req.id] = req
        
        return extracted
    
    def get_all_requirements(self) -> List[Requirement]:
        """Get all stored requirements."""
        return list(self.requirements.values())
    
    def get_requirement_by_id(self, req_id: str) -> Optional[Requirement]:
        """Get a specific requirement by ID."""
        return self.requirements.get(req_id)
    
    def export_to_json(self) -> str:
        """Export all requirements to JSON format."""
        reqs_data = [
            {
                "id": req.id,
                "description": req.description,
                "priority": req.priority,
                "category": req.category,
                "source_text": req.source_text
            }
            for req in self.requirements.values()
        ]
        return json.dumps({"requirements": reqs_data}, indent=2)

# Example usage
if __name__ == "__main__":
    analyzer = ClaudeQuestionAnalyzer()
    manager = RequirementManager(analyzer)
    
    user_answer = """
    We need a system that can handle at least 10,000 concurrent users.
    The response time should be under 200ms for API calls.
    It should support OAuth2 authentication.
    The UI needs to be responsive and work on mobile devices.
    """
    
    requirements = manager.process_user_answer(user_answer)
    
    print(f"Extracted {len(requirements)} requirements:")
    for req in requirements:
        print(f"- [{req.priority}] {req.description} ({req.category})")
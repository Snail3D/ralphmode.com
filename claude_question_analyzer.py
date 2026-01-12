import os
import json
from typing import Dict, List, Optional
import anthropic

class ClaudeQuestionAnalyzer:
    """Extracts requirements from user answers using Claude AI."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key required")
        self.client = anthropic.Anthropic(api_key=self.api_key)
    
    def extract_requirements(
        self, 
        question: str, 
        user_answer: str,
        context: Optional[Dict] = None
    ) -> Dict:
        """Extract requirements from user's answer to a question."""
        prompt = self._build_prompt(question, user_answer, context)
        
        try:
            response = self.client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )
            result = self._parse_response(response.content[0].text)
            result["success"] = True
            return result
        except Exception as e:
            return {"success": False, "error": str(e), "requirements": [], "metadata": {}}
    
    def _build_prompt(self, question: str, user_answer: str, context: Optional[Dict] = None) -> str:
        prompt = f"""Analyze the following user answer and extract requirements.

Question: {question}
User Answer: {user_answer}
"""
        if context:
            prompt += f"\nContext:\n{json.dumps(context, indent=2)}\n"
        
        prompt += """Return JSON with this structure:
{
  "requirements": [
    {"id": "unique_id", "description": "description", "priority": "high|medium|low", "category": "functional|non-functional|constraint"}
  ],
  "summary": "brief summary",
  "ambiguities": ["list of ambiguities"]
}"""
        return prompt
    
    def _parse_response(self, response_text: str) -> Dict:
        try:
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}") + 1
            if start_idx != -1 and end_idx > start_idx:
                return json.loads(response_text[start_idx:end_idx])
        except json.JSONDecodeError:
            pass
        return {"requirements": [], "summary": response_text, "ambiguities": [], "metadata": {"raw_response": response_text}}
    
    def batch_extract_requirements(self, qa_pairs: List[Dict[str, str]], context: Optional[Dict] = None) -> List[Dict]:
        """Extract requirements from multiple question-answer pairs."""
        return [self.extract_requirements(qa.get("question", ""), qa.get("answer", ""), context) for qa in qa_pairs]


def integrate_with_system(system_config: Dict) -> ClaudeQuestionAnalyzer:
    """Factory function to integrate ClaudeQuestionAnalyzer with existing systems."""
    analyzer = ClaudeQuestionAnalyzer(api_key=system_config.get("anthropic_api_key"))
    
    if "custom_prompt_template" in system_config:
        analyzer._build_prompt = lambda q, a, c=None: system_config["custom_prompt_template"].format(
            question=q, answer=a, context=json.dumps(c) if c else ""
        )
    return analyzer


if __name__ == "__main__":
    analyzer = ClaudeQuestionAnalyzer()
    question = "What features should our project management tool have?"
    answer = "We need task creation, assignment, deadlines, Slack integration, mobile-friendly UI, and data encryption."
    result = analyzer.extract_requirements(question, answer)
    print(json.dumps(result, indent=2))
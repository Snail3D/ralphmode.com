import anthropic
from typing import Dict, List, Optional
import json


class ClaudeQuestionAnalyzer:
    """Analyzes user answers using Claude to extract requirements."""
    
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
    
    def analyze_answer(self, question: str, answer: str, context: Optional[Dict] = None) -> Dict:
        prompt = self._build_prompt(question, answer, context)
        
        response = self.client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return self._parse_response(response.content[0].text)
    
    def _build_prompt(self, question: str, answer: str, context: Optional[Dict]) -> str:
        prompt = f"""Analyze the following user answer and extract requirements.

Question: {question}
User Answer: {answer}
"""
        if context:
            prompt += f"\nAdditional Context:\n{json.dumps(context, indent=2)}\n"
        
        prompt += """
Return your response in the following JSON format:
{
    "requirements": [
        {
            "type": "functional|non-functional|constraint",
            "description": "Clear description of the requirement",
            "priority": "high|medium|low",
            "source": "explicit|implicit"
        }
    ],
    "clarifications_needed": ["list of questions to clarify ambiguous requirements"],
    "summary": "Brief summary of the user's needs"
}
"""
        return prompt
    
    def _parse_response(self, response_text: str) -> Dict:
        try:
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            json_str = response_text[start:end]
            return json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            return {"error": "Failed to parse response", "raw_response": response_text}
    
    def batch_analyze(self, qa_pairs: List[Dict]) -> List[Dict]:
        results = []
        for pair in qa_pairs:
            result = self.analyze_answer(
                question=pair['question'],
                answer=pair['answer'],
                context=pair.get('context')
            )
            results.append(result)
        return results
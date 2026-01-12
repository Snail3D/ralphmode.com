from typing import Dict, List
from claude_question_analyzer import ClaudeQuestionAnalyzer


class RequirementExtractionService:
    """Service integrating Claude analysis with existing systems."""
    
    def __init__(self, api_key: str, storage_backend=None):
        self.analyzer = ClaudeQuestionAnalyzer(api_key)
        self.storage = storage_backend
    
    def process_user_response(self, user_id: str, question_id: str, answer: str) -> Dict:
        question = self._get_question(question_id)
        context = self._get_user_context(user_id)
        analysis = self.analyzer.analyze_answer(question, answer, context)
        self._store_analysis(user_id, question_id, analysis)
        return analysis
    
    def _get_question(self, question_id: str) -> str:
        if self.storage:
            return self.storage.get_question(question_id)
        return "What are your requirements?"
    
    def _get_user_context(self, user_id: str) -> Dict:
        if self.storage:
            return self.storage.get_user_context(user_id)
        return {}
    
    def _store_analysis(self, user_id: str, question_id: str, analysis: Dict):
        if self.storage:
            self.storage.store_analysis(user_id, question_id, analysis)
    
    def get_user_requirements(self, user_id: str) -> List[Dict]:
        if self.storage:
            return self.storage.get_user_requirements(user_id)
        return []